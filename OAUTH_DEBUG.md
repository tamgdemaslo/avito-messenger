# Отладка OAuth авторизации Avito

## Проблема: "Такой страницы не существует"

Если при нажатии на "Войти через Avito" вы видите ошибку 404, проверьте следующее:

### 1. Проверьте Client ID и Client Secret

Убедитесь, что в `app.py` указаны правильные значения:
```python
AVITO_CLIENT_ID = "HHiafcJb3rn8agxhzM8g"
AVITO_CLIENT_SECRET = "DusHGZF4gADWpNwIHbeefVNwxqoUXe5i_LQ2_g2o"
```

### 2. Проверьте Redirect URI в настройках Avito

1. Перейдите на [Портал разработчика Avito](https://developers.avito.ru)
2. Найдите ваше приложение
3. Убедитесь, что Redirect URI точно совпадает:
   ```
   http://localhost:5001/callback
   ```
   (обратите внимание на порт 5001, а не 5000!)

### 3. Проверьте URL авторизации

При запуске приложения в консоли будет выведен URL авторизации. Проверьте его:
- Должен начинаться с `https://api.avito.ru/oauth/authorize`
- Должен содержать ваш `client_id`
- Должен содержать правильный `redirect_uri`

### 4. Возможные варианты URL

Если основной URL не работает, попробуйте изменить в `app.py`:

**Вариант 1 (текущий):**
```python
AVITO_AUTH_URL = "https://api.avito.ru/oauth"
```

**Вариант 2:**
```python
AVITO_AUTH_URL = "https://www.avito.ru/oauth"
```

### 5. Проверьте формат scopes

Scopes должны быть разделены пробелами:
```python
scopes = "messenger:read messenger:write"
```

### 6. Проверьте, что приложение активно

В настройках приложения Avito убедитесь, что:
- Приложение активно (не заблокировано)
- У приложения есть необходимые разрешения (scopes)
- Client ID и Client Secret правильные

### 7. Проверьте логи

При нажатии на "Войти через Avito" в консоли, где запущен Flask, должны появиться логи с URL авторизации. Скопируйте этот URL и откройте его вручную в браузере, чтобы увидеть точную ошибку.

### 8. Альтернативный способ проверки

Попробуйте открыть URL авторизации напрямую в браузере:
```
https://api.avito.ru/oauth/authorize?client_id=HHiafcJb3rn8agxhzM8g&response_type=code&redirect_uri=http://localhost:5001/callback&scope=messenger:read messenger:write
```

Если этот URL тоже не работает, возможно:
- Client ID неправильный
- Приложение не настроено в Avito
- Нужно использовать другой формат URL



