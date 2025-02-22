from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher
import json
import re
# from deeppavlov.models.embedders.fasttext_embedder import FasttextEmbedder
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import gensim.downloader as api
import re
from rasa_sdk import Action
from rasa_sdk.events import SlotSet, AllSlotsReset
import pandas as pd
import os


# Загружаем предобученные эмбеддинги
word2vec_model = api.load("word2vec-google-news-300")


synonyms = {
    "ml": "machine learning",
    "sql": "database",
    "python": "programming",
    "tensorflow": "deep learning",
}
#

role_requirements = {
            "Data Scientist": {"min_experience": 3, "required_skills": ["Python", "SQL", "TensorFlow", "PyTorch", "NLP", "Pandas", "Numpy", "Scikit-learn", "Jupyter", "A/B"]},
            "Data Engineer": {"min_experience": 3, "required_skills": ["Python", "SQL", "Spark", "Hadoop", "Kafka", "Airflow", "MongoDB", "Apache"]},
            "MLOps Engineer": {"min_experience": 2, "required_skills": ["Docker", "Kubernetes", "CI/CD", "Prometheus", "MLflow", "TorchServe"]},
            "Project Manager": {"min_experience": 5, "required_skills": ["Agile", "Scrum", "Jira", "Confluence", "roadmap", "backlog"]},
            "Data Analyst": {"min_experience": 2, "required_skills": ["SQL", "BI", "Python", "Excel", "Tableau", "Pandas"]},
}




class ActionResetSlots(Action):
    def name(self):
        return "action_reset_slots"

    def run(self, dispatcher, tracker, domain):
        return [AllSlotsReset()]

def parse_experience(experience_str):
    experience_str = experience_str.lower().strip()

    if re.search(r"без опыта|новичок|только закончил", experience_str):
        return 0.0

    if re.search(r"полтора года", experience_str):
        return 1.5

    match = re.search(r"(\d+(?:[.,]\d+)?)\s?(год|лет|месяц|месяцев)?", experience_str)

    if not match:
        if re.search(r"есть опыт|опыт работы", experience_str):
            return 1.0
        return None

    value = float(match.group(1).replace(",", "."))
    unit = match.group(2)

    # ✅ Добавляем проверку: если значение слишком большое, это НЕ опыт работы
    if value > 50:  # Люди не работают 200+ лет
        return None

    if unit in ["месяц", "месяцев"]:
        return round(value / 12, 2)

    return value


class ActionExtractExperience(Action):
    def name(self):
        return "action_extract_experience"

    def run(self, dispatcher, tracker, domain):
        experience_str = tracker.latest_message.get("text")
        intent = tracker.latest_message.get("intent", {}).get("name")

        if intent != "provide_experience":
            return []

        experience_years = parse_experience(experience_str)

        if experience_years is None:
            dispatcher.utter_message("Не смог определить ваш опыт. Попробуйте сказать, например: '5 лет', '7 месяцев' или 'без опыта'.")
            return []

        dispatcher.utter_message(f"Я понял, что у вас {experience_years} лет опыта.")
        return [SlotSet("experience", experience_years)]




def normalize_skill(skill):
    """
    Преобразует навык в синоним, если он есть в словаре.
    """
    skill = skill.lower()
    return synonyms.get(skill, skill)  # Если есть синоним → заменяем

def get_word_embedding(word):
    """
    Получает вектор слова из Word2Vec.
    Если слова нет, возвращает нулевой вектор.
    """
    word = word.lower()  # Приводим к lowercase
    try:
        return word2vec_model[word]
    except KeyError:
        print(f"[WARNING] Слово '{word}' отсутствует в модели Word2Vec!")
        return np.zeros(300)  # Размер вектора 300


def compute_similarity(candidate_skills, required_skills):
    """
    Считает косинусное сходство между навыками кандидата и требованиями вакансии.
    """
    candidate_vectors = []
    required_vectors = []

    for skill in candidate_skills:
        normalized_skill = normalize_skill(skill)
        vec = get_word_embedding(normalized_skill)
        if np.any(vec):  
            candidate_vectors.append(vec)

    for skill in required_skills:
        normalized_skill = normalize_skill(skill)
        vec = get_word_embedding(normalized_skill)
        if np.any(vec):  
            required_vectors.append(vec)

    if not candidate_vectors or not required_vectors:
        return 0  # Если нет совпадающих слов, возвращаем 0

    similarities = []
    for c_vec in candidate_vectors:
        for r_vec in required_vectors:
            similarity = cosine_similarity([c_vec], [r_vec])[0][0]
            similarities.append(similarity)

    return np.mean(similarities) if similarities else 0


