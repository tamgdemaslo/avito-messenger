"""
YClients API Integration - ПРОСТАЯ ВЕРСИЯ
Только booking endpoints с Partner Token
"""
import os
import requests
import logging
import json

log = logging.getLogger(__name__)

# Конфигурация
YCLIENTS_PARTNER_TOKEN = os.environ.get('YCLIENTS_PARTNER_TOKEN', '')
YCLIENTS_COMPANY_ID = int(os.environ.get('YCLIENTS_COMPANY_ID', '0'))

API = "https://api.yclients.com/api/v1"
HEADERS = {
    "Authorization": f"Bearer {YCLIENTS_PARTNER_TOKEN}",
    "Accept": "application/vnd.yclients.v2+json",
    "Content-Type": "application/json"
}

# Логирование конфигурации
if YCLIENTS_PARTNER_TOKEN:
    print(f"✅ YClients: Partner Token установлен ({len(YCLIENTS_PARTNER_TOKEN)} символов)")
else:
    print("⚠️ YClients: Partner Token НЕ УСТАНОВЛЕН!")

if YCLIENTS_COMPANY_ID:
    print(f"✅ YClients: Company ID = {YCLIENTS_COMPANY_ID}")
else:
    print("⚠️ YClients: Company ID НЕ УСТАНОВЛЕН!")


def _get(path, params=None):
    """Внутренний GET запрос"""
    url = API + path
    try:
        response = requests.get(url, headers=HEADERS, params=params or {}, timeout=10)
        response.raise_for_status()
        result = response.json()
        return result.get('data', result)
    except Exception as e:
        log.error(f"YClients GET error ({url}): {e}")
        print(f"YClients GET error ({url}): {e}")
        raise


def _post(path, json_data):
    """Внутренний POST запрос"""
    url = API + path
    
    # Проверяем конфигурацию
    if not YCLIENTS_PARTNER_TOKEN:
        raise ValueError("YCLIENTS_PARTNER_TOKEN не установлен")
    if not YCLIENTS_COMPANY_ID or YCLIENTS_COMPANY_ID <= 0:
        raise ValueError("YCLIENTS_COMPANY_ID не установлен или некорректен")
    
    # Логируем отправляемые данные для отладки
    print(f"📤 YClients POST to {url}")
    print(f"📤 Payload: {json.dumps(json_data, indent=2, ensure_ascii=False)}")
    
    try:
        response = requests.post(url, headers=HEADERS, json=json_data, timeout=10)
        
        # ВСЕГДА логируем ответ для отладки (даже успешный, но особенно ошибки)
        print(f"📥 YClients response status: {response.status_code}")
        print(f"📥 YClients response headers: {dict(response.headers)}")
        
        # Пытаемся получить детали ошибки из ответа
        if not response.ok:
            error_detail = f"Status {response.status_code}"
            error_full = None
            error_data_dict = None
            
            try:
                # Пробуем получить JSON ответ
                error_json = response.json()
                error_data_dict = error_json if isinstance(error_json, dict) else {}
                error_full = json.dumps(error_json, indent=2, ensure_ascii=False)
                
                print(f"❌ YClients error response ({response.status_code}):")
                print(f"❌ Full JSON response: {error_full}")
                print(f"❌ Response text (first 1000 chars): {response.text[:1000] if response.text else 'Empty'}")
                
                # Пытаемся извлечь детальное сообщение об ошибке - пробуем разные форматы ответов YClients
                if isinstance(error_json, dict):
                    # Формат 1: meta.error или meta.message
                    if 'meta' in error_json and isinstance(error_json['meta'], dict):
                        error_detail = error_json['meta'].get('error') or error_json['meta'].get('message') or error_detail
                    
                    # Формат 2: error или message на верхнем уровне
                    if 'error' in error_json:
                        error_detail = error_json['error']
                    elif 'message' in error_json:
                        error_detail = error_json['message']
                    
                    # Формат 3: errors - словарь с полями и сообщениями (валидация)
                    if 'errors' in error_json:
                        errors_dict = error_json['errors']
                        if isinstance(errors_dict, dict):
                            error_parts = []
                            for field, messages in errors_dict.items():
                                if isinstance(messages, list):
                                    error_parts.append(f"{field}: {', '.join(str(m) for m in messages)}")
                                elif isinstance(messages, dict):
                                    # Если messages - словарь, извлекаем значения
                                    error_parts.append(f"{field}: {', '.join(str(v) for v in messages.values())}")
                                else:
                                    error_parts.append(f"{field}: {messages}")
                            if error_parts:
                                error_detail = "; ".join(error_parts)
                    
                    # Формат 4: может быть массив ошибок
                    if 'error' in error_json and isinstance(error_json['error'], list):
                        error_detail = "; ".join(str(e) for e in error_json['error'])
                    
                    # Формат 5: text на верхнем уровне
                    if 'text' in error_json:
                        error_detail = error_json['text']
                        
            except ValueError as json_error:
                # Если не JSON, пробуем прочитать как текст
                error_full = response.text[:1000] if response.text else str(response)
                print(f"⚠️ Response is not JSON. Text: {error_full}")
            except Exception as parse_error:
                error_full = response.text[:1000] if response.text else str(response)
                print(f"⚠️ Could not parse error response: {parse_error}, raw text: {error_full}")
            
            # Формируем финальное сообщение об ошибке
            error_msg = error_detail
            if error_full and error_full != error_detail:
                error_msg += f"\n\nПолный ответ API:\n{error_full}"
            
            log.error(f"YClients POST error ({url}): {error_msg}")
            print(f"❌ YClients POST error ({url}): {error_msg}")
            
            # Создаем исключение с детальной информацией
            http_error = requests.exceptions.HTTPError(f"{response.status_code} Client Error: {response.reason} for url: {url}")
            http_error.response = response
            http_error.error_detail = error_detail
            http_error.error_full = error_full
            http_error.error_data = error_data_dict  # Добавляем словарь для удобства
            raise http_error
        
        result = response.json()
        print(f"✅ YClients success response: {json.dumps(result, indent=2, ensure_ascii=False)}")
        return result.get('data', result)
    except requests.exceptions.HTTPError as e:
        # Пробрасываем HTTPError с деталями
        raise
    except Exception as e:
        log.error(f"YClients POST error ({url}): {e}")
        print(f"❌ YClients POST error ({url}): {e}")
        raise


