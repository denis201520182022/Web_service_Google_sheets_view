"""
FastAPI Backend для работы с Google Sheets
С поддержкой БД, блокировок и расширенным логированием
"""
import uvicorn
import gspread
import re
import time
import logging
from gspread import Cell
from gspread.exceptions import APIError
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional, Dict
from typing import List, Optional, Dict, Any
from datetime import timedelta, datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc
from backend.models import Base, User, UserSpreadsheet, LockedRange, CellStyle
from gspread.utils import rowcol_to_a1
from backend.config import (
    SERVICE_ACCOUNT_FILE, 
    HOST, 
    PORT, 
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from backend.database import get_db, engine
from backend.models import Base, User, UserSpreadsheet, LockedRange
from backend.auth import (
    authenticate_user, 
    create_access_token, 
    verify_token, 
    require_admin,
    log_action
)

# === ЛОГИРОВАНИЕ ===
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)-15s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# === ИНИЦИАЛИЗАЦИЯ ===
app = FastAPI(title="Zabota Tables API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    allow_credentials=True,
    expose_headers=["*"],
)

# Создание таблиц БД при запуске
Base.metadata.create_all(bind=engine)
logger.info("✅ База данных инициализирована")

try:
    gc = gspread.service_account(filename=SERVICE_ACCOUNT_FILE)
    logger.info("✅ Google Sheets API подключен")
except Exception as e:
    logger.error(f"❌ Ошибка подключения к Google: {e}")
    gc = None

active_sheets: Dict[str, any] = {}

# === МОДЕЛИ ДАННЫХ ===
class LoginRequest(BaseModel):
    username: str
    password: str

class SheetURLRequest(BaseModel):
    url: str

class CellChange(BaseModel):
    row: int
    col: int
    newValue: str

class BatchUpdate(BaseModel):
    updates: List[CellChange]

class SheetSelection(BaseModel):
    sheet_name: str

class LockRangeRequest(BaseModel):
    spreadsheet_id: str
    sheet_name: str
    range_notation: str
    reason: Optional[str] = None

class StyleUpdate(BaseModel):
    row: int
    col: int
    style: Dict[str, Any]  # Словарь стилей, например {"bold": True, "align": "center"}

class BatchStyleRequest(BaseModel):
    spreadsheet_id: str
    sheet_name: str
    styles: List[StyleUpdate]

# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===
def extract_spreadsheet_id(url: str) -> Optional[str]:
    pattern = r'/spreadsheets/d/([a-zA-Z0-9-_]+)'
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    return None


def get_client_ip(request: Request) -> str:
    """Получение IP адреса клиента"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0]
    return request.client.host


def is_cell_locked(
    db: Session,
    spreadsheet_id: str,
    sheet_name: str,
    row: int,
    col: int
) -> Optional[LockedRange]:
    """
    Проверка, заблокирована ли ячейка
    
    Returns:
        LockedRange если ячейка заблокирована, иначе None
    """
    locked_ranges = db.query(LockedRange).filter(
        LockedRange.spreadsheet_id == spreadsheet_id,
        LockedRange.sheet_name == sheet_name
    ).all()
    
    for lock in locked_ranges:
        # Парсим range_notation (например: A1:C10)
        if is_cell_in_range(row, col, lock.range_notation):
            return lock
    
    return None


def is_cell_in_range(row: int, col: int, range_notation: str) -> bool:
    """
    Проверка, попадает ли ячейка в диапазон
    """
    try:
        # === ИСПРАВЛЕНИЕ ЗДЕСЬ ===
        if ':' not in range_notation:
            # Если это одна ячейка (например, "A1")
            start_cell = end_cell = range_notation
        else:
            # Если это диапазон (например, "A1:C10")
            parts = range_notation.split(':')
            if len(parts) != 2:
                return False
            start_cell, end_cell = parts
        # =========================
        
        # Конвертируем A1 в координаты
        start_col, start_row = parse_cell_notation(start_cell)
        end_col, end_row = parse_cell_notation(end_cell)
        
        # Проверяем попадание (помним, что наши индексы 0-based)
        return (start_row <= row <= end_row and start_col <= col <= end_col)
    except:
        return False

def parse_cell_notation(cell: str) -> tuple:
    """
    Парсинг A1 в (col, row) 0-based
    
    Args:
        cell: Строка типа 'A1', 'BC45'
    
    Returns:
        (col_index, row_index) 0-based
    """
    import string
    col_str = ''.join(filter(str.isalpha, cell)).upper()
    row_str = ''.join(filter(str.isdigit, cell))
    
    # Конвертируем столбец (A=0, B=1, ..., Z=25, AA=26)
    col_index = 0
    for char in col_str:
        col_index = col_index * 26 + (ord(char) - ord('A') + 1)
    col_index -= 1
    
    row_index = int(row_str) - 1
    
    return (col_index, row_index)


# === API ENDPOINTS ===

@app.get("/")
def read_root():
    return FileResponse("frontend/index.html")


@app.post("/api/login")
def login(
    credentials: LoginRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """Авторизация пользователя"""
    user = authenticate_user(db, credentials.username, credentials.password)
    
    if not user:
        log_action(
            db, 
            user=None,
            action="login_failed",
            details={"username": credentials.username},
            ip_address=get_client_ip(request)
        )
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    log_action(db, user, "login", ip_address=get_client_ip(request))
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "username": user.username,
        "is_admin": user.is_admin
    }


@app.post("/api/set-sheet")
def set_sheet(
    request_data: SheetURLRequest,
    request: Request,
    user: User = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Подключение к Google таблице"""
    if not gc:
        raise HTTPException(status_code=500, detail="Google API не подключен")
    
    spreadsheet_id = extract_spreadsheet_id(request_data.url)
    if not spreadsheet_id:
        raise HTTPException(status_code=400, detail="Невалидная ссылка")
    
    try:
        spreadsheet = gc.open_by_key(spreadsheet_id)
        active_sheets[user.username] = spreadsheet
        sheet_names = [ws.title for ws in spreadsheet.worksheets()]
        
        # Сохраняем в БД
        existing = db.query(UserSpreadsheet).filter(
            UserSpreadsheet.user_id == user.id,
            UserSpreadsheet.spreadsheet_id == spreadsheet_id
        ).first()
        
        if existing:
            existing.access_count += 1
            existing.last_accessed = datetime.now()
            logger.info(f"📊 {user.username} повторно открыл таблицу: {spreadsheet.title}")
        else:
            new_sheet = UserSpreadsheet(
                user_id=user.id,
                spreadsheet_id=spreadsheet_id,
                spreadsheet_title=spreadsheet.title,
                spreadsheet_url=request_data.url
            )
            db.add(new_sheet)
            logger.info(f"📊 {user.username} открыл новую таблицу: {spreadsheet.title}")
        
        db.commit()
        log_action(
            db, user, "open_sheet",
            spreadsheet_id=spreadsheet_id,
            details={"title": spreadsheet.title},
            ip_address=get_client_ip(request)
        )
        
        return {
            "status": "success",
            "title": spreadsheet.title,
            "sheets": sheet_names,
            "spreadsheet_id": spreadsheet_id
        }
    except Exception as e:
        logger.error(f"❌ Ошибка доступа к таблице: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка доступа: {str(e)}")


