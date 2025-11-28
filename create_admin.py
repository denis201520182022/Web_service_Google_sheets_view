"""
Скрипт для создания первого администратора
"""
from sqlalchemy.orm import Session
from backend.database import SessionLocal, engine
from backend.models import Base, User
from passlib.context import CryptContext
import sys

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_admin(username: str = "admin", password: str = "admin123"):
    """Создает администратора в БД"""
    
    # Создаем таблицы если их нет
    Base.metadata.create_all(bind=engine)
    print("✅ Таблицы БД созданы/проверены")
    
    db = SessionLocal()
    
    try:
        # Проверяем, есть ли уже этот пользователь
        existing_user = db.query(User).filter(User.username == username).first()
        if existing_user:
            print(f"❌ Пользователь '{username}' уже существует!")
            
            # Предлагаем обновить пароль
            update = input("Обновить пароль? (y/n): ")
            if update.lower() == 'y':
                new_password = input("Новый пароль: ")
                existing_user.hashed_password = pwd_context.hash(new_password)
                db.commit()
                print(f"✅ Пароль для '{username}' обновлен!")
            return
        
        # Создаем нового админа
        hashed_password = pwd_context.hash(password)
        admin = User(
            username=username,
            hashed_password=hashed_password,
            is_admin=True,
            is_active=True
        )
        db.add(admin)
        db.commit()
        
        print(f"✅ Администратор создан успешно!")
        print(f"   Логин: {username}")
        print(f"   Пароль: {password}")
        print(f"\n⚠️  ВАЖНО: Смените пароль после первого входа!")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        db.rollback()
    finally:
        db.close()


def create_test_user(username: str, password: str):
    """Создает обычного пользователя"""
    
    db = SessionLocal()
    
    try:
        existing_user = db.query(User).filter(User.username == username).first()
        if existing_user:
            print(f"❌ Пользователь '{username}' уже существует!")
            return
        
        hashed_password = pwd_context.hash(password)
        user = User(
            username=username,
            hashed_password=hashed_password,
            is_admin=False,
            is_active=True
        )
        db.add(user)
        db.commit()
        
        print(f"✅ Пользователь '{username}' создан!")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        db.rollback()
    finally:
        db.close()


def list_users():
    """Выводит список всех пользователей"""
    db = SessionLocal()
    
    try:
        users = db.query(User).all()
        
        if not users:
            print("📭 Пользователей нет в БД")
            return
        
        print("\n👥 Список пользователей:")
        print("-" * 70)
        print(f"{'ID':<5} {'Username':<20} {'Admin':<10} {'Active':<10} {'Created'}")
        print("-" * 70)
        
        for user in users:
            admin_mark = "✓" if user.is_admin else ""
            active_mark = "✓" if user.is_active else "✗"
            created = user.created_at.strftime("%Y-%m-%d") if user.created_at else "N/A"
            
            print(f"{user.id:<5} {user.username:<20} {admin_mark:<10} {active_mark:<10} {created}")
        
        print("-" * 70)
        
    finally:
        db.close()


def main():
    print("=" * 70)
    print("ZABOTA TABLES - Управление пользователями")
    print("=" * 70)
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "create-admin":
            username = sys.argv[2] if len(sys.argv) > 2 else "admin"
            password = sys.argv[3] if len(sys.argv) > 3 else "admin123"
            create_admin(username, password)
        
        elif command == "create-user":
            if len(sys.argv) < 4:
                print("❌ Использование: python create_admin.py create-user <username> <password>")
                return
            username = sys.argv[2]
            password = sys.argv[3]
            create_test_user(username, password)
        
        elif command == "list":
            list_users()
        
        else:
            print(f"❌ Неизвестная команда: {command}")
            print_help()
    else:
        print_help()
        print("\n🚀 Создать админа по умолчанию? (admin/admin123)")
        choice = input("Продолжить? (y/n): ")
        if choice.lower() == 'y':
            create_admin()


def print_help():
    print("\nДоступные команды:")
    print("  python create_admin.py create-admin [username] [password]")
    print("  python create_admin.py create-user <username> <password>")
    print("  python create_admin.py list")
    print("\nПримеры:")
    print("  python create_admin.py create-admin")
    print("  python create_admin.py create-admin superadmin MySecurePass123")
    print("  python create_admin.py create-user john pass123")
    print("  python create_admin.py list")


if __name__ == "__main__":
    main()