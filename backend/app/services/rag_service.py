import time
import re
import logging
from typing import List, Dict, Tuple, Any, Optional, Callable, Awaitable
from backend.app.config import settings
from backend.app.database.vector_db import vector_db
from backend.app.services.gemini_service import gemini_service
from backend.app.services.jina_service import jina_service
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

    def ingest_chunks(self, chunks: List[Dict]) -> int:
        if not chunks:
            return 0

        vector_db.save(chunks)
        return len(chunks)

    def condense_query(self, user_query: str, history: List[Dict[str, str]]) -> Tuple[str, Any]:
        history_str = ""
        for msg in history:
            role_label = "Người dùng" if msg["role"] == "user" else "Trợ lý AI"
            history_str += f"{role_label}: {msg['content']}\n"

        prompt = (
            f"Dưới đây là Lịch sử cuộc hội thoại giữa Người dùng và Trợ lý AI:\n"
            f"{history_str}\n"
            f"Hãy diễn giải lại câu hỏi mới nhất dưới đây của Người dùng thành một câu hỏi độc lập, "
            f"đầy đủ bối cảnh nhưng giữ nguyên ý định ban đầu.\n"
            f"Lưu ý: CHỈ trả về duy nhất nội dung câu hỏi đã được diễn giải lại, không thêm bất kỳ văn bản giải thích nào khác.\n"
            f"Câu hỏi mới nhất: {user_query}"
        )

        try:
            condensed, usage_metadata = gemini_service.generate_answer(prompt=prompt)
            condensed_clean = condensed.strip()
            if condensed_clean:
                return condensed_clean, usage_metadata
        except Exception as e:
            logger.error(f"Failed to condense query: {e}")
        return user_query, None

    async def query(
        self,
        user_query: str,
        history: List[Dict[str, str]] = None,
        check_cancelled: Optional[Callable[[], Awaitable[None]]] = None
    ) -> Dict[str, Any]:
        if vector_db.is_empty():
            return {
                "answer": "Cơ sở dữ liệu pháp luật hiện đang trống. Vui lòng thực hiện ingest dữ liệu trước.",
                "sources": []
            }

        timing_details = {}
        token_details = {
            "prompt_tokens": 0,
            "response_tokens": 0,
            "total_tokens": 0
        }

        if check_cancelled:
            await check_cancelled()

        t_condense = time.perf_counter()
        search_query = user_query
        if history:
            search_query, condense_metadata = self.condense_query(user_query, history)
            if condense_metadata:
                token_details['prompt_tokens'] += condense_metadata.prompt_token_count or 0
                token_details['response_tokens'] += condense_metadata.candidates_token_count or 0
                token_details['total_tokens'] += condense_metadata.total_token_count or 0
        timing_details["condense"] = round(time.perf_counter() - t_condense, 3)

        if check_cancelled:
            await check_cancelled()

        t_search = time.perf_counter()
        dense_results = dense_search(search_query, top_k=20)
        sparse_results = sparse_search(search_query, top_k=20)
        fused_candidates = reciprocal_rank_fusion(
            dense_results,
            sparse_results,
            top_n=15,
            k=settings.RRF_K
        )
        timing_details["search"] = round(time.perf_counter() - t_search, 3)

        if check_cancelled:
            await check_cancelled()

        t_rerank = time.perf_counter()
        candidates = [chunk for chunk, score in fused_candidates]
        reranked_ids = jina_service.rerank(search_query, candidates, top_n=settings.RRF_TOP_N)
        timing_details["rerank"] = round(time.perf_counter() - t_rerank, 3)

        if check_cancelled:
            await check_cancelled()

        fused_results = []
        candidate_map = {c["chunk_id"]: c for c in candidates}
        for idx, cid in enumerate(reranked_ids):
            if cid in candidate_map:
                score = 1.0 - (idx * 0.05)
                fused_results.append((candidate_map[cid], score))

        contexts_text_list = []
        sources = []

        for idx, (chunk, score) in enumerate(fused_results):
            metadata = chunk.get("metadata", {})
            doc_title = metadata.get("document_title") or "N/A"
            article = metadata.get("article_title") or metadata.get("article_number") or "N/A"
            clause = metadata.get("clause_number") or "N/A"
            point = metadata.get("point") or ""
            text = chunk.get("text") or ""

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

        history_text = ""
        if history:
            history_text = "Lịch sử cuộc hội thoại trước đó:\n"
            for msg in history:
                role_label = "Người dùng" if msg["role"] == "user" else "Trợ lý AI"
                history_text += f"- {role_label}: {msg['content']}\n"
            history_text += "\n"

        prompt = (
            f"Ngữ cảnh pháp luật được cung cấp:\n"
            f"=================================\n"
            f"{contexts_text}\n"
            f"=================================\n\n"
            f"{history_text}"
            f"Câu hỏi tiếp theo của Người dùng: {user_query}"
        )

        t_llm = time.perf_counter()
        answer, answer_metadata = gemini_service.generate_answer(
            prompt=prompt,
            system_instruction=self.SYSTEM_INSTRUCTION
        )
        timing_details["llm"] = round(time.perf_counter() - t_llm, 3)
        timing_details["total_time"] = round(sum(timing_details.values()), 3)
        if answer_metadata:
            token_details['prompt_tokens'] += answer_metadata.prompt_token_count or 0
            token_details['response_tokens'] += answer_metadata.candidates_token_count or 0
            token_details['total_tokens'] += answer_metadata.total_token_count or 0

        fallback_markers = [
            "Tôi không tìm thấy thông tin phù hợp",
            "không tìm thấy thông tin phù hợp",
            "không có thông tin phù hợp"
        ]

        has_legal_content = False
        if re.search(r"(Điều|Khoản)\s+\d+", answer):
            has_legal_content = True
        elif re.search(r"\(([^)]*(Điều|Khoản|Bộ luật|Luật|Quyết định|Thông tư|Nghị định)[^)]*)\)", answer):
            has_legal_content = True
        else:
            capital_keywords = ["Bộ luật", "Quyết định", "Thông tư", "Nghị định", "Hiến pháp"]
            if any(kw in answer for kw in capital_keywords):
                has_legal_content = True

        if any(marker in answer for marker in fallback_markers) or not has_legal_content:
            sources = []

        return {
            "answer": answer,
            "sources": sources,
            "token_details": token_details,
            "timing_details": timing_details
        }


rag_service = RAGService()
