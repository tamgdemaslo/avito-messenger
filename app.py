#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Avito Messenger Web Application
Backend для работы с API Avito Messenger
"""

from flask import Flask, render_template, request, jsonify, redirect, session, url_for
from flask_cors import CORS
import requests
import os
from datetime import datetime
import json

# Получаем абсолютный путь к директории проекта
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, 
            template_folder=os.path.join(BASE_DIR, 'templates'),
            static_folder=os.path.join(BASE_DIR, 'static'),
            static_url_path='/static')

# Используем переменную окружения для secret_key в продакшене
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))
CORS(app)

# Разрешаем доступ ко всем статическим файлам
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# Конфигурация Avito API
# Используем переменные окружения для продакшена
AVITO_CLIENT_ID = os.environ.get('AVITO_CLIENT_ID', "HHiafcJb3rn8agxhzM8g")
AVITO_CLIENT_SECRET = os.environ.get('AVITO_CLIENT_SECRET', "DusHGZF4gADWpNwIHbeefVNwxqoUXe5i_LQ2_g2o")
AVITO_REDIRECT_URI = os.environ.get('AVITO_REDIRECT_URI', "http://localhost:5002/callback")
AVITO_AUTH_URL = "https://api.avito.ru/oauth"
AVITO_API_URL = "https://api.avito.ru"

# Хранилище токенов (в продакшене использовать БД)
tokens = {}


@app.route('/')
def index():
    """Главная страница"""
    try:
        # Проверяем, что шаблон существует
        template_path = os.path.join(app.template_folder, 'index.html')
        if not os.path.exists(template_path):
            # Возвращаем простую HTML страницу если шаблон не найден
            return """
            <!DOCTYPE html>
            <html>
            <head><meta charset="UTF-8"><title>Avito Messenger</title></head>
            <body>
                <h1>Ошибка: шаблон не найден</h1>
                <p>Путь: {}</p>
                <p>Проверьте, что файл templates/index.html существует</p>
            </body>
            </html>
            """.format(template_path), 500
        return render_template('index.html')
    except Exception as e:
        import traceback
        error_msg = f"Ошибка загрузки шаблона: {str(e)}\n{traceback.format_exc()}"
        return f"<html><head><meta charset='UTF-8'></head><body><pre>{error_msg}</pre></body></html>", 500


@app.route('/test')
def test():
    """Тестовая страница для проверки работы"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Test - Flask работает!</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; }
            h1 { color: #00a046; }
            .success { background: #d4edda; padding: 15px; border-radius: 5px; margin: 20px 0; }
            code { background: #f0f0f0; padding: 2px 6px; border-radius: 3px; }
        </style>
    </head>
    <body>
        <h1>✅ Flask работает!</h1>
        <div class="success">
            <p>Если вы видите это сообщение, значит Flask запущен правильно.</p>
        </div>
        <p><strong>Важно:</strong> Убедитесь, что в адресной строке указан порт:</p>
        <p>Правильно: <code>http://localhost:5001</code></p>
        <p>Неправильно: <code>http://localhost</code> (без порта)</p>
        <p><a href="/test-oauth">→ Проверить OAuth настройки</a></p>
        <p><a href="/">→ Перейти на главную страницу</a></p>
    </body>
    </html>
    """


@app.route('/test-oauth')
def test_oauth():
    """Тестовая страница для проверки OAuth настроек"""
    from urllib.parse import urlencode
    scopes = "messenger:read messenger:write"
    params = {
        'client_id': AVITO_CLIENT_ID,
        'response_type': 'code',
        'redirect_uri': AVITO_REDIRECT_URI,
        'scope': scopes
    }
    auth_url = f"{AVITO_AUTH_URL}/authorize?{urlencode(params)}"
    
    return render_template('test_oauth.html',
                         client_id=AVITO_CLIENT_ID,
                         redirect_uri=AVITO_REDIRECT_URI,
                         scopes=scopes,
                         auth_url=auth_url)


@app.errorhandler(404)
def not_found(error):
    return "Страница не найдена", 404


@app.errorhandler(500)
def internal_error(error):
    return f"Внутренняя ошибка сервера: {str(error)}", 500


@app.route('/login')
def login():
    """Инициация OAuth авторизации"""
    from urllib.parse import urlencode
    
    # Добавляем необходимые scopes для работы с сообщениями
    # Avito использует пробелы для разделения scopes
    scopes = "messenger:read messenger:write"
    
    # Правильный URL для OAuth авторизации Avito
    params = {
        'client_id': AVITO_CLIENT_ID,
        'response_type': 'code',
        'redirect_uri': AVITO_REDIRECT_URI,
        'scope': scopes
    }
    
    auth_url = f"{AVITO_AUTH_URL}/authorize?{urlencode(params)}"
    
    # Логируем для отладки
    print("=" * 60)
    print("OAuth авторизация:")
    print(f"Client ID: {AVITO_CLIENT_ID}")
    print(f"Redirect URI: {AVITO_REDIRECT_URI}")
    print(f"Scopes: {scopes}")
    print(f"Auth URL: {auth_url}")
    print("=" * 60)
    
    return redirect(auth_url)


@app.route('/callback')
def callback():
    """OAuth callback обработчик"""
    code = request.args.get('code')
    if not code:
        return jsonify({"error": "No authorization code"}), 400
    
    # Обмен кода на токен
    token_data = {
        "grant_type": "authorization_code",
        "client_id": AVITO_CLIENT_ID,
        "client_secret": AVITO_CLIENT_SECRET,
        "code": code,
        "redirect_uri": AVITO_REDIRECT_URI
    }
    
    try:
        response = requests.post(
            f"{AVITO_AUTH_URL}/token",
            data=token_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code == 200:
            token_info = response.json()
            access_token = token_info.get('access_token')
            refresh_token = token_info.get('refresh_token')
            
            # Сохраняем токены
            session['access_token'] = access_token
            session['refresh_token'] = refresh_token
            tokens['access_token'] = access_token
            tokens['refresh_token'] = refresh_token
            
            return redirect(url_for('messages'))
        else:
            return jsonify({
                "error": "Failed to get token",
                "details": response.text
            }), response.status_code
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def get_access_token():
    """Получить актуальный access token"""
    if 'access_token' in session:
        return session['access_token']
    return tokens.get('access_token')


def refresh_access_token():
    """Обновить access token используя refresh token"""
    refresh_token = session.get('refresh_token') or tokens.get('refresh_token')
    if not refresh_token:
        return None
    
    token_data = {
        "grant_type": "refresh_token",
        "client_id": AVITO_CLIENT_ID,
        "client_secret": AVITO_CLIENT_SECRET,
        "refresh_token": refresh_token
    }
    
    try:
        response = requests.post(
            f"{AVITO_AUTH_URL}/token",
            data=token_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code == 200:
            token_info = response.json()
            access_token = token_info.get('access_token')
            session['access_token'] = access_token
            tokens['access_token'] = access_token
            return access_token
    except Exception as e:
        print(f"Error refreshing token: {e}")
    
    return None


def make_avito_request(method, endpoint, data=None, retry=True):
    """Выполнить запрос к Avito API"""
    access_token = get_access_token()
    if not access_token:
        return None, "No access token"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    url = f"{AVITO_API_URL}{endpoint}"
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data)
        elif method == "PUT":
            response = requests.put(url, headers=headers, json=data)
        else:
            return None, "Unsupported method"
        
        # Если токен истек, попробуем обновить
        if response.status_code == 401 and retry:
            new_token = refresh_access_token()
            if new_token:
                return make_avito_request(method, endpoint, data, retry=False)
        
        if response.status_code == 200:
            return response.json(), None
        else:
            return None, f"API error: {response.status_code} - {response.text}"
            
    except Exception as e:
        return None, str(e)


@app.route('/messages')
def messages():
    """Страница с сообщениями"""
    if not get_access_token():
        return redirect(url_for('login'))
    return render_template('messages.html')


@app.route('/api/messages', methods=['GET'])
def get_messages():
    """Получить список сообщений"""
    # Получаем user_id из профиля
    profile, error = make_avito_request("GET", "/core/v1/accounts/self")
    if error:
        return jsonify({"error": error}), 500
    
    user_id = profile.get('id')
    if not user_id:
        return jsonify({"error": "Could not get user ID"}), 500
    
    # Получаем чаты
    chats, error = make_avito_request("GET", f"/messenger/v2/accounts/{user_id}/chats")
    if error:
        return jsonify({"error": error}), 500
    
    # Получаем сообщения для каждого чата
    all_messages = []
    if chats and isinstance(chats, dict) and 'chats' in chats:
        for chat in chats['chats']:
            chat_id = chat.get('id')
            if chat_id:
                messages_data, msg_error = make_avito_request(
                    "GET",
                    f"/messenger/v2/accounts/{user_id}/chats/{chat_id}/messages"
                )
                if not msg_error and messages_data:
                    messages_list = messages_data.get('messages', [])
                    for msg in messages_list:
                        msg['chat_id'] = chat_id
                        msg['chat_info'] = chat
                    all_messages.extend(messages_list)
    
    # Сортируем по дате (новые первыми)
    all_messages.sort(
        key=lambda x: x.get('created', 0),
        reverse=True
    )
    
    return jsonify({
        "messages": all_messages,
        "chats": chats.get('chats', []) if chats else []
    })


@app.route('/api/chats', methods=['GET'])
def get_chats():
    """Получить список чатов"""
    profile, error = make_avito_request("GET", "/core/v1/accounts/self")
    if error:
        return jsonify({"error": error}), 500
    
    user_id = profile.get('id')
    if not user_id:
        return jsonify({"error": "Could not get user ID"}), 500
    
    chats, error = make_avito_request("GET", f"/messenger/v2/accounts/{user_id}/chats")
    if error:
        return jsonify({"error": error}), 500
    
    return jsonify(chats if chats else {"chats": []})


@app.route('/api/messages/send', methods=['POST'])
def send_message():
    """Отправить сообщение"""
    data = request.json
    chat_id = data.get('chat_id')
    message_text = data.get('message')
    
    if not chat_id or not message_text:
        return jsonify({"error": "chat_id and message are required"}), 400
    
    profile, error = make_avito_request("GET", "/core/v1/accounts/self")
    if error:
        return jsonify({"error": error}), 500
    
    user_id = profile.get('id')
    if not user_id:
        return jsonify({"error": "Could not get user ID"}), 500
    
    # Отправляем сообщение
    message_data = {
        "message": {
            "text": message_text
        }
    }
    
    result, error = make_avito_request(
        "POST",
        f"/messenger/v2/accounts/{user_id}/chats/{chat_id}/messages",
        message_data
    )
    
    if error:
        return jsonify({"error": error}), 500
    
    return jsonify({"success": True, "data": result})


@app.route('/api/profile', methods=['GET'])
def get_profile():
    """Получить информацию о профиле"""
    profile, error = make_avito_request("GET", "/core/v1/accounts/self")
    if error:
        return jsonify({"error": error}), 500
    
    return jsonify(profile if profile else {})


@app.route('/logout')
def logout():
    """Выход из системы"""
    session.clear()
    tokens.clear()
    return redirect(url_for('index'))


if __name__ == '__main__':
    print("=" * 50)
    print("Avito Messenger запускается...")
    print("Откройте в браузере: http://localhost:5000")
    print("=" * 50)
    print(f"Рабочая директория: {BASE_DIR}")
    print(f"Шаблоны: {app.template_folder}")
    print(f"Статика: {app.static_folder}")
    print("=" * 50)
    try:
        # Запускаем с разрешением доступа со всех интерфейсов
        # Используем порт 5002, так как 5000 и 5001 могут быть заняты
        port = 5002
        print(f"\n🌐 Сервер запущен на порту {port}")
        print(f"📱 Откройте в браузере: http://localhost:{port}")
        print("=" * 50)
        app.run(debug=True, host='127.0.0.1', port=port, threaded=True, use_reloader=False)
    except PermissionError as e:
        print(f"Ошибка прав доступа: {e}")
        print("Попробуйте запустить с другим портом:")
        print("  Измените port=5000 на port=5001 в app.py")
    except Exception as e:
        print(f"Ошибка запуска: {e}")
        import traceback
        traceback.print_exc()

