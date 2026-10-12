"""Parse Russian experience and monthly salary inputs without network access."""

import math
import re


def parse_experience(value):
    """Return years as a float, or None when input is ambiguous or invalid."""
    if value is None or isinstance(value, bool):
        return None
    text = str(value).strip().lower()
    if re.search(r"без опыта|нет опыта|новичок|только закончил|не работал", text):
        return 0.0
    if "полтора года" in text:
        return 1.5
    if re.fullmatch(r"(один )?год", text):
        return 1.0
    if re.search(r"-\s*\d", text):
        return None
    matches = re.findall(r"(\d+(?:[.,]\d+)?)\s*(месяц\w*|год\w*|лет)?", text)
    if len(matches) != 1:
        return None
    number, unit = matches[0]
    years = float(number.replace(",", "."))
    if unit.startswith("месяц"):
        years /= 12
    return round(years, 2) if math.isfinite(years) and 0 <= years <= 50 else None


def parse_salary(value):
    """Return one positive amount in RUB; salary ranges require clarification."""
    if value is None or isinstance(value, bool):
        return None
    text = str(value).strip().lower().replace("\u00a0", " ")
    if re.search(r"-\s*\d|\d\s*(?:до|[-–—])\s*\d", text):
        return None
    text = re.sub(r"(?<=\d)\s+(?=\d{3}(?:\D|$))", "", text)
    matches = re.findall(r"(\d+(?:[.,]\d+)?)\s*(млн|миллион\w*|тыс\w*|тыщ\w*|[кk])?", text)
    if len(matches) != 1:
        return None
    number, unit = matches[0]
    amount = float(number.replace(",", "."))
    if unit.startswith(("млн", "миллион")):
        amount *= 1_000_000
    elif unit.startswith(("тыс", "тыщ")) or unit in {"к", "k"}:
        amount *= 1_000
    return int(amount) if math.isfinite(amount) and 0 < amount <= 100_000_000 else None
