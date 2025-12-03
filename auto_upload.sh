#!/bin/bash
# Автоматическая загрузка на GitHub

echo "🚀 Автоматическая загрузка на GitHub"
echo "===================================="
echo ""

# Переходим в директорию проекта
cd /Users/ilaeliseenko/Desktop/avito-messenger

# Добавляем все файлы
git add .

# Коммит
git commit -m "Update to Client Credentials Flow with correct file structure"

# Push (потребуется токен)
echo ""
echo "Сейчас потребуется ваш GitHub Personal Access Token"
echo "Если у вас его нет, создайте здесь:"
echo "https://github.com/settings/tokens/new"
echo ""
echo "Отметьте 'repo' и скопируйте токен"
echo ""

git push origin main

echo ""
echo "✅ Загрузка завершена!"
echo "Проверьте: https://github.com/tamgdemaslo/avito-messenger"

