"""
Database module for storing customer information
SQLite база данных для хранения информации о клиентах
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'customers.db')


def init_database():
    """Инициализация базы данных"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Таблица клиентов
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
    
    # Индексы для быстрого поиска
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_source_id 
        ON customers(source, source_id)
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Database initialized")


def get_customer(source, source_id):
    """Получить информацию о клиенте"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
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
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Проверяем существует ли клиент
    existing = get_customer(source, source_id)
    
    if existing:
        # Обновляем существующего
        update_fields = []
        params = []
        
        if name is not None:
            update_fields.append('name = ?')
            params.append(name)
        if vin is not None:
            update_fields.append('vin = ?')
            params.append(vin)
        if phone is not None:
            update_fields.append('phone = ?')
            params.append(phone)
        if comments is not None:
            update_fields.append('comments = ?')
            params.append(comments)
        
        update_fields.append('updated_at = ?')
        params.append(datetime.now())
        
        params.extend([source, source_id])
        
        cursor.execute(f'''
            UPDATE customers 
            SET {', '.join(update_fields)}
            WHERE source = ? AND source_id = ?
        ''', params)
    else:
        # Создаем нового
        cursor.execute('''
            INSERT INTO customers (source, source_id, name, vin, phone, comments)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (source, source_id, name, vin, phone, comments))
    
    conn.commit()
    customer_id = cursor.lastrowid
    conn.close()
    
    return get_customer(source, source_id)


def search_customers(query):
    """Поиск клиентов по имени, VIN, телефону"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    search_pattern = f'%{query}%'
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
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
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
init_database()

