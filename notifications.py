"""
Модуль для отправки уведомлений клиентам через Telegram/WhatsApp
"""

import re
import database
import telegram_client
import whatsapp_client
from datetime import datetime, timedelta


def format_template(template_text, variables):
    """Форматировать шаблон, подставляя переменные"""
    text = template_text
    for key, value in variables.items():
        # Заменяем {key} на значение
        placeholder = f"{{{key}}}"
        text = text.replace(placeholder, str(value) if value else "")
    return text


def normalize_phone(phone):
    """Нормализовать номер телефона для поиска"""
    if not phone:
        return None
    # Убираем все символы кроме цифр и +
    phone = re.sub(r'[^\d+]', '', str(phone))
    # Убираем + для поиска
    phone = phone.replace('+', '')
    return phone


def find_chat_by_phone(phone):
    """Найти чат по номеру телефона (Telegram или WhatsApp)"""
    if not phone:
        return None, None
    
    normalized_phone = normalize_phone(phone)
    
    # Пробуем найти в Telegram чатах
    try:
        telegram_chats = telegram_client.get_telegram_chats(limit=200)
        for chat in telegram_chats:
            # В Telegram номера телефонов не всегда доступны через API
            # Но можно проверить по имени или другим признакам
            # Для простоты, проверяем только чаты с ID
            pass
    except Exception as e:
        print(f"Ошибка поиска в Telegram: {e}")
    
    # Пробуем найти в WhatsApp чатах
    try:
        whatsapp_chats = whatsapp_client.get_whatsapp_chats(limit=200)
        for chat in whatsapp_chats:
            # В WhatsApp тоже номера могут быть недоступны через API
            # Но можно проверить chat_id или другие признаки
            pass
    except Exception as e:
        print(f"Ошибка поиска в WhatsApp: {e}")
    
    # Если не нашли, возвращаем None
    # В будущем можно сохранить в базе данных связь телефон-чат_id
    return None, None


def send_notification(phone, fullname, template_type, variables=None):
    """Отправить уведомление клиенту"""
    if not phone:
        return False, "Номер телефона не указан"
    
    # Получаем шаблон
    template = database.get_template_by_type(template_type)
    if not template:
        return False, f"Шаблон типа {template_type} не найден"
    
    if not template.get('is_active'):
        return False, f"Шаблон {template['name']} неактивен"
    
    # Формируем текст сообщения
    if variables is None:
        variables = {}
    
    message_text = format_template(template['text'], variables)
    
    # Пытаемся найти чат
    chat_id, source = find_chat_by_phone(phone)
    
    if not chat_id:
        # Если чат не найден, возвращаем False
        # В будущем можно сохранить задачу для отправки позже
        return False, f"Чат с номером {phone} не найден в Telegram/WhatsApp"
    
    # Отправляем сообщение
    try:
        if source == 'telegram':
            result = telegram_client.send_telegram_message(chat_id, message_text)
        elif source == 'whatsapp':
            result = whatsapp_client.send_whatsapp_message(chat_id, message_text)
        else:
            return False, f"Неизвестный источник: {source}"
        
        if result and result.get('success'):
            return True, "Сообщение отправлено"
        else:
            return False, result.get('error', 'Ошибка отправки')
    except Exception as e:
        return False, f"Ошибка отправки: {str(e)}"


def schedule_review_request(phone, fullname, booking_datetime, variables=None):
    """Запланировать отправку просьбы об отзыве через 2 часа после записи"""
    try:
        # Получаем шаблон
        template = database.get_template_by_type('review_request')
        if not template:
            print(f"Шаблон review_request не найден, пропускаем отложенную отправку")
            return False
        
        if not template.get('is_active'):
            print(f"Шаблон {template['name']} неактивен, пропускаем отложенную отправку")
            return False
        
        # Формируем текст сообщения
        if variables is None:
            variables = {}
        
        message_text = format_template(template['text'], variables)
        
        # Вычисляем время отправки (через 2 часа после записи)
        if isinstance(booking_datetime, str):
            try:
                # Пытаемся распарсить datetime (формат ISO 8601: "2026-01-14T09:40:00+02:00" или "2026-01-14T09:40:00")
                booking_dt_str = booking_datetime.replace('Z', '+00:00')
                # Удаляем таймзону для упрощения (если она есть)
                if '+' in booking_dt_str or booking_dt_str.endswith('Z'):
                    # Парсим с таймзоной
                    if booking_dt_str.endswith('Z'):
                        booking_dt_str = booking_dt_str[:-1] + '+00:00'
                    booking_dt = datetime.fromisoformat(booking_dt_str)
                else:
                    # Парсим без таймзоны
                    booking_dt = datetime.fromisoformat(booking_dt_str)
                    # Используем UTC время
                    booking_dt = booking_dt.replace(tzinfo=timezone.utc)
            except (ValueError, AttributeError) as e:
                print(f"⚠️ Ошибка парсинга datetime '{booking_datetime}': {e}")
                # Используем текущее время + 2 часа как fallback
                booking_dt = datetime.now(timezone.utc)
        else:
            booking_dt = booking_datetime
            if isinstance(booking_dt, datetime) and booking_dt.tzinfo is None:
                booking_dt = booking_dt.replace(tzinfo=timezone.utc)
        
        send_at = booking_dt + timedelta(hours=2)
        
        # Создаем отложенную задачу
        task_id = database.create_scheduled_message(
            phone=phone,
            fullname=fullname,
            template_type='review_request',
            message_text=message_text,
            send_at=send_at,
            chat_id=None,  # Будет определено при отправке
            source=None
        )
        
        print(f"✅ Отложенная задача создана (ID: {task_id}), отправка через 2 часа в {send_at}")
        return True
    except Exception as e:
        print(f"❌ Ошибка создания отложенной задачи: {e}")
        return False


def process_scheduled_messages():
    """Обработать отложенные задачи отправки сообщений"""
    try:
        pending_tasks = database.get_pending_scheduled_messages()
        
        for task in pending_tasks:
            try:
                # Пытаемся найти чат
                chat_id, source = find_chat_by_phone(task['phone'])
                
                if not chat_id:
                    # Если чат не найден, помечаем задачу как ошибку
                    database.mark_scheduled_message_sent(
                        task['id'],
                        error=f"Чат с номером {task['phone']} не найден"
                    )
                    continue
                
                # Отправляем сообщение
                if source == 'telegram':
                    result = telegram_client.send_telegram_message(chat_id, task['message_text'])
                elif source == 'whatsapp':
                    result = whatsapp_client.send_whatsapp_message(chat_id, task['message_text'])
                else:
                    database.mark_scheduled_message_sent(
                        task['id'],
                        error=f"Неизвестный источник: {source}"
                    )
                    continue
                
                if result and result.get('success'):
                    database.mark_scheduled_message_sent(task['id'], error=None)
                    print(f"✅ Отложенное сообщение отправлено (задача {task['id']})")
                else:
                    database.mark_scheduled_message_sent(
                        task['id'],
                        error=result.get('error', 'Ошибка отправки')
                    )
            except Exception as e:
                database.mark_scheduled_message_sent(
                    task['id'],
                    error=f"Ошибка обработки: {str(e)}"
                )
    except Exception as e:
        print(f"❌ Ошибка обработки отложенных задач: {e}")


def check_new_yclients_records():
    """Проверить новые записи в YClients и отправить уведомления"""
    try:
        import yclients_client
        from datetime import datetime, timedelta
        
        if not yclients_client.is_yclients_configured():
            return
        
        # Получаем записи за последние 24 часа
        date_from = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        date_to = datetime.now().strftime('%Y-%m-%d')
        
        records = yclients_client.get_records(date_from=date_from, date_to=date_to, limit=100)
        
        if not records or not isinstance(records, list):
            return
        
        # Получаем имена услуг и мастеров для подстановки
        services = {}
        staff = {}
        try:
            services_list = yclients_client.get_services()
            if services_list and isinstance(services_list, list):
                services = {s.get('id'): s.get('title') or s.get('name') for s in services_list}
        except:
            pass
        
        for record in records:
            try:
                record_id = str(record.get('id') or record.get('record_id', ''))
                if not record_id:
                    continue
                
                # Проверяем, была ли запись уже обработана
                if database.is_record_processed(record_id):
                    continue
                
                # Извлекаем данные записи
                phone = record.get('phone') or record.get('client', {}).get('phone')
                fullname = record.get('fullname') or record.get('client', {}).get('name')
                
                if not phone:
                    continue
                
                # Получаем информацию о записи
                appointments = record.get('appointments', [])
                if not appointments and record.get('services'):
                    # Если appointments нет, но есть services, формируем appointments
                    appointments = [{
                        'services': record.get('services', []),
                        'staff_id': record.get('staff_id'),
                        'datetime': record.get('date') or record.get('datetime')
                    }]
                
                if not appointments:
                    continue
                
                first_appointment = appointments[0]
                service_id = first_appointment.get('services', [first_appointment.get('service_id')])[0] if first_appointment.get('services') else first_appointment.get('service_id')
                staff_id = first_appointment.get('staff_id')
                datetime_str = first_appointment.get('datetime') or record.get('date')
                
                # Получаем имена
                service_name = services.get(service_id) if service_id and service_id in services else None
                if not service_name and service_id:
                    try:
                        staff_list = yclients_client.get_staff(service_ids=[service_id] if service_id else None)
                        if staff_list and isinstance(staff_list, list):
                            staff_member = next((s for s in staff_list if s.get('id') == staff_id), None)
                            if staff_member:
                                staff[staff_id] = staff_member.get('name')
                    except:
                        pass
                
                staff_name = staff.get(staff_id) if staff_id else None
                
                # Формируем переменные для шаблонов
                template_variables = {
                    'fullname': fullname or 'Клиент',
                    'phone': phone,
                    'datetime': datetime_str or '',
                    'service_name': service_name or f'Услуга #{service_id}' if service_id else 'Услуга',
                    'staff_name': staff_name or f'Мастер #{staff_id}' if staff_id else 'Мастер',
                    'comment': record.get('comment') or ''
                }
                
                # Отправляем уведомление о записи
                success, message = send_notification(
                    phone=phone,
                    fullname=fullname or 'Клиент',
                    template_type='booking_confirmation',
                    variables=template_variables
                )
                
                if success:
                    print(f"✅ Уведомление о записи отправлено для {fullname} ({phone}): {message}")
                else:
                    print(f"⚠️ Не удалось отправить уведомление для {fullname} ({phone}): {message}")
                
                # Планируем отправку отзыва через 2 часа
                if datetime_str:
                    schedule_review_request(
                        phone=phone,
                        fullname=fullname or 'Клиент',
                        booking_datetime=datetime_str,
                        variables=template_variables
                    )
                
                # Помечаем запись как обработанную
                database.mark_record_processed(record_id, phone, fullname, datetime_str)
                
            except Exception as e:
                print(f"⚠️ Ошибка обработки записи {record.get('id', 'unknown')}: {e}")
                continue
                
    except Exception as e:
        print(f"❌ Ошибка проверки новых записей YClients: {e}")
