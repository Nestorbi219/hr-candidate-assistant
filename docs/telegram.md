# Подключение Telegram

1. Создайте своего бота через [BotFather](https://t.me/BotFather) и получите новый токен.
2. Скопируйте `credentials.example.yml` в `credentials.local.yml`.
3. Замените `YOUR_TELEGRAM_BOT_TOKEN`, `YOUR_BOT_USERNAME` (без `@`) и `YOUR_PUBLIC_HTTPS_HOST` на свои значения.
4. Обучите модель командой `rasa train` и запустите `rasa run actions` в отдельном терминале.
5. Настройте доступный Telegram публичный HTTPS-адрес с маршрутом на локальный порт 5005. Адрес webhook должен оканчиваться на `/webhooks/telegram/webhook`.
6. Запустите Rasa:

```bash
rasa run --credentials credentials.local.yml --port 5005
```

Откройте бота в Telegram и отправьте `/start`. Rasa регистрирует webhook при подключении канала. Адрес должен оставаться доступным; после смены адреса туннеля обновите конфигурацию и перезапустите сервер.

Для Telegram используется webhook-режим. REST и консоль работают без токена Telegram. В демо HR-контакт вымышленный; подходящие заявки сохраняются локально, а не отправляются отдельному рекрутеру.
