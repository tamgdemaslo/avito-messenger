"""
Database module for storing customer information
Поддержка PostgreSQL (продакшен) и SQLite (локально)
"""

import os
from datetime import datetime

# Определяем тип БД
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    # PostgreSQL (Railway)
    import psycopg2
    from psycopg2.extras import RealDictCursor
    USE_POSTGRES = True
    print("📊 Using PostgreSQL database")
else:
    # SQLite (локально)
    import sqlite3
    USE_POSTGRES = False
    DB_PATH = os.path.join(os.path.dirname(__file__), 'customers.db')
    print("📊 Using SQLite database")


def get_connection():
    """Получить подключение к БД"""
    if USE_POSTGRES:
        return psycopg2.connect(DATABASE_URL)
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn


def init_database():
    """Инициализация базы данных"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if USE_POSTGRES:
        # PostgreSQL синтаксис
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS customers (
                id SERIAL PRIMARY KEY,
                source TEXT NOT NULL,
                source_id TEXT NOT NULL,
                name TEXT,
                vin TEXT,
                phone TEXT,
                comments TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(source, source_id)
            )
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_source_id 
            ON customers(source, source_id)
        ''')
        
        # Таблица для шаблонов сообщений
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS message_templates (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                text TEXT NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица для отложенных задач отправки сообщений
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scheduled_messages (
                id SERIAL PRIMARY KEY,
                phone TEXT NOT NULL,
                fullname TEXT,
                template_type TEXT NOT NULL,
                message_text TEXT NOT NULL,
                chat_id TEXT,
                source TEXT,
                send_at TIMESTAMP NOT NULL,
                sent BOOLEAN DEFAULT FALSE,
                sent_at TIMESTAMP,
                error TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_scheduled_messages_send_at 
            ON scheduled_messages(send_at) WHERE sent = FALSE
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_scheduled_messages_phone 
            ON scheduled_messages(phone)
        ''')
        
        # Таблица для отслеживания обработанных записей YClients
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS processed_yclients_records (
                id SERIAL PRIMARY KEY,
                yclients_record_id TEXT NOT NULL UNIQUE,
                phone TEXT NOT NULL,
                fullname TEXT,
                datetime TIMESTAMP,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_processed_records_id 
            ON processed_yclients_records(yclients_record_id)
        ''')
    else:
        # SQLite синтаксис
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                source_id TEXT NOT NULL,
                name TEXT,
                vin TEXT,
                phone TEXT,
                comments TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(source, source_id)
            )
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_source_id 
            ON customers(source, source_id)
        ''')
        
        # Таблица для шаблонов сообщений
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS message_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                text TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица для отложенных задач отправки сообщений
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scheduled_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone TEXT NOT NULL,
                fullname TEXT,
                template_type TEXT NOT NULL,
                message_text TEXT NOT NULL,
                chat_id TEXT,
                source TEXT,
                send_at TIMESTAMP NOT NULL,
                sent INTEGER DEFAULT 0,
                sent_at TIMESTAMP,
                error TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_scheduled_messages_send_at 
            ON scheduled_messages(send_at) WHERE sent = 0
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_scheduled_messages_phone 
            ON scheduled_messages(phone)
        ''')
        
        # Таблица для отслеживания обработанных записей YClients
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS processed_yclients_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                yclients_record_id TEXT NOT NULL UNIQUE,
                phone TEXT NOT NULL,
                fullname TEXT,
                datetime TIMESTAMP,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_processed_records_id 
            ON processed_yclients_records(yclients_record_id)
        ''')
    
    conn.commit()
    conn.close()
    print("✅ Database initialized")


def get_customer(source, source_id):
    """Получить информацию о клиенте"""
    conn = get_connection()
    
    if USE_POSTGRES:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
    else:
        cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM customers 
        WHERE source = %s AND source_id = %s
    ''' if USE_POSTGRES else '''
        SELECT * FROM customers 
        WHERE source = ? AND source_id = ?
    ''', (source, source_id))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return None


def save_customer(source, source_id, name=None, vin=None, phone=None, comments=None):
    """Сохранить/обновить информацию о клиенте"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Проверяем существует ли клиент
    existing = get_customer(source, source_id)
    
    if existing:
        # Обновляем существующего
        update_fields = []
        params = []
        
        if name is not None:
            update_fields.append('name = %s' if USE_POSTGRES else 'name = ?')
            params.append(name)
        if vin is not None:
            update_fields.append('vin = %s' if USE_POSTGRES else 'vin = ?')
            params.append(vin)
        if phone is not None:
            update_fields.append('phone = %s' if USE_POSTGRES else 'phone = ?')
            params.append(phone)
        if comments is not None:
            update_fields.append('comments = %s' if USE_POSTGRES else 'comments = ?')
            params.append(comments)
        
        update_fields.append('updated_at = %s' if USE_POSTGRES else 'updated_at = ?')
        params.append(datetime.now())
        
        params.extend([source, source_id])
        
        placeholder = '%s' if USE_POSTGRES else '?'
        cursor.execute(f'''
            UPDATE customers 
            SET {', '.join(update_fields)}
            WHERE source = {placeholder} AND source_id = {placeholder}
        ''', params)
    else:
        # Создаем нового
        placeholder = '%s' if USE_POSTGRES else '?'
        cursor.execute(f'''
            INSERT INTO customers (source, source_id, name, vin, phone, comments)
            VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})
        ''', (source, source_id, name, vin, phone, comments))
    
    conn.commit()
    conn.close()
    
    return get_customer(source, source_id)


