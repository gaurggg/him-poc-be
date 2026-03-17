from fastapi import APIRouter
from database import get_db
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

router = APIRouter(prefix="/tickets", tags=["Support Tickets"])


class TicketUpdate(BaseModel):
    status: str
    notes: Optional[str] = None


@router.get("/")
async def list_tickets():
    db = get_db()
    tickets = []
    async for t in db.support_tickets.find().sort("created_at", -1).limit(200):
        t["_id"] = str(t["_id"])
        tickets.append(t)
    return {"tickets": tickets, "total": len(tickets)}


@router.patch("/{ticket_id}/status")
async def update_ticket(ticket_id: str, body: TicketUpdate):
    db = get_db()
    update: dict = {"status": body.status}
    if body.status in ("Resolved", "Closed"):
        update["resolved_at"] = datetime.utcnow().isoformat()
    if body.notes is not None:
        update["notes"] = body.notes
    await db.support_tickets.update_one(
        {"ticket_id": ticket_id}, {"$set": update}
    )
    return {"message": f"Ticket {ticket_id} updated to {body.status}"}


@router.delete("/clear")
async def clear_tickets():
    db = get_db()
    result = await db.support_tickets.delete_many(
        {"status": {"$in": ["Resolved", "Closed"]}}
    )
    return {"message": f"Cleared {result.deleted_count} resolved/closed tickets"}
