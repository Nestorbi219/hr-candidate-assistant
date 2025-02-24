import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
import joblib

# Данные о кандидатах
data = pd.DataFrame([
    {"role": "Data Scientist", "experience": 3, "skills": "Python,SQL,TensorFlow", "salary": 200000},
    {"role": "Data Engineer", "experience": 4, "skills": "Python,SQL,Spark", "salary": 180000},
    {"role": "MLOps Engineer", "experience": 2, "skills": "Docker,Kubernetes,CI/CD", "salary": 220000},
    {"role": "Project Manager", "experience": 5, "skills": "Agile,Scrum", "salary": 150000},
    {"role": "Data Analyst", "experience": 2, "skills": "SQL,BI,Python", "salary": 140000},
    {"role": "Data Scientist", "experience": 5, "skills": "Python,SQL,Deep Learning", "salary": 250000},
    {"role": "Data Engineer", "experience": 6, "skills": "Python,SQL,Hadoop", "salary": 210000},
    {"role": "MLOps Engineer", "experience": 3, "skills": "Docker,Kubernetes,Terraform", "salary": 230000},
    {"role": "Data Scientist", "experience": 7, "skills": "Python,SQL,PyTorch,NLP", "salary": 270000},
    {"role": "Data Engineer", "experience": 5, "skills": "Python,SQL,Kafka,Airflow", "salary": 220000},
    {"role": "MLOps Engineer", "experience": 4, "skills": "Docker,Kubernetes,Prometheus,MLFlow", "salary": 240000},
    {"role": "Project Manager", "experience": 6, "skills": "Agile,Scrum,Jira,Confluence", "salary": 180000},
    {"role": "Data Analyst", "experience": 3, "skills": "SQL,BI,Power BI,Tableau", "salary": 160000},
    {"role": "Data Scientist", "experience": 2, "skills": "Python,SQL,A/B Testing,Scikit-learn", "salary": 190000},
    {"role": "Data Engineer", "experience": 7, "skills": "Python,SQL,Hadoop,Kafka,Databricks", "salary": 230000},
    {"role": "MLOps Engineer", "experience": 5, "skills": "Docker,Kubernetes,Terraform,CI/CD,Bash", "salary": 260000},
    {"role": "Project Manager", "experience": 4, "skills": "Agile,Scrum,Trello,Confluence", "salary": 170000},
    {"role": "Data Analyst", "experience": 4, "skills": "SQL,BI,Python,Excel,ETL", "salary": 150000},
    {"role": "Data Scientist", "experience": 6, "skills": "Python,SQL,PyTorch,Reinforcement Learning", "salary": 280000},
    {"role": "Data Engineer", "experience": 8, "skills": "Python,SQL,Spark,Hadoop,Airflow,Kafka", "salary": 250000},
])

# Преобразование данных
X_experience = np.array(data["experience"]).reshape(-1, 1)  # Опыт работы
vectorizer = TfidfVectorizer()
X_skills = vectorizer.fit_transform(data["skills"])  # Векторизация навыков
X = np.hstack((X_experience, X_skills.toarray()))  # Объединение признаков
y = np.array(data["salary"])  # Зарплата

# Обучение модели
model = make_pipeline(StandardScaler(), RandomForestRegressor(n_estimators=100, random_state=42))
model.fit(X, y)

# Сохранение модели и векторизатора
joblib.dump(model, "salary_model.pkl")
joblib.dump(vectorizer, "skills_vectorizer.pkl")

# Функция для оценки зарплаты кандидата
def evaluate_salary(experience, skills):
    """Оценивает, подходит ли кандидат по зарплате."""
    skills_vectorized = vectorizer.transform([" ".join(skills)])
    features = np.hstack((np.array([[experience]]), skills_vectorized.toarray()))
    predicted_salary = model.predict(features)[0]
    return predicted_salary

# Пример использования
candidate_experience = 4
candidate_skills = ["Python", "SQL", "Spark"]
predicted_salary = evaluate_salary(candidate_experience, candidate_skills)

print(f"Ожидаемая зарплата: {predicted_salary:.2f}")
