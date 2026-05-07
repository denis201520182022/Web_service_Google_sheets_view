import pytest
from sqlalchemy import create_all, create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from backend.database import Base, get_db
from backend.main import app
from backend.models import User
from backend.auth import get_password_hash

# Используем SQLite в памяти для тестов
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session")
def db_engine():
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def db(db_engine):
    connection = db_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    # Создаем админа для тестов
    admin = User(
        username="testadmin",
        hashed_password=get_password_hash("adminpass"),
        is_admin=True,
        is_active=True
    )
    # Создаем обычного юзера
    user = User(
        username="testuser",
        hashed_password=get_password_hash("userpass"),
        is_admin=False,
        is_active=True
    )
    session.add(admin)
    session.add(user)
    session.commit()

    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(scope="function")
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
