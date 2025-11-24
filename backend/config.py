"""
Конфигурация приложения с поддержкой .env файлов
"""
import os
from typing import Dict
from dotenv import load_dotenv

# Загружаем переменные из .env файла (если есть)
load_dotenv()

# === БЕЗОПАСНОСТЬ ===
# В production обязательно используй .env или БД для хранения паролей!
USERS: Dict[str, str] = {
    "admin": os.getenv("ADMIN_PASSWORD"),
    "user1": os.getenv("USER1_PASSWORD"),
}

# JWT Secret (ОБЯЗАТЕЛЬНО измени в production!)
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))

# === GOOGLE SHEETS ===
SERVICE_ACCOUNT_FILE = os.getenv("SERVICE_ACCOUNT_FILE")

# === СЕРВЕР ===
HOST = os.getenv("HOST")
PORT = int(os.getenv("PORT"))

# === CORS ===
# В development разрешаем все источники
# В production укажи конкретные домены!
ALLOWED_ORIGINS_STR = os.getenv("ALLOWED_ORIGINS", "*")
if ALLOWED_ORIGINS_STR == "*":
    ALLOWED_ORIGINS = ["*"]
else:
    ALLOWED_ORIGINS = ALLOWED_ORIGINS_STR.split(",")

# Функция для генерации безопасного ключа
def generate_secret_key():
    """Генерирует безопасный SECRET_KEY для production"""
    import secrets
    return secrets.token_urlsafe(32)

if __name__ == "__main__":
    print("🔑 Сгенерированный SECRET_KEY для production:")
    print(generate_secret_key())
    print("\n⚠️  Добавь его в .env файл!")