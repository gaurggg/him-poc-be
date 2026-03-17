from fastapi import APIRouter
from database import get_db
from config import get_settings
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from openai import AsyncAzureOpenAI      # ← async client — does NOT block the event loop
import re
import uuid

router   = APIRouter(prefix="/chatbot", tags=["Chatbot"])
settings = get_settings()

# In-memory session store (POC — resets on server restart)
sessions: dict = {}

# ── Intent keyword lists ──────────────────────────────────────────────────────
REFUND_KEYWORDS    = ["refund", "return my order", "want to return", "damaged",
                      "defective", "wrong item", "broken", "never received",
                      "lost package", "not delivered", "missing item", "cancel order"]
COMPLAINT_KEYWORDS = ["complaint", "very unhappy", "worst", "cheat", "fraud",
                      "pathetic", "worst service", "rubbish", "horrible"]
TRENDING_KEYWORDS  = ["trending", "popular", "bestseller", "best seller",
                      "top rated", "most popular", "recommend", "suggestion"]
OFFER_KEYWORDS     = ["offer", "sale", "discount", "deal", "coupon",
                      "promo", "cheap", "cheapest", "under ₹", "best price"]
SIZE_KEYWORDS      = ["size", "sizing", "fit", "measurement", "chest",
                      "which size", "size guide", "size chart"]


class ChatMessage(BaseModel):
    message:    str
    session_id: Optional[str] = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _kw(text: str, keywords: list) -> bool:
    t = text.lower()
    return any(k in t for k in keywords)


def extract_order_id(message: str) -> Optional[str]:
    match = re.search(r"ORD-[A-F0-9]{8}", message.upper())
    return match.group(0) if match else None


async def get_order_context(db, order_id: str) -> str:
    order = await db.orders.find_one({"order_id": order_id})
    if not order:
        return f"Order {order_id}: NOT FOUND in the database."
    summary = ", ".join(
        f"{i['name']} x{i['quantity']} (size {i['size']})"
        for i in order.get("items", [])
    )
    return (
        f"Order {order_id} found — "
        f"Status: {order['status']}, Items: {summary}, "
        f"Total: ₹{order['total_amount']:.0f}, Placed: {order['created_at'][:10]}, "
        f"Customer: {order.get('customer_name','')}"
    )


async def get_trending_products(db) -> str:
    products = await db.products.find().sort("rating", -1).limit(6).to_list(6)
    if not products:
        return ""
    lines = []
    for p in products:
        disc = round(((p["original_price"] - p["price"]) / p["original_price"]) * 100) \
               if p.get("original_price", 0) > p.get("price", 0) else 0
        disc_str = f" — {disc}% OFF" if disc > 0 else ""
        lines.append(
            f"• {p['name']} ({p['category']}) — ₹{p['price']:,}{disc_str} | "
            f"Rating: {p.get('rating', 'N/A')}⭐ | Sizes: {', '.join(p.get('sizes', []))}"
        )
    return "CURRENT TRENDING PRODUCTS (live from catalog):\n" + "\n".join(lines)


async def get_current_offers(db) -> str:
    pipeline = [
        {"$match": {"$expr": {"$gt": ["$original_price", "$price"]}}},
        {"$addFields": {
            "disc_pct": {"$round": [{"$multiply": [
                {"$divide": [{"$subtract": ["$original_price", "$price"]}, "$original_price"]},
                100
            ]}, 0]}
        }},
        {"$sort": {"disc_pct": -1}},
        {"$limit": 6},
    ]
    products = [p async for p in db.products.aggregate(pipeline)]
    if not products:
        return ""
    lines = []
    for p in products:
        lines.append(
            f"• {p['name']} ({p['category']}) — ₹{p['price']:,} "
            f"(was ₹{p['original_price']:,}, {int(p['disc_pct'])}% OFF) | "
            f"Sizes: {', '.join(p.get('sizes', []))}"
        )
    return "CURRENT OFFERS & DISCOUNTS (live from catalog):\n" + "\n".join(lines)


