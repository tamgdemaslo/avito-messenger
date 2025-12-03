# Настройка переменных окружения в Railway

## После успешного деплоя

Railway должен успешно задеплоить приложение. Теперь нужно настроить переменные окружения.

---

## Шаг 1: Откройте ваш проект в Railway

1. Перейдите на https://railway.app/dashboard
2. Найдите проект `avito-messenger`
3. Откройте его

---

## Шаг 2: Добавьте переменные окружения

В Railway Dashboard:

1. Перейдите в раздел **Variables** (или **Environment**)
2. Нажмите **New Variable** или **Add Variable**

### Добавьте следующие переменные:

#### 1. AVITO_CLIENT_ID
```
HHiafcJb3rn8agxhzM8g
```

#### 2. AVITO_CLIENT_SECRET
```
DusHGZF4gADWpNwIHbeefVNwxqoUXe5i_LQ2_g2o
```

#### 3. SECRET_KEY

Сгенерируйте случайный ключ. Выполните в терминале:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Скопируйте результат и используйте как значение `SECRET_KEY`.

Или используйте этот:
```
a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2
```

#### 4. FLASK_ENV
```
production
```

---

## Шаг 3: Получите URL приложения

### Создайте домен:

1. В Railway Dashboard перейдите в **Settings** → **Domains**
2. Нажмите **Generate Domain**
3. Railway создаст домен типа:
   ```
   avito-messenger-production.up.railway.app
   ```

4. **Скопируйте этот URL!**

---

## Шаг 4: Добавьте REDIRECT_URI

Вернитесь в **Variables** и добавьте ещё одну переменную:

#### 5. AVITO_REDIRECT_URI

Используйте ваш URL от Railway + `/callback`:
```
https://ваш-домен.up.railway.app/callback
```

Например:
```
https://avito-messenger-production.up.railway.app/callback
```

---

## Шаг 5: Перезапустите приложение

После добавления всех переменных:

1. Railway автоматически перезапустит приложение
2. Или нажмите **Restart** вручную

---

## Шаг 6: Проверьте работу

Откройте ваше приложение:
```
https://ваш-домен.up.railway.app
```

Вы должны увидеть страницу входа Avito Messenger!

---

## Итого: 5 переменных

✅ `AVITO_CLIENT_ID` = `HHiafcJb3rn8agxhzM8g`
✅ `AVITO_CLIENT_SECRET` = `DusHGZF4gADWpNwIHbeefVNwxqoUXe5i_LQ2_g2o`
✅ `SECRET_KEY` = (сгенерированный ключ)
✅ `FLASK_ENV` = `production`
✅ `AVITO_REDIRECT_URI` = `https://ваш-домен.up.railway.app/callback`

---

## Что дальше?

После настройки переменных переходите к **Шагу 4: Настройка Avito**

Нужно добавить Redirect URI в настройках приложения Avito.