# ═══════════════════════════════════════════════════════════
# BOOKING ENDPOINTS (Partner Token Only)
# ═══════════════════════════════════════════════════════════

def get_services(company_id=None):
    """GET /book_services/{company_id} - Получить услуги для бронирования"""
    cid = company_id or YCLIENTS_COMPANY_ID
    data = _get(f"/book_services/{cid}")
    
    # Возвращаем только массив services
    if isinstance(data, dict):
        return data.get('services', [])
    return data


def get_staff(company_id=None, service_ids=None):
    """GET /book_staff/{company_id} - Получить сотрудников для бронирования"""
    cid = company_id or YCLIENTS_COMPANY_ID
    params = {}
    if service_ids:
        params["service_ids[]"] = service_ids
    return _get(f"/book_staff/{cid}", params)


def get_book_dates(company_id=None, service_ids=None, staff_id=None):
    """GET /book_dates/{company_id} - Получить доступные даты"""
    cid = company_id or YCLIENTS_COMPANY_ID
    params = {}
    if service_ids:
        for sid in service_ids:
            params.setdefault("service_ids[]", []).append(sid)
    if staff_id:
        params["staff_id"] = staff_id
    return _get(f"/book_dates/{cid}", params)


def get_free_slots(staff_id, date_iso, service_ids=None, company_id=None):
    """GET /book_times/{company_id}/{staff_id}/{date} - Получить свободные слоты"""
    cid = company_id or YCLIENTS_COMPANY_ID
    params = {}
    if service_ids:
        params["service_ids[]"] = service_ids
    return _get(f"/book_times/{cid}/{staff_id}/{date_iso}", params)


def create_booking(phone, fullname, appointments, email="", comment=None, company_id=None):
    """POST /book_record/{company_id} - Создать запись
    
    appointments должен быть массивом объектов, где каждый объект содержит:
    - services: [id_услуги] или id: id_услуги
    - staff_id: id_мастера
    - datetime: дата и время в формате ISO 8601 (например: "2024-12-15T14:00:00")
    """
    cid = company_id or YCLIENTS_COMPANY_ID
    
    # Валидация входных данных
    if not phone or not phone.strip():
        raise ValueError("Телефон обязателен для заполнения")
    
    if not fullname or not fullname.strip():
        raise ValueError("Имя клиента обязательно для заполнения")
    
    if not appointments or not isinstance(appointments, list) or len(appointments) == 0:
        raise ValueError("Необходимо указать хотя бы одну запись (appointments)")
    
    # Нормализуем phone - убираем пробелы и приводим к строке
    phone = str(phone).strip().replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
    if not phone.startswith('+'):
        # Если нет +, добавляем +7 для российских номеров
        if phone.startswith('7') or phone.startswith('8'):
            phone = '+7' + phone.lstrip('78')
        else:
            phone = '+7' + phone
    
    # Нормализуем appointments - проверяем и исправляем формат
    normalized_appointments = []
    for idx, apt in enumerate(appointments):
        normalized_apt = {}
        
        # Проверяем формат услуги
        service_id = None
        if 'id' in apt:
            service_id = apt['id']
        elif 'services' in apt:
            services = apt['services']
            if isinstance(services, list) and len(services) > 0:
                service_id = services[0]
            else:
                service_id = services
        elif 'service_id' in apt:
            service_id = apt['service_id']
        else:
            raise ValueError(f"В записи #{idx+1} отсутствует поле 'id', 'services' или 'service_id': {apt}")
        
        # Убеждаемся, что service_id - это число
        try:
            service_id = int(service_id)
        except (ValueError, TypeError):
            raise ValueError(f"В записи #{idx+1} ID услуги должен быть числом, получено: {service_id}")
        
        normalized_apt['services'] = [service_id]
        
        # Проверяем staff_id
        if 'staff_id' not in apt:
            raise ValueError(f"В записи #{idx+1} отсутствует поле 'staff_id': {apt}")
        
        staff_id = apt['staff_id']
        try:
            staff_id = int(staff_id)
        except (ValueError, TypeError):
            raise ValueError(f"В записи #{idx+1} ID мастера должен быть числом, получено: {staff_id}")
        
        normalized_apt['staff_id'] = staff_id
        
        # Проверяем datetime
        if 'datetime' not in apt:
            raise ValueError(f"В записи #{idx+1} отсутствует поле 'datetime': {apt}")
        
        datetime_value = apt['datetime']
        if not datetime_value or not isinstance(datetime_value, str):
            raise ValueError(f"В записи #{idx+1} datetime должен быть строкой в формате ISO 8601, получено: {datetime_value}")
        
        # Проверяем формат datetime (должен быть примерно "2024-12-15T14:00:00" или "2024-12-15 14:00:00")
        if 'T' not in datetime_value and ' ' not in datetime_value:
            raise ValueError(f"В записи #{idx+1} datetime должен быть в формате ISO 8601 (например: '2024-12-15T14:00:00'), получено: {datetime_value}")
        
        # Нормализуем datetime: заменяем пробел на T для ISO 8601
        if ' ' in datetime_value:
            datetime_value = datetime_value.replace(' ', 'T')
        
        normalized_apt['datetime'] = datetime_value
        
        # YClients API требует id в каждом appointment (обычно 1 для первой записи)
        normalized_apt['id'] = idx + 1
        
        normalized_appointments.append(normalized_apt)
    
    payload = {
        "phone": phone,
        "fullname": fullname,
        "email": email or f"{phone.replace('+', '').replace(' ', '')}@temp.mail",
        "appointments": normalized_appointments,
    }
    
    if comment:
        payload["comment"] = str(comment).strip()
    
    log.info(f"Creating YClients booking for {fullname} ({phone}) with {len(normalized_appointments)} appointment(s)")
    print(f"📅 Creating booking: {fullname}, phone: {phone}, appointments: {len(normalized_appointments)}")
    print(f"📅 Normalized payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")
    return _post(f"/book_record/{cid}", payload)


def is_yclients_configured():
    """Проверить настроен ли YClients"""
    return bool(YCLIENTS_PARTNER_TOKEN and YCLIENTS_COMPANY_ID > 0)

