source venv/bin/activate
systemctl restart zabota_tables
systemctl status zabota_tables
journalctl -u zabota_tables -f


tester pass123


# 🚀 SheetPro - Прокси для Google Таблиц

Безопасный веб-сервис для работы с Google Sheets через собственный интерфейс.

## 📋 Возможности

✅ **Авторизация** - защита паролем  
✅ **Выбор таблиц** - подключение по ссылке  
✅ **Множественные листы** - переключение между листами  
✅ **Редактирование** - полноценная работа с ячейками  
✅ **Формулы** - поддержка всех формул Google Sheets  
✅ **Автосохранение** - изменения сразу в облаке  
✅ **Красивый дизайн** - современный UI  

## 🛠️ Установка

### 1. Требования
```bash
Python 3.8+
pip install fastapi uvicorn gspread python-jose[cryptography]
```

### 2. Структура проекта
```
project/
├── backend/
│   ├── main.py
│   ├── auth.py
│   ├── config.py
│   └── service_account.json   # <- Получить из Google Cloud
├── frontend/
│   └── index.html
└── README.md
```

### 3. Настройка Google Sheets API

#### Шаг 1: Создать проект в Google Cloud
1. Перейти: https://console.cloud.google.com/
2. Создать новый проект
3. Включить **Google Sheets API**

#### Шаг 2: Создать Service Account
1. IAM & Admin → Service Accounts → Create
2. Скачать JSON ключ
3. Сохранить как `service_account.json` в папку `backend/`

#### Шаг 3: Дать доступ к таблице
1. Открыть вашу Google Таблицу
2. Поделиться → добавить email из `service_account.json`
3. Дать права "Редактор"

### 4. Конфигурация

Отредактируй `backend/config.py`:
```python
# Измени логины/пароли
USERS = {
    "admin": "твой_пароль",
    "user1": "пароль123"
}

# Измени секретный ключ (для JWT)
SECRET_KEY = "сгенерируй-случайную-строку-тут"
```

### 5. Запуск

#### Backend:
```bash
cd backend
python main.py
```
Сервер запустится на `http://127.0.0.1:8000`

#### Frontend:
Открой `frontend/index.html` в браузере

## 📖 Использование

### Вход
1. Введи логин: `admin`
2. Введи пароль из `config.py`

### Подключение таблицы
1. Скопируй ссылку на Google Таблицу
2. Вставь в поле
3. Нажми "Подключить"

### Работа с данными
- **Редактирование**: клик на ячейку → ввод текста
- **Формулы**: начни с `=` (например: `=SUM(A1:A10)`)
- **Переключение листов**: клик на вкладки вверху
- **Добавление строк/столбцов**: кнопки на панели

## 🔒 Безопасность

⚠️ **Для production:**

1. **Замени пароли** в `config.py` на сложные
2. **Сгенерируй SECRET_KEY**:
   ```python
   import secrets
   print(secrets.token_urlsafe(32))
   ```
3. **Используй HTTPS** (не HTTP)
4. **Настрой CORS** правильно (не `allow_origins=["*"]`)
5. **Добавь rate limiting**
6. **Храни пароли в БД** (хэшированные)

## 🐛 Решение проблем

### Ошибка "Таблица не найдена"
- Проверь, что Service Account имеет доступ к таблице

### Ошибка "Невалидный токен"
- Токен истек (8 часов), войди заново

### Таблица не обновляется
- Проверь консоль браузера (F12) на ошибки
- Проверь логи backend

### CORS ошибка
- Убедись что backend запущен
- Проверь `API_URL` в `index.html`

## 📝 API Endpoints

```
POST /api/login              - Авторизация
POST /api/set-sheet          - Установка таблицы
GET  /api/sheets             - Список листов
POST /api/select-sheet       - Выбор листа
GET  /api/data               - Получение данных
POST /api/batch-update       - Обновление ячеек
POST /api/add-row            - Добавить строку
POST /api/add-column         - Добавить столбец
```

## 🎨 Кастомизация

### Изменить цвета
В `index.html` найди:
```css
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
```
Замени на свои цвета.

### Изменить название
Замени `SheetPro` на свое название в:
- `<title>` тег
- `.logo` блок
- `.login-box h1`

## 📄 Лицензия

MIT - используй как хочешь

## 🤝 Поддержка

Если есть вопросы - пиши в Issues на GitHub

---

**Сделано с ❤️ для удобной работы с таблицами**