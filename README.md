# Avito Messenger Web Application

Веб-приложение для получения и ответа на сообщения Avito через API.

## Возможности

- ✅ OAuth авторизация через Avito
- ✅ Просмотр списка чатов
- ✅ Просмотр сообщений в чатах
- ✅ Отправка ответов на сообщения
- ✅ Современный и удобный интерфейс
- ✅ Адаптивный дизайн

## Установка

1. Установите зависимости:
```bash
pip install -r requirements.txt
```

2. Убедитесь, что в `app.py` правильно указаны:
   - `AVITO_CLIENT_ID` - ваш Client ID
   - `AVITO_CLIENT_SECRET` - ваш Client Secret
   - `AVITO_REDIRECT_URI` - URL для callback (по умолчанию `http://localhost:5000/callback`)

3. В настройках приложения Avito укажите Redirect URI:
   - Перейдите в [Портал разработчика Avito](https://developers.avito.ru)
   - Найдите ваше приложение
   - Добавьте `http://localhost:5000/callback` в список разрешенных Redirect URI

## Запуск

```bash
python app.py
```

Приложение будет доступно по адресу: `http://localhost:5000`

## Использование

1. Откройте `http://localhost:5000` в браузере
2. Нажмите "Войти через Avito"
3. Авторизуйтесь в Avito
4. После авторизации вы увидите список ваших чатов
5. Выберите чат для просмотра сообщений
6. Введите сообщение и нажмите "Отправить"

## Структура проекта

```
avito-messenger/
├── app.py                 # Flask backend приложение
├── requirements.txt       # Python зависимости
├── templates/            # HTML шаблоны
│   ├── index.html        # Страница входа
│   └── messages.html     # Страница с сообщениями
├── static/               # Статические файлы
│   ├── css/
│   │   └── style.css     # Стили
│   └── js/
│       └── app.js        # JavaScript логика
└── README.md             # Документация
```

## API Endpoints

- `GET /` - Главная страница
- `GET /login` - Инициация OAuth авторизации
- `GET /callback` - OAuth callback обработчик
- `GET /messages` - Страница с сообщениями
- `GET /api/messages` - Получить список сообщений
- `GET /api/chats` - Получить список чатов
- `POST /api/messages/send` - Отправить сообщение
- `GET /api/profile` - Получить информацию о профиле
- `GET /logout` - Выход из системы

## Примечания

- Токены хранятся в сессии Flask (в продакшене рекомендуется использовать БД)
- Приложение использует стандартный OAuth 2.0 flow
- API endpoints могут отличаться в зависимости от версии Avito API

## Troubleshooting

Если возникают проблемы с авторизацией:
1. Проверьте правильность Client ID и Client Secret
2. Убедитесь, что Redirect URI совпадает в приложении и в коде
3. Проверьте, что приложение имеет необходимые разрешения (scopes) в Avito



