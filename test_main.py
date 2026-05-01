import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from database import Base, get_db

# Настройка тестовой БД (SQLite в памяти)
SQLALCHEMY_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def auth_token():
    """Фикстура для получения токена авторизации."""
    client.post(
        "/auth/register", json={"username": "testuser", "password": "testpassword", "role": "admin"}
    )
    response = client.post("/auth/token", data={"username": "testuser", "password": "testpassword"})
    return response.json()["access_token"]


# --- Тесты ---


def test_register_user():
    response = client.post(
        "/auth/register", json={"username": "newuser", "password": "password123", "role": "manager"}
    )
    assert response.status_code == 201
    assert response.json()["username"] == "newuser"


def test_login_get_token():
    # Исправлен путь
    response = client.post("/auth/token", data={"username": "newuser", "password": "password123"})
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_create_category_and_product(auth_token: str):
    headers = {"Authorization": f"Bearer {auth_token}"}

    # 1. Создаем категорию
    cat_resp = client.post(
        "/categories", json={"name": "Electronics", "risk_factor": 0.5}, headers=headers
    )
    assert cat_resp.status_code == 201
    category_id = cat_resp.json()["id"]

    # 2. Создаем продукт
    prod_resp = client.post(
        "/products",
        json={
            "name": "Laptop",
            "quantity": 5,
            "min_stock": 10,
            "price": 1000.0,
            "category_id": category_id,
        },
        headers=headers,
    )
    assert prod_resp.status_code == 201
    assert prod_resp.json()["name"] == "Laptop"


def test_delete_product_access_control(auth_token: str):
    headers = {"Authorization": f"Bearer {auth_token}"}
    cat_resp = client.post(
        "/categories", json={"name": "Tools", "risk_factor": 1.0}, headers=headers
    )
    prod_resp = client.post(
        "/products",
        json={
            "name": "Hammer",
            "quantity": 10,
            "min_stock": 5,
            "price": 20.0,
            "category_id": cat_resp.json()["id"],
        },
        headers=headers,
    )
    product_id = prod_resp.json()["id"]

    # Пытаемся удалить без токена
    no_auth_resp = client.delete(f"/products/{product_id}")
    assert no_auth_resp.status_code == 401

    # Удаляем с токеном. Ожидаем 204
    auth_resp = client.delete(f"/products/{product_id}", headers=headers)
    assert auth_resp.status_code == 204


def test_inventory_optimize(auth_token: str):
    headers = {"Authorization": f"Bearer {auth_token}"}

    cat_resp = client.post(
        "/categories", json={"name": "Critical", "risk_factor": 0.9}, headers=headers
    )
    client.post(
        "/products",
        json={
            "name": "Urgent Part",
            "quantity": 2,
            "min_stock": 10,
            "price": 50.0,
            "category_id": cat_resp.json()["id"],
        },
        headers=headers,
    )

    response = client.post("/inventory/optimize?budget=500", headers=headers)

    assert response.status_code == 200
    recommendations = response.json()
    assert isinstance(recommendations, list)
    if len(recommendations) > 0:
        assert "product_id" in recommendations[0]
        assert "restock_quantity" in recommendations[0]
