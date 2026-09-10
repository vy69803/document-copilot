"""Unit tests for Reciprocal Rank Fusion (RRF) logic."""

from app.retrieval.fusion import reciprocal_rank_fusion


def test_rrf_single_ranking():
    ranking = ["doc_a", "doc_b", "doc_c"]
    fused = reciprocal_rank_fusion([ranking], k=60)

    assert len(fused) == 3
    # doc_a: 1 / (60 + 1) = 1/61
    # doc_b: 1 / (60 + 2) = 1/62
    # doc_c: 1 / (60 + 3) = 1/63
    assert fused[0][0] == "doc_a"
    assert round(fused[0][1], 6) == round(1.0 / 61, 6)
    assert fused[1][0] == "doc_b"
    assert round(fused[1][1], 6) == round(1.0 / 62, 6)
    assert fused[2][0] == "doc_c"
    assert round(fused[2][1], 6) == round(1.0 / 63, 6)


def test_rrf_dual_rankings_intersection():
    # Dense: doc_a, doc_b, doc_c
    dense = ["doc_a", "doc_b", "doc_c"]
    # Lexical: doc_b, doc_d, doc_a
    lexical = ["doc_b", "doc_d", "doc_a"]

    fused = reciprocal_rank_fusion([dense, lexical], k=60)

    # doc_b is rank 2 in dense (1/62) and rank 1 in lexical (1/61) -> 1/62 + 1/61 ~= 0.0325
    # doc_a is rank 1 in dense (1/61) and rank 3 in lexical (1/63) -> 1/61 + 1/63 ~= 0.0322
    # doc_d is only in lexical (1/62) ~= 0.0161
    # doc_c is only in dense (1/63) ~= 0.0158
    assert fused[0][0] == "doc_b"
    assert fused[1][0] == "doc_a"
    assert fused[2][0] == "doc_d"
    assert fused[3][0] == "doc_c"


def test_rrf_empty_inputs():
    assert reciprocal_rank_fusion([]) == []
    assert reciprocal_rank_fusion([[], []]) == []


def test_rrf_custom_k():
    ranking_a = ["doc_1", "doc_2"]
    ranking_b = ["doc_2", "doc_1"]

    # With symmetrical 1st/2nd ranks, both items have identical total score
    fused = reciprocal_rank_fusion([ranking_a, ranking_b], k=10)
    assert len(fused) == 2
    assert round(fused[0][1], 6) == round(fused[1][1], 6)
    expected_score = (1.0 / 11) + (1.0 / 12)
    assert round(fused[0][1], 6) == round(expected_score, 6)
