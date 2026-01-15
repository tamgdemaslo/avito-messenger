#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Avito Messenger Web Application
Backend для работы с API Avito Messenger (Client Credentials Flow)
"""

from flask import Flask, render_template, request, jsonify, redirect, session, url_for
from flask_cors import CORS
import requests
import os
from datetime import datetime, timedelta
import json
import telegram_client
import whatsapp_client
import database
import yclients_client
import notifications

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
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response

# Обработка OPTIONS запросов для CORS
@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        response = jsonify({})
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add('Access-Control-Allow-Headers', "Content-Type,Authorization")
        response.headers.add('Access-Control-Allow-Methods', "GET,PUT,POST,DELETE,OPTIONS")
        return response

# Конфигурация Avito API - используем персональную авторизацию
AVITO_CLIENT_ID = os.environ.get('AVITO_CLIENT_ID', "1cIpj04gx6i3v7Ym5wNj")
AVITO_CLIENT_SECRET = os.environ.get('AVITO_CLIENT_SECRET', "IncASFD6M42y86XctwJitqCwHVE5y7AivuOgkfoK")
AVITO_API_URL = "https://api.avito.ru"

# Хранилище токена
token_cache = {
    'access_token': None,
    'expires_at': None
}


def get_avito_token():
    """Получить access token используя client_credentials"""
    # Проверяем кэш
    if token_cache['access_token'] and token_cache['expires_at']:
        if datetime.now() < token_cache['expires_at']:
            return token_cache['access_token']
    
    # Получаем новый токен
    token_url = f"{AVITO_API_URL}/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": AVITO_CLIENT_ID,
        "client_secret": AVITO_CLIENT_SECRET
    }
    
    try:
        response = requests.post(
            token_url,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code == 200:
            token_info = response.json()
            access_token = token_info.get('access_token')
            expires_in = token_info.get('expires_in', 86400)  # По умолчанию 24 часа
            
            # Сохраняем в кэш
            token_cache['access_token'] = access_token
            token_cache['expires_at'] = datetime.now() + timedelta(seconds=expires_in - 300)  # -5 минут для безопасности
            
            return access_token
        else:
            print(f"Error getting token: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Exception getting token: {e}")
        return None


def make_avito_request(method, endpoint, data=None):
    """Выполнить запрос к Avito API"""
    access_token = get_avito_token()
    if not access_token:
        return None, "Failed to get access token"
    
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
        
        if response.status_code == 200:
            return response.json(), None
        else:
            return None, f"API error: {response.status_code} - {response.text}"
            
    except Exception as e:
        return None, str(e)


@app.route('/')
def index():
    """Главная страница - сразу показываем сообщения"""
    return redirect(url_for('messages'))


@app.route('/messages')
def messages():
    """Страница с сообщениями"""
    return render_template('messages.html')


@app.route('/api/profile', methods=['GET'])
def get_profile():
    """Получить информацию о профиле"""
    profile, error = make_avito_request("GET", "/core/v1/accounts/self")
    if error:
        return jsonify({"error": error}), 500
    
    return jsonify(profile if profile else {})


@app.route('/api/chats', methods=['GET', 'OPTIONS'])
def get_chats():
    """Получить объединенный список чатов из Avito и Telegram"""
    # Проверяем отложенные задачи и новые записи YClients при запросе чатов
    check_scheduled_messages()
    check_new_yclients_records()
    
    try:
        all_chats = []
        current_user_id = None
        
        # === AVITO ЧАТЫ ===
        try:
            profile, error = make_avito_request("GET", "/core/v1/accounts/self")
            if not error and profile:
                user_id = profile.get('id')
                current_user_id = user_id
                
                if user_id:
                    print(f"Got Avito user_id: {user_id}")
                    chats_data, chats_error = make_avito_request("GET", f"/messenger/v2/accounts/{user_id}/chats")
                    
                    if not chats_error and chats_data and isinstance(chats_data, dict) and 'chats' in chats_data:
                        avito_chats = chats_data['chats']
                        # Помечаем как Avito
                        for chat in avito_chats:
                            chat['source'] = 'avito'
                            chat['source_icon'] = 'avito'
                        all_chats.extend(avito_chats)
                        print(f"Loaded {len(avito_chats)} Avito chats")
                    elif chats_error:
                        print(f"⚠️ Avito error (может требоваться подписка): {chats_error}")
        except Exception as e:
            print(f"⚠️ Avito chats error (skipping): {e}")
        
        # === TELEGRAM ЧАТЫ ===
        try:
            telegram_chats = telegram_client.get_telegram_chats(limit=100)
            if telegram_chats:
                print(f"Loaded {len(telegram_chats)} Telegram chats")
                all_chats.extend(telegram_chats)
        except Exception as e:
            print(f"Telegram chats error (skipping): {e}")
        
        # === WHATSAPP ЧАТЫ ===
        try:
            # Сначала проверяем статус
            status = whatsapp_client.get_whatsapp_status()
            if status.get('ready'):
                whatsapp_chats = whatsapp_client.get_whatsapp_chats(limit=30)
                if whatsapp_chats:
                    print(f"Loaded {len(whatsapp_chats)} WhatsApp chats")
                    all_chats.extend(whatsapp_chats)
            else:
                print(f"⚠️ WhatsApp not ready: {status}")
        except Exception as e:
            print(f"WhatsApp chats error (skipping): {e}")
        
        # Сортируем по времени обновления (новые сверху)
        all_chats.sort(key=lambda x: x.get('updated', 0), reverse=True)
        
        print(f"Total chats: {len(all_chats)}")
        
        return jsonify({
            "chats": all_chats,
            "current_user_id": current_user_id,
            "sources": {
                "avito": len([c for c in all_chats if c.get('source') == 'avito']),
                "telegram": len([c for c in all_chats if c.get('source') == 'telegram']),
                "whatsapp": len([c for c in all_chats if c.get('source') == 'whatsapp'])
            }
        })
    except Exception as e:
        import traceback
        print(f"Error in get_chats: {e}\n{traceback.format_exc()}")
        return jsonify({
            "error": str(e),
            "chats": [],
            "current_user_id": None,
            "sources": {"avito": 0, "telegram": 0, "whatsapp": 0}
        }), 500


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
                    f"/messenger/v3/accounts/{user_id}/chats/{chat_id}/messages/"
                )
                if not msg_error and messages_data:
                    messages_list = messages_data if isinstance(messages_data, list) else []
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


@app.route('/api/chats/<chat_id>/messages', methods=['GET'])
def get_chat_messages(chat_id):
    """Получить сообщения конкретного чата (Avito, Telegram или WhatsApp)"""
    print(f"Fetching messages for chat_id: {chat_id}")
    
    # Определяем источник по префиксу ID
    if chat_id.startswith('wa_'):
        # === WHATSAPP ===
        try:
            messages_list = whatsapp_client.get_whatsapp_messages(chat_id, limit=30)
            
            return jsonify({
                "messages": messages_list,
                "chat_id": chat_id,
                "chat_info": None,
                "current_user_id": None,
                "source": "whatsapp"
            })
        except Exception as e:
            print(f"WhatsApp messages error: {e}")
            return jsonify({"error": f"WhatsApp error: {str(e)}"}), 500
    
    elif chat_id.startswith('tg_'):
        # === TELEGRAM ===
        try:
            messages_list = telegram_client.get_telegram_messages(chat_id, limit=30)
            
            # Получаем информацию о чате
            telegram_chats = telegram_client.get_telegram_chats(limit=100)
            chat_info = next((c for c in telegram_chats if c['id'] == chat_id), None)
            
            # Преобразуем формат сообщений для единого интерфейса
            for msg in messages_list:
                if 'content' not in msg:
                    msg['content'] = {'text': msg.get('text', '')}
                msg['source'] = 'telegram'
            
            return jsonify({
                "messages": messages_list,
                "chat_id": chat_id,
                "chat_info": chat_info,
                "current_user_id": None,
                "source": "telegram"
            })
        except Exception as e:
            print(f"Telegram messages error: {e}")
            return jsonify({"error": f"Telegram error: {str(e)}"}), 500
    
    else:
        # === AVITO ===
        profile, error = make_avito_request("GET", "/core/v1/accounts/self")
        if error:
            print(f"Error getting profile: {error}")
            return jsonify({"error": error}), 500
        
        user_id = profile.get('id')
        if not user_id:
            print(f"No user ID in profile: {profile}")
            return jsonify({"error": "Could not get user ID"}), 500
        
        # Получаем информацию о чате (для пользователей)
        chats_data, chats_error = make_avito_request("GET", f"/messenger/v2/accounts/{user_id}/chats")
        chat_info = None
        if not chats_error and chats_data and 'chats' in chats_data:
            for chat in chats_data['chats']:
                if chat.get('id') == chat_id:
                    chat_info = chat
                    break
        
        # Получаем сообщения для чата (только последние 30 для скорости)
        messages_data, error = make_avito_request(
            "GET",
            f"/messenger/v3/accounts/{user_id}/chats/{chat_id}/messages/?limit=30"
        )
        
        if error:
            print(f"Error getting messages: {error}")
            return jsonify({"error": error}), 500
        
        # Обрабатываем ответ
        if isinstance(messages_data, dict):
            messages_list = messages_data.get('messages', [])
        elif isinstance(messages_data, list):
            messages_list = messages_data
        else:
            messages_list = []
        
        # Помечаем как Avito
        for msg in messages_list:
            msg['source'] = 'avito'
        
        print(f"Number of Avito messages: {len(messages_list)}")
        
        return jsonify({
            "messages": messages_list,
            "chat_id": chat_id,
            "chat_info": chat_info,
            "current_user_id": user_id,
            "source": "avito"
        })


@app.route('/api/messages/send', methods=['POST'])
def send_message():
    """Отправить сообщение (Avito, Telegram или WhatsApp)"""
    data = request.json
    chat_id = data.get('chat_id')
    message_text = data.get('message')
    
    if not chat_id or not message_text:
        return jsonify({"error": "chat_id and message are required"}), 400
    
    # Определяем источник
    if chat_id.startswith('wa_'):
        # === WHATSAPP ===
        try:
            result = whatsapp_client.send_whatsapp_message(chat_id, message_text)
            if result and result.get('success'):
                return jsonify({"success": True, "data": result})
            else:
                return jsonify({"error": result.get('error', 'Unknown error')}), 500
        except Exception as e:
            return jsonify({"error": f"WhatsApp error: {str(e)}"}), 500
    
    elif chat_id.startswith('tg_'):
        # === TELEGRAM ===
        try:
            result = telegram_client.send_telegram_message(chat_id, message_text)
            if result and result.get('success'):
                return jsonify({"success": True, "data": result})
            else:
                return jsonify({"error": result.get('error', 'Unknown error')}), 500
        except Exception as e:
            return jsonify({"error": f"Telegram error: {str(e)}"}), 500
    
    else:
        # === AVITO ===
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
            },
            "type": "text"
        }
        
        result, error = make_avito_request(
            "POST",
            f"/messenger/v1/accounts/{user_id}/chats/{chat_id}/messages",
            message_data
        )
        
        if error:
            return jsonify({"error": error}), 500
        
        return jsonify({"success": True, "data": result})


@app.route('/api/messages/delete', methods=['POST'])
def delete_message():
    """Удалить сообщение"""
    data = request.json
    chat_id = data.get('chat_id')
    message_id = data.get('message_id')
    
    if not chat_id or not message_id:
        return jsonify({"error": "chat_id and message_id are required"}), 400
    
    profile, error = make_avito_request("GET", "/core/v1/accounts/self")
    if error:
        return jsonify({"error": error}), 500
    
    user_id = profile.get('id')
    if not user_id:
        return jsonify({"error": "Could not get user ID"}), 500
    
    result, error = make_avito_request(
        "POST",
        f"/messenger/v1/accounts/{user_id}/chats/{chat_id}/messages/{message_id}"
    )
    
    if error:
        return jsonify({"error": error}), 500
    
    return jsonify({"success": True, "data": result})


@app.route('/api/chats/<chat_id>/read', methods=['POST'])
def mark_chat_read(chat_id):
    """Пометить чат как прочитанный (Avito, Telegram или WhatsApp)"""
    
    # Определяем источник по префиксу ID
    if chat_id.startswith('wa_'):
        # === WHATSAPP ===
        try:
            result = whatsapp_client.mark_whatsapp_read(chat_id)
            if result and result.get('success'):
                return jsonify({"success": True})
            else:
                return jsonify({"error": result.get('error', 'Unknown error')}), 500
        except Exception as e:
            return jsonify({"error": f"WhatsApp error: {str(e)}"}), 500
    
    elif chat_id.startswith('tg_'):
        # === TELEGRAM ===
        try:
            result = telegram_client.mark_telegram_read(chat_id)
            if result and result.get('success'):
                return jsonify({"success": True})
            else:
                return jsonify({"error": result.get('error', 'Unknown error')}), 500
        except Exception as e:
            return jsonify({"error": f"Telegram error: {str(e)}"}), 500
    
    else:
        # === AVITO ===
        profile, error = make_avito_request("GET", "/core/v1/accounts/self")
        if error:
            return jsonify({"error": error}), 500
        
        user_id = profile.get('id')
        if not user_id:
            return jsonify({"error": "Could not get user ID"}), 500
        
        result, error = make_avito_request(
            "POST",
            f"/messenger/v1/accounts/{user_id}/chats/{chat_id}/read"
        )
        
        if error:
            return jsonify({"error": error}), 500
        
        return jsonify({"success": True, "data": result})


@app.route('/api/images/upload', methods=['POST'])
def upload_image():
    """Загрузить изображение"""
    if 'image' not in request.files:
        return jsonify({"error": "No image file provided"}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    profile, error = make_avito_request("GET", "/core/v1/accounts/self")
    if error:
        return jsonify({"error": error}), 500
    
    user_id = profile.get('id')
    if not user_id:
        return jsonify({"error": "Could not get user ID"}), 500
    
    # Подготовка multipart/form-data запроса
    files = {'uploadfile[]': (file.filename, file.stream, file.content_type)}
    
    token = get_avito_token()
    if not token:
        return jsonify({"error": "No access token"}), 401
    
    headers = {
        'Authorization': f'Bearer {token}'
    }
    
    try:
        response = requests.post(
            f"{AVITO_API_URL}/messenger/v1/accounts/{user_id}/uploadImages",
            files=files,
            headers=headers
        )
        response.raise_for_status()
        return jsonify({"success": True, "data": response.json()})
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/messages/send-image', methods=['POST'])
def send_image_message():
    """Отправить сообщение с изображением"""
    data = request.json
    chat_id = data.get('chat_id')
    image_id = data.get('image_id')
    
    if not chat_id or not image_id:
        return jsonify({"error": "chat_id and image_id are required"}), 400
    
    profile, error = make_avito_request("GET", "/core/v1/accounts/self")
    if error:
        return jsonify({"error": error}), 500
    
    user_id = profile.get('id')
    if not user_id:
        return jsonify({"error": "Could not get user ID"}), 500
    
    image_data = {"image_id": image_id}
    
    result, error = make_avito_request(
        "POST",
        f"/messenger/v1/accounts/{user_id}/chats/{chat_id}/messages/image",
        image_data
    )
    
    if error:
        return jsonify({"error": error}), 500
    
    return jsonify({"success": True, "data": result})


@app.route('/api/voice/get', methods=['GET'])
def get_voice_messages():
    """Получить голосовые сообщения"""
    voice_ids = request.args.getlist('voice_ids')
    
    if not voice_ids:
        return jsonify({"error": "voice_ids parameter is required"}), 400
    
    profile, error = make_avito_request("GET", "/core/v1/accounts/self")
    if error:
        return jsonify({"error": error}), 500
    
    user_id = profile.get('id')
    if not user_id:
        return jsonify({"error": "Could not get user ID"}), 500
    
    # Формируем query string с массивом voice_ids
    query_params = '&'.join([f'voice_ids={vid}' for vid in voice_ids])
    
    result, error = make_avito_request(
        "GET",
        f"/messenger/v1/accounts/{user_id}/getVoiceFiles?{query_params}"
    )
    
    if error:
        return jsonify({"error": error}), 500
    
    return jsonify({"success": True, "data": result})


@app.route('/api/blacklist/add', methods=['POST'])
def add_to_blacklist():
    """Добавить пользователя в черный список"""
    data = request.json
    users = data.get('users', [])
    
    if not users:
        return jsonify({"error": "users array is required"}), 400
    
    profile, error = make_avito_request("GET", "/core/v1/accounts/self")
    if error:
        return jsonify({"error": error}), 500
    
    user_id = profile.get('id')
    if not user_id:
        return jsonify({"error": "Could not get user ID"}), 500
    
    blacklist_data = {"users": users}
    
    result, error = make_avito_request(
        "POST",
        f"/messenger/v2/accounts/{user_id}/blacklist",
        blacklist_data
    )
    
    if error:
        return jsonify({"error": error}), 500
    
    return jsonify({"success": True, "data": result})


@app.route('/api/webhooks/list', methods=['POST'])
def list_webhooks():
    """Получить список подписок"""
    result, error = make_avito_request(
        "POST",
        "/messenger/v1/subscriptions"
    )
    
    if error:
        return jsonify({"error": error}), 500
    
    return jsonify({"success": True, "data": result})


@app.route('/api/webhooks/subscribe', methods=['POST'])
def subscribe_webhook():
    """Подписаться на webhook уведомления"""
    data = request.json
    url = data.get('url')
    
    if not url:
        return jsonify({"error": "url is required"}), 400
    
    webhook_data = {"url": url}
    
    result, error = make_avito_request(
        "POST",
        "/messenger/v3/webhook",
        webhook_data
    )
    
    if error:
        return jsonify({"error": error}), 500
    
    return jsonify({"success": True, "data": result})


@app.route('/api/webhooks/unsubscribe', methods=['POST'])
def unsubscribe_webhook():
    """Отписаться от webhook уведомлений"""
    data = request.json
    url = data.get('url')
    
    if not url:
        return jsonify({"error": "url is required"}), 400
    
    webhook_data = {"url": url}
    
    result, error = make_avito_request(
        "POST",
        "/messenger/v1/webhook/unsubscribe",
        webhook_data
    )
    
    if error:
        return jsonify({"error": error}), 500
    
    return jsonify({"success": True, "data": result})


@app.route('/api/chats/<chat_id>/info', methods=['GET'])
def get_chat_info(chat_id):
    """Получить информацию о конкретном чате"""
    profile, error = make_avito_request("GET", "/core/v1/accounts/self")
    if error:
        return jsonify({"error": error}), 500
    
    user_id = profile.get('id')
    if not user_id:
        return jsonify({"error": "Could not get user ID"}), 500
    
    result, error = make_avito_request(
        "GET",
        f"/messenger/v2/accounts/{user_id}/chats/{chat_id}"
    )
    
    if error:
        return jsonify({"error": error}), 500
    
    return jsonify({"success": True, "data": result})


@app.route('/api/telegram/auth', methods=['POST'])
def telegram_auth():
    """Авторизация в Telegram"""
    data = request.json
    phone = data.get('phone', '+79992556031')
    code = data.get('code')
    password = data.get('password')
    
    try:
        result = telegram_client.authorize_telegram(phone, code, password)
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/telegram/status', methods=['GET'])
def telegram_status():
    """Проверить статус авторизации Telegram"""
    try:
        # Инициализируем клиент
        telegram_client.run_async(telegram_client.init_telegram_client())
        if telegram_client.telegram_client and telegram_client.telegram_client.is_connected():
            is_auth = telegram_client.run_async(telegram_client.telegram_client.is_user_authorized())
            return jsonify({
                "connected": True,
                "authorized": is_auth
            })
        return jsonify({"connected": False, "authorized": False})
    except Exception as e:
        return jsonify({"connected": False, "authorized": False, "error": str(e)})


@app.route('/telegram/auth')
def telegram_auth_page():
    """Страница авторизации Telegram"""
    return render_template('telegram_auth.html')


@app.route('/whatsapp/auth')
def whatsapp_auth_page():
    """Страница авторизации WhatsApp"""
    return render_template('whatsapp_auth.html')


@app.route('/api/whatsapp/status', methods=['GET'])
def whatsapp_status():
    """Проверить статус WhatsApp клиента"""
    try:
        status = whatsapp_client.get_whatsapp_status()
        return jsonify(status)
    except Exception as e:
        return jsonify({"ready": False, "error": str(e)})


@app.route('/api/whatsapp/qr', methods=['GET'])
def whatsapp_qr():
    """Получить QR код для авторизации WhatsApp"""
    try:
        qr_data = whatsapp_client.get_whatsapp_qr()
        if qr_data:
            return jsonify(qr_data)
        else:
            return jsonify({"error": "QR код не доступен"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/telegram/avatar/<chat_id>', methods=['GET'])
def get_telegram_avatar(chat_id):
    """Ленивая загрузка аватарки Telegram чата"""
    try:
        avatar_url = telegram_client.download_telegram_avatar(chat_id)
        if avatar_url:
            return jsonify({"success": True, "avatar": avatar_url})
        else:
            return jsonify({"success": False, "message": "No avatar"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/test')
def test():
    """Тестовая страница"""
    token = get_avito_token()
    return f"""
    <html>
    <head><title>Test</title></head>
    <body>
        <h1>Avito Messenger - Test</h1>
        <p>Token получен: {'Да' if token else 'Нет'}</p>
        <p>Token: {token[:20] if token else 'Отсутствует'}...</p>
        <p><a href="/messages">Перейти к сообщениям</a></p>
    </body>
    </html>
    """


# === API для работы с данными клиентов ===

@app.route('/api/customers/<source>/<source_id>', methods=['GET'])
def get_customer_info(source, source_id):
    """Получить информацию о клиенте"""
    try:
        customer = database.get_customer(source, source_id)
        if customer:
            return jsonify(customer)
        else:
            return jsonify({
                'source': source,
                'source_id': source_id,
                'vin': None,
                'phone': None,
                'comments': None
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/customers/<source>/<source_id>', methods=['POST'])
def update_customer_info(source, source_id):
    """Обновить информацию о клиенте"""
    try:
        data = request.json
        name = data.get('name')
        vin = data.get('vin')
        phone = data.get('phone')
        comments = data.get('comments')
        
        customer = database.save_customer(
            source=source,
            source_id=source_id,
            name=name,
            vin=vin,
            phone=phone,
            comments=comments
        )
        
        return jsonify({"success": True, "customer": customer})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/customers/search', methods=['GET'])
def search_customers():
    """Поиск клиентов"""
    try:
        query = request.args.get('q', '')
        if not query:
            return jsonify([])
        
        results = database.search_customers(query)
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# === API для работы с YClients ===

@app.route('/api/yclients/status', methods=['GET'])
def yclients_status():
    """Проверить настроен ли YClients"""
    try:
        configured = yclients_client.is_yclients_configured()
        return jsonify({
            "configured": configured,
            "company_id": yclients_client.YCLIENTS_COMPANY_ID if configured else None
        })
    except Exception as e:
        return jsonify({"configured": False, "error": str(e)})


@app.route('/api/yclients/services', methods=['GET'])
def get_yclients_services():
    """Получить список услуг YClients"""
    try:
        if not yclients_client.is_yclients_configured():
            return jsonify({"error": "YClients не настроен. Добавьте YCLIENTS_PARTNER_TOKEN и YCLIENTS_COMPANY_ID"}), 400
        
        print(f"Loading YClients services for company {yclients_client.YCLIENTS_COMPANY_ID}")
        services = yclients_client.get_services()
        print(f"YClients returned {len(services) if isinstance(services, list) else 'unknown'} services")
        return jsonify(services)
    except Exception as e:
        print(f"YClients services error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/yclients/staff', methods=['GET'])
def get_yclients_staff():
    """Получить список мастеров"""
    try:
        service_ids = request.args.get('service_ids')
        staff = yclients_client.get_staff(service_ids=[int(service_ids)] if service_ids else None)
        return jsonify(staff)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/yclients/dates', methods=['GET'])
def get_yclients_dates():
    """Получить доступные даты"""
    try:
        dates = yclients_client.get_book_dates()
        return jsonify(dates)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/yclients/slots', methods=['GET'])
def get_yclients_slots():
    """Получить свободные слоты"""
    try:
        staff_id = request.args.get('staff_id')
        service_id = request.args.get('service_id')
        date_iso = request.args.get('date')
        
        if not all([staff_id, service_id, date_iso]):
            return jsonify({"error": "Missing required parameters"}), 400
        
        slots = yclients_client.get_free_slots(
            staff_id=int(staff_id),
            date_iso=date_iso,
            service_ids=[int(service_id)]
        )
        return jsonify(slots)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/yclients/book', methods=['POST'])
def create_yclients_booking():
    """Создать запись клиента в YClients"""
    try:
        # Проверяем конфигурацию YClients
        if not yclients_client.is_yclients_configured():
            return jsonify({
                "error": "YClients не настроен. Добавьте YCLIENTS_PARTNER_TOKEN и YCLIENTS_COMPANY_ID в переменные окружения"
            }), 400
        
        data = request.json
        if not data:
            return jsonify({"error": "Request body is required"}), 400
        
        phone = data.get('phone')
        fullname = data.get('fullname')
        appointments = data.get('appointments')
        comment = data.get('comment')
        
        if not all([phone, fullname, appointments]):
            return jsonify({
                "error": "Missing required fields",
                "details": {
                    "phone": bool(phone),
                    "fullname": bool(fullname),
                    "appointments": bool(appointments)
                }
            }), 400
        
        result = yclients_client.create_booking(
            phone=phone,
            fullname=fullname,
            appointments=appointments,
            comment=comment
        )
        
        # После успешного создания записи отправляем уведомления
        try:
            # Получаем информацию о первой записи для формирования переменных
            first_appointment = appointments[0] if appointments else {}
            service_id = first_appointment.get('services', [first_appointment.get('service_id')])[0] if first_appointment.get('services') else first_appointment.get('service_id')
            staff_id = first_appointment.get('staff_id')
            datetime_str = first_appointment.get('datetime', '')
            
            # Получаем имена услуг и мастеров (если возможно)
            service_name = None
            staff_name = None
            try:
                services = yclients_client.get_services()
                if services and isinstance(services, list):
                    service = next((s for s in services if s.get('id') == service_id), None)
                    if service:
                        service_name = service.get('title') or service.get('name')
                
                staff_list = yclients_client.get_staff(service_ids=[service_id] if service_id else None)
                if staff_list and isinstance(staff_list, list):
                    staff = next((s for s in staff_list if s.get('id') == staff_id), None)
                    if staff:
                        staff_name = staff.get('name')
            except Exception as e:
                print(f"⚠️ Ошибка получения имен услуг/мастеров: {e}")
            
            # Формируем переменные для шаблонов
            template_variables = {
                'fullname': fullname,
                'phone': phone,
                'datetime': datetime_str,
                'service_name': service_name or f'Услуга #{service_id}' if service_id else 'Услуга',
                'staff_name': staff_name or f'Мастер #{staff_id}' if staff_id else 'Мастер',
                'comment': comment or ''
            }
            
            # Отправляем уведомление о записи
            success, message = notifications.send_notification(
                phone=phone,
                fullname=fullname,
                template_type='booking_confirmation',
                variables=template_variables
            )
            if success:
                print(f"✅ Уведомление о записи отправлено: {message}")
            else:
                print(f"⚠️ Не удалось отправить уведомление о записи: {message}")
            
            # Планируем отправку отзыва через 2 часа
            if datetime_str:
                notifications.schedule_review_request(
                    phone=phone,
                    fullname=fullname,
                    booking_datetime=datetime_str,
                    variables=template_variables
                )
        except Exception as e:
            # Ошибки уведомлений не должны влиять на успех создания записи
            print(f"⚠️ Ошибка отправки уведомлений: {e}")
        
        return jsonify({"success": True, "data": result})
    except requests.exceptions.HTTPError as e:
        error_msg = str(e)
        error_detail = None
        
        # Извлекаем детальное сообщение об ошибке из исключения
        if hasattr(e, 'error_detail'):
            error_detail = e.error_detail
            error_msg = error_detail
        
        # Если не нашли детали, пробуем извлечь из response
        if not error_detail:
            try:
                if hasattr(e, 'response') and e.response:
                    error_data = e.response.json()
                    if isinstance(error_data, dict):
                        # Пытаемся найти сообщение об ошибке в разных полях
                        if 'meta' in error_data and isinstance(error_data['meta'], dict):
                            error_msg = error_data['meta'].get('error', error_data['meta'].get('message', error_msg))
                        elif 'error' in error_data:
                            if isinstance(error_data['error'], list):
                                error_msg = "; ".join(str(x) for x in error_data['error'])
                            else:
                                error_msg = error_data['error']
                        elif 'message' in error_data:
                            error_msg = error_data['message']
                        elif 'errors' in error_data:
                            # Ошибки валидации
                            errors_dict = error_data['errors']
                            if isinstance(errors_dict, dict):
                                error_parts = []
                                for field, messages in errors_dict.items():
                                    if isinstance(messages, list):
                                        error_parts.append(f"{field}: {', '.join(str(m) for m in messages)}")
                                    elif isinstance(messages, dict):
                                        error_parts.append(f"{field}: {', '.join(str(v) for v in messages.values())}")
                                    else:
                                        error_parts.append(f"{field}: {messages}")
                                error_msg = "; ".join(error_parts) if error_parts else error_msg
                            else:
                                error_msg = str(errors_dict)
            except Exception as parse_err:
                print(f"⚠️ Could not parse error in app.py: {parse_err}")
        
        print(f"YClients HTTP error: {error_msg}")
        status_code = 500
        if hasattr(e, 'response') and e.response:
            status_code = e.response.status_code
        
        # Формируем детальный ответ
        error_response = {
            "error": f"YClients API error: {error_msg}",
            "status_code": status_code
        }
        
        # Добавляем полные детали ошибки для отладки
        if hasattr(e, 'error_data') and e.error_data:
            error_response["details"] = e.error_data
        elif hasattr(e, 'error_full') and e.error_full:
            try:
                # Пытаемся распарсить как JSON
                if isinstance(e.error_full, str):
                    try:
                        error_response["details"] = json.loads(e.error_full)
                    except json.JSONDecodeError:
                        error_response["details"] = {"raw": e.error_full}
                else:
                    error_response["details"] = e.error_full
            except Exception as parse_err:
                error_response["details"] = {"raw": str(e.error_full), "parse_error": str(parse_err)}
        
        # Также добавляем response.text если доступен
        if hasattr(e, 'response') and e.response and hasattr(e.response, 'text'):
            if 'details' not in error_response or not isinstance(error_response['details'], dict):
                error_response["details"] = {}
            error_response["details"]["response_text"] = e.response.text[:2000]  # Первые 2000 символов
        
        # Для 422 ошибок добавляем подсказку
        if status_code == 422:
            error_response["hint"] = "Ошибка валидации данных. Проверьте правильность заполнения всех полей."
        
        return jsonify(error_response), status_code
    except ValueError as e:
        print(f"YClients validation error: {e}")
        return jsonify({"error": f"Validation error: {str(e)}"}), 400
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"YClients booking error: {e}\n{error_trace}")
        
        # Проверяем, это ошибка валидации данных?
        error_msg = str(e)
        if "ValueError" in str(type(e).__name__) or "validation" in error_msg.lower():
            return jsonify({
                "error": f"Ошибка валидации данных: {error_msg}",
                "type": type(e).__name__,
                "details": "Проверьте формат данных: телефон, имя, услуга, мастер, дата и время должны быть заполнены корректно"
            }), 400
        
        return jsonify({
            "error": f"Внутренняя ошибка: {error_msg}",
            "type": type(e).__name__,
            "traceback": error_trace if app.debug else None
        }), 500


# === API для работы с шаблонами сообщений ===

@app.route('/api/templates', methods=['GET'])
def get_templates():
    """Получить все шаблоны сообщений"""
    try:
        templates = database.get_all_templates()
        return jsonify({"success": True, "templates": templates})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/templates/<int:template_id>', methods=['GET'])
def get_template(template_id):
    """Получить шаблон по ID"""
    try:
        template = database.get_template(template_id)
        if template:
            return jsonify({"success": True, "template": template})
        else:
            return jsonify({"error": "Template not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/templates', methods=['POST'])
def create_template():
    """Создать новый шаблон"""
    try:
        data = request.json
        name = data.get('name')
        template_type = data.get('type')
        text = data.get('text')
        is_active = data.get('is_active', True)
        
        if not name or not template_type or not text:
            return jsonify({"error": "name, type and text are required"}), 400
        
        template = database.create_template(name, template_type, text, is_active)
        return jsonify({"success": True, "template": template})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/templates/<int:template_id>', methods=['PUT'])
def update_template(template_id):
    """Обновить шаблон"""
    try:
        data = request.json
        name = data.get('name')
        template_type = data.get('type')
        text = data.get('text')
        is_active = data.get('is_active')
        
        template = database.update_template(
            template_id,
            name=name,
            template_type=template_type,
            text=text,
            is_active=is_active
        )
        
        if template:
            return jsonify({"success": True, "template": template})
        else:
            return jsonify({"error": "Template not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/templates/<int:template_id>', methods=['DELETE'])
def delete_template(template_id):
    """Удалить шаблон"""
    try:
        database.delete_template(template_id)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/templates')
def templates_page():
    """Страница управления шаблонами"""
    return render_template('templates.html')


@app.route('/api/scheduled-messages/process', methods=['POST'])
def process_scheduled_messages_endpoint():
    """Обработать отложенные задачи отправки сообщений"""
    try:
        notifications.process_scheduled_messages()
        return jsonify({"success": True, "message": "Обработка завершена"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Обрабатываем отложенные задачи при каждом запросе к API (но не слишком часто)
_last_scheduled_check = None

_last_yclients_check = None

def check_scheduled_messages():
    """Проверить и обработать отложенные задачи (не чаще раза в минуту)"""
    global _last_scheduled_check
    now = datetime.now()
    
    # Проверяем не чаще раза в минуту
    if _last_scheduled_check and (now - _last_scheduled_check).total_seconds() < 60:
        return
    
    _last_scheduled_check = now
    
    try:
        notifications.process_scheduled_messages()
    except Exception as e:
        print(f"⚠️ Ошибка обработки отложенных задач: {e}")


def check_new_yclients_records():
    """Проверить новые записи в YClients (не чаще раза в 5 минут)"""
    global _last_yclients_check
    now = datetime.now()
    
    # Проверяем не чаще раза в 5 минут
    if _last_yclients_check and (now - _last_yclients_check).total_seconds() < 300:
        return
    
    _last_yclients_check = now
    
    try:
        notifications.check_new_yclients_records()
    except Exception as e:
        print(f"⚠️ Ошибка проверки новых записей YClients: {e}")


if __name__ == '__main__':
    print("=" * 50)
    print("Avito Messenger (Client Credentials) запускается...")
    print("Откройте в браузере: http://localhost:5002")
    print("=" * 50)
    print(f"Рабочая директория: {BASE_DIR}")
    print(f"Шаблоны: {app.template_folder}")
    print(f"Статика: {app.static_folder}")
    print("=" * 50)
    try:
        # Запускаем с разрешением доступа со всех интерфейсов
        port = 5002
        print(f"\n🌐 Сервер запущен на порту {port}")
        print(f"📱 Откройте в браузере: http://localhost:{port}")
        print("=" * 50)
        app.run(debug=True, host='127.0.0.1', port=port, threaded=True, use_reloader=False)
    except PermissionError as e:
        print(f"Ошибка прав доступа: {e}")
        print("Попробуйте запустить с другим портом:")
        print("  Измените port=5002 на port=5003 в app.py")
    except Exception as e:
        print(f"Ошибка запуска: {e}")
        import traceback
        traceback.print_exc()

