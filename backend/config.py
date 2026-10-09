import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))  # 8 часов
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_filename = os.getenv("SERVICE_ACCOUNT_FILE")
SERVICE_ACCOUNT_FILE = os.path.join(BASE_DIR, _filename)
HOST = os.getenv("HOST")
PORT = int(os.getenv("PORT"))
DATABASE_URL = os.getenv("DATABASE_URL")

ALLOWED_ORIGINS_STR = os.getenv("ALLOWED_ORIGINS", "*")
if ALLOWED_ORIGINS_STR == "*":
    ALLOWED_ORIGINS = ["*"]
else:
    ALLOWED_ORIGINS = ALLOWED_ORIGINS_STR.split(",")


LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


def generate_secret_key():
    """Генерирует безопасный SECRET_KEY для production"""
    import secrets
    return secrets.token_urlsafe(32)


def validate_config():
    """Проверка критичных настроек"""
    warnings = []
    
    if SECRET_KEY == "CHANGE_THIS_IN_PRODUCTION":
        warnings.append("⚠️  SECRET_KEY использует значение по умолчанию!")
    
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        warnings.append(f"⚠️  Файл {SERVICE_ACCOUNT_FILE} не найден!")
    
    if "localhost" in DATABASE_URL and os.getenv("ENVIRONMENT") == "production":
        warnings.append("⚠️  В production используется localhost БД!")
    
    if warnings:
        print("\n" + "=" * 70)
        print("ПРЕДУПРЕЖДЕНИЯ КОНФИГУРАЦИИ:")
        for warning in warnings:
            print(warning)
        print("=" * 70 + "\n")
    
    return len(warnings) == 0


if __name__ == "__main__":
    print("🔧 Текущая конфигурация:")
    print(f"   HOST: {HOST}")
    print(f"   PORT: {PORT}")
    print(f"   DATABASE: {DATABASE_URL}")
    print(f"   JWT EXPIRE: {ACCESS_TOKEN_EXPIRE_MINUTES} минут")
    print(f"   LOG LEVEL: {LOG_LEVEL}")
    print()
    
    validate_config()
    
    print("\n🔑 Сгенерировать новый SECRET_KEY?")
    print("Новый ключ:")
    print(generate_secret_key())
    print("\n⚠️  Добавьте его в .env файл как SECRET_KEY=...")