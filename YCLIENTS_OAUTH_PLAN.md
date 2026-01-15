# План реализации OAuth интеграции YClients

## Текущая ситуация

- ✅ Partner Token работает для создания записей (`/book_record`)
- ❌ Partner Token НЕ работает для получения записей (`/records`)
- Для получения записей нужен **User Token** системного пользователя

## Что нужно сделать

### 1. Регистрация приложения в YClients маркетплейсе

1. Зайти в YClients → Настройки → API и интеграции → Мои приложения
2. Создать новое приложение
3. Настроить права доступа для системного пользователя:
   - ✅ Журнал записи (для получения записей)
   - ✅ Клиентская база (для получения данных клиентов)
   - ✅ Услуги (для получения списка услуг)

### 2. Настройка OAuth endpoints

В настройках приложения указать:

- **Callback Url**: `https://avito.tamgdemaslocrm.ru/api/yclients/webhook`
  - Для получения webhooks об отключении интеграции

- **Registration Redirect Url**: `https://avito.tamgdemaslocrm.ru/yclients/connect`
  - Форма регистрации/подключения интеграции
  - Можно открывать в iframe

- **Передавать данные пользователя при подключении**: ✅ Включить
  - Автоматическая регистрация пользователя

- **Разрешить добавлять приложение в несколько филиалов**: ✅ Включить
  - Подключение сразу во все филиалы

### 3. Реализация OAuth flow

#### 3.1. Endpoint для подключения интеграции

```
GET /yclients/connect
```

- Принимает параметры от YClients (company_id, user_id, token и т.д.)
- Сохраняет User Token в базе данных
- Связывает токен с company_id

#### 3.2. Endpoint для webhook

```
POST /api/yclients/webhook
```

- Обрабатывает события отключения интеграции
- Удаляет User Token из базы данных

#### 3.3. Хранение User Token

Создать таблицу в БД:
```sql
CREATE TABLE yclients_integrations (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL UNIQUE,
    user_token TEXT NOT NULL,
    user_id INTEGER,
    connected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
)
```

### 4. Использование User Token для получения записей

Обновить `yclients_client.py`:

```python
def get_user_token(company_id):
    """Получить User Token для компании"""
    # Получить из БД
    pass

def get_records(company_id=None, date_from=None, date_to=None, limit=100):
    """GET /records/{company_id} - Получить список записей"""
    cid = company_id or YCLIENTS_COMPANY_ID
    
    # Получить User Token для этой компании
    user_token = get_user_token(cid)
    if not user_token:
        print("⚠️ User Token не найден. Интеграция не подключена.")
        return []
    
    # Использовать User Token вместо Partner Token
    headers = {
        "Authorization": f"Bearer {user_token}",
        "Accept": "application/vnd.yclients.v2+json",
        "Content-Type": "application/json"
    }
    
    # Запрос к API
    ...
```

### 5. Обновить функцию проверки записей

Включить обратно `check_new_yclients_records()` в `notifications.py`:
- Использовать User Token для получения записей
- Отправлять уведомления для всех новых записей

## Преимущества

- ✅ Уведомления будут работать для всех записей (и созданных через API, и напрямую в YClients)
- ✅ Можно получать данные о клиентах
- ✅ Можно получать историю записей
- ✅ Автоматическое подключение при установке приложения

## Сложности

- ⚠️ Нужно зарегистрировать приложение в маркетплейсе YClients
- ⚠️ Нужно реализовать OAuth flow
- ⚠️ Нужно обрабатывать webhooks
- ⚠️ Нужно хранить User Token для каждой компании

## Альтернатива

Если не хотите регистрировать приложение в маркетплейсе:
- Использовать встроенные уведомления YClients для записей, созданных напрямую
- Наш API отправляет уведомления только для записей, созданных через `/api/yclients/book`
