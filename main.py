from typing import List

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session, joinedload

from auth import (
    authenticate_user,
    create_access_token,
    get_current_active_user,
    get_current_user,
    get_password_hash,
)

# Импорты локальных модулей проекта
from database import Base, engine, get_db
from logic import calculate_optimal_restock
from models import Category, Product, User
from schemas import (
    CategoryCreate,
    CategoryRead,
    ProductCreate,
    ProductRead,
    RestockRecommendation,
    Token,
    UserCreate,
    UserRead,
)

# Автоматическое создание таблиц при запуске
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Smart Inventory Optimizer API")


# --- AUTH ENDPOINTS ---


@app.post("/auth/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user_data.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        username=user_data.username, hashed_password=hashed_password, role=user_data.role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@app.post("/auth/token", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


# --- CATEGORY CRUD ---


@app.get("/categories", response_model=List[CategoryRead])
def get_categories(db: Session = Depends(get_db)):
    return db.query(Category).all()


@app.post("/categories", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(category: CategoryCreate, db: Session = Depends(get_db)):
    db_category = Category(**category.model_dump())
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category


@app.put("/categories/{category_id}", response_model=CategoryRead)
def update_category(category_id: int, category_data: CategoryCreate, db: Session = Depends(get_db)):
    db_category = db.query(Category).filter(Category.id == category_id).first()
    if not db_category:
        raise HTTPException(status_code=404, detail="Category not found")

    for key, value in category_data.model_dump().items():
        setattr(db_category, key, value)

    db.commit()
    db.refresh(db_category)
    return db_category


@app.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: int, db: Session = Depends(get_db)) -> None:
    db_category = db.query(Category).filter(Category.id == category_id).first()
    if not db_category:
        raise HTTPException(status_code=404, detail="Category not found")
    db.delete(db_category)
    db.commit()


# --- PRODUCT CRUD ---


@app.get("/products", response_model=List[ProductRead])
def get_products(db: Session = Depends(get_db)):
    return db.query(Product).all()


@app.get("/products/{product_id}", response_model=ProductRead)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@app.post("/products", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    # Проверка существования категории
    if not db.query(Category).filter(Category.id == product.category_id).first():
        raise HTTPException(status_code=400, detail="Invalid category_id")

    db_product = Product(**product.model_dump())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product


@app.put("/products/{product_id}", response_model=ProductRead)
def update_product(product_id: int, product_data: ProductCreate, db: Session = Depends(get_db)):
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    for key, value in product_data.model_dump().items():
        setattr(db_product, key, value)

    db.commit()
    db.refresh(db_product)
    return db_product


@app.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),  # Требуется авторизация
) -> None:
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    db.delete(db_product)
    db.commit()


@app.post("/inventory/optimize", response_model=List[RestockRecommendation])
def optimize_inventory(
    budget: float = Query(..., gt=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    products = db.query(Product).options(joinedload(Product.category)).all()
    return calculate_optimal_restock(products, budget)
