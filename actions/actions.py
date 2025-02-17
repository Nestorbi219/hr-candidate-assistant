from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
import json
import re
# from deeppavlov.models.embedders.fasttext_embedder import FasttextEmbedder
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import gensim.downloader as api

# Загружаем предобученные эмбеддинги
word2vec_model = api.load("word2vec-google-news-300")


synonyms = {
    "ml": "machine learning",
    "sql": "database",
    "python": "programming",
    "tensorflow": "deep learning",
}


def parse_experience(experience_str):
    """
    Преобразует строку с опытом работы в число лет.
    """
    experience_str = experience_str.lower().strip()

    # 🔹 Если указано "без опыта", возвращаем 0 лет
    if re.search(r"без опыта|новичок|нет опыта", experience_str):
        return 0.0

    # 🔹 Обрабатываем "полтора года" как 1.5 года
    if re.search(r"полтора года", experience_str):
        return 1.5

    # 🔹 Ищем число и единицу измерения
    match = re.search(r"(\d+(?:[.,]\d+)?)\s?(год|лет|месяц|месяцев)?", experience_str)

    if not match:
        # Если числа нет, но сказано что "есть опыт" → по умолчанию 1 год
        if re.search(r"есть опыт|опыт работы", experience_str):
            return 1.0
        return None  # Если ничего не нашли, возвращаем None

    value = float(match.group(1).replace(",", "."))  # Приводим к float (учитываем запятые)
    unit = match.group(2)  # "год", "лет", "месяц", "месяцев"

    # 🔹 Если указаны месяцы, переводим в годы
    if unit in ["месяц", "месяцев"]:
        return round(value / 12, 2)

    return value  # Если указан "год" или "лет", оставляем как есть



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
            experience = int(parse_experience(experience))
        except ValueError:
            dispatcher.utter_message(text="Ошибка: Некорректный формат опыта работы.")
            return []

        role_requirements = {
            "Data Scientist": {"min_experience": 3, "required_skills": ["Python", "SQL", "TensorFlow", "PyTorch", "NLP", "Pandas", "Numpy", "Scikit-learn", "Jupyter", "A/B"]},
            "Data Engineer": {"min_experience": 3, "required_skills": ["Python", "SQL", "Spark", "Hadoop", "Kafka", "Airflow", "MongoDB", "Apache"]},
            "MLOps Engineer": {"min_experience": 2, "required_skills": ["Docker", "Kubernetes", "CI/CD", "Prometheus", "MLflow", "TorchServe"]},
            "Project Manager": {"min_experience": 5, "required_skills": ["Agile", "Scrum", "Jira", "Confluence", "roadmap", "backlog"]},
            "Data Analyst": {"min_experience": 2, "required_skills": ["SQL", "BI", "Python", "Excel", "Tableau", "Pandas"]},
        }

        if role not in role_requirements:
            dispatcher.utter_message(text="Ошибка: указанной роли не существует.")
            return []

        required = role_requirements[role]

        # Оценка соответствия
        exp_ok = experience >= required["min_experience"]
        skill_similarity = compute_similarity(skills, required["required_skills"])

        print("kkkk", exp_ok, skill_similarity)
        if exp_ok and skill_similarity > 0.5:  # Порог 50% сходства
            print("Сходство :", skill_similarity)
            response = f"Ваш профиль подходит на {role}! Ваша заявка отправлена на рассмотрение."
        elif exp_ok and skill_similarity > 0.4 and role == 'Data Scientist':
            print("Сходство :", skill_similarity)
            response = f"Ваш профиль подходит на {role}! Ваша заявка отправлена на рассмотрение."
        else:
            print("Сходство :", skill_similarity)
            response = f"К сожалению, вам пока не хватает опыта или навыков."

        dispatcher.utter_message(text=response)
        return []

