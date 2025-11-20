import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Product as ProductSchema, Order as OrderSchema, OrderItem as OrderItemSchema, Customer as CustomerSchema

app = FastAPI(title="MyAutoKit API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Utilities
class ProductResponse(BaseModel):
    id: str
    title: str
    slug: str
    description: Optional[str] = None
    price: float
    category: str
    image: Optional[str] = None
    gallery: Optional[List[str]] = None
    in_stock: bool
    featured: bool
    specs: Optional[dict] = None


def serialize_doc(doc: dict) -> dict:
    if not doc:
        return doc
    d = doc.copy()
    if "_id" in d:
        d["id"] = str(d.pop("_id"))
    # Convert any nested ObjectIds if present
    for k, v in list(d.items()):
        if isinstance(v, ObjectId):
            d[k] = str(v)
    return d


# Seed sample data on first run
async def seed_products_if_empty():
    try:
        if db is None:
            return
        count = db["product"].count_documents({})
        if count == 0:
            samples: List[ProductSchema] = [
                ProductSchema(
                    title="Neon Drive LED Poster",
                    slug="neon-drive-led-poster",
                    description="Futuristic neon car silhouette with dynamic glow, perfect for garage or game room.",
                    price=89.0,
                    category="LED Poster",
                    image="https://images.unsplash.com/photo-1542362567-b07e54358753?q=80&w=1200&auto=format&fit=crop",
                    gallery=[
                        "https://images.unsplash.com/photo-1542362567-b07e54358753?q=80&w=1200&auto=format&fit=crop",
                        "https://images.unsplash.com/photo-1483721310020-03333e577078?q=80&w=1200&auto=format&fit=crop",
                    ],
                    in_stock=True,
                    featured=True,
                    specs={"size": "24x36 in", "power": "USB-C", "brightness": "Adjustable"},
                ),
                ProductSchema(
                    title="Carbon Wave LED Poster",
                    slug="carbon-wave-led-poster",
                    description="Matte carbon fibers meet flowing LED accents for a bold, stealthy vibe.",
                    price=99.0,
                    category="LED Poster",
                    image="https://images.unsplash.com/photo-1520975922203-b272b1e4e766?q=80&w=1200&auto=format&fit=crop",
                    gallery=None,
                    in_stock=True,
                    featured=True,
                    specs={"size": "18x24 in", "power": "USB-A", "mount": "Magnetic"},
                ),
                ProductSchema(
                    title="Redline Interior Glow Kit",
                    slug="redline-interior-glow-kit",
                    description="Premium ambient lighting kit with deep red tones inspired by performance interiors.",
                    price=59.0,
                    category="Car Decor",
                    image="https://images.unsplash.com/photo-1511919884226-fd3cad34687c?q=80&w=1200&auto=format&fit=crop",
                    gallery=None,
                    in_stock=True,
                    featured=False,
                    specs={"length": "4x 60cm", "modes": 12, "remote": True},
                ),
            ]
            for p in samples:
                create_document("product", p)
    except Exception:
        # Silently ignore seeding errors to avoid blocking startup
        pass


@app.on_event("startup")
async def on_startup():
    await seed_products_if_empty()


@app.get("/")
def read_root():
    return {"message": "MyAutoKit API is running"}


@app.get("/api/products", response_model=List[ProductResponse])
def list_products():
    try:
        docs = get_documents("product", {}, None)
        return [ProductResponse(**serialize_doc(d)) for d in docs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/products/featured", response_model=List[ProductResponse])
def featured_products():
    try:
        docs = get_documents("product", {"featured": True}, 8)
        return [ProductResponse(**serialize_doc(d)) for d in docs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/products/{slug}", response_model=ProductResponse)
def get_product(slug: str):
    try:
        doc = db["product"].find_one({"slug": slug})
        if not doc:
            raise HTTPException(status_code=404, detail="Product not found")
        return ProductResponse(**serialize_doc(doc))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class OrderCreate(BaseModel):
    items: List[OrderItemSchema]
    customer: CustomerSchema
    shipping: float = 0.0


@app.post("/api/orders")
def create_order(order: OrderCreate):
    # Recalculate totals based on product IDs and quantities
    try:
        if not order.items:
            raise HTTPException(status_code=400, detail="Cart is empty")

        subtotal = 0.0
        normalized_items = []
        for it in order.items:
            # Fetch product price by id
            try:
                prod = db["product"].find_one({"_id": ObjectId(it.product_id)})
            except Exception:
                prod = None
            if not prod:
                raise HTTPException(status_code=400, detail=f"Invalid product: {it.product_id}")
            price = float(prod.get("price", 0.0))
            subtotal += price * it.quantity
            normalized_items.append({
                "product_id": it.product_id,
                "title": prod.get("title"),
                "price": price,
                "quantity": it.quantity,
                "image": prod.get("image"),
            })

        shipping = float(order.shipping or 0.0)
        total = round(subtotal + shipping, 2)

        order_doc = OrderSchema(
            items=[OrderItemSchema(**ni) for ni in normalized_items],
            customer=order.customer,
            subtotal=round(subtotal, 2),
            shipping=shipping,
            total=total,
            status="pending",
        )
        order_id = create_document("order", order_doc)
        return {"order_id": order_id, "total": total, "status": "pending"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
