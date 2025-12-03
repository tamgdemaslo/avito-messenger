"""
Telegram Client Integration
Использует Telethon для полного доступа к Telegram чатам
"""

import os
import asyncio
from telethon import TelegramClient, events
from telethon.tl.types import User, Chat, Channel
from datetime import datetime

# Конфигурация
TELEGRAM_API_ID = int(os.environ.get('TELEGRAM_API_ID', '39642736'))
TELEGRAM_API_HASH = os.environ.get('TELEGRAM_API_HASH', 'b635af221c00e27082d0132d6c4a9ab2')
TELEGRAM_PHONE = os.environ.get('TELEGRAM_PHONE', '+79992556031')

# Глобальный клиент
telegram_client = None
client_loop = None


def get_event_loop():
    """Получить или создать event loop"""
    global client_loop
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        client_loop = loop
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        client_loop = loop
    return client_loop


async def init_telegram_client():
    """Инициализация Telegram клиента"""
    global telegram_client
    
    try:
        # Проверяем существующий клиент
        if telegram_client:
            try:
                if telegram_client.is_connected():
                    # Проверяем авторизацию
                    if await telegram_client.is_user_authorized():
                        return telegram_client
            except:
                # Клиент не подключен, пересоздаем
                telegram_client = None
        
        # Создаем новый клиент
        telegram_client = TelegramClient(
            'avito_crm_session',
            TELEGRAM_API_ID,
            TELEGRAM_API_HASH
        )
        
        await telegram_client.connect()
        
        # Проверяем авторизацию
        if not await telegram_client.is_user_authorized():
            print(f"Telegram: требуется авторизация для {TELEGRAM_PHONE}")
            await telegram_client.disconnect()
            return None
        
        print("Telegram: клиент успешно подключен и авторизован")
        return telegram_client
    except Exception as e:
        print(f"Telegram: ошибка инициализации клиента: {e}")
        return None


def run_async(coro):
    """Запуск async функции синхронно"""
    # Создаем новый event loop для каждого запроса (Flask/gunicorn синхронный)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def get_telegram_chats_async(limit=100):
    """Получить список чатов Telegram"""
    chats = []
    
    try:
        client = await init_telegram_client()
        if not client:
            print("Telegram: клиент не авторизован, пропускаем загрузку чатов")
            return []
        
        # Проверяем авторизацию еще раз
        if not await client.is_user_authorized():
            print("Telegram: пользователь не авторизован")
            return []
        
        try:
            dialogs = await client.get_dialogs(limit=limit)
        except Exception as e:
            error_msg = str(e)
            if 'not registered' in error_msg or 'not authorized' in error_msg.lower():
                print("Telegram: требуется авторизация (ключ не зарегистрирован)")
                return []
            raise  # Пробрасываем другие ошибки
        
    except Exception as e:
        error_msg = str(e)
        if 'not registered' in error_msg or 'not authorized' in error_msg.lower():
            print("Telegram: требуется авторизация")
        else:
            print(f"Telegram: ошибка при получении чатов: {e}")
        return []
    
    for dialog in dialogs:
        try:
            entity = dialog.entity
            
            # Получаем информацию о чате
            chat_data = {
                'id': f'tg_{dialog.id}',
                'source': 'telegram',
                'original_id': dialog.id,
                'name': dialog.name or 'Без названия',
                'unread_count': dialog.unread_count,
                'created': int(dialog.date.timestamp()) if dialog.date else 0,
                'updated': int(dialog.date.timestamp()) if dialog.date else 0,
            }
            
            # Последнее сообщение
            if dialog.message:
                msg = dialog.message
                chat_data['last_message'] = {
                    'id': msg.id,
                    'text': msg.message or '',
                    'created': int(msg.date.timestamp()) if msg.date else 0,
                    'from_id': msg.sender_id
                }
            
            # Аватарка
            if hasattr(entity, 'photo') and entity.photo:
                try:
                    photo_path = await client.download_profile_photo(
                        entity,
                        file=f'static/avatars/tg_{dialog.id}.jpg'
                    )
                    if photo_path:
                        chat_data['avatar'] = f'/static/avatars/tg_{dialog.id}.jpg'
                except Exception as e:
                    print(f"Не удалось загрузить аватарку для {dialog.name}: {e}")
            
            # Тип чата
            if isinstance(entity, User):
                chat_data['type'] = 'private'
                chat_data['is_bot'] = entity.bot if hasattr(entity, 'bot') else False
            elif isinstance(entity, Chat):
                chat_data['type'] = 'group'
            elif isinstance(entity, Channel):
                chat_data['type'] = 'channel'
                chat_data['is_broadcast'] = entity.broadcast if hasattr(entity, 'broadcast') else False
            
            chats.append(chat_data)
        except Exception as e:
            print(f"Ошибка обработки диалога {dialog.id}: {e}")
            continue
    
    return chats


