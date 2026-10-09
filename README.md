# Zabota Tables

Веб-сервис для работы с Google Sheets через собственный интерфейс с авторизацией.

## Описание

Proxy-приложение, которое позволяет подключать Google Таблицы по ссылке и работать с ними через удобный веб-интерфейс (Handsontable). Все изменения синхронизируются с облаком в реальном времени.

## Стек

- **Backend:** FastAPI + gspread (Google Sheets API)
- **Frontend:** Vanilla JS + Handsontable + SheetJS (Excel export)
- **Auth:** JWT (Bearer token)
- **Конфиг:** `.env` (python-dotenv)

## Функционал

- 🔐 JWT-авторизация (логин/пароль из конфига)
- 🔗 Подключение таблиц по ссылке (Google Sheets API)
- 📑 Множественные листы с переключением
- ✏️ Редактирование ячеек в реальном времени (debounce 2s)
- 📐 Формулы Google Sheets (`=SUM`, `=VLOOKUP`, `=IF` и др.)
- 💾 Автосохранение с retry при превышении квот (Exponential Backoff)
- 📥 Экспорт в Excel (.xlsx)
- ➕ Добавление строк/столбцов

## Структура

```
├── backend/
│   ├── main.py          # FastAPI сервер + Google Sheets API
│   ├── auth.py          # JWT логика
│   ├── config.py        # Конфиг из .env
│   └── service_account.json  # Ключ доступа Google (добавить отдельно)
├── frontend/
│   └── index.html       # Клиентское приложение
└── requirements.txt
```

## Быстрый старт

### 1. Установка

```bash
pip install -r requirements.txt
cp backend/.env.example backend/.env  # и заполнить
```

### 2. Google Cloud API

1. Создать проект в [Google Cloud Console](https://console.cloud.google.com/)
2. Включить **Google Sheets API**
3. Создать Service Account → скачать JSON-ключ
4. Положить ключ в `backend/service_account.json`
5. Дать доступ Service Account к нужным таблицам (права "Редактор")

### 3. Запуск

```bash
# Backend
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000

# Frontend
Открыть frontend/index.html в браузере
```

## API

| Метод    | Endpoint            | Описание              |
|----------|---------------------|-----------------------|
| POST     | `/api/login`        | Авторизация           |
| POST     | `/api/set-sheet`    | Подключить таблицу    |
| GET      | `/api/sheets`       | Список листов         |
| POST     | `/api/select-sheet` | Выбрать лист          |
| GET      | `/api/data`         | Получить данные       |
| POST     | `/api/batch-update` | Обновить ячейки       |
| POST     | `/api/add-row`      | Добавить строку       |
| POST     | `/api/add-column`   | Добавить столбец      |

