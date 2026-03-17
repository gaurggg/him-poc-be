from fastapi import APIRouter, HTTPException
from database import get_db
from pydantic import BaseModel
from typing import List
from datetime import datetime
import uuid

router = APIRouter(prefix="/orders", tags=["Orders"])


class OrderItem(BaseModel):
    product_id: str
    size: str
    quantity: int
    price: float
    name: str


class CreateOrderRequest(BaseModel):
    items: List[OrderItem]
    customer_name: str = "Guest"
    customer_email: str = "guest@demo.com"


@router.post("/")
async def create_order(request: CreateOrderRequest):
    db = get_db()
    order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"

    # Check stock and deduct atomically
    for item in request.items:
        inv = await db.inventory.find_one({
            "product_id": item.product_id,
            "size": item.size,
        })
        if not inv:
            raise HTTPException(status_code=400, detail=f"Inventory not found for {item.name} size {item.size}")
        if inv["quantity"] < item.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock for {item.name} size {item.size}. Available: {inv['quantity']}"
            )

    # All checks passed — deduct inventory
    for item in request.items:
        await db.inventory.update_one(
            {"product_id": item.product_id, "size": item.size},
            {"$inc": {"quantity": -item.quantity}}
        )

    total_amount = sum(i.price * i.quantity for i in request.items)

    order_doc = {
        "order_id": order_id,
        "customer_name": request.customer_name,
        "customer_email": request.customer_email,
        "items": [i.model_dump() for i in request.items],
        "total_amount": total_amount,
        "status": "Confirmed",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }

    await db.orders.insert_one(order_doc)

    # Send order confirmation email (best-effort, non-blocking)
    try:
        from utils.email import send_order_confirmation_email
        await send_order_confirmation_email(order_doc)
    except Exception as e:
        print(f"📧 Order email skipped: {e}")

    return {"order_id": order_id, "status": "Confirmed", "total_amount": total_amount}


@router.get("/{order_id}")
async def get_order(order_id: str):
    db = get_db()
    order = await db.orders.find_one({"order_id": order_id})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    order["id"] = str(order["_id"])
    del order["_id"]
    return order


@router.get("/")
async def list_orders():
    db = get_db()
    cursor = db.orders.find().sort("created_at", -1).limit(50)
    orders = []
    async for o in cursor:
        o["id"] = str(o["_id"])
        del o["_id"]
        orders.append(o)
    return {"orders": orders}


@router.patch("/{order_id}/status")
async def update_order_status(order_id: str, status: str):
    db = get_db()
    valid_statuses = ["Confirmed", "Processing", "Shipped", "Delivered", "Cancelled"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Valid: {valid_statuses}")
    result = await db.orders.update_one(
        {"order_id": order_id},
        {"$set": {"status": status, "updated_at": datetime.utcnow().isoformat()}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Order not found")
    return {"order_id": order_id, "status": status}