async def get_telegram_messages_async(chat_id, limit=100):
    """Получить сообщения из Telegram чата"""
    client = await init_telegram_client()
    if not client:
        return []
    
    # Извлекаем оригинальный ID
    original_id = int(chat_id.replace('tg_', ''))
    
    try:
        messages = await client.get_messages(original_id, limit=limit)
        result = []
        
        for msg in messages:
            if not msg:
                continue
                
            message_data = {
                'id': f'tg_{msg.id}',
                'original_id': msg.id,
                'author_id': msg.sender_id,
                'created': int(msg.date.timestamp()) if msg.date else 0,
                'text': msg.message or '',
                'type': 'text',
                'direction': 'out' if msg.out else 'in'
            }
            
            # Медиафайлы
            if msg.photo:
                message_data['type'] = 'photo'
                message_data['has_media'] = True
            elif msg.video:
                message_data['type'] = 'video'
                message_data['has_media'] = True
            elif msg.document:
                message_data['type'] = 'document'
                message_data['has_media'] = True
            elif msg.voice:
                message_data['type'] = 'voice'
                message_data['has_media'] = True
            
            result.append(message_data)
        
        return result
    except Exception as e:
        print(f"Ошибка получения сообщений Telegram: {e}")
        return []


async def send_telegram_message_async(chat_id, text):
    """Отправить сообщение в Telegram"""
    client = await init_telegram_client()
    if not client:
        return None
    
    original_id = int(chat_id.replace('tg_', ''))
    
    try:
        message = await client.send_message(original_id, text)
        return {
            'success': True,
            'message_id': message.id,
            'date': int(message.date.timestamp()) if message.date else 0
        }
    except Exception as e:
        print(f"Ошибка отправки сообщения Telegram: {e}")
        return {'success': False, 'error': str(e)}


async def authorize_telegram_async(phone, code=None, password=None):
    """Авторизация в Telegram"""
    global telegram_client
    
    try:
        # Закрываем существующий клиент, если есть
        if telegram_client:
            try:
                await telegram_client.disconnect()
            except:
                pass
        
        # Создаем новый клиент
        telegram_client = TelegramClient(
            'avito_crm_session',
            TELEGRAM_API_ID,
            TELEGRAM_API_HASH
        )
        
        await telegram_client.connect()
        
        # Проверяем, авторизован ли уже
        if await telegram_client.is_user_authorized():
            return {'status': 'already_authorized', 'message': 'Уже авторизованы'}
        
        if not code:
            # Отправляем код
            await telegram_client.send_code_request(phone)
            return {'status': 'code_sent', 'message': 'Код отправлен на ваш Telegram'}
        else:
            # Авторизуемся с кодом
            try:
                await telegram_client.sign_in(phone, code, password=password)
                # Проверяем успешность
                if await telegram_client.is_user_authorized():
                    return {'status': 'authorized', 'message': 'Авторизация успешна'}
                else:
                    return {'status': 'error', 'message': 'Авторизация не удалась'}
            except Exception as e:
                error_msg = str(e)
                # Проверяем, нужен ли пароль 2FA
                if 'password' in error_msg.lower() or '2FA' in error_msg:
                    return {'status': 'password_required', 'message': 'Требуется пароль 2FA'}
                return {'status': 'error', 'message': error_msg}
    except Exception as e:
        return {'status': 'error', 'message': f'Ошибка авторизации: {str(e)}'}


async def get_telegram_user_info_async(user_id):
    """Получить информацию о пользователе Telegram"""
    client = await init_telegram_client()
    if not client:
        return None
    
    try:
        entity = await client.get_entity(user_id)
        user_info = {
            'id': entity.id,
            'name': f"{entity.first_name or ''} {entity.last_name or ''}".strip(),
            'username': entity.username if hasattr(entity, 'username') else None,
            'phone': entity.phone if hasattr(entity, 'phone') else None
        }
        
        # Аватарка
        if hasattr(entity, 'photo') and entity.photo:
            try:
                photo_path = await client.download_profile_photo(
                    entity,
                    file=f'static/avatars/tg_user_{user_id}.jpg'
                )
                if photo_path:
                    user_info['avatar'] = f'/static/avatars/tg_user_{user_id}.jpg'
            except:
                pass
        
        return user_info
    except Exception as e:
        print(f"Ошибка получения информации о пользователе: {e}")
        return None


# Синхронные обертки для Flask
def get_telegram_chats(limit=100):
    """Синхронная обертка для получения чатов"""
    try:
        return run_async(get_telegram_chats_async(limit))
    except Exception as e:
        print(f"Ошибка получения чатов Telegram: {e}")
        return []


def get_telegram_messages(chat_id, limit=100):
    """Синхронная обертка для получения сообщений"""
    try:
        return run_async(get_telegram_messages_async(chat_id, limit))
    except Exception as e:
        print(f"Ошибка получения сообщений Telegram: {e}")
        return []


def send_telegram_message(chat_id, text):
    """Синхронная обертка для отправки сообщения"""
    try:
        return run_async(send_telegram_message_async(chat_id, text))
    except Exception as e:
        print(f"Ошибка отправки сообщения Telegram: {e}")
        return {'success': False, 'error': str(e)}


def authorize_telegram(phone, code=None, password=None):
    """Синхронная обертка для авторизации"""
    try:
        return run_async(authorize_telegram_async(phone, code, password))
    except Exception as e:
        print(f"Ошибка авторизации Telegram: {e}")
        return {'status': 'error', 'message': str(e)}


def get_telegram_user_info(user_id):
    """Синхронная обертка для получения информации о пользователе"""
    try:
        return run_async(get_telegram_user_info_async(user_id))
    except Exception as e:
        print(f"Ошибка получения информации о пользователе: {e}")
        return None

