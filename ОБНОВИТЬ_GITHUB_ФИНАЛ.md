# 🚀 Финальное обновление на GitHub

## Осталось обновить app.py на GitHub!

Код исправлен локально, теперь нужно загрузить на GitHub.

---

## 📝 Откройте для редактирования:

https://github.com/tamgdemaslo/avito-messenger/edit/main/app.py

---

## ✏️ Сделайте 3 изменения:

### Изменение 1: Строка 40

Найдите:
```python
AVITO_AUTH_URL = "https://api.avito.ru/oauth"
```

Замените на:
```python
AVITO_AUTH_URL = "https://www.avito.ru/oauth"
```

---

### Изменение 2: Строки примерно 115 и 151

Найдите (2 раза):
```python
auth_url = f"{AVITO_AUTH_URL}/authorize?{urlencode(params)}"
```

Замените на:
```python
auth_url = f"{AVITO_AUTH_URL}?{urlencode(params)}"
```

(удалите `/authorize`)

---

### Изменение 3: Строки примерно 183 и 232

Найдите (2 раза):
```python
response = requests.post(
    f"{AVITO_AUTH_URL}/token",
```

Замените на:
```python
response = requests.post(
    f"{AVITO_API_URL}/token",
```

(замените `AVITO_AUTH_URL` на `AVITO_API_URL`)

---

## ✅ Commit changes

Commit message: `Fix OAuth URLs according to Avito documentation`

---

## ⏰ Через 1-2 минуты после коммита:

1. Railway задеплоит изменения
2. Откройте: `https://avito.tamgdemaslocrm.ru`
3. Нажмите "Войти через Avito"
4. **Авторизуйтесь в Avito**
5. **Начните работать с сообщениями!** 🎉

---

## 🎯 Итоговый правильный URL:

```
https://www.avito.ru/oauth?client_id=1cIpj04gx6i3v7Ym5wNj&response_type=code&redirect_uri=https://avito.tamgdemaslocrm.ru/callback&scope=messenger:read messenger:write
```

Именно такой URL будет теперь использоваться!

---

Обновите эти 3 места в app.py на GitHub! 🚀

