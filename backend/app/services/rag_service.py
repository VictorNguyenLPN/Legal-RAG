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
        "Bạn là một trợ lý pháp lý AI chuyên nghiệp. Nhiệm vụ của bạn là hỗ trợ và trả lời các câu hỏi của người dùng một cách chính xác.\n\n"
        "Hãy tuân thủ các nguyên tắc sau:\n"
        "1. Đối với các câu hỏi về pháp luật: Chỉ trả lời dựa vào thông tin có trong ngữ cảnh (context) pháp luật được cung cấp. Không tự ý thêm bớt, suy diễn ngoài ngữ cảnh. "
        "Nếu ngữ cảnh pháp luật không chứa đủ thông tin để trả lời, hãy trả lời rõ ràng là: \"Tôi không tìm thấy thông tin phù hợp trong cơ sở dữ liệu pháp luật được cung cấp.\"\n"
        "2. Đối với các thông tin cá nhân của người dùng (như tên, tuổi, thông tin người dùng đã chia sẻ trực tiếp trong cuộc hội thoại) hoặc các câu chào hỏi, giao tiếp thông thường: "
        "Hãy trả lời một cách tự nhiên và chính xác dựa trên Lịch sử cuộc hội thoại được cung cấp, không áp dụng nguyên tắc từ chối của câu hỏi pháp luật.\n"
        "3. Với mỗi thông tin pháp lý đưa ra trong câu trả lời, bắt buộc phải trích dẫn nguồn rõ ràng trong ngoặc đơn bao gồm: Tên văn bản, Điều, Khoản, Điểm (ví dụ: (Bộ luật Hình sự số 15/1999/QH10, Điều 168, Khoản 1)).\n"
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
        chunks = chunks[:100]
        
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

    def condense_query(self, user_query: str, history: List[Dict[str, str]]) -> Tuple[str, Any]:
        """
        Condenses a user's follow-up query with the conversation history into a standalone query.
        Returns a tuple of (condensed_query, usage_metadata).
        """
        history_str = ""
        for msg in history:
            role_label = "Người dùng" if msg["role"] == "user" else "Trợ lý AI"
            history_str += f"{role_label}: {msg['content']}\n"
            
        prompt = (
            "Dựa vào lịch sử hội thoại pháp lý dưới đây và câu hỏi mới nhất của người dùng, "
            "hãy viết lại câu hỏi mới này thành một câu hỏi độc lập (standalone question) bằng tiếng Việt, "
            "đầy đủ ngữ cảnh để có thể dùng tìm kiếm trực tiếp trong cơ sở dữ liệu pháp luật. "
            "Không tự trả lời câu hỏi, không thêm bất kỳ văn bản giải thích hoặc dẫn nhập nào, "
            "chỉ trả về duy nhất câu hỏi đã được viết lại.\n\n"
            f"Lịch sử hội thoại:\n{history_str}\n"
            f"Câu hỏi mới nhất: {user_query}\n\n"
            "Câu hỏi độc lập:"
        )
        try:
            condensed, usage_metadata = gemini_service.generate_answer(prompt=prompt)
            condensed_clean = condensed.strip()
            if condensed_clean:
                # logger.info(f"Condensed query: '{user_query}' -> '{condensed_clean}'")
                return condensed_clean, usage_metadata
        except Exception as e:
            logger.error(f"Error in query condensation: {e}")
        return user_query, None

    def query(self, user_query: str, history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Full hybrid search + generation pipeline with history support.
        """
        if vector_db.is_empty():
            return {
                "answer": "Cơ sở dữ liệu pháp luật hiện đang trống. Vui lòng thực hiện ingest dữ liệu trước.",
                "sources": []
            }

        prompt_tokens = 0
        response_tokens = 0
        total_tokens = 0

        # 0. Condense query if chat history exists
        search_query = user_query
        if history:
            search_query, condense_metadata = self.condense_query(user_query, history)
            if condense_metadata:
                prompt_tokens += condense_metadata.prompt_token_count or 0
                response_tokens += condense_metadata.candidates_token_count or 0
                total_tokens += condense_metadata.total_token_count or 0

        # 1. Dense Search - retrieve a broader pool for reranking
        query_vector = gemini_service.get_embedding(search_query)
        dense_results = dense_search(query_vector, top_k=20)

        # 2. Sparse Search - retrieve a broader pool for reranking
        sparse_results = sparse_search.search(search_query, top_k=20)

        # 3. Reciprocal Rank Fusion (RRF) - merge into a candidate pool
        fused_candidates = reciprocal_rank_fusion(
            dense_results, 
            sparse_results, 
            top_n=15,
            k=settings.RRF_K
        )

        # 3b. Gemini Listwise Reranking - rank the candidates and choose top RRF_TOP_N
        candidates = [chunk for chunk, score in fused_candidates]
        reranked_ids = gemini_service.rerank(search_query, candidates, top_n=settings.RRF_TOP_N)
        
        # Map IDs back to chunks and assign scores based on new rank
        fused_results = []
        candidate_map = {c["chunk_id"]: c for c in candidates}
        for idx, cid in enumerate(reranked_ids):
            if cid in candidate_map:
                # Mock score decreasing with rank
                score = 1.0 - (idx * 0.05)
                fused_results.append((candidate_map[cid], score))


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
        
        # 5. Build conversation history text if present
        history_text = ""
        if history:
            history_text = "Lịch sử cuộc hội thoại trước đó:\n"
            for msg in history:
                role_label = "Người dùng" if msg["role"] == "user" else "Trợ lý AI"
                history_text += f"- {role_label}: {msg['content']}\n"
            history_text += "\n"

        # 6. Build full prompt
        prompt = (
            f"Ngữ cảnh pháp luật được cung cấp:\n"
            f"=================================\n"
            f"{contexts_text}\n"
            f"=================================\n\n"
            f"{history_text}"
            f"Câu hỏi tiếp theo của Người dùng: {user_query}"
        )

        # 7. Generate answer using Gemini 2.5 Flash
        answer, answer_metadata = gemini_service.generate_answer(
            prompt=prompt,
            system_instruction=self.SYSTEM_INSTRUCTION
        )
        if answer_metadata:
            prompt_tokens += answer_metadata.prompt_token_count or 0
            response_tokens += answer_metadata.candidates_token_count or 0
            total_tokens += answer_metadata.total_token_count or 0

        # print(answer)

        # Clear sources if the LLM states it cannot find the relevant information,
        # or if the response is purely conversational and contains no legal citations.
        fallback_markers = [
            "Tôi không tìm thấy thông tin phù hợp",
            "không tìm thấy thông tin phù hợp",
            "không có thông tin phù hợp"
        ]
        
        import re
        has_legal_content = False
        
        # 1. Capitalized Điều or Khoản followed by a number (e.g., Điều 168, Khoản 2)
        if re.search(r"(Điều|Khoản)\s+\d+", answer):
            has_legal_content = True
        # 2. Parenthesized citation containing legal keywords
        elif re.search(r"\(([^)]*(Điều|Khoản|Bộ luật|Luật|Quyết định|Thông tư|Nghị định)[^)]*)\)", answer):
            has_legal_content = True
        # 3. Capitalized document type keywords (case-sensitive)
        else:
            capital_keywords = ["Bộ luật", "Quyết định", "Thông tư", "Nghị định", "Hiến pháp"]
            if any(kw in answer for kw in capital_keywords):
                has_legal_content = True
                
        if any(marker in answer for marker in fallback_markers) or not has_legal_content:
            sources = []

        return {
            "answer": answer,
            "sources": sources,
            "prompt_tokens": prompt_tokens if prompt_tokens > 0 else None,
            "response_tokens": response_tokens if response_tokens > 0 else None,
            "total_tokens": total_tokens if total_tokens > 0 else None,
        }

# Singleton instance of RAGService
rag_service = RAGService()