SIZE_GUIDE_TEXT = """
TECHNOSPORT SIZE GUIDE:
Adults (chest in inches): XS=32", S=34", M=36", L=38", XL=40", XXL=42"
Boys (age-based): 8Y (7–8 yrs), 10Y (9–10 yrs), 12Y (11–12 yrs), 14Y (13–14 yrs)
Fit tip: For athletic fit, choose your exact chest size. For relaxed fit, go one size up.
Fabric stretch: TechnoDry and TechnoCool+ fabrics have 4-way stretch — true to size works well.
If between sizes: for T-shirts go smaller for snug athletic fit; for sweatshirts go larger for comfort.
"""


async def create_support_ticket(db, session_id: str, conversation: list,
                                 priority: str = "Medium", reason: str = "") -> str:
    ticket_id = f"TKT-{str(uuid.uuid4())[:8].upper()}"
    lines = []
    for m in conversation[-8:]:
        role = "Customer" if m["role"] == "user" else "Bot"
        lines.append(f"{role}: {m['content'][:150]}")
    summary = (f"[{reason}] " if reason else "") + " → ".join(lines)

    ticket = {
        "ticket_id":       ticket_id,
        "session_id":      session_id,
        "status":          "Open",
        "priority":        priority,
        "issue_summary":   summary,
        "created_at":      datetime.utcnow().isoformat(),
        "resolved_at":     None,
        "notes":           "",
    }
    await db.support_tickets.insert_one(ticket)

    # Notify support team via email
    try:
        from utils.email import send_ticket_notification_email
        await send_ticket_notification_email(ticket)
    except Exception as e:
        print(f"📧 Ticket email skipped: {e}")

    return ticket_id


async def call_ai(messages: list) -> str:
    """Call Azure OpenAI asynchronously — never blocks the event loop."""
    client = AsyncAzureOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_key,
        api_version="2024-10-21",
    )
    resp = await client.chat.completions.create(
        model=settings.azure_openai_deployment,
        messages=messages,
        temperature=0.7,
        max_tokens=500,
    )
    return resp.choices[0].message.content.strip()


async def fallback_reply(db, message: str) -> str:
    """FAQ keyword match when Azure OpenAI is unavailable."""
    msg_lower = message.lower()
    best, best_score = None, 0
    async for faq in db.faqs.find():
        score = sum(1 for k in faq.get("keywords", []) if k.lower() in msg_lower)
        if score > best_score:
            best_score, best = score, faq
    if best and best_score > 0:
        return best["answer"]
    return (
        "I'm here to help with order tracking, returns, sizes, offers and more. "
        "Could you share more details so I can assist you better? 😊"
    )


# ── Main route ────────────────────────────────────────────────────────────────

