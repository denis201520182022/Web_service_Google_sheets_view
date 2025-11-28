"""
Модуль авторизации с JWT и поддержкой БД
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import User, AuditLog
from backend.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
import logging

logger = logging.getLogger(__name__)
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверка пароля"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Хеширование пароля"""
    return pwd_context.hash(password)


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """
    Проверка логина/пароля через БД
    
    Args:
        db: Сессия БД
        username: Имя пользователя
        password: Пароль
    
    Returns:
        User объект если авторизация успешна, иначе None
    """
    user = db.query(User).filter(User.username == username).first()
    
    if not user:
        logger.warning(f"❌ Попытка входа с несуществующим пользователем: {username}")
        return None
    
    if not user.is_active:
        logger.warning(f"❌ Попытка входа заблокированного пользователя: {username}")
        return None
    
    if not verify_password(password, user.hashed_password):
        logger.warning(f"❌ Неверный пароль для пользователя: {username}")
        return None
    
    logger.info(f"✅ Успешный вход пользователя: {username} (admin={user.is_admin})")
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Создание JWT токена
    
    Args:
        data: Данные для кодирования в токен
        expires_delta: Время жизни токена (опционально)
    
    Returns:
        JWT токен в виде строки
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Проверка JWT токена и получение пользователя
    
    Args:
        credentials: HTTP авторизационные данные с токеном
        db: Сессия БД
    
    Returns:
        User объект
    
    Raises:
        HTTPException: Если токен невалидный или истек
    """
    token = credentials.credentials
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Невалидный токен или сессия истекла",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        
        if username is None:
            logger.error("❌ Токен без username")
            raise credentials_exception
        
        user = db.query(User).filter(User.username == username).first()
        if user is None:
            logger.error(f"❌ Пользователь из токена не найден: {username}")
            raise credentials_exception
        
        if not user.is_active:
            logger.error(f"❌ Заблокированный пользователь пытается использовать токен: {username}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Пользователь заблокирован"
            )
        
        return user
        
    except JWTError as e:
        logger.error(f"❌ Ошибка JWT: {e}")
        raise credentials_exception


def require_admin(user: User = Depends(verify_token)) -> User:
    """
    Проверка прав администратора
    
    Args:
        user: Текущий пользователь
    
    Returns:
        User объект если он админ
    
    Raises:
        HTTPException: Если пользователь не админ
    """
    if not user.is_admin:
        logger.warning(f"⚠️ Попытка доступа к админ-функции от {user.username}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуются права администратора"
        )
    return user


def log_action(
    db: Session,
    user: Optional[User],
    action: str,
    spreadsheet_id: Optional[str] = None,
    sheet_name: Optional[str] = None,
    details: Optional[dict] = None,
    ip_address: Optional[str] = None
):
    """
    Логирование действия пользователя
    
    Args:
        db: Сессия БД
        user: Пользователь
        action: Тип действия
        spreadsheet_id: ID таблицы (опционально)
        sheet_name: Название листа (опционально)
        details: Дополнительные данные (опционально)
        ip_address: IP адрес (опционально)
    """
    try:
        log = AuditLog(
            user_id=user.id if user else None,
            username=user.username if user else "anonymous",
            action=action,
            spreadsheet_id=spreadsheet_id,
            sheet_name=sheet_name,
            details=details,
            ip_address=ip_address
        )
        db.add(log)
        db.commit()
        
        emoji = "🔒" if action.startswith("lock") else "📝" if action.startswith("update") else "📊"
        user_name = user.username if user else "anonymous"
        logger.info(f"{emoji} {user_name}: {action} | sheet={sheet_name} | details={details}")
    except Exception as e:
        logger.error(f"❌ Ошибка записи audit лога: {e}")
        db.rollback()