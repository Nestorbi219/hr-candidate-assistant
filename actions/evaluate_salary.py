"""Deterministic teaching model fitted lazily to 20 illustrative examples."""

import json
from functools import lru_cache
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


@lru_cache(maxsize=1)
def build_salary_model():
    source = Path(__file__).resolve().parents[1] / "data" / "salary_demo.json"
    rows = json.loads(source.read_text(encoding="utf-8"))
    vectorizer = TfidfVectorizer()
    skill_features = vectorizer.fit_transform([row["skills"] for row in rows]).toarray()
    features = np.column_stack(([row["experience"] for row in rows], skill_features))
    model = make_pipeline(
        StandardScaler(), RandomForestRegressor(n_estimators=100, random_state=42)
    )
    model.fit(features, [row["salary"] for row in rows])
    return model, vectorizer


def evaluate_salary(experience, skills):
    """Estimate a demo salary in RUB; this is not a market salary estimate."""
    model, vectorizer = build_salary_model()
    skill_features = vectorizer.transform([" ".join(skills)]).toarray()
    features = np.column_stack(([float(experience)], skill_features))
    return float(model.predict(features)[0])
