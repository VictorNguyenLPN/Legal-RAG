from typing import List, Dict, Tuple
from backend.app.config import settings

def reciprocal_rank_fusion(
    dense_results: List[Tuple[Dict, float]],
    sparse_results: List[Tuple[Dict, float]],
    top_n: int = None,
    k: int = None
) -> List[Tuple[Dict, float]]:
    """
    Combines dense and sparse search results using Reciprocal Rank Fusion (RRF).
    
    Formula: RRF_Score(doc) = Sum_m ( 1 / (k + rank_m(doc)) )
    """
    if top_n is None:
        top_n = settings.RRF_TOP_N
    if k is None:
        k = settings.RRF_K

    rrf_scores: Dict[str, float] = {}
    chunk_mapping: Dict[str, Dict] = {}

    # Helper to update RRF scores
    def update_scores(results: List[Tuple[Dict, float]]):
        for rank_idx, (chunk, _) in enumerate(results):
            # chunks have chunk_id
            chunk_id = chunk["chunk_id"]
            rank = rank_idx + 1  # 1-based ranking
            
            if chunk_id not in rrf_scores:
                rrf_scores[chunk_id] = 0.0
                chunk_mapping[chunk_id] = chunk
                
            rrf_scores[chunk_id] += 1.0 / (k + rank)

    # Accumulate scores from dense search
    update_scores(dense_results)
    
    # Accumulate scores from sparse search
    update_scores(sparse_results)

    # Sort chunks by RRF score in descending order
    sorted_chunks = sorted(rrf_scores.items(), key=lambda item: item[1], reverse=True)

    # Select top_n
    top_n = min(top_n, len(sorted_chunks))
    result = []
    for chunk_id, score in sorted_chunks[:top_n]:
        result.append((chunk_mapping[chunk_id], score))

    return result