def search_customers(query):
    """Поиск клиентов по имени, VIN, телефону"""
    conn = get_connection()
    
    if USE_POSTGRES:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
    else:
        cursor = conn.cursor()
    
    search_pattern = f'%{query}%'
    
    if USE_POSTGRES:
        cursor.execute('''
            SELECT * FROM customers 
            WHERE name ILIKE %s OR vin ILIKE %s OR phone ILIKE %s OR comments ILIKE %s
            ORDER BY updated_at DESC
            LIMIT 50
        ''', (search_pattern, search_pattern, search_pattern, search_pattern))
    else:
        cursor.execute('''
            SELECT * FROM customers 
            WHERE name LIKE ? OR vin LIKE ? OR phone LIKE ? OR comments LIKE ?
            ORDER BY updated_at DESC
            LIMIT 50
        ''', (search_pattern, search_pattern, search_pattern, search_pattern))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def get_all_customers(limit=100):
    """Получить всех клиентов"""
    conn = get_connection()
    
    if USE_POSTGRES:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute('''
            SELECT * FROM customers 
            ORDER BY updated_at DESC
            LIMIT %s
        ''', (limit,))
    else:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM customers 
            ORDER BY updated_at DESC
            LIMIT ?
        ''', (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


# ==================== Функции для работы с шаблонами сообщений ====================

def get_all_templates():
    """Получить все шаблоны сообщений"""
    conn = get_connection()
    
    if USE_POSTGRES:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute('SELECT * FROM message_templates ORDER BY created_at DESC')
    else:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM message_templates ORDER BY created_at DESC')
    
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_template(template_id):
    """Получить шаблон по ID"""
    conn = get_connection()
    
    if USE_POSTGRES:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute('SELECT * FROM message_templates WHERE id = %s', (template_id,))
    else:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM message_templates WHERE id = ?', (template_id,))
    
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_template_by_type(template_type):
    """Получить активный шаблон по типу"""
    conn = get_connection()
    
    if USE_POSTGRES:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute('''
            SELECT * FROM message_templates 
            WHERE type = %s AND is_active = TRUE 
            ORDER BY created_at DESC 
            LIMIT 1
        ''', (template_type,))
    else:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM message_templates 
            WHERE type = ? AND is_active = 1 
            ORDER BY created_at DESC 
            LIMIT 1
        ''', (template_type,))
    
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def create_template(name, template_type, text, is_active=True):
    """Создать новый шаблон"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if USE_POSTGRES:
        cursor.execute('''
            INSERT INTO message_templates (name, type, text, is_active)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        ''', (name, template_type, text, is_active))
        template_id = cursor.fetchone()[0]
    else:
        cursor.execute('''
            INSERT INTO message_templates (name, type, text, is_active)
            VALUES (?, ?, ?, ?)
        ''', (name, template_type, text, 1 if is_active else 0))
        template_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    return get_template(template_id)


def update_template(template_id, name=None, template_type=None, text=None, is_active=None):
    """Обновить шаблон"""
    conn = get_connection()
    cursor = conn.cursor()
    
    update_fields = []
    params = []
    
    if name is not None:
        update_fields.append('name = %s' if USE_POSTGRES else 'name = ?')
        params.append(name)
    if template_type is not None:
        update_fields.append('type = %s' if USE_POSTGRES else 'type = ?')
        params.append(template_type)
    if text is not None:
        update_fields.append('text = %s' if USE_POSTGRES else 'text = ?')
        params.append(text)
    if is_active is not None:
        update_fields.append('is_active = %s' if USE_POSTGRES else 'is_active = ?')
        params.append(1 if is_active else 0 if not USE_POSTGRES else is_active)
    
    update_fields.append('updated_at = %s' if USE_POSTGRES else 'updated_at = ?')
    params.append(datetime.now())
    params.append(template_id)
    
    placeholder = '%s' if USE_POSTGRES else '?'
    cursor.execute(f'''
        UPDATE message_templates 
        SET {', '.join(update_fields)}
        WHERE id = {placeholder}
    ''', params)
    
    conn.commit()
    conn.close()
    return get_template(template_id)


def delete_template(template_id):
    """Удалить шаблон"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if USE_POSTGRES:
        cursor.execute('DELETE FROM message_templates WHERE id = %s', (template_id,))
    else:
        cursor.execute('DELETE FROM message_templates WHERE id = ?', (template_id,))
    
    conn.commit()
    conn.close()


