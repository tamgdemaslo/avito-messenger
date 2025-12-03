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
phone_code_hash_storage = {}  # Хранилище для phone_code_hash


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
    global client_loop
    
    # Переиспользуем существующий loop или создаем новый
    if not client_loop or client_loop.is_closed():
        client_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(client_loop)
    
    # НЕ закрываем loop - Telegram клиент использует его для фоновых задач
    return client_loop.run_until_complete(coro)


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
            
            # ФИЛЬТР: Загружаем ТОЛЬКО личные диалоги с пользователями
            # Пропускаем группы (Chat) и каналы (Channel)
            if not isinstance(entity, User):
                continue
            
            # Пропускаем ботов (опционально)
            # if hasattr(entity, 'bot') and entity.bot:
            #     continue
            
            # Получаем информацию о чате
            chat_data = {
                'id': f'tg_{dialog.id}',
                'source': 'telegram',
                'original_id': dialog.id,
                'name': dialog.name or 'Без названия',
                'unread_count': dialog.unread_count,
                'created': int(dialog.date.timestamp()) if dialog.date else 0,
                'updated': int(dialog.date.timestamp()) if dialog.date else 0,
                'type': 'private',
                'is_bot': entity.bot if hasattr(entity, 'bot') else False
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
            
            # Аватарка - НЕ загружаем файлы, используем заглушки
            # Загрузка 100 аватарок занимает 20-30 секунд!
            # Вместо этого используем initials/placeholder
            if hasattr(entity, 'photo') and entity.photo:
                # Просто помечаем что аватарка есть, но не загружаем
                chat_data['has_photo'] = True
            else:
                chat_data['has_photo'] = False
            
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


async def mark_telegram_read_async(chat_id):
    """Пометить сообщения в Telegram чате как прочитанные"""
    client = await init_telegram_client()
    if not client:
        return {'success': False, 'error': 'Client not initialized'}
    
    original_id = int(chat_id.replace('tg_', ''))
    
    try:
        # Помечаем все сообщения в чате как прочитанные
        await client.send_read_acknowledge(original_id)
        print(f"Telegram: чат {chat_id} помечен прочитанным")
        return {'success': True}
    except Exception as e:
        print(f"Ошибка пометки прочитанным Telegram: {e}")
        return {'success': False, 'error': str(e)}


async def authorize_telegram_async(phone, code=None, password=None):
    """Авторизация в Telegram"""
    global telegram_client, phone_code_hash_storage
    
    try:
        # Создаем/переиспользуем клиент
        if not telegram_client or not telegram_client.is_connected():
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
            # Отправляем код и СОХРАНЯЕМ phone_code_hash
            result = await telegram_client.send_code_request(phone)
            phone_code_hash_storage[phone] = result.phone_code_hash
            print(f"Telegram: код отправлен, phone_code_hash сохранен для {phone}")
            return {'status': 'code_sent', 'message': 'Код отправлен на ваш Telegram'}
        else:
            # Авторизуемся с кодом и сохраненным phone_code_hash
            try:
                phone_code_hash = phone_code_hash_storage.get(phone)
                
                # Если есть пароль, используем check_password
                if password:
                    try:
                        await telegram_client.sign_in(password=password)
                        if await telegram_client.is_user_authorized():
                            phone_code_hash_storage.pop(phone, None)
                            print(f"Telegram: авторизация с 2FA успешна для {phone}")
                            return {'status': 'authorized', 'message': 'Авторизация успешна'}
                    except Exception as e:
                        print(f"Telegram: ошибка 2FA: {e}")
                        return {'status': 'error', 'message': f'Неверный пароль 2FA: {str(e)}'}
                
                # Обычная авторизация с кодом
                if not phone_code_hash:
                    return {'status': 'error', 'message': 'Сначала запросите код'}
                
                await telegram_client.sign_in(
                    phone, 
                    code, 
                    phone_code_hash=phone_code_hash
                )
                
                # Проверяем успешность
                if await telegram_client.is_user_authorized():
                    # Удаляем phone_code_hash из хранилища
                    phone_code_hash_storage.pop(phone, None)
                    print(f"Telegram: авторизация успешна для {phone}")
                    return {'status': 'authorized', 'message': 'Авторизация успешна'}
                else:
                    return {'status': 'error', 'message': 'Авторизация не удалась'}
            except Exception as e:
                error_msg = str(e)
                # Проверяем, нужен ли пароль 2FA
                if 'password' in error_msg.lower() or 'SessionPasswordNeededError' in error_msg:
                    return {'status': 'password_required', 'message': 'Требуется пароль 2FA'}
                print(f"Telegram: ошибка sign_in: {error_msg}")
                return {'status': 'error', 'message': error_msg}
    except Exception as e:
        error_msg = str(e)
        print(f"Telegram: общая ошибка авторизации: {error_msg}")
        return {'status': 'error', 'message': f'Ошибка авторизации: {error_msg}'}


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
        
        # Аватарка - не загружаем для скорости
        user_info['has_photo'] = hasattr(entity, 'photo') and entity.photo is not None
        
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


def mark_telegram_read(chat_id):
    """Синхронная обертка для пометки чата прочитанным"""
    try:
        return run_async(mark_telegram_read_async(chat_id))
    except Exception as e:
        print(f"Ошибка пометки чата прочитанным: {e}")
        return {'success': False, 'error': str(e)}

