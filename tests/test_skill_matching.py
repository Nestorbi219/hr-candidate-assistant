import numpy as np
import pytest

from actions.skill_matching import compute_similarity, get_word_embedding


class TinyEmbeddings(dict):
    vector_size = 2


def test_aliases_duplicates_and_case_do_not_inflate_coverage():
    assert compute_similarity(
        ["питон", "Python", "PY", "postgres"], ["Python", "SQL", "Spark"]
    ) == pytest.approx(2 / 3)


def test_unrelated_skills_have_zero_coverage():
    assert compute_similarity(["Agile"], ["Python", "SQL"]) == 0


def test_semantic_similarity_uses_vectors():
    model = TinyEmbeddings(python=np.array([1.0, 0.0]), sql=np.array([0.0, 1.0]))
    assert compute_similarity(["py"], ["python"], model) == 1
    assert compute_similarity(["python"], ["sql"], model) == 0
    assert get_word_embedding("unknown", model).shape == (2,)
    assert compute_similarity(["unknown"], ["sql"], model) == 0
