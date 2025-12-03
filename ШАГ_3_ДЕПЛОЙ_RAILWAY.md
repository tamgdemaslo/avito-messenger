# Шаг 3: Деплой на Railway

## После загрузки кода на GitHub

Убедитесь, что код загружен: https://github.com/tamgdemaslo/avito-messenger

---

## Деплой на Railway

### 1. Откройте Railway

Перейдите на https://railway.app

### 2. Войдите через GitHub

1. Нажмите "Start a New Project"
2. Выберите "Login with GitHub"
3. Авторизуйте Railway

### 3. Создайте новый проект

1. Нажмите "New Project"
2. Выберите "Deploy from GitHub repo"
3. Найдите и выберите `tamgdemaslo/avito-messenger`
4. Railway начнет автоматический деплой

### 4. Дождитесь завершения деплоя

Railway автоматически:
- Определит Flask приложение
- Установит зависимости из `requirements.txt`
- Запустит приложение через `Procfile`

Это займет 2-3 минуты.

### 5. Настройте переменные окружения

В Railway Dashboard:

1. Откройте ваш проект
2. Перейдите в раздел **Variables**
3. Нажмите **New Variable** и добавьте:

```
AVITO_CLIENT_ID
```
Значение: `HHiafcJb3rn8agxhzM8g`

```
AVITO_CLIENT_SECRET
```
Значение: `DusHGZF4gADWpNwIHbeefVNwxqoUXe5i_LQ2_g2o`

```
SECRET_KEY
```
Значение: сгенерируйте случайный ключ (см. ниже)

```
FLASK_ENV
```
Значение: `production`

#### Генерация SECRET_KEY:

Выполните в терминале:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Скопируйте результат и используйте как значение `SECRET_KEY`.

### 6. Получите URL приложения

1. В Railway Dashboard найдите раздел **Settings** → **Domains**
2. Нажмите **Generate Domain**
3. Railway создаст домен типа:
   ```
   avito-messenger-production.up.railway.app
   ```

4. Скопируйте этот URL

### 7. Добавьте REDIRECT_URI

В Railway Variables добавьте еще одну переменную:

```
AVITO_REDIRECT_URI
```
Значение: `https://ваш-домен.up.railway.app/callback`

Например:
```
https://avito-messenger-production.up.railway.app/callback
```

Railway автоматически перезапустит приложение.

### 8. Проверьте работу

Откройте ваше приложение:
```
https://ваш-домен.up.railway.app
```

Вы должны увидеть страницу входа Avito Messenger.

---

## Что дальше?

Переходите к **Шагу 4: Настройка Avito**

---

## Troubleshooting

### Приложение не запускается

**Проверьте логи:**
1. В Railway Dashboard откройте раздел **Deployments**
2. Нажмите на последний деплой
3. Посмотрите логи - там будет указана ошибка

**Частые проблемы:**
- Не установлен `gunicorn` → проверьте `requirements.txt`
- Неправильный `Procfile` → должно быть `web: gunicorn app:app`
- Не добавлены переменные окружения

### 502 Bad Gateway

Подождите 1-2 минуты - приложение может запускаться.

### Домен не создается

Попробуйте вручную:
1. Settings → Networking
2. Generate Domain

---

## Стоимость

Railway предоставляет **$5 бесплатных кредитов** каждый месяц.

Этого достаточно для работы приложения 24/7.

