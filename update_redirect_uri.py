#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для обновления Redirect URI в app.py
"""

import sys

def update_redirect_uri(new_uri):
    """Обновить AVITO_REDIRECT_URI в app.py"""
    
    # Читаем файл
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Ищем и заменяем
    import re
    pattern = r'AVITO_REDIRECT_URI = "([^"]+)"'
    
    match = re.search(pattern, content)
    if match:
        old_uri = match.group(1)
        print(f"Старый URI: {old_uri}")
        print(f"Новый URI: {new_uri}")
        
        new_content = re.sub(pattern, f'AVITO_REDIRECT_URI = "{new_uri}"', content)
        
        # Записываем обратно
        with open('app.py', 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print("✅ Redirect URI успешно обновлен!")
        print("\nТеперь перезапустите сервер:")
        print("  python3 app.py")
    else:
        print("❌ Не удалось найти AVITO_REDIRECT_URI в app.py")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Использование:")
        print("  python3 update_redirect_uri.py <новый_redirect_uri>")
        print("\nПримеры:")
        print("  python3 update_redirect_uri.py http://127.0.0.1:5002/callback")
        print("  python3 update_redirect_uri.py https://abc123.ngrok.io/callback")
        sys.exit(1)
    
    new_uri = sys.argv[1]
    update_redirect_uri(new_uri)

