# ⚠️ Исправление ошибки Python на Railway

## Проблема

Railway не может установить `python-3.11.0` из-за специфики платформы.

Ошибка:
```
mise ERROR no precompiled python found for core:python@3.11.0
```

## ✅ Решение: Исправить runtime.txt

### Вариант 1: Через веб-интерфейс GitHub (проще)

1. Откройте файл на GitHub:
   https://github.com/tamgdemaslo/avito-messenger/blob/main/runtime.txt

2. Нажмите кнопку **"Edit"** (карандаш) справа

3. Измените содержимое с:
   ```
   python-3.11.0
   ```
   
   На:
   ```
   python-3.11
   ```

4. Внизу страницы нажмите **"Commit changes"**

5. Нажмите **"Commit changes"** ещё раз для подтверждения

### Вариант 2: Удалить runtime.txt (Railway сам выберет версию)

1. Откройте: https://github.com/tamgdemaslo/avito-messenger

2. Найдите файл `runtime.txt`

3. Нажмите на него

4. Нажмите кнопку с тремя точками **"..."** справа

5. Выберите **"Delete file"**

6. Commit changes

Railway автоматически использует последнюю стабильную версию Python 3.

---

## После исправления

Railway автоматически:
1. Обнаружит изменения в GitHub
2. Перезапустит деплой
3. Успешно установит Python

Проверьте логи в Railway Dashboard - деплой должен пройти успешно!

---

## Альтернатива: Настройка в Railway напрямую

Если не хотите менять файл, можно настроить в Railway:

1. Откройте ваш проект в Railway Dashboard
2. Перейдите в **Settings** → **Environment**
3. Добавьте переменную:
   ```
   NIXPACKS_PYTHON_VERSION=3.11
   ```
4. Сохраните и перезапустите деплой

