"""
Database Schemas for MyAutoKit

Each Pydantic model represents a collection in your MongoDB database.
Collection name is the lowercase of the class name (e.g., Product -> "product").
"""
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List

class Product(BaseModel):
    """
    Product catalog schema
    Collection: "product"
    """
    title: str = Field(..., description="Product title")
    slug: str = Field(..., description="URL-friendly unique slug")
    description: Optional[str] = Field(None, description="Detailed description")
    price: float = Field(..., ge=0, description="Price in USD")
    category: str = Field(..., description="Category like 'LED Poster' or 'Car Decor'")
    image: Optional[str] = Field(None, description="Primary image URL")
    gallery: Optional[List[str]] = Field(default=None, description="Additional image URLs")
    in_stock: bool = Field(True, description="Whether product is available")
    featured: bool = Field(False, description="Show in featured section")
    specs: Optional[dict] = Field(default=None, description="Specification key-value pairs")

class OrderItem(BaseModel):
    product_id: str = Field(..., description="Referenced product _id string")
    title: str = Field(..., description="Snapshot of title at purchase time")
    price: float = Field(..., ge=0, description="Unit price at purchase time")
    quantity: int = Field(..., ge=1, description="Quantity ordered")
    image: Optional[str] = None

class Customer(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    address_line1: str
    address_line2: Optional[str] = None
    city: str
    state: str
    postal_code: str
    country: str

class Order(BaseModel):
    """
    Orders schema
    Collection: "order"
    """
    items: List[OrderItem]
    customer: Customer
    subtotal: float = Field(..., ge=0)
    shipping: float = Field(..., ge=0)
    total: float = Field(..., ge=0)
    status: str = Field("pending", description="Order status")
