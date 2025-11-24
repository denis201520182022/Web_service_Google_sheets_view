"""
Модуль авторизации с JWT
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from config import USERS, SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

security = HTTPBearer()


def authenticate_user(username: str, password: str) -> bool:
    """
    Проверка логина/пароля
    
    Args:
        username: Имя пользователя
        password: Пароль
    
    Returns:
        True если авторизация успешна, иначе False
    """
    if username in USERS and USERS[username] == password:
        return True
    return False


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


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    Проверка JWT токена
    
    Args:
        credentials: HTTP авторизационные данные с токеном
    
    Returns:
        Username из токена
    
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
            raise credentials_exception
            
        return username
        
    except JWTError:
        raise credentials_exception


def get_current_user(username: str = Depends(verify_token)) -> str:
    """
    Получение текущего пользователя (алиас для verify_token)
    
    Args:
        username: Username из токена
    
    Returns:
        Username текущего пользователя
    """
    return username