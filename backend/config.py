import os
from typing import Dict
from dotenv import load_dotenv

load_dotenv()

USERS: Dict[str, str] = {
    "admin": os.getenv("ADMIN_PASSWORD"),
    "user1": os.getenv("USER1_PASSWORD"),
}
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))
SERVICE_ACCOUNT_FILE = os.getenv("SERVICE_ACCOUNT_FILE")
HOST = os.getenv("HOST")
PORT = int(os.getenv("PORT"))

ALLOWED_ORIGINS_STR = os.getenv("ALLOWED_ORIGINS", "*")
if ALLOWED_ORIGINS_STR == "*":
    ALLOWED_ORIGINS = ["*"]
else:
    ALLOWED_ORIGINS = ALLOWED_ORIGINS_STR.split(",")

def generate_secret_key():
    """Генерирует безопасный SECRET_KEY для production"""
    import secrets
    return secrets.token_urlsafe(32)

if __name__ == "__main__":
    print("🔑 Сгенерированный SECRET_KEY для production:")
    print(generate_secret_key())
    print("\n⚠️  Добавь его в .env файл!")