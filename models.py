from sqlalchemy import String, ForeignKey, Float, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List
from database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="viewer")


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    risk_factor: Mapped[float] = mapped_column(Float, default=1.0)

    # One-to-Many: Одна категория может иметь много продуктов
    products: Mapped[List["Product"]] = relationship(
        back_populates="category", cascade="all, delete-orphan"
    )


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    min_stock: Mapped[int] = mapped_column(Integer, default=10)
    price: Mapped[float] = mapped_column(Float, nullable=False)

    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), nullable=False)

    # Many-to-One: Продукт принадлежит одной категории
    category: Mapped["Category"] = relationship(back_populates="products")
