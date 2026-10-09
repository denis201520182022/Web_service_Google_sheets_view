# Zabota Tables

Многопользовательский веб-сервис для работы с Google Sheets с разграничением прав, аудитом действий и админ-панелью.

## Описание

Расширенная версия табличного редактора, превращенная в полноценное SaaS-приложение. Поддерживает работу нескольких пользователей с одними и теми же таблицами, систему блокировок диапазонов (как в Google Docs), локальную стилизацию и детальную статистику доступа.

## Стек

- **Backend:** FastAPI, SQLAlchemy (PostgreSQL), Alembic, gspread, JWT (Bcrypt)
- **Frontend:** Vanilla JS, Handsontable, SheetJS (Excel export)
- **Infra:** Docker, Docker Compose, GitLab CI

## Функционал

### Редактирование
- 📊 **Полный клон:** редактирование, формулы, автосохранение (debounce 2s)
- 📥 **Экспорт:** выгрузка в `.xlsx` через SheetJS
- 📑 **Валидация:** поддержка выпадающих списков из Google Sheets
- ⚡ **Batch Updates:** групповая запись с Exponential Backoff (защита от 429 ошибок)

### Многопользовательский режим
- 👥 **Учетные записи:** регистрация через админа, JWT-сессии (8 часов)
- 📜 **История:** список открытых таблиц с счетчиком и датой доступа
- 🔒 **Блокировки:** админ может заблокировать диапазоны (readOnly для других)
- 🎨 **Стили:** локальное сохранение форматирования (жирный, цвет, выравнивание)

### Безопасность и логи
- 📋 **Audit Log:** регистрация всех действий (login, update, lock) с IP-адресом
- 🛡 **Rate Limiting:** автоматические повторы при превышении квот Google API
- 🏢 **Service Accounts:** поддержка пула аккаунтов (балансировка нагрузки)

## Структура

```
├── alembic/                 # Миграции БД
├── backend/
│   ├── main.py              # FastAPI (Auth, Sheets, Admin API)
│   ├── auth.py              # JWT, Bcrypt, Audit Logic
│   ├── models.py            # SQLAlchemy (5 таблиц)
│   ├── database.py          # Подключение PostgreSQL
│   └── config.py            # .env конфигурация
├── frontend/
│   ├── index.html           # SPA (Editor + Admin UI)
│   ├── admin_users.js       # Управление пользователями
│   └── admin_users.css      # Стили админ-панели
├── create_admin.py          # Скрипт создания первого админа
├── docker-compose.yml       # Стек: Backend + PostgreSQL
├── Dockerfile               # Сборка бэкенда
└── requirements.txt
```

## Быстрый старт

### 1. Установка

```bash
pip install -r requirements.txt
cp .env.example .env  # Заполнить переменные
```

### 2. Настройка Google Cloud

1. Создать Service Accounts в [Google Cloud Console](https://console.cloud.google.com/)
2. Включить **Google Sheets API**
3. Положить JSON-ключи в папку `backend/service_accounts/`
   *(опционально: можно использовать один основной ключ в `.env`)*

### 3. База данных

Проект использует PostgreSQL.
```bash
# Применить миграции (создание таблиц)
alembic upgrade head

# Создать первого администратора
python create_admin.py
# По умолчанию: admin / admin123
```

### 4. Запуск

```bash
# Backend
uvicorn backend.main:app --host 0.0.0.0 --port 8000

# Frontend
Открыть frontend/index.html в браузере
```

### Docker (готовый стек)

```bash
docker-compose up --build
# БД и Бэкенд поднимутся автоматически
```

## Админ-панель

Доступна авторизованным администраторам:
- **Управление пользователями:** создание, редактирование, удаление, смена ролей.
- **Блокировки:** выбор диапазона ячеек → запрет редактирования для других.
- **Стили:** применение форматирования к диапазонам.

## API

### Авторизация
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/login` | Вход (возвращает JWT + инфо о юзере) |

### Таблицы
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/set-sheet` | Подключить таблицу по URL |
| GET | `/api/my-sheets` | История таблиц пользователя |
| POST | `/api/select-sheet` | Выбрать активный лист |
| GET | `/api/data` | Данные + Формулы + Валидации |
| POST | `/api/batch-update` | Сохранение изменений |

### Администрирование
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/admin/users` | Список всех пользователей |
| POST | `/api/admin/users` | Создать пользователя |
| PUT | `/api/admin/users/{id}` | Редактировать |
| DELETE | `/api/admin/users/{id}` | Удалить |
| POST | `/api/admin/lock-range` | Заблокировать диапазон |
| DELETE | `/api/admin/unlock-range/{id}` | Разблокировать |

### Стили
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/styles` | Загрузка стилей ячеек |
| POST | `/api/styles/save` | Сохранение стилей |

