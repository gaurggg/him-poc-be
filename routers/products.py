from fastapi import APIRouter, HTTPException, Query
from database import get_db
from bson import ObjectId
from typing import Optional

router = APIRouter(prefix="/products", tags=["Products"])


def serialize_product(p) -> dict:
    p["id"] = str(p["_id"])
    del p["_id"]
    return p


@router.get("/")
async def list_products(
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    sort_by: Optional[str] = Query("name"),
    order: Optional[str] = Query("asc"),
    limit: int = Query(50),
    skip: int = Query(0),
):
    db = get_db()
    query = {}
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}},
            {"technology": {"$regex": search, "$options": "i"}},
            {"tags": {"$in": [search.lower()]}},
        ]
    if category and category != "All":
        query["category"] = category

    sort_direction = 1 if order == "asc" else -1
    sort_field = sort_by if sort_by in ["name", "price", "rating"] else "name"

    cursor = db.products.find(query).sort(sort_field, sort_direction).skip(skip).limit(limit)
    products = [serialize_product(p) async for p in cursor]
    total = await db.products.count_documents(query)
    return {"products": products, "total": total}


@router.get("/{product_id}")
async def get_product(product_id: str):
    db = get_db()
    try:
        oid = ObjectId(product_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid product ID")

    product = await db.products.find_one({"_id": oid})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Attach inventory per size
    inventory_cursor = db.inventory.find({"product_id": product_id})
    inventory = {doc["size"]: doc["quantity"] async for doc in inventory_cursor}
    product = serialize_product(product)
    product["inventory"] = inventory
    return product
