from fastapi import APIRouter, HTTPException
from database import get_db
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from bson import ObjectId

router = APIRouter(prefix="/invoices", tags=["Invoices"])


class UpdateInvoiceStatus(BaseModel):
    status: str


def _oid(invoice_id: str) -> ObjectId:
    try:
        return ObjectId(invoice_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid invoice ID format")


@router.get("/")
async def list_invoices():
    db = get_db()
    invoices = []
    async for inv in db.invoices.find().sort("created_at", -1):
        inv["id"] = str(inv["_id"])
        del inv["_id"]
        invoices.append(inv)
    return {"invoices": invoices, "total": len(invoices)}


@router.patch("/{invoice_id}/status")
async def update_invoice_status(invoice_id: str, body: UpdateInvoiceStatus):
    db = get_db()
    valid = ["Pending", "Ordered", "Received", "Cancelled"]
    if body.status not in valid:
        raise HTTPException(status_code=400, detail=f"Invalid status. Valid: {valid}")

    oid = _oid(invoice_id)

    # Fetch the invoice first — we need it for inventory updates
    invoice = await db.invoices.find_one({"_id": oid})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    now = datetime.utcnow().isoformat()
    update_fields: dict = {"status": body.status, "updated_at": now}

    if body.status == "Ordered":
        update_fields["approved_at"] = now

    # ── KEY FIX: When marked Received → restock inventory ─────────────────
    if body.status == "Received":
        update_fields["received_at"] = now

        product_id   = invoice.get("product_id", "")
        product_name = invoice.get("product_name", "")
        vendor       = invoice.get("vendor", "")
        sizes        = invoice.get("sizes") or []
        total_qty    = invoice.get("quantity", 0)

        # Distribute quantity evenly across sizes
        qty_per_size = (total_qty // len(sizes)) if sizes else total_qty
        remainder    = total_qty - (qty_per_size * len(sizes)) if sizes else 0

        restocked = []
        for i, size in enumerate(sizes):
            add_qty = qty_per_size + (1 if i < remainder else 0)
            result = await db.inventory.update_one(
                {"product_id": product_id, "size": size},
                {
                    "$inc": {"quantity": add_qty},
                    "$set": {"last_restocked_at": now, "last_restocked_by": f"PO-{invoice_id[-8:].upper()}"},
                },
            )
            if result.matched_count > 0:
                restocked.append({"size": size, "added": add_qty})

        # Write an audit record into inventory_history
        if restocked:
            await db.inventory_history.insert_one({
                "invoice_id":    invoice_id,
                "invoice_ref":   f"PO-{invoice_id[-8:].upper()}",
                "product_id":    product_id,
                "product_name":  product_name,
                "vendor":        vendor,
                "restocked":     restocked,
                "total_added":   total_qty,
                "event":         "restock",
                "created_at":    now,
            })

    await db.invoices.update_one({"_id": oid}, {"$set": update_fields})
    return {"id": invoice_id, "status": body.status}


@router.get("/history")
async def inventory_history():
    """Return the audit log of all restock events."""
    db = get_db()
    history = []
    async for h in db.inventory_history.find().sort("created_at", -1).limit(100):
        h["_id"] = str(h["_id"])
        history.append(h)
    return {"history": history, "total": len(history)}


@router.delete("/clear")
async def clear_invoices():
    """Clear only Received/Cancelled invoices — keeps active orders."""
    db = get_db()
    result = await db.invoices.delete_many({"status": {"$in": ["Received", "Cancelled"]}})
    return {"deleted": result.deleted_count, "message": f"Cleared {result.deleted_count} completed invoices"}
