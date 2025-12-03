# Автоматическая загрузка на GitHub

## Проблема

Файлы загружены не в правильные папки. Нужно:
- `templates/index.html` (не просто `index.html`)
- `templates/messages.html`
- `static/css/style.css`
- `static/js/app.js`

## Решение: Создайте Personal Access Token

### Шаг 1: Создайте токен

1. Откройте: https://github.com/settings/tokens/new
2. **Note:** `avito-messenger-upload`
3. **Expiration:** `30 days`
4. **Select scopes:** ✅ отметьте `repo`
5. Нажмите **"Generate token"**
6. **Скопируйте токен!** (будет показан только один раз)

### Шаг 2: Сохраните токен

Выполните в терминале:
```bash
git config --global credential.helper store
```

### Шаг 3: Загрузите файлы

Выполните команды:
```bash
cd /Users/ilaeliseenko/Desktop/avito-messenger

# Отправьте изменения
git push -u origin main
```

Когда попросит:
- **Username:** `tamgdemaslo`
- **Password:** вставьте ваш токен

После этого Git запомнит токен!

---

## Альтернатива: Через SSH

Если есть SSH ключ:
```bash
git remote set-url origin git@github.com:tamgdemaslo/avito-messenger.git
git push -u origin main
```

---

Создайте токен и дайте команду - я помогу загрузить! 🚀

