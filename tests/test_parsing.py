import pytest

from actions.parsing import parse_experience, parse_salary


@pytest.mark.parametrize(
    "text,expected",
    [
        ("5 лет", 5.0),
        ("2,5 года", 2.5),
        ("полтора года", 1.5),
        ("6 месяцев", 0.5),
        ("3 месяца", 0.25),
        ("год", 1.0),
        ("без опыта", 0.0),
        (0, 0.0),
        (3.5, 3.5),
        (None, None),
        ("150000", None),
        ("-2 года", None),
        ("не знаю", None),
    ],
)
def test_experience(text, expected):
    assert parse_experience(text) == expected


@pytest.mark.parametrize(
    "text,expected",
    [
        ("150к", 150000),
        ("150k", 150000),
        ("90 тысяч", 90000),
        ("200 тыщ в месяц", 200000),
        ("1.2 млн", 1200000),
        ("150 000 рублей", 150000),
        (150000.0, 150000),
        ("90 до 120 тысяч", None),
        ("90–120к", None),
        ("-100", None),
        (0, None),
        (None, None),
        ("не знаю", None),
    ],
)
def test_salary(text, expected):
    assert parse_salary(text) == expected
