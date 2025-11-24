"""
FastAPI Backend для работы с Google Sheets
С защитой от превышения квот (Retry with Exponential Backoff)
"""
import uvicorn
import gspread
import re
import time  # Добавлено для задержки
from gspread import Cell
from gspread.exceptions import APIError # Импорт для обработки ошибок
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import timedelta

from config import (
    SERVICE_ACCOUNT_FILE, 
    HOST, 
    PORT, 
    ACCESS_TOKEN_EXPIRE_MINUTES,
    ALLOWED_ORIGINS
)
from auth import authenticate_user, create_access_token, verify_token

# === ИНИЦИАЛИЗАЦИЯ ===
app = FastAPI(title="Google Sheets Proxy API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    allow_credentials=True,
    expose_headers=["*"],
)

try:
    gc = gspread.service_account(filename=SERVICE_ACCOUNT_FILE)
    print("✅ Google Sheets API подключен")
except Exception as e:
    print(f"❌ Ошибка подключения к Google: {e}")
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

# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===
def extract_spreadsheet_id(url: str) -> Optional[str]:
    pattern = r'/spreadsheets/d/([a-zA-Z0-9-_]+)'
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    return None

# === API ENDPOINTS ===

@app.get("/")
def root():
    return {"service": "Google Sheets Proxy", "status": "active", "version": "2.1"}

@app.post("/api/login")
def login(credentials: LoginRequest):
    if not authenticate_user(credentials.username, credentials.password):
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    
    access_token = create_access_token(
        data={"sub": credentials.username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer", "username": credentials.username}

@app.post("/api/set-sheet")
def set_sheet(request: SheetURLRequest, username: str = Depends(verify_token)):
    if not gc:
        raise HTTPException(status_code=500, detail="Google API не подключен")
    
    spreadsheet_id = extract_spreadsheet_id(request.url)
    if not spreadsheet_id:
        raise HTTPException(status_code=400, detail="Невалидная ссылка")
    
    try:
        spreadsheet = gc.open_by_key(spreadsheet_id)
        active_sheets[username] = spreadsheet
        sheet_names = [ws.title for ws in spreadsheet.worksheets()]
        return {"status": "success", "title": spreadsheet.title, "sheets": sheet_names}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка доступа: {str(e)}")

@app.get("/api/sheets")
def get_sheets(username: str = Depends(verify_token)):
    if username not in active_sheets:
        raise HTTPException(status_code=400, detail="Таблица не выбрана")
    try:
        spreadsheet = active_sheets[username]
        sheets = [{"title": ws.title, "index": ws.index} for ws in spreadsheet.worksheets()]
        return {"sheets": sheets}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/select-sheet")
def select_sheet(request: SheetSelection, username: str = Depends(verify_token)):
    if username not in active_sheets:
        raise HTTPException(status_code=400, detail="Таблица не выбрана")
    try:
        spreadsheet = active_sheets[username]
        worksheet = spreadsheet.worksheet(request.sheet_name)
        if not hasattr(active_sheets[username], '_active_worksheet'):
            active_sheets[username]._active_worksheet = {}
        active_sheets[username]._active_worksheet[username] = worksheet
        return {"status": "success", "sheet": request.sheet_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/data")
def get_data(sheet_name: Optional[str] = None, username: str = Depends(verify_token)):
    if username not in active_sheets:
        raise HTTPException(status_code=400, detail="Таблица не выбрана")
    
    try:
        spreadsheet = active_sheets[username]
        if sheet_name:
            worksheet = spreadsheet.worksheet(sheet_name)
        elif hasattr(spreadsheet, '_active_worksheet') and username in spreadsheet._active_worksheet:
            worksheet = spreadsheet._active_worksheet[username]
        else:
            worksheet = spreadsheet.sheet1
        
        data = worksheet.get_all_values()
        
        min_rows, min_cols = 100, 26
        if len(data) < min_rows:
            data.extend([[''] * max(len(data[0]) if data else min_cols, min_cols) 
                        for _ in range(min_rows - len(data))])
        for row in data:
            if len(row) < min_cols:
                row.extend([''] * (min_cols - len(row)))
        
        return {"data": data, "sheet_name": worksheet.title}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка чтения: {str(e)}")

@app.post("/api/batch-update")
def batch_update(batch: BatchUpdate, sheet_name: Optional[str] = None, 
                username: str = Depends(verify_token)):
    """
    Массовое обновление с повторными попытками (Exponential Backoff)
    """
    if username not in active_sheets:
        raise HTTPException(status_code=400, detail="Таблица не выбрана")
    
    if not batch.updates:
        return {"status": "ignored"}
    
    try:
        spreadsheet = active_sheets[username]
        if sheet_name:
            worksheet = spreadsheet.worksheet(sheet_name)
        elif hasattr(spreadsheet, '_active_worksheet') and username in spreadsheet._active_worksheet:
            worksheet = spreadsheet._active_worksheet[username]
        else:
            worksheet = spreadsheet.sheet1
        
        cells_to_update = []
        for item in batch.updates:
            row = item.row + 1
            col = item.col + 1
            cells_to_update.append(Cell(row, col, item.newValue))
        
        # === АЛГОРИТМ ПОВТОРНЫХ ПОПЫТОК ===
        max_retries = 5  # Максимум попыток
        for i in range(max_retries):
            try:
                # Попытка записи
                worksheet.update_cells(cells_to_update, value_input_option='USER_ENTERED')
                
                # Если успешно - выходим из функции
                return {"status": "success", "updated_count": len(cells_to_update)}
            
            except APIError as e:
                # Проверяем код ошибки. 429 = Too Many Requests
                if e.response.status_code == 429:
                    if i == max_retries - 1:
                        # Если это была последняя попытка - пробрасываем ошибку
                        raise HTTPException(status_code=429, detail="Слишком много запросов к Google, попробуйте позже")
                    
                    # Экспоненциальная задержка: 1s, 2s, 4s, 8s...
                    sleep_time = (2 ** i)
                    print(f"⚠️ Превышен лимит квот. Ожидание {sleep_time} сек...")
                    time.sleep(sleep_time)
                else:
                    # Если ошибка другая (например, нет прав), падаем сразу
                    raise e
                    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка записи: {str(e)}")

@app.post("/api/add-row")
def add_row(username: str = Depends(verify_token)):
    # Здесь тоже можно добавить retry логику, если нужно
    if username not in active_sheets:
        raise HTTPException(status_code=400, detail="Таблица не выбрана")
    try:
        spreadsheet = active_sheets[username]
        worksheet = spreadsheet._active_worksheet.get(username, spreadsheet.sheet1)
        worksheet.append_row([''] * worksheet.col_count)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/add-column")
def add_column(username: str = Depends(verify_token)):
    if username not in active_sheets:
        raise HTTPException(status_code=400, detail="Таблица не выбрана")
    try:
        spreadsheet = active_sheets[username]
        worksheet = spreadsheet._active_worksheet.get(username, spreadsheet.sheet1)
        worksheet.add_cols(1)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT)