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


# Инициализируем БД при импорте модуля
try:
    init_database()
except Exception as e:
    print(f"⚠️ Database initialization error: {e}")
