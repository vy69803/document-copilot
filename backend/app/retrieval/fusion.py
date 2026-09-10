"""Reciprocal Rank Fusion (RRF) algorithm.

Combines multiple ranked lists of document chunk IDs (e.g. dense semantic search
and Postgres full-text search) into a single ranked list.

Formula:
    RRF_score(d) = sum_{r in rankings} 1 / (k + rank_r(d))

where `k` is a smoothing constant (default 60), and `rank_r(d)` is the 1-based rank
of document `d` in ranking `r`.
"""

from collections import defaultdict

from app.config import settings

DEFAULT_RRF_K = settings.retrieval_rrf_k


def reciprocal_rank_fusion(
    rankings: list[list[str]],
    k: int = DEFAULT_RRF_K,
) -> list[tuple[str, float]]:
    """Fuse multiple ranked lists of chunk/document IDs into one ranked list.

    Args:
        rankings: A list of rankings, where each ranking is an ordered list of string IDs.
        k: Smoothing constant to balance high vs lower ranked items (default 60).

    Returns:
        A list of (id, rrf_score) tuples sorted in descending order of score.
    """
    scores: dict[str, float] = defaultdict(float)

    for ranking in rankings:
        for rank, item_id in enumerate(ranking, start=1):
            scores[item_id] += 1.0 / (k + rank)

    return sorted(scores.items(), key=lambda item: item[1], reverse=True)
