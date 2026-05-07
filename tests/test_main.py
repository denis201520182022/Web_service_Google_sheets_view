import pytest
from unittest.mock import patch, MagicMock
from backend.models import User, LockedRange, AuditLog

def test_login_success(client):
    """Тест успешного входа"""
    response = client.post(
        "/api/login",
        json={"username": "testuser", "password": "userpass"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["username"] == "testuser"
    assert data["is_admin"] is False

def test_login_invalid_password(client):
    """Тест входа с неверным паролем"""
    response = client.post(
        "/api/login",
        json={"username": "testuser", "password": "wrongpassword"}
    )
    assert response.status_code == 401

def test_protected_route_without_token(client):
    """Тест доступа к защищенному маршруту без токена"""
    response = client.get("/api/my-sheets")
    assert response.status_code == 401 # FastAPI security returns 401 if missing

def test_user_management_by_admin(client):
    """Тест управления пользователями (только для админа)"""
    # Логинимся как админ
    login_res = client.post(
        "/api/login",
        json={"username": "testadmin", "password": "adminpass"}
    )
    admin_token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Получаем список пользователей
    response = client.get("/api/admin/users", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) >= 2

    # 2. Создаем нового пользователя
    new_user_data = {
        "username": "newuser",
        "password": "newpassword",
        "first_name": "Ivan",
        "last_name": "Ivanov",
        "is_admin": False
    }
    response = client.post("/api/admin/users", json=new_user_data, headers=headers)
    assert response.status_code == 200
    user_id = response.json()["user_id"]

    # 3. Редактируем пользователя
    update_data = {"first_name": "Petr"}
    response = client.put(f"/api/admin/users/{user_id}", json=update_data, headers=headers)
    assert response.status_code == 200

    # 4. Удаляем пользователя
    response = client.delete(f"/api/admin/users/{user_id}", headers=headers)
    assert response.status_code == 200

def test_user_management_by_regular_user_denied(client):
    """Тест: обычному пользователю запрещено управлять другими пользователями"""
    # Логинимся как обычный юзер
    login_res = client.post(
        "/api/login",
        json={"username": "testuser", "password": "userpass"}
    )
    user_token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {user_token}"}

    response = client.get("/api/admin/users", headers=headers)
    assert response.status_code == 403 # Forbidden

def test_lock_and_unlock_range(client):
    """Тест блокировки и разблокировки диапазона ячеек"""
    # Логинимся как админ
    login_res = client.post(
        "/api/login",
        json={"username": "testadmin", "password": "adminpass"}
    )
    admin_token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Блокируем диапазон
    lock_data = {
        "spreadsheet_id": "test_id",
        "sheet_name": "Sheet1",
        "range_notation": "A1:B10",
        "reason": "Protect headers"
    }
    response = client.post("/api/admin/lock-range", json=lock_data, headers=headers)
    assert response.status_code == 200
    lock_id = response.json()["lock_id"]

    # Проверяем список блокировок
    response = client.get("/api/admin/locked-ranges?spreadsheet_id=test_id", headers=headers)
    assert response.status_code == 200
    assert len(response.json()["locks"]) > 0

    # Разблокируем
    response = client.delete(f"/api/admin/unlock-range/{lock_id}", headers=headers)
    assert response.status_code == 200

@patch("backend.main.get_gc")
def test_batch_update_with_lock_check(mock_get_gc, client, db):
    """Тест проверки блокировок при массовом обновлении"""
    # 1. Устанавливаем блокировку вручную в БД
    lock = LockedRange(
        spreadsheet_id="test_id",
        sheet_name="Sheet1",
        range_notation="A1:A1",
        locked_by=1 # testadmin id (usually 1 in clean test db)
    )
    db.add(lock)
    db.commit()

    # 2. Логинимся как обычный юзер
    login_res = client.post(
        "/api/login",
        json={"username": "testuser", "password": "userpass"}
    )
    user_token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {user_token}"}

    # 3. Мокаем активную таблицу
    mock_spreadsheet = MagicMock()
    mock_spreadsheet.id = "test_id"
    mock_spreadsheet.sheet1.title = "Sheet1"
    
    # Чтобы active_sheets работал, нам нужно либо вызвать set_sheet, либо внедрить в словарь
    from backend.main import active_sheets
    active_sheets["testuser"] = mock_spreadsheet

    # 4. Пытаемся обновить заблокированную ячейку (A1 -> row 0, col 0)
    update_data = {
        "updates": [{"row": 0, "col": 0, "newValue": "Hack"}]
    }
    response = client.post("/api/batch-update?sheet_name=Sheet1", json=update_data, headers=headers)
    
    assert response.status_code == 403
    assert "заблокированы администратором" in response.json()["detail"]

def test_audit_log_generation(client, db):
    """Тест генерации записей в журнале аудита"""
    # Выполняем вход
    client.post(
        "/api/login",
        json={"username": "testuser", "password": "userpass"}
    )
    
    # Проверяем наличие записи в БД
    log = db.query(AuditLog).filter(AuditLog.action == "login").first()
    assert log is not None
    assert log.username == "testuser"
