from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
import json
import re
from deeppavlov.models.embedders.fasttext_embedder import FasttextEmbedder
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import gensim.downloader as api

# Загружаем предобученные эмбеддинги
word2vec_model = api.load("word2vec-google-news-300")

#print("sql" in word2vec_model)
#print("python" in word2vec_model)

synonyms = {
    "ml": "machine learning",
    "sql": "database",
    "python": "programming",
    "tensorflow": "deep learning",
}



def parse_experience(experience_str):
    """
    Преобразует строковый опыт в число лет.
    """
    match = re.search(r"(\d+)\s?(год|лет|месяц|месяцев)?", experience_str.lower())

    if not match:
        return None  # Если не удалось распознать, вернуть None

    value = int(match.group(1))
    unit = match.group(2)  # Год / месяц

    if unit in ["месяц", "месяцев"]:  
        return round(value / 12, 2)  # Преобразуем месяцы в годы
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
            "Data Scientist": {"min_experience": 3, "required_skills": ["Python", "SQL"]},
            "Data Engineer": {"min_experience": 3, "required_skills": ["Python", "SQL", "Spark"]},
            "MLOps Engineer": {"min_experience": 2, "required_skills": ["Docker", "Kubernetes", "CI/CD"]},
            "Project Manager": {"min_experience": 5, "required_skills": ["Agile", "Scrum", "JIRA"]},
            "Data Analyst": {"min_experience": 2, "required_skills": ["SQL", "Power BI", "Python"]},
        }

        if role not in role_requirements:
            dispatcher.utter_message(text="Ошибка: указанной роли не существует.")
            return []

        required = role_requirements[role]

        # Оценка соответствия
        exp_ok = experience >= required["min_experience"]
        skill_similarity = compute_similarity(skills, required["required_skills"])

        print("kkkk", exp_ok, skill_similarity)
        if exp_ok and skill_similarity > 0.75:  # Порог 75% сходства
            response = f"Ваш профиль подходит на {role}! Ваша заявка отправлена на рассмотрение. (Сходство навыков: {round(skill_similarity * 100, 2)}%)"
        else:
            response = f"К сожалению, вам пока не хватает опыта или навыков. (Сходство навыков: {round(skill_similarity * 100, 2)}%)"

        dispatcher.utter_message(text=response)
        return []

