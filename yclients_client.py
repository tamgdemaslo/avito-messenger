"""
YClients API Integration - ПРОСТАЯ ВЕРСИЯ
Только booking endpoints с Partner Token
"""
import os
import requests
import logging

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
    try:
        response = requests.post(url, headers=HEADERS, json=json_data, timeout=10)
        response.raise_for_status()
        result = response.json()
        return result.get('data', {})
    except Exception as e:
        log.error(f"YClients POST error ({url}): {e}")
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
    """POST /book_record/{company_id} - Создать запись"""
    cid = company_id or YCLIENTS_COMPANY_ID
    
    payload = {
        "phone": phone,
        "fullname": fullname,
        "email": email or f"{phone}@temp.mail",
        "appointments": appointments,
    }
    
    if comment:
        payload["comment"] = comment
    
    log.info(f"Creating YClients booking for {fullname} ({phone})")
    return _post(f"/book_record/{cid}", payload)


def is_yclients_configured():
    """Проверить настроен ли YClients"""
    return bool(YCLIENTS_PARTNER_TOKEN and YCLIENTS_COMPANY_ID > 0)

