# Настройка Redirect URI для Avito

## Проблема

Avito выдает ошибку: **"Ссылка введена в неверном формате"** для `http://localhost:5002/callback`

## Решения

### ✅ Вариант 1: Использовать 127.0.0.1 вместо localhost

Попробуйте ввести:
```
http://127.0.0.1:5002/callback
```

### ✅ Вариант 2: Использовать ngrok (рекомендуется)

Avito может требовать публичный HTTPS URL.

#### Шаг 1: Установите ngrok

**macOS:**
```bash
brew install ngrok
```

**Или скачайте с сайта:**
https://ngrok.com/download

#### Шаг 2: Запустите ngrok

```bash
ngrok http 5002
```

Вы увидите что-то вроде:
```
Forwarding   https://abc123.ngrok.io -> http://localhost:5002
```

#### Шаг 3: Используйте ngrok URL

В форме Avito введите:
```
https://abc123.ngrok.io/callback
```

(замените `abc123.ngrok.io` на ваш URL из ngrok)

#### Шаг 4: Обновите код

Откройте `app.py` и измените:
```python
AVITO_REDIRECT_URI = "https://abc123.ngrok.io/callback"
```

#### Шаг 5: Перезапустите сервер

```bash
# Остановите текущий сервер (Ctrl+C)
cd /Users/ilaeliseenko/Desktop/avito-messenger
python3 app.py
```

#### Шаг 6: Откройте приложение через ngrok URL

```
https://abc123.ngrok.io
```

### ✅ Вариант 3: Попробовать без порта

Некоторые системы не принимают нестандартные порты. Попробуйте:
```
http://127.0.0.1/callback
```

Но тогда нужно запустить сервер на порту 80 (требует sudo):
```bash
sudo python3 app.py
```

И изменить в коде:
```python
port = 80
```

### ✅ Вариант 4: Использовать HTTPS с самоподписанным сертификатом

Если Avito требует HTTPS:
```
https://127.0.0.1:5002/callback
```

## Рекомендация

**Используйте ngrok (Вариант 2)** - это самый надежный способ для локальной разработки с внешними API.

## После успешного добавления Redirect URI

1. Нажмите "Запросить доступ" в форме Avito
2. Дождитесь подтверждения
3. Обновите `AVITO_REDIRECT_URI` в `app.py`
4. Перезапустите сервер
5. Попробуйте авторизацию снова

