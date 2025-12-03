# Шаг 2: Загрузка кода на GitHub

## Вариант 1: Через терминал (с авторизацией)

Выполните в терминале:

```bash
cd /Users/ilaeliseenko/Desktop/avito-messenger

# Если нужно, настройте Git
git config --global user.name "Ваше Имя"
git config --global user.email "your@email.com"

# Отправьте код
git push -u origin main
```

При запросе авторизации:
- **Username:** `tamgdemaslo`
- **Password:** используйте Personal Access Token (не пароль!)

### Как создать Personal Access Token:

1. Откройте https://github.com/settings/tokens
2. Нажмите "Generate new token" → "Generate new token (classic)"
3. Название: `avito-messenger-deploy`
4. Выберите срок действия: 90 days
5. Отметьте галочки:
   - ✅ `repo` (полный доступ к репозиториям)
6. Нажмите "Generate token"
7. **Скопируйте токен** (он больше не будет показан!)
8. Используйте этот токен вместо пароля при push

---

## Вариант 2: Через GitHub Desktop (проще)

1. Скачайте GitHub Desktop: https://desktop.github.com
2. Войдите в свой аккаунт GitHub
3. File → Add Local Repository
4. Выберите папку: `/Users/ilaeliseenko/Desktop/avito-messenger`
5. Нажмите "Publish repository"
6. Выберите репозиторий `tamgdemaslo/avito-messenger`
7. Нажмите "Push origin"

---

## Вариант 3: Через веб-интерфейс GitHub (самый простой)

1. Откройте https://github.com/tamgdemaslo/avito-messenger
2. Нажмите "uploading an existing file"
3. Перетащите все файлы из папки `/Users/ilaeliseenko/Desktop/avito-messenger`
4. **Важно:** Не забудьте загрузить папки `templates` и `static` со всеми файлами внутри
5. Напишите commit message: "Initial commit"
6. Нажмите "Commit changes"

---

## После успешной загрузки

Проверьте, что все файлы загружены:
- ✅ `app.py`
- ✅ `requirements.txt`
- ✅ `Procfile`
- ✅ `runtime.txt`
- ✅ папка `templates/` с файлами
- ✅ папка `static/` с файлами

Затем переходите к **Шагу 3: Деплой на Railway**

