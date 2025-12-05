"""
YClients API Integration
Запись клиентов через API YClients
"""

import os
import requests
from datetime import datetime, date
import logging

log = logging.getLogger(__name__)

# Конфигурация YClients
YCLIENTS_PARTNER_TOKEN = os.environ.get('YCLIENTS_PARTNER_TOKEN', '')
YCLIENTS_COMPANY_ID = int(os.environ.get('YCLIENTS_COMPANY_ID', '0'))
YCLIENTS_LOGIN = os.environ.get('YCLIENTS_LOGIN', '')  # Email или телефон
YCLIENTS_PASSWORD = os.environ.get('YCLIENTS_PASSWORD', '')  # Пароль
YCLIENTS_USER_TOKEN = None  # Будет получен при первом запросе

# Детальная проверка конфигурации
if not YCLIENTS_PARTNER_TOKEN:
    print("⚠️ YClients: YCLIENTS_PARTNER_TOKEN НЕ УСТАНОВЛЕН!")
elif len(YCLIENTS_PARTNER_TOKEN) < 10:
    print(f"⚠️ YClients: YCLIENTS_PARTNER_TOKEN слишком короткий: {len(YCLIENTS_PARTNER_TOKEN)} символов")
else:
    print(f"✅ YClients: Token установлен ({len(YCLIENTS_PARTNER_TOKEN)} символов: {YCLIENTS_PARTNER_TOKEN[:5]}...{YCLIENTS_PARTNER_TOKEN[-3:]})")

if YCLIENTS_COMPANY_ID == 0:
    print("⚠️ YClients: YCLIENTS_COMPANY_ID НЕ УСТАНОВЛЕН!")
else:
    print(f"✅ YClients: Company ID = {YCLIENTS_COMPANY_ID}")

API = "https://api.yclients.com/api/v1"

# Стандартные заголовки с Bearer токеном
HEADERS = {
    "Authorization": f"Bearer {YCLIENTS_PARTNER_TOKEN}",
    "Accept": "application/vnd.yclients.v2+json",
    "Content-Type": "application/json"
}

# Альтернативные заголовки для booking endpoints (без Bearer)
BOOKING_HEADERS = {
    "Authorization": YCLIENTS_PARTNER_TOKEN,  # Без "Bearer"
    "Accept": "application/json",
    "Content-Type": "application/json"
}

# Логирование конфигурации
print(f"YClients Config: Token={'***' if YCLIENTS_PARTNER_TOKEN else 'NOT SET'} (len={len(YCLIENTS_PARTNER_TOKEN) if YCLIENTS_PARTNER_TOKEN else 0}), Company ID={YCLIENTS_COMPANY_ID}")


def get_user_token():
    """Получить User Token через авторизацию"""
    global YCLIENTS_USER_TOKEN
    
    if YCLIENTS_USER_TOKEN:
        return YCLIENTS_USER_TOKEN
    
    if not YCLIENTS_LOGIN or not YCLIENTS_PASSWORD:
        print("⚠️ YClients: YCLIENTS_LOGIN или YCLIENTS_PASSWORD не установлены, User Token недоступен")
        return None
    
    try:
        url = f"{API}/auth"
        headers = {
            "Authorization": f"Bearer {YCLIENTS_PARTNER_TOKEN}",
            "Accept": "application/vnd.yclients.v2+json",
            "Content-Type": "application/json"
        }
        payload = {
            "login": YCLIENTS_LOGIN,
            "password": YCLIENTS_PASSWORD
        }
        
        print(f"YClients: Получаем User Token для {YCLIENTS_LOGIN[:3]}***")
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        
        if response.status_code == 201:
            result = response.json()
            YCLIENTS_USER_TOKEN = result.get('user_token')
            print(f"✅ YClients: User Token получен ({YCLIENTS_USER_TOKEN[:10]}...)")
            return YCLIENTS_USER_TOKEN
        elif response.status_code == 200:
            # Требуется 2FA
            print("⚠️ YClients: Требуется код подтверждения 2FA (пока не поддерживается)")
            return None
        else:
            print(f"❌ YClients: Ошибка авторизации {response.status_code}: {response.text[:200]}")
            return None
    except Exception as e:
        print(f"❌ YClients: Ошибка получения User Token: {e}")
        return None


