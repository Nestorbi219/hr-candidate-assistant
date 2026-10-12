"""Portable local candidate storage. Generated records stay outside Git."""

import json
import os
from pathlib import Path
from threading import Lock

_WRITE_LOCK = Lock()


def save_candidate(candidate):
    directory = Path(os.getenv("CANDIDATE_DATA_DIR", "runtime"))
    directory.mkdir(parents=True, exist_ok=True)
    with _WRITE_LOCK:
        with (directory / "candidates.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(candidate, ensure_ascii=False) + "\n")
        if os.getenv("EXPORT_EXCEL", "false").lower() == "true":
            import pandas as pd

            rows = [
                json.loads(line)
                for line in (directory / "candidates.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]
            for row in rows:
                row["skills"] = ", ".join(row["skills"])
            pd.DataFrame(rows).to_excel(directory / "candidates.xlsx", index=False)
