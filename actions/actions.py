"""Rasa custom actions for the HR candidate questionnaire."""

import logging

from rasa_sdk import Action, FormValidationAction
from rasa_sdk.events import AllSlotsReset

from actions.evaluate_salary import evaluate_salary
from actions.parsing import parse_experience, parse_salary
from actions.skill_matching import match_skills
from actions.storage import save_candidate
from actions.vacancies import ROLE_REQUIREMENTS

logger = logging.getLogger(__name__)


class ActionResetSlots(Action):
    def name(self):
        return "action_reset_slots"

    def run(self, dispatcher, tracker, domain):
        return [AllSlotsReset()]


class ValidateHRForm(FormValidationAction):
    def name(self):
        return "validate_hr_form"

    def validate_role(self, value, dispatcher, tracker, domain):
        role = next(
            (role for role in ROLE_REQUIREMENTS if role.casefold() == str(value).casefold()), None
        )
        if role is None:
            dispatcher.utter_message(text="Выберите одну из пяти позиций с помощью кнопок.")
        return {"role": role}

    def validate_experience(self, value, dispatcher, tracker, domain):
        years = parse_experience(value)
        if years is None:
            dispatcher.utter_message(text="Укажите опыт, например: 5 лет, 6 месяцев или без опыта.")
        return {"experience": years}

    def validate_salary(self, value, dispatcher, tracker, domain):
        salary = parse_salary(value)
        if salary is None:
            dispatcher.utter_message(
                text="Укажите одну сумму в рублях в месяц, например: 150к или 150 000."
            )
        return {"salary": salary}

    def validate_skills(self, value, dispatcher, tracker, domain):
        values = value if isinstance(value, list) else [value]
        skills = list(
            dict.fromkeys(str(item).strip() for item in values if item and str(item).strip())
        )
        if not skills:
            dispatcher.utter_message(text="Перечислите навыки, например: Python, SQL, Pandas.")
        return {"skills": skills or None}


class ActionShowApplicationSummary(Action):
    def name(self):
        return "action_show_application_summary"

    def run(self, dispatcher, tracker, domain):
        skills = ", ".join(tracker.get_slot("skills") or [])
        experience = parse_experience(tracker.get_slot("experience"))
        salary = parse_salary(tracker.get_slot("salary"))
        if experience is None or salary is None:
            dispatcher.utter_message(text="Анкета ещё не заполнена.")
            return []
        amount = f"{salary:,}".replace(",", " ")
        years = f"{experience:g}".replace(".", ",")
        dispatcher.utter_message(
            text=(
                f"Ваша анкета:\nПозиция: {tracker.get_slot('role')}\n"
                f"Опыт: {years} лет\nНавыки: {skills}\n"
                f"Зарплатные ожидания: {amount} ₽/мес."
            )
        )
        return []


class ActionEvaluateCandidate(Action):
    def name(self):
        return "action_evaluate_candidate"

    def run(self, dispatcher, tracker, domain):
        role = tracker.get_slot("role")
        experience = parse_experience(tracker.get_slot("experience"))
        salary = parse_salary(tracker.get_slot("salary"))
        skills = tracker.get_slot("skills")
        if role not in ROLE_REQUIREMENTS or experience is None or salary is None or not skills:
            dispatcher.utter_message(
                text="Недостаточно данных для оценки. Заполните анкету заново."
            )
            return []
        required = ROLE_REQUIREMENTS[role]
        similarity = match_skills(skills, required["required_skills"])
        prediction = evaluate_salary(experience, skills)
        suitable = (
            experience >= required["min_experience"]
            and similarity > 0.5
            and salary <= prediction * 1.2
        )
        if suitable:
            candidate = {
                "sender_id": tracker.sender_id,
                "role": role,
                "experience": experience,
                "skills": skills,
                "salary": salary,
            }
            try:
                save_candidate(candidate)
                result = "По условиям демо ваш профиль подходит. Заявка сохранена локально."
            except OSError:
                logger.exception("Could not save candidate record")
                result = "По условиям демо ваш профиль подходит, но заявку сохранить не удалось."
        else:
            result = "По условиям демо профиль пока не соответствует всем требованиям."
        salary_text = f"{salary:,}".replace(",", " ")
        prediction_text = f"{prediction:,.0f}".replace(",", " ")
        dispatcher.utter_message(
            text=(
                f"{result}\n"
                f"Сопоставление навыков: {similarity:.0%}.\n"
                f"Опыт: {experience:g} лет; требуется от {required['min_experience']}.\n"
                f"Прогноз учебной модели: {prediction_text} ₽/мес.; ожидания: {salary_text} ₽/мес.\n"
                "Результат демонстрационный; решение о найме принимает рекрутер."
            ),
            buttons=[{"title": "Начать заново", "payload": "/restart"}],
        )
        return []
