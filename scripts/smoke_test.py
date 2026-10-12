"""Run a complete questionnaire against local Rasa and action servers."""

import json
import os
import time
import uuid
from urllib.error import URLError
from urllib.request import Request, urlopen

BASE_URL = os.getenv("RASA_URL", "http://localhost:5005").rstrip("/")


def request(path, data=None):
    body = json.dumps(data).encode() if data is not None else None
    req = Request(BASE_URL + path, data=body, headers={"Content-Type": "application/json"})
    with urlopen(req, timeout=60) as response:
        return json.load(response)


def main():
    deadline = time.monotonic() + 90
    while True:
        try:
            request("/status")
            with urlopen("http://localhost:5055/health", timeout=2) as response:
                if response.status == 200:
                    break
        except URLError:
            if time.monotonic() >= deadline:
                raise RuntimeError("Rasa and action servers were not ready within 90 seconds")
            time.sleep(1)
    sender = "portfolio-demo-" + uuid.uuid4().hex[:8]
    messages = [
        "/greet",
        "/provide_info",
        '/provide_desired_role{"role":"Data Scientist"}',
        '/provide_experience{"experience":"3.5 года"}',
        '/provide_skills{"skills":["Python","SQL","Pandas","NumPy","Scikit-learn"]}',
        '/provide_salary_expectation{"salary":"150к"}',
    ]
    responses = []
    for message in messages:
        reply = request("/webhooks/rest/webhook", {"sender": sender, "message": message})
        responses.extend(reply)
        print(json.dumps(reply, ensure_ascii=False, indent=2))
    tracker = request(f"/conversations/{sender}/tracker")
    slots = tracker["slots"]
    assert slots["role"] == "Data Scientist", slots
    assert slots["experience"] == 3.5, slots
    assert slots["salary"] == 150000, slots
    assert slots["skills"] == ["Python", "SQL", "Pandas", "NumPy", "Scikit-learn"], slots
    assert not tracker["active_loop"], tracker["active_loop"]
    assert any("Заявка сохранена локально" in reply.get("text", "") for reply in responses), (
        responses
    )
    print("PASS: complete questionnaire, normalized slots, candidate saved locally")


if __name__ == "__main__":
    main()
