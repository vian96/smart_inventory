from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

# --- AUTH SCHEMAS ---


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class UserBase(BaseModel):
    username: str
    role: str = Field(default="viewer", pattern="^(admin|manager|viewer)$")


class UserCreate(UserBase):
    password: str


class UserRead(UserBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


# --- CATEGORY SCHEMAS ---


class CategoryBase(BaseModel):
    name: str
    risk_factor: float = Field(ge=0.0, le=1.0, description="Risk factor from 0 to 1")


class CategoryCreate(CategoryBase):
    pass


class CategoryRead(CategoryBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


# --- PRODUCT SCHEMAS ---


class ProductBase(BaseModel):
    name: str
    quantity: int = Field(ge=0)
    min_stock: int = Field(ge=0)
    price: float = Field(gt=0)
    category_id: int


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    quantity: Optional[int] = Field(None, ge=0)
    min_stock: Optional[int] = Field(None, ge=0)
    price: Optional[float] = Field(None, gt=0)
    category_id: Optional[int] = None


class ProductRead(ProductBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
