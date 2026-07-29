import logging
from typing import List, Dict, Tuple, Any
import numpy as np
from backend.app.config import settings
from backend.app.database.vector_db import vector_db
from backend.app.services.gemini_service import gemini_service
from backend.app.retrieval.dense import dense_search
from backend.app.retrieval.sparse import sparse_search
from backend.app.retrieval.fusion import reciprocal_rank_fusion

logger = logging.getLogger(__name__)

class RAGService:
    SYSTEM_INSTRUCTION = (
        "Bạn là một trợ lý pháp lý AI chuyên nghiệp. Nhiệm vụ của bạn là trả lời câu hỏi của người dùng "
        "một cách chính xác dựa trên các ngữ cảnh (context) pháp luật được cung cấp.\n\n"
        "Hãy tuân thủ nghiêm ngặt các nguyên tắc sau:\n"
        "1. Chỉ trả lời dựa vào thông tin có trong ngữ cảnh được cung cấp. Không tự ý thêm bớt, suy diễn ngoài ngữ cảnh.\n"
        "2. Nếu ngữ cảnh không chứa đủ thông tin để trả lời câu hỏi, hãy trả lời rõ ràng rằng: "
        "\"Tôi không tìm thấy thông tin phù hợp trong cơ sở dữ liệu pháp luật được cung cấp.\"\n"
        "3. Với mỗi thông tin đưa ra trong câu trả lời, bắt buộc phải trích dẫn nguồn rõ ràng trong ngoặc đơn bao gồm:\n"
        "   - Tên văn bản (ví dụ: Bộ luật Hình sự số 15/1999/QH10)\n"
        "   - Điều (ví dụ: Điều 98)\n"
        "   - Khoản (ví dụ: Khoản 1)\n"
        "   - Điểm (nếu có, ví dụ: Điểm a)\n"
        "   Ví dụ trích dẫn: (Quyết định số 27/2016/QĐ-UBND, Điều 4, Khoản 2, Điểm a).\n"
        "4. Trình bày câu trả lời rõ ràng, logic, đúng văn phong pháp lý, định dạng Markdown."
    )

    def format_embedding_text(self, chunk: Dict) -> str:
        """
        Formats raw chunk + metadata into a descriptive text representation for embedding.
        """
        metadata = chunk.get("metadata", {})
        doc_title = metadata.get("document_title") or ""
        
        hierarchy = metadata.get("hierarchy_path") or []
        hierarchy_str = " > ".join([str(h) for h in hierarchy if h])
        
        article_title = metadata.get("article_title") or ""
        text = chunk.get("text") or ""
        
        parts = [
            f"Văn bản: {doc_title}",
            f"Vị trí cấu trúc: {hierarchy_str}",
            f"Tiêu đề Điều: {article_title}",
            f"Nội dung điều khoản: {text}"
        ]
        return "\n".join(parts)

    def ingest_chunks(self, chunks: List[Dict]) -> int:
        """
        Prepares texts, generates embeddings, and saves to vector database.
        Returns the number of processed chunks.
        """
        if not chunks:
            return 0
        
        # Limit to 100 chunks for demo purposes
        chunks = chunks[:1000]
        
        logger.info(f"Ingesting {len(chunks)} chunks...")
        
        # 1. Format texts for embedding
        embedding_texts = [self.format_embedding_text(chunk) for chunk in chunks]
        
        # 2. Call Gemini API to get embeddings in batch
        embeddings_list = gemini_service.get_embeddings_batch(embedding_texts)
        embeddings_matrix = np.array(embeddings_list, dtype=np.float32)
        
        # 3. Save to VectorDB (.npy and json)
        vector_db.save(chunks, embeddings_matrix)
        
        # 4. Force sparse search index rebuild
        sparse_search.initialize()
        
        logger.info(f"Successfully saved {len(chunks)} chunks & embeddings.")
        return len(chunks)

    def query(self, user_query: str) -> Dict[str, Any]:
        """
        Full hybrid search + generation pipeline.
        """
        if vector_db.is_empty():
            return {
                "answer": "Cơ sở dữ liệu pháp luật hiện đang trống. Vui lòng thực hiện ingest dữ liệu trước.",
                "sources": []
            }

        # 1. Dense Search
        query_vector = gemini_service.get_embedding(user_query)
        dense_results = dense_search(query_vector, top_k=settings.DENSE_TOP_K)

        # 2. Sparse Search
        sparse_results = sparse_search.search(user_query, top_k=settings.SPARSE_TOP_K)

        # 3. Reciprocal Rank Fusion (RRF)
        fused_results = reciprocal_rank_fusion(
            dense_results, 
            sparse_results, 
            top_n=settings.RRF_TOP_N,
            k=settings.RRF_K
        )

        # 4. Construct context text for prompt
        contexts_text_list = []
        sources = []
        
        for idx, (chunk, score) in enumerate(fused_results):
            metadata = chunk.get("metadata", {})
            doc_title = metadata.get("document_title") or "N/A"
            article = metadata.get("article_title") or metadata.get("article_number") or "N/A"
            clause = metadata.get("clause_number") or "N/A"
            point = metadata.get("point") or ""
            text = chunk.get("text") or ""
            
            # Format display context
            context_item = (
                f"Tài liệu [{idx + 1}]:\n"
                f"- Tên văn bản: {doc_title}\n"
                f"- Điều: {article}\n"
                f"- Khoản: {clause}\n"
            )
            if point:
                context_item += f"- Điểm: {point}\n"
            context_item += f"- Nội dung: {text}\n"
            
            contexts_text_list.append(context_item)
            
            # Capture metadata details for api response
            sources.append({
                "chunk_id": chunk.get("chunk_id"),
                "document_title": doc_title,
                "article_title": metadata.get("article_title"),
                "article_number": metadata.get("article_number"),
                "clause_number": clause,
                "point": point if point else None,
                "text": text,
                "rrf_score": score
            })

        contexts_text = "\n\n".join(contexts_text_list)
        
        # 5. Build full prompt
        prompt = (
            f"Ngữ cảnh pháp luật được cung cấp:\n"
            f"=================================\n"
            f"{contexts_text}\n"
            f"=================================\n\n"
            f"Câu hỏi: {user_query}"
        )

        # 6. Generate answer using Gemini 2.5 Flash
        answer = gemini_service.generate_answer(
            prompt=prompt,
            system_instruction=self.SYSTEM_INSTRUCTION
        )

        return {
            "answer": answer,
            "sources": sources
        }

# Singleton instance of RAGService
rag_service = RAGService()