@app.get("/api/my-sheets")
def get_my_sheets(
    user: User = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Получение истории таблиц пользователя"""
    sheets = db.query(UserSpreadsheet).filter(
        UserSpreadsheet.user_id == user.id
    ).order_by(desc(UserSpreadsheet.last_accessed)).all()
    
    return {
        "sheets": [
            {
                "id": s.spreadsheet_id,
                "title": s.spreadsheet_title,
                "url": s.spreadsheet_url,
                "last_accessed": s.last_accessed.isoformat(),
                "access_count": s.access_count,
                "is_favorite": s.is_favorite
            }
            for s in sheets
        ]
    }


@app.post("/api/select-sheet")
def select_sheet(
    request_data: SheetSelection,
    user: User = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Выбор листа в таблице"""
    if user.username not in active_sheets:
        raise HTTPException(status_code=400, detail="Таблица не выбрана")
    
    try:
        spreadsheet = active_sheets[user.username]
        worksheet = spreadsheet.worksheet(request_data.sheet_name)
        
        if not hasattr(active_sheets[user.username], '_active_worksheet'):
            active_sheets[user.username]._active_worksheet = {}
        active_sheets[user.username]._active_worksheet[user.username] = worksheet
        
        logger.info(f"📄 {user.username} выбрал лист: {request_data.sheet_name}")
        
        return {"status": "success", "sheet": request_data.sheet_name}
    except Exception as e:
        logger.error(f"❌ Ошибка выбора листа: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/data")
def get_data(
    sheet_name: Optional[str] = None,
    user: User = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Получение данных, формул и выпадающих списков"""
    if user.username not in active_sheets:
        raise HTTPException(status_code=400, detail="Таблица не выбрана")
    
    try:
        spreadsheet = active_sheets[user.username]
        if sheet_name:
            worksheet = spreadsheet.worksheet(sheet_name)
        elif hasattr(spreadsheet, '_active_worksheet') and user.username in spreadsheet._active_worksheet:
            worksheet = spreadsheet._active_worksheet[user.username]
        else:
            worksheet = spreadsheet.sheet1
        
        # 1. Получаем значения и формулы (как и было)
        all_values = worksheet.get_all_values()
        try:
            raw_formulas = worksheet.get_all_values(value_render_option='FORMULA')
            formulas = {f"{r},{c}": val for r, row in enumerate(raw_formulas) 
                        for c, val in enumerate(row) if isinstance(val, str) and val.startswith('=')}
        except:
            formulas = {}

        # 2. НОВОЕ: Получаем выпадающие списки (Data Validation)
        validations = {}
        try:
            # Делаем прямой запрос к API для получения структуры ячеек
            # Нам нужны поля dataValidation
            params = {
                'includeGridData': True,
                'ranges': f"'{worksheet.title}'!A1:Z100", # Берем запас 100 строк
                'fields': 'sheets.data.rowData.values.dataValidation'
            }
            sheet_data = spreadsheet.fetch_sheet_metadata(params)
            
            # Парсим ответ
            grid_data = sheet_data['sheets'][0]['data'][0]
            if 'rowData' in grid_data:
                for r, row in enumerate(grid_data['rowData']):
                    if 'values' in row:
                        for c, cell in enumerate(row['values']):
                            if 'dataValidation' in cell:
                                dv = cell['dataValidation']
                                # Проверяем, что это список (ONE_OF_LIST)
                                if dv.get('condition', {}).get('type') == 'ONE_OF_LIST':
                                    values = [v.get('userEnteredValue') for v in dv['condition'].get('values', [])]
                                    validations[f"{r},{c}"] = values
                                # Если список из диапазона (ONE_OF_RANGE), это чуть сложнее,
                                # но для начала реализуем прямой список
        except Exception as e:
            logger.error(f"⚠️ Ошибка получения валидаций: {e}")

        # Дополняем пустые строки/колонки
        min_rows, min_cols = 100, 26
        while len(all_values) < min_rows:
            all_values.append([''] * max(len(all_values[0]) if all_values else min_cols, min_cols))
        for row in all_values:
            while len(row) < min_cols:
                row.append('')
        
        return {
            "data": all_values,
            "formulas": formulas,
            "validations": validations, # Отправляем списки на фронт
            "sheet_name": worksheet.title
        }
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/batch-update")
def batch_update(
    batch: BatchUpdate,
    sheet_name: Optional[str] = None,
    request: Request = None,
    user: User = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Массовое обновление ячеек с проверкой блокировок"""
    if user.username not in active_sheets:
        raise HTTPException(status_code=400, detail="Таблица не выбрана")
    
    if not batch.updates:
        return {"status": "ignored"}
    
    try:
        spreadsheet = active_sheets[user.username]
        spreadsheet_id = spreadsheet.id
        
        if sheet_name:
            worksheet = spreadsheet.worksheet(sheet_name)
        elif hasattr(spreadsheet, '_active_worksheet') and user.username in spreadsheet._active_worksheet:
            worksheet = spreadsheet._active_worksheet[user.username]
        else:
            worksheet = spreadsheet.sheet1
        
        # Проверяем блокировки (только для не-админов)
        if not user.is_admin:
            blocked_cells = []
            for item in batch.updates:
                lock = is_cell_locked(db, spreadsheet_id, worksheet.title, item.row, item.col)
                if lock:
                    blocked_cells.append((item.row, item.col, lock.range_notation))
            
            if blocked_cells:
                logger.warning(
                    f"🔒 {user.username} попытался изменить заблокированные ячейки: {blocked_cells}"
                )
                raise HTTPException(
                    status_code=403,
                    detail=f"Ячейки заблокированы администратором: {blocked_cells[0][2]}"
                )
        
        cells_to_update = []
        for item in batch.updates:
            row = item.row + 1
            col = item.col + 1
            cells_to_update.append(Cell(row, col, item.newValue))
        
        # Retry логика
        max_retries = 5
        for i in range(max_retries):
            try:
                worksheet.update_cells(cells_to_update, value_input_option='USER_ENTERED')
                
                logger.info(
                    f"✏️ {user.username} обновил {len(cells_to_update)} ячеек в {worksheet.title}"
                )
                
                log_action(
                    db, user, "batch_update",
                    spreadsheet_id=spreadsheet_id,
                    sheet_name=worksheet.title,
                    details={"cell_count": len(cells_to_update)},
                    ip_address=get_client_ip(request)
                )
                
                return {"status": "success", "updated_count": len(cells_to_update)}
            
            except APIError as e:
                if e.response.status_code == 429:
                    if i == max_retries - 1:
                        raise HTTPException(
                            status_code=429,
                            detail="Слишком много запросов к Google, попробуйте позже"
                        )
                    
                    sleep_time = (2 ** i)
                    logger.warning(f"⚠️ Quota exceeded. Waiting {sleep_time}s...")
                    time.sleep(sleep_time)
                else:
                    raise e
                    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка записи: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка записи: {str(e)}")


@app.get("/api/sheets")
def get_sheets_list(
    user: User = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Получение актуального списка листов"""
    if user.username not in active_sheets:
        raise HTTPException(status_code=400, detail="Таблица не выбрана")
    
    try:
        spreadsheet = active_sheets[user.username]
        # Запрашиваем свежий список листов у Google
        sheet_names = [ws.title for ws in spreadsheet.worksheets()]
        return {"sheets": sheet_names}
    except Exception as e:
        logger.error(f"❌ Ошибка получения списка листов: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# === АДМИН ENDPOINTS ===

@app.post("/api/admin/lock-range")
def lock_range(
    request_data: LockRangeRequest,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Блокировка диапазона ячеек (только для админа)"""
    # Проверяем, не заблокирован ли уже этот диапазон
    existing = db.query(LockedRange).filter(
        LockedRange.spreadsheet_id == request_data.spreadsheet_id,
        LockedRange.sheet_name == request_data.sheet_name,
        LockedRange.range_notation == request_data.range_notation
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Диапазон уже заблокирован")
    
    lock = LockedRange(
        spreadsheet_id=request_data.spreadsheet_id,
        sheet_name=request_data.sheet_name,
        range_notation=request_data.range_notation,
        locked_by=admin.id,
        reason=request_data.reason
    )
    db.add(lock)
    db.commit()
    
    logger.info(
        f"🔒 {admin.username} заблокировал диапазон {request_data.sheet_name}!{request_data.range_notation}"
    )
    
    log_action(
        db, admin, "lock_range",
        spreadsheet_id=request_data.spreadsheet_id,
        sheet_name=request_data.sheet_name,
        details={"range": request_data.range_notation, "reason": request_data.reason},
        ip_address=get_client_ip(request)
    )
    
    return {"status": "success", "lock_id": lock.id}


@app.get("/api/admin/locked-ranges")
def get_locked_ranges(
    spreadsheet_id: str,
    sheet_name: Optional[str] = None,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Получение списка заблокированных диапазонов"""
    query = db.query(LockedRange).filter(
        LockedRange.spreadsheet_id == spreadsheet_id
    )
    
    if sheet_name:
        query = query.filter(LockedRange.sheet_name == sheet_name)
    
    locks = query.all()
    
    return {
        "locks": [
            {
                "id": lock.id,
                "sheet_name": lock.sheet_name,
                "range": lock.range_notation,
                "reason": lock.reason,
                "locked_by": lock.user.username,
                "created_at": lock.created_at.isoformat()
            }
            for lock in locks
        ]
    }


@app.delete("/api/admin/unlock-range/{lock_id}")
def unlock_range(
    lock_id: int,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Разблокировка диапазона"""
    lock = db.query(LockedRange).filter(LockedRange.id == lock_id).first()
    
    if not lock:
        raise HTTPException(status_code=404, detail="Блокировка не найдена")
    
    logger.info(
        f"🔓 {admin.username} разблокировал диапазон {lock.sheet_name}!{lock.range_notation}"
    )
    
    log_action(
        db, admin, "unlock_range",
        spreadsheet_id=lock.spreadsheet_id,
        sheet_name=lock.sheet_name,
        details={"range": lock.range_notation},
        ip_address=get_client_ip(request)
    )
    
    db.delete(lock)
    db.commit()
    
    return {"status": "success"}

# === СТИЛИЗАЦИЯ (НОВЫЙ БЛОК) ===
@app.post("/api/styles/save")
def save_styles(
    request_data: BatchStyleRequest,
    request: Request, # Добавь request сюда для логов
    user: User = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Сохранение стилей с проверкой блокировок"""
    
    # Проверяем блокировки (только для не-админов)
    if not user.is_admin:
        for item in request_data.styles:
            lock = is_cell_locked(db, request_data.spreadsheet_id, request_data.sheet_name, item.row, item.col)
            if lock:
                logger.warning(f"🔒 {user.username} пытался покрасить заблокированную ячейку")
                raise HTTPException(
                    status_code=403, 
                    detail=f"Нельзя форматировать заблокированные ячейки ({lock.range_notation})"
                )

    count = 0
    for item in request_data.styles:
        existing_style = db.query(CellStyle).filter(
            CellStyle.spreadsheet_id == request_data.spreadsheet_id,
            CellStyle.sheet_name == request_data.sheet_name,
            CellStyle.row == item.row,
            CellStyle.col == item.col
        ).first()
        
        if existing_style:
            existing_style.style_json = item.style
        else:
            new_style = CellStyle(
                spreadsheet_id=request_data.spreadsheet_id,
                sheet_name=request_data.sheet_name,
                row=item.row,
                col=item.col,
                style_json=item.style
            )
            db.add(new_style)
        count += 1
    
    db.commit()
    return {"status": "success", "updated": count}


@app.get("/api/styles")
def get_styles(
    spreadsheet_id: str,
    sheet_name: str,
    user: User = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Загрузка всех стилей для конкретного листа"""
    styles = db.query(CellStyle).filter(
        CellStyle.spreadsheet_id == spreadsheet_id,
        CellStyle.sheet_name == sheet_name
    ).all()
    
    # Преобразуем в список для фронтенда
    result = []
    for s in styles:
        result.append({
            "row": s.row,
            "col": s.col,
            "style": s.style_json
        })
        
    return {"styles": result}

if __name__ == "__main__":
    logger.info(f"🚀 Запуск сервера на {HOST}:{PORT}")
    uvicorn.run(app, host=HOST, port=PORT)