import pytest
from fastapi.testclient import TestClient

from app.database import Base, get_db, get_inmemory_db, inmemory_engine
from app.main import app


app.dependency_overrides[get_db] = get_inmemory_db
client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=inmemory_engine)
    yield
    Base.metadata.drop_all(bind=inmemory_engine)


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


def test_update_category(auth_token: str):
    headers = {"Authorization": f"Bearer {auth_token}"}

    # Сначала создаем
    create_resp = client.post(
        "/categories", json={"name": "Old Name", "risk_factor": 0.1}, headers=headers
    )
    category_id = create_resp.json()["id"]

    # Обновляем
    update_data = {"name": "New Name", "risk_factor": 0.8}
    response = client.put(f"/categories/{category_id}", json=update_data, headers=headers)

    assert response.status_code == 200
    assert response.json()["name"] == "New Name"
    assert response.json()["risk_factor"] == 0.8

    # Тест на 404
    response_404 = client.put("/categories/9999", json=update_data, headers=headers)
    assert response_404.status_code == 404


def test_delete_category(auth_token: str):
    headers = {"Authorization": f"Bearer {auth_token}"}

    cat_resp = client.post(
        "/categories", json={"name": "To Be Deleted", "risk_factor": 0.5}, headers=headers
    )
    category_id = cat_resp.json()["id"]

    # Удаляем
    delete_resp = client.delete(f"/categories/{category_id}", headers=headers)
    assert delete_resp.status_code == 204

    # Проверяем, что удалено (404 при повторном удалении или получении, если бы был эндпоинт get)
    delete_again = client.delete(f"/categories/{category_id}", headers=headers)
    assert delete_again.status_code == 404


def test_get_product(auth_token: str):
    headers = {"Authorization": f"Bearer {auth_token}"}

    # Подготовка данных (категория + продукт)
    cat_resp = client.post(
        "/categories", json={"name": "FetchTest", "risk_factor": 0.5}, headers=headers
    )
    cat_id = cat_resp.json()["id"]

    prod_payload = {
        "name": "Specific Product",
        "quantity": 10,
        "min_stock": 5,
        "price": 100.0,
        "category_id": cat_id,
    }
    create_prod = client.post("/products", json=prod_payload, headers=headers)
    product_id = create_prod.json()["id"]

    # Тест получения
    response = client.get(f"/products/{product_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Specific Product"

    # Тест на 404
    response_404 = client.get("/products/99999")
    assert response_404.status_code == 404


def test_update_product(auth_token: str):
    headers = {"Authorization": f"Bearer {auth_token}"}

    # Подготовка
    cat_resp = client.post(
        "/categories", json={"name": "UpdateProdTest", "risk_factor": 0.5}, headers=headers
    )
    cat_id = cat_resp.json()["id"]

    create_prod = client.post(
        "/products",
        json={
            "name": "Before Update",
            "quantity": 1,
            "min_stock": 1,
            "price": 1.0,
            "category_id": cat_id,
        },
        headers=headers,
    )
    product_id = create_prod.json()["id"]

    # Обновление
    update_payload = {
        "name": "After Update",
        "quantity": 50,
        "min_stock": 20,
        "price": 99.99,
        "category_id": cat_id,
    }
    response = client.put(f"/products/{product_id}", json=update_payload, headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "After Update"
    assert data["quantity"] == 50
    assert data["price"] == 99.99

    # Тест на 404
    response_404 = client.put("/products/99999", json=update_payload, headers=headers)
    assert response_404.status_code == 404
