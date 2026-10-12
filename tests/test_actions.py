import json
from types import SimpleNamespace

import pytest
from rasa_sdk.executor import CollectingDispatcher

from actions.actions import ActionEvaluateCandidate, ActionShowApplicationSummary, ValidateHRForm
from actions.evaluate_salary import build_salary_model, evaluate_salary
from actions.storage import save_candidate


def tracker(**changes):
    slots = {
        "role": "Data Scientist",
        "experience": 3.5,
        "skills": ["Python", "SQL", "Pandas", "NumPy", "scikit-learn"],
        "salary": 150000,
    }
    slots.update(changes)
    return SimpleNamespace(sender_id="demo-user", get_slot=slots.get)


def test_form_validation_preserves_months_and_rejects_salary_ranges():
    validator = ValidateHRForm()
    dispatcher = CollectingDispatcher()
    assert validator.validate_experience("6 месяцев", dispatcher, None, {}) == {"experience": 0.5}
    assert validator.validate_experience("без опыта", dispatcher, None, {}) == {"experience": 0.0}
    assert validator.validate_salary("90 до 120к", dispatcher, None, {}) == {"salary": None}


def test_valid_candidate_is_stored_without_network(monkeypatch, tmp_path):
    monkeypatch.setenv("SKILL_MATCHER", "lexical")
    monkeypatch.setenv("CANDIDATE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("EXPORT_EXCEL", "false")
    dispatcher = CollectingDispatcher()
    ActionEvaluateCandidate().run(dispatcher, tracker(), {})
    record = json.loads((tmp_path / "candidates.jsonl").read_text())
    assert record["experience"] == 3.5
    assert record["salary"] == 150000
    assert "83%" in dispatcher.messages[0]["text"]
    assert "сохранена локально" in dispatcher.messages[0]["text"]


@pytest.mark.parametrize("years", [0, 2.9])
def test_insufficient_experience_is_valid_input_but_not_accepted(monkeypatch, tmp_path, years):
    monkeypatch.setenv("SKILL_MATCHER", "lexical")
    monkeypatch.setenv("CANDIDATE_DATA_DIR", str(tmp_path))
    dispatcher = CollectingDispatcher()
    ActionEvaluateCandidate().run(dispatcher, tracker(experience=years), {})
    assert "не соответствует" in dispatcher.messages[0]["text"]
    assert not (tmp_path / "candidates.jsonl").exists()


def test_missing_salary_does_not_crash():
    dispatcher = CollectingDispatcher()
    ActionEvaluateCandidate().run(dispatcher, tracker(salary=None), {})
    assert "Недостаточно данных" in dispatcher.messages[0]["text"]


def test_summary_formats_skills_and_salary_for_chat():
    dispatcher = CollectingDispatcher()
    ActionShowApplicationSummary().run(dispatcher, tracker(), {})
    text = dispatcher.messages[0]["text"]
    assert "Python, SQL, Pandas" in text
    assert "150 000 ₽/мес." in text
    assert "['" not in text


def test_storage_failure_is_not_reported_as_success(monkeypatch):
    def fail(_):
        raise OSError("disk unavailable")

    monkeypatch.setattr("actions.actions.save_candidate", fail)
    monkeypatch.setenv("SKILL_MATCHER", "lexical")
    dispatcher = CollectingDispatcher()
    ActionEvaluateCandidate().run(dispatcher, tracker(), {})
    assert "сохранить не удалось" in dispatcher.messages[0]["text"]


def test_salary_model_is_cached_and_does_not_write_files(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    build_salary_model.cache_clear()
    first = evaluate_salary(3.5, ["Python", "SQL"])
    assert first == evaluate_salary(3.5, ["Python", "SQL"])
    assert build_salary_model.cache_info().hits == 1
    assert list(tmp_path.iterdir()) == []


def test_excel_export_is_optional_and_portable(monkeypatch, tmp_path):
    import pandas as pd

    monkeypatch.setenv("CANDIDATE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("EXPORT_EXCEL", "true")
    candidate = {
        "sender_id": "demo",
        "role": "Data Analyst",
        "experience": 2.5,
        "skills": ["Python", "SQL"],
        "salary": 140000,
    }
    save_candidate(candidate)
    rows = pd.read_excel(tmp_path / "candidates.xlsx")
    assert rows.iloc[0]["skills"] == "Python, SQL"
    assert rows.iloc[0]["experience"] == 2.5