@router.post("/")
async def chat(body: ChatMessage):
    db      = get_db()
    message = body.message.strip()
    msg_low = message.lower()

    # Session init
    session_id = body.session_id or str(uuid.uuid4())
    if session_id not in sessions:
        sessions[session_id] = {
            "history":       [],
            "user_turns":    0,
            "resolved":      False,
            "ticket_created": False,
        }
    session = sessions[session_id]

    # ── IMMEDIATE TICKET for refund / serious complaint ──────────────────────
    immediate_ticket_id = None
    if not session["ticket_created"] and (_kw(msg_low, REFUND_KEYWORDS) or _kw(msg_low, COMPLAINT_KEYWORDS)):
        reason   = "Refund/Return" if _kw(msg_low, REFUND_KEYWORDS) else "Complaint"
        priority = "High"
        session["history"].append({"role": "user", "content": message})
        session["user_turns"] += 1
        immediate_ticket_id = await create_support_ticket(
            db, session_id, session["history"], priority=priority, reason=reason
        )
        session["ticket_created"] = True

        # Still get an AI reply for this message
        # ... continue to AI call below with the ticket note injected

    else:
        session["history"].append({"role": "user", "content": message})
        session["user_turns"] += 1

    # ── Build dynamic context ────────────────────────────────────────────────
    extra_context_parts = []

    # Order lookup
    order_id = extract_order_id(message)
    if order_id:
        ctx = await get_order_context(db, order_id)
        extra_context_parts.append(f"\n[ORDER LOOKUP]: {ctx}")
        session["resolved"] = True

    # Trending products
    if _kw(msg_low, TRENDING_KEYWORDS):
        ctx = await get_trending_products(db)
        if ctx:
            extra_context_parts.append(f"\n{ctx}")

    # Offers / discounts
    if _kw(msg_low, OFFER_KEYWORDS):
        ctx = await get_current_offers(db)
        if ctx:
            extra_context_parts.append(f"\n{ctx}")

    # Size guide
    if _kw(msg_low, SIZE_KEYWORDS):
        extra_context_parts.append(f"\n{SIZE_GUIDE_TEXT}")

    # Ticket note (for the AI to acknowledge)
    if immediate_ticket_id:
        extra_context_parts.append(
            f"\n[SYSTEM NOTE]: A support ticket {immediate_ticket_id} has already been created "
            f"for this customer's refund/complaint. Acknowledge it warmly in your reply."
        )

    # ── System prompt ────────────────────────────────────────────────────────
    system_prompt = (
        "You are TechnoSport's intelligent and friendly customer support assistant "
        "for an Indian performance sportswear brand.\n\n"
        "You help with:\n"
        "- Order tracking (ask for Order ID like ORD-XXXXXXXX)\n"
        "- Returns & refunds (7-day return window from delivery date, full refund for defects)\n"
        "- Exchanges (within 15 days, subject to stock availability)\n"
        "- Shipping (standard 3–5 business days; express 1–2 days for ₹99 extra)\n"
        "- Size guide (use the size chart when provided below)\n"
        "- Trending & popular products (use live data when provided)\n"
        "- Current offers & discounts (use live data when provided)\n"
        "- Fabric technologies: TechnoDry=moisture-wicking, TechnoGuard=UV protection, "
        "TechnoCool+=cooling, TechnoWarm+=thermal insulation\n"
        "- Payment & order issues\n\n"
        "Rules:\n"
        "- Be warm, empathetic, and conversational\n"
        "- Keep replies to 3–5 sentences unless showing a list (e.g., products/sizes)\n"
        "- Always use ₹ for Indian prices\n"
        "- When showing product lists, format each on a new line with bullet points\n"
        "- Support Hinglish naturally if the customer uses it\n"
        "- NEVER invent order data — only use what is explicitly provided in [ORDER LOOKUP]\n"
        "- If a support ticket was already created, mention the ticket ID warmly\n"
        "- For refund/return queries, be empathetic and provide the process clearly"
        + "".join(extra_context_parts)
    )

    messages_to_send = [{"role": "system", "content": system_prompt}] + session["history"]

    # ── Call AI ──────────────────────────────────────────────────────────────
    if settings.azure_openai_key and settings.azure_openai_endpoint:
        try:
            reply = await call_ai(messages_to_send)
        except Exception as exc:
            print(f"⚠️ Azure OpenAI error: {exc}")
            reply = await fallback_reply(db, message)
    else:
        print("⚠️ Azure OpenAI not configured — using FAQ fallback")
        reply = await fallback_reply(db, message)

    session["history"].append({"role": "assistant", "content": reply})

    # ── Resolution tracking ──────────────────────────────────────────────────
    reply_low = reply.lower()
    if any(s in reply_low for s in [
        "your order", "return policy", "you can return", "shipping", "size guide",
        "here's the info", "₹", "refund will be", "replacement", "we'll process",
        "ticket", "hope that helps", "is there anything else",
    ]):
        session["resolved"] = True

    # ── Auto-ticket after 3 unresolved turns (generic issues) ────────────────
    escalation_ticket_id = None
    if (session["user_turns"] >= 3
            and not session["resolved"]
            and not session["ticket_created"]):
        escalation_ticket_id = await create_support_ticket(
            db, session_id, session["history"],
            priority="Medium", reason="Auto-escalated after 3 unresolved turns"
        )
        session["ticket_created"] = True
        reply += (
            f"\n\n🎫 I've escalated your case to our support team "
            f"(Ticket **{escalation_ticket_id}**). "
            f"A specialist will reach out within 24 hours!"
        )

    ticket_id = immediate_ticket_id or escalation_ticket_id

    # ── Feedback form trigger ────────────────────────────────────────────────
    action = None
    if any(w in msg_low for w in ["feedback", "review", "rate my experience"]):
        action = "open_feedback_form"

    return {
        "intent":     "ai_response",
        "session_id": session_id,
        "reply":      reply,
        "action":     action,
        "ticket_id":  ticket_id,
    }
