"""Offline skill coverage and optional FastText semantic similarity."""

import os
from functools import lru_cache

import numpy as np

SYNONYMS = {
    "питон": "python",
    "py": "python",
    "postgres": "sql",
    "postgresql": "sql",
    "mysql": "sql",
    "пандас": "pandas",
    "sklearn": "scikit-learn",
    "tensorflow": "deep learning",
    "pytorch": "deep learning",
    "deep": "deep learning",
    "learning": "deep learning",
    "ci/cd": "continuous integration",
    "mlflow": "machine learning pipeline",
    "restapi": "api",
    "rest api": "api",
    "a/b": "ab testing",
    "a/b testing": "ab testing",
    "data warehouse": "warehouse",
    "dwh": "warehouse",
    "etl": "data pipeline",
}


def normalize_skill(skill):
    value = " ".join(str(skill).casefold().split())
    return SYNONYMS.get(value, value)


@lru_cache(maxsize=1)
def load_embeddings():
    # Explicit opt-in: importing actions never downloads a multi-GB model.
    import gensim.downloader as api

    return api.load(os.getenv("FASTTEXT_MODEL", "fasttext-wiki-news-subwords-300"))


def get_word_embedding(word, model):
    word = normalize_skill(word)
    if word in model:
        return model[word]
    vectors = [model[part] for part in word.split() if part in model]
    return np.mean(vectors, axis=0) if vectors else np.zeros(model.vector_size)


def compute_mean_vector(skills, model):
    vectors = [get_word_embedding(skill, model) for skill in skills]
    vectors = [vector for vector in vectors if np.any(vector)]
    return np.mean(vectors, axis=0) if vectors else np.zeros(model.vector_size)


def compute_similarity(candidate_skills, required_skills, model=None):
    """Return a score in [0, 1]; lexical coverage and semantic scores differ."""
    if model is None:
        candidate = {normalize_skill(skill) for skill in candidate_skills}
        required = {normalize_skill(skill) for skill in required_skills}
        return len(candidate & required) / len(required) if required else 0.0
    candidate = compute_mean_vector(candidate_skills, model)
    required = compute_mean_vector(required_skills, model)
    denominator = np.linalg.norm(candidate) * np.linalg.norm(required)
    if denominator == 0:
        return 0.0
    return float(np.clip(np.dot(candidate, required) / denominator, 0, 1))


def match_skills(candidate_skills, required_skills):
    mode = os.getenv("SKILL_MATCHER", "lexical")
    if mode not in {"lexical", "fasttext"}:
        raise ValueError("SKILL_MATCHER must be lexical or fasttext")
    model = load_embeddings() if mode == "fasttext" else None
    return compute_similarity(candidate_skills, required_skills, model)
