# Демонстрация полной анкеты через REST

Этот сценарий проверяет форму и действия с явными intent/entity payloads. Качество NLU проверяется отдельно: свободный текст и его распознавание зависят от обучения.

В одном терминале запустите `rasa run actions`, в другом:

```bash
rasa run --enable-api --credentials credentials.yml --port 5005
```

Из третьего терминала выполните сообщения по порядку, каждый раз с одним и тем же sender:

```bash
curl -s http://localhost:5005/webhooks/rest/webhook -H 'Content-Type: application/json' \
  -d '{"sender":"portfolio-demo","message":"/greet"}'
curl -s http://localhost:5005/webhooks/rest/webhook -H 'Content-Type: application/json' \
  -d '{"sender":"portfolio-demo","message":"/provide_info"}'
curl -s http://localhost:5005/webhooks/rest/webhook -H 'Content-Type: application/json' \
  -d '{"sender":"portfolio-demo","message":"/provide_desired_role{\"role\":\"Data Scientist\"}"}'
curl -s http://localhost:5005/webhooks/rest/webhook -H 'Content-Type: application/json' \
  -d '{"sender":"portfolio-demo","message":"/provide_experience{\"experience\":\"3.5 года\"}"}'
curl -s http://localhost:5005/webhooks/rest/webhook -H 'Content-Type: application/json' \
  -d '{"sender":"portfolio-demo","message":"/provide_skills{\"skills\":[\"Python\",\"SQL\",\"Pandas\",\"NumPy\",\"Scikit-learn\"]}"}'
curl -s http://localhost:5005/webhooks/rest/webhook -H 'Content-Type: application/json' \
  -d '{"sender":"portfolio-demo","message":"/provide_salary_expectation{\"salary\":\"150к\"}"}'
```

Автоматическая версия этого сценария — `scripts/smoke_test.py`. Скрипт отправляет те же сообщения через REST и проверяет итоговые слоты и ответ. Нужны запущенные серверы Rasa и действий; API используется только локально для проверки.

```bash
python scripts/smoke_test.py
```

Успех означает, что заполненная анкета содержит числовые опыт/зарплату и корректный список навыков, бот показывает результат и сохраняет заявку. Используется фиктивный sender и учебные данные. Записи остаются локальными в `runtime/`.
