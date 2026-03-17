from fastapi import APIRouter
from database import get_db
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

router = APIRouter(prefix="/feedback", tags=["Feedback"])


class FeedbackRequest(BaseModel):
    product_id: Optional[str] = None
    order_id: Optional[str] = None
    customer_name: str = "Anonymous"
    customer_email: str = ""
    rating: int  # 1–5
    comment: str


@router.post("/")
async def submit_feedback(body: FeedbackRequest):
    db = get_db()

    doc = {
        "product_id": body.product_id,
        "order_id": body.order_id,
        "customer_name": body.customer_name,
        "customer_email": body.customer_email,
        "rating": max(1, min(5, body.rating)),
        "comment": body.comment,
        "created_at": datetime.utcnow().isoformat(),
    }
    await db.feedback.insert_one(doc)

    # Send email notification
    try:
        from utils.email import send_feedback_email
        await send_feedback_email(doc)
    except Exception as e:
        print(f"📧 Email notification skipped: {e}")

    return {"message": "Thank you for your feedback! We appreciate you taking the time to share your experience.", "status": "received"}


@router.get("/")
async def list_feedback():
    db = get_db()
    cursor = db.feedback.find().sort("created_at", -1).limit(100)
    items = []
    async for f in cursor:
        f["id"] = str(f["_id"])
        del f["_id"]
        items.append(f)
    return {"feedback": items, "total": len(items)}