def _get(path, params=None, headers=None, use_user_token=False):
    """Внутренний GET запрос"""
    url = API + path
    
    # Если требуется User Token, получаем его
    if use_user_token:
        user_token = get_user_token()
        if user_token:
            headers = {
                "Authorization": f"Bearer {YCLIENTS_PARTNER_TOKEN}",
                "Accept": "application/vnd.yclients.v2+json",
                "Content-Type": "application/json"
            }
    
    request_headers = headers or HEADERS
    try:
        print(f"YClients GET: {url}")
        print(f"YClients Headers: {request_headers}")
        
        response = requests.get(url, headers=request_headers, params=params or {}, timeout=10)
        print(f"YClients Response Status: {response.status_code}")
        
        # Логируем ответ при ошибке
        if response.status_code != 200:
            print(f"YClients Error Response: {response.text[:500]}")
            try:
                error_json = response.json()
                print(f"YClients Error JSON: {error_json}")
            except:
                pass
        
        response.raise_for_status()
        result = response.json()
        
        print(f"YClients Response Keys: {result.keys() if isinstance(result, dict) else 'Not a dict'}")
        data = result.get('data', result)  # Если нет 'data', возвращаем весь результат
        print(f"YClients Data Type: {type(data)}, Length: {len(data) if isinstance(data, (list, dict)) else 'N/A'}")
        
        return data
    except requests.exceptions.HTTPError as e:
        print(f"YClients HTTP Error ({url}): {e}")
        if hasattr(e.response, 'text'):
            print(f"YClients Error Response Text: {e.response.text[:500]}")
        log.error(f"YClients GET error ({url}): {e}")
        raise
    except Exception as e:
        print(f"YClients GET error ({url}): {e}")
        log.error(f"YClients GET error ({url}): {e}")
        raise


def _post(path, json_data):
    """Внутренний POST запрос"""
    url = API + path
    try:
        response = requests.post(url, headers=HEADERS, json=json_data, timeout=10)
        response.raise_for_status()
        result = response.json()
        return result.get('data', {})
    except Exception as e:
        log.error(f"YClients POST error ({url}): {e}")
        raise


# ═══════════════════════════════════════════════════════════
# API Функции
# ═══════════════════════════════════════════════════════════

def get_services(company_id=None):
    """Получить список услуг - требует User Token"""
    cid = company_id or YCLIENTS_COMPANY_ID
    
    # Получаем User Token
    user_token = get_user_token()
    if not user_token:
        print("⚠️ YClients: Не удалось получить User Token для загрузки услуг")
        return []
    
    # Используем /company/{id}/services с User Token вместо Partner Token
    headers = {
        "Authorization": f"Bearer {user_token}",
        "Accept": "application/vnd.yclients.v2+json",
        "Content-Type": "application/json"
    }
    return _get(f"/company/{cid}/services", headers=headers)


def get_staff(company_id=None, service_ids=None):
    """Получить список мастеров - требует User Token"""
    cid = company_id or YCLIENTS_COMPANY_ID
    params = {}
    if service_ids:
        params["service_ids[]"] = service_ids
    
    # Получаем User Token
    user_token = get_user_token()
    if not user_token:
        print("⚠️ YClients: Не удалось получить User Token для загрузки мастеров")
        return []
    
    # Используем /company/{id}/staff с User Token
    headers = {
        "Authorization": f"Bearer {user_token}",
        "Accept": "application/vnd.yclients.v2+json",
        "Content-Type": "application/json"
    }
    return _get(f"/company/{cid}/staff", params, headers=headers)


