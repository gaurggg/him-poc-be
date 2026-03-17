from fastapi import APIRouter
from database import get_db

router = APIRouter(prefix="/inventory", tags=["Inventory"])


@router.get("/")
async def get_inventory():
    db = get_db()

    # Aggregate inventory with product info
    pipeline = [
        {
            "$lookup": {
                "from": "products",
                "let": {"pid": "$product_id"},
                "pipeline": [
                    {"$addFields": {"str_id": {"$toString": "$_id"}}},
                    {"$match": {"$expr": {"$eq": ["$str_id", "$$pid"]}}}
                ],
                "as": "product"
            }
        },
        {"$unwind": {"path": "$product", "preserveNullAndEmptyArrays": True}},
        {
            "$project": {
                "_id": 0,
                "id": {"$toString": "$_id"},
                "product_id": 1,
                "size": 1,
                "quantity": 1,
                "threshold": 1,
                "vendor": 1,
                "reorder_quantity": 1,
                "product_name": "$product.name",
                "category": "$product.category",
                "image_url": "$product.image_url",
                "is_low_stock": {"$lt": ["$quantity", "$threshold"]},
                "last_restocked_at": 1,
                "last_restocked_by": 1,
            }
        },
        {"$sort": {"product_name": 1, "size": 1}},
    ]

    cursor = db.inventory.aggregate(pipeline)
    inventory = [doc async for doc in cursor]
    low_stock_count = sum(1 for i in inventory if i.get("is_low_stock"))
    return {"inventory": inventory, "low_stock_count": low_stock_count, "total": len(inventory)}


@router.patch("/{product_id}/{size}")
async def update_stock(product_id: str, size: str, quantity: int):
    """Manually update stock quantity (for demo purposes)."""
    db = get_db()
    result = await db.inventory.update_one(
        {"product_id": product_id, "size": size},
        {"$set": {"quantity": quantity}}
    )
    if result.matched_count == 0:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Inventory record not found")
    return {"product_id": product_id, "size": size, "quantity": quantity}
