"""
WhatsApp Client Integration
Взаимодействие с Node.js микросервисом whatsapp-web.js
"""

import os
import requests

# URL микросервиса WhatsApp
WHATSAPP_SERVICE_URL = os.environ.get('WHATSAPP_SERVICE_URL', 'http://localhost:3001')

# Добавляем https:// если не указан протокол
if WHATSAPP_SERVICE_URL and not WHATSAPP_SERVICE_URL.startswith(('http://', 'https://')):
    WHATSAPP_SERVICE_URL = f'https://{WHATSAPP_SERVICE_URL}'

# Убираем :3001 если это публичный Railway URL (Railway использует стандартный 443)
if 'railway.app' in WHATSAPP_SERVICE_URL and ':3001' in WHATSAPP_SERVICE_URL:
    WHATSAPP_SERVICE_URL = WHATSAPP_SERVICE_URL.replace(':3001', '')
    
print(f"WhatsApp Service URL: {WHATSAPP_SERVICE_URL}")


def get_whatsapp_status():
    """Проверить статус WhatsApp клиента"""
    try:
        response = requests.get(f'{WHATSAPP_SERVICE_URL}/status', timeout=5)
        return response.json()
    except Exception as e:
        print(f"WhatsApp: ошибка проверки статуса: {e}")
        return {'ready': False, 'authenticating': False, 'error': str(e)}


def get_whatsapp_qr():
    """Получить QR код для авторизации"""
    try:
        response = requests.get(f'{WHATSAPP_SERVICE_URL}/qr', timeout=5)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"WhatsApp: ошибка получения QR: {e}")
        return None


def get_whatsapp_chats(limit=30):
    """Получить список чатов WhatsApp"""
    try:
        response = requests.get(
            f'{WHATSAPP_SERVICE_URL}/chats',
            params={'limit': limit},
            timeout=10
        )
        if response.status_code == 200:
            chats = response.json()
            print(f"WhatsApp: загружено {len(chats)} чатов")
            return chats
        else:
            print(f"WhatsApp: ошибка {response.status_code}")
            return []
    except Exception as e:
        print(f"WhatsApp: ошибка получения чатов: {e}")
        return []


def get_whatsapp_messages(chat_id, limit=30):
    """Получить сообщения из WhatsApp чата"""
    try:
        response = requests.get(
            f'{WHATSAPP_SERVICE_URL}/chats/{chat_id}/messages',
            params={'limit': limit},
            timeout=10
        )
        if response.status_code == 200:
            messages = response.json()
            # Преобразуем формат для единого интерфейса
            for msg in messages:
                if 'content' not in msg:
                    msg['content'] = {'text': msg.get('text', '')}
                msg['source'] = 'whatsapp'
            return messages
        else:
            print(f"WhatsApp: ошибка получения сообщений {response.status_code}")
            return []
    except Exception as e:
        print(f"WhatsApp: ошибка получения сообщений: {e}")
        return []


def send_whatsapp_message(chat_id, text):
    """Отправить сообщение в WhatsApp"""
    try:
        response = requests.post(
            f'{WHATSAPP_SERVICE_URL}/messages/send',
            json={'chat_id': chat_id, 'message': text},
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        else:
            return {'success': False, 'error': f'HTTP {response.status_code}'}
    except Exception as e:
        print(f"WhatsApp: ошибка отправки сообщения: {e}")
        return {'success': False, 'error': str(e)}


def mark_whatsapp_read(chat_id):
    """Пометить WhatsApp чат как прочитанный"""
    try:
        response = requests.post(
            f'{WHATSAPP_SERVICE_URL}/chats/{chat_id}/read',
            timeout=5
        )
        if response.status_code == 200:
            return {'success': True}
        else:
            return {'success': False, 'error': f'HTTP {response.status_code}'}
    except Exception as e:
        print(f"WhatsApp: ошибка пометки прочитанным: {e}")
        return {'success': False, 'error': str(e)}