def get_book_dates(company_id=None):
    """Получить доступные даты для записи"""
    cid = company_id or YCLIENTS_COMPANY_ID
    return _get(f"/book_dates/{cid}")


def get_free_slots(staff_id, service_id, date_iso, company_id=None):
    """
    Получить свободные слоты для записи
    
    Args:
        staff_id: ID мастера
        service_id: ID услуги
        date_iso: Дата в формате YYYY-MM-DD
        company_id: ID компании (опционально)
    
    Returns:
        List of {"time": "17:30", "datetime": "2025-06-17T14:30:00+03:00"}
    """
    cid = company_id or YCLIENTS_COMPANY_ID
    return _get(
        f"/book_times/{cid}/{staff_id}/{date_iso}",
        params={"service_ids[]": service_id}
    )


def create_booking(
    phone,
    fullname,
    appointments,
    email="",
    comment=None,
    company_id=None
):
    """
    Создать запись клиента
    
    Args:
        phone: Телефон клиента (+79991234567)
        fullname: ФИО клиента
        appointments: Список записей [{"id": service_id, "staff_id": staff_id, "datetime": "2025-06-17T14:30:00+03:00"}]
        email: Email клиента (опционально)
        comment: Комментарий к записи
        company_id: ID компании (опционально)
    
    Returns:
        Результат создания записи
    """
    cid = company_id or YCLIENTS_COMPANY_ID
    
    payload = {
        "phone": phone,
        "fullname": fullname,
        "email": email or f"{phone}@temp.mail",  # YClients требует email
        "appointments": appointments,
    }
    
    if comment:
        payload["comment"] = comment
    
    log.info(f"Creating YClients booking for {fullname} ({phone})")
    return _post(f"/book_record/{cid}", payload)


def search_client_by_phone(phone, company_id=None):
    """
    Поиск клиента по телефону в YClients
    
    Args:
        phone: Телефон клиента
        company_id: ID компании
    
    Returns:
        Информация о клиенте или None
    """
    cid = company_id or YCLIENTS_COMPANY_ID
    
    try:
        result = _get(f"/clients/{cid}", params={"phone": phone})
        if result and len(result) > 0:
            return result[0]  # Возвращаем первого найденного
        return None
    except Exception as e:
        log.error(f"Error searching client: {e}")
        return None


def get_client_records(client_id, company_id=None):
    """
    Получить записи клиента
    
    Args:
        client_id: ID клиента в YClients
        company_id: ID компании
    
    Returns:
        Список записей клиента
    """
    cid = company_id or YCLIENTS_COMPANY_ID
    
    try:
        result = _get(f"/records/{cid}", params={"client_id": client_id})
        return result
    except Exception as e:
        log.error(f"Error getting client records: {e}")
        return []


# ═══════════════════════════════════════════════════════════
# Утилиты
# ═══════════════════════════════════════════════════════════

def format_date_russian(date_iso):
    """Форматирует дату с русскими месяцами"""
    try:
        d = date.fromisoformat(date_iso)
        months = {
            1: 'янв', 2: 'фев', 3: 'мар', 4: 'апр', 5: 'май', 6: 'июн',
            7: 'июл', 8: 'авг', 9: 'сен', 10: 'окт', 11: 'ноя', 12: 'дек'
        }
        weekdays = {
            0: 'пн', 1: 'вт', 2: 'ср', 3: 'чт', 4: 'пт', 5: 'сб', 6: 'вс'
        }
        month = months[d.month]
        weekday = weekdays[d.weekday()]
        return f"{d.day} {month} ({weekday})"
    except Exception as e:
        return date_iso


def is_yclients_configured():
    """Проверить настроен ли YClients"""
    return bool(YCLIENTS_PARTNER_TOKEN and YCLIENTS_COMPANY_ID > 0)