def parse_salary(salary_str):
    salary_str = salary_str.lower().strip()

    match = re.search(r"(\d+(?:[.,]\d+)?)\s?(к|тыс|тысяч|млн|миллион)?", salary_str)

    if not match:
        value = re.search(r"\d{5,7}", salary_str)  # ✅ Поиск 5-7 значных чисел (обычные зарплаты)
        if value:
            return int(value.group(0))
        return None

    value = float(match.group(1).replace(",", "."))
    unit = match.group(2)

    if unit in ["к", "тыс", "тысяч"]:
        return int(value * 1000)
    elif unit in ["млн", "миллион"]:
        return int(value * 1000000)

    return int(value)


class ActionExtractSalary(Action):
    def name(self):
        return "action_extract_salary"

    def run(self, dispatcher, tracker, domain):
        salary_str = tracker.latest_message.get("text")
        intent = tracker.latest_message.get("intent", {}).get("name")

        if intent != "provide_salary_expectation":
            return []

        salary_amount = parse_salary(salary_str)

        if salary_amount is None:
            dispatcher.utter_message(
                "Не смог определить зарплату. Попробуйте сказать, например: '150к', '90 тысяч', '1.2 млн'.")
            return []

        dispatcher.utter_message(f"Я понял, что вы ожидаете зарплату {salary_amount} рублей.")
        return [SlotSet("salary", salary_amount)]


class ActionSaveCandidateData(Action):
    def name(self) -> Text:
        return "action_save_candidate_data"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        # Получаем данные из слотов
        candidate_data = {
            "role": tracker.get_slot("role"),
            "experience": tracker.get_slot("experience"),
            "skills": tracker.get_slot("skills"),
            "salary": tracker.get_slot("salary")
        }

        # Сохраняем в JSON (можно изменить на запись в БД)
        with open("candidates.json", "a") as file:
            file.write(json.dumps(candidate_data, ensure_ascii=False) + "\n")

        dispatcher.utter_message(text="Ваши данные сохранены. Спасибо!")

        return []


class ActionEvaluateCandidate(Action):
    def name(self) -> str:
        return "action_evaluate_candidate"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: dict) -> list:

        role = tracker.get_slot("role")
        experience = tracker.get_slot("experience")
        skills = tracker.get_slot("skills")
        salary = tracker.get_slot("salary")

        if not role or not experience or not skills:
            dispatcher.utter_message(text="Недостаточно данных для оценки. Заполните анкету заново.")
            return []

        try:
            experience = int(parse_experience(str(experience)))
        except ValueError:
            dispatcher.utter_message(text="Ошибка: Некорректный формат опыта работы.")
            return []

        if role not in role_requirements:
            dispatcher.utter_message(text="Ошибка: указанной роли не существует.")
            return []

        required = role_requirements[role]

        # Оценка соответствия
        exp_ok = experience >= required["min_experience"]
        skill_similarity = compute_similarity(skills, required["required_skills"])

        if exp_ok and skill_similarity > 0.5:  # Порог 60% сходства
            response = f"✅ Ваш профиль подходит на {role}! Ваша заявка отправлена на рассмотрение. Сходство: {skill_similarity:.2f}"

            # ✅ Сохраняем кандидата в Excel
            self.save_candidate_to_excel(role, experience, skills, salary)

        else:
            response = f"❌ К сожалению, вам пока не хватает опыта или навыков. Сходство: {skill_similarity:.2f}"

        dispatcher.utter_message(
            text=response,
            buttons=[
                {"title": "🔄 Начать заново", "payload": "/restart"}
            ]
        )
        return []

    def save_candidate_to_excel(self, role, experience, skills, salary):
        """Сохраняет данные подходящих кандидатов в Excel"""

        file_path = "candidates_data.xlsx"

        # Создаём DataFrame
        new_data = pd.DataFrame([{
            "Опыт (лет)": experience,
            "Навыки": ", ".join(skills) if skills else "",
            "Ожидания по зарплате": salary,
            "Желаемая роль": role
        }])

        # Если файл уже есть, дописываем в него
        if os.path.exists(file_path):
            existing_data = pd.read_excel(file_path)
            updated_data = pd.concat([existing_data, new_data], ignore_index=True)
        else:
            updated_data = new_data

        # Сохраняем в Excel
        updated_data.to_excel(file_path, index=False)