# ==================== Функции для работы с отложенными задачами ====================

def create_scheduled_message(phone, fullname, template_type, message_text, send_at, chat_id=None, source=None):
    """Создать отложенную задачу отправки сообщения"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if USE_POSTGRES:
        cursor.execute('''
            INSERT INTO scheduled_messages (phone, fullname, template_type, message_text, send_at, chat_id, source)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        ''', (phone, fullname, template_type, message_text, send_at, chat_id, source))
        task_id = cursor.fetchone()[0]
    else:
        cursor.execute('''
            INSERT INTO scheduled_messages (phone, fullname, template_type, message_text, send_at, chat_id, source)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (phone, fullname, template_type, message_text, send_at, chat_id, source))
        task_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    return task_id


def get_pending_scheduled_messages():
    """Получить все неотправленные отложенные задачи, время отправки которых наступило"""
    conn = get_connection()
    
    if USE_POSTGRES:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute('''
            SELECT * FROM scheduled_messages 
            WHERE sent = FALSE AND send_at <= CURRENT_TIMESTAMP
            ORDER BY send_at ASC
        ''')
    else:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM scheduled_messages 
            WHERE sent = 0 AND send_at <= datetime('now')
            ORDER BY send_at ASC
        ''')
    
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def mark_scheduled_message_sent(task_id, error=None):
    """Пометить отложенную задачу как отправленную"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if USE_POSTGRES:
        cursor.execute('''
            UPDATE scheduled_messages 
            SET sent = TRUE, sent_at = CURRENT_TIMESTAMP, error = %s
            WHERE id = %s
        ''', (error, task_id))
    else:
        cursor.execute('''
            UPDATE scheduled_messages 
            SET sent = 1, sent_at = datetime('now'), error = ?
            WHERE id = ?
        ''', (error, task_id))
    
    conn.commit()
    conn.close()


# Инициализируем БД при импорте модуля
try:
    init_database()
except Exception as e:
    print(f"⚠️ Database initialization error: {e}")
