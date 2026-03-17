from fastapi import APIRouter
from database import get_db
from config import get_settings
from datetime import datetime
import json
import random

router = APIRouter(prefix="/agent", tags=["AI Agent"])
settings = get_settings()


def mock_generate_invoices(low_stock_items: list) -> list:
    """Fallback: rule-based invoice generation when Azure OpenAI is not configured."""
    invoices = []
    grouped = {}
    for item in low_stock_items:
        key = (item["product_id"], item["product_name"], item["vendor"])
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(item)

    for (product_id, product_name, vendor), items in grouped.items():
        total_needed = sum(i.get("reorder_quantity", 100) for i in items)
        invoices.append({
            "product_id": product_id,
            "product_name": product_name,
            "vendor": vendor,
            "sizes": [i["size"] for i in items],
            "quantity": total_needed,
            "estimated_cost": total_needed * random.randint(150, 400),
            "ai_justification": (
                f"Stock for '{product_name}' ({', '.join([i['size'] for i in items])}) "
                f"is critically low (current: {sum(i['quantity'] for i in items)} units across sizes). "
                f"Recommend immediate reorder of {total_needed} units to maintain service level."
            ),
            "priority": "HIGH" if sum(i["quantity"] for i in items) < 5 else "MEDIUM",
        })
    return invoices


async def azure_openai_generate_invoices(low_stock_items: list) -> list:
    """Uses Azure OpenAI to generate intelligent reorder recommendations."""
    try:
        from openai import AzureOpenAI
        client = AzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_key,
            api_version="2024-02-01",
        )

        prompt = f"""
You are an inventory management AI agent for Technosport, a performance sportswear brand.

The following products are running LOW on stock (below threshold):
{json.dumps(low_stock_items, indent=2)}

Generate a JSON array of purchase order recommendations. For each unique product+vendor combination, create one order.
Each order must have these exact fields:
- product_id (string)
- product_name (string)
- vendor (string)
- sizes (array of sizes to reorder)
- quantity (total units to reorder, considering demand and lead time)
- estimated_cost (in INR, based on realistic sportswear wholesale pricing)
- ai_justification (1-2 sentence explanation)
- priority (HIGH, MEDIUM, or LOW)

Respond with ONLY a valid JSON array, no markdown, no explanation outside the JSON.
"""
        response = client.chat.completions.create(
            model=settings.azure_openai_deployment,
            messages=[
                {"role": "system", "content": "You are a supply chain AI assistant. Always respond with valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=1500,
        )

        content = response.choices[0].message.content.strip()
        # Strip any accidental markdown
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        return json.loads(content)

    except Exception as e:
        print(f"⚠️  Azure OpenAI error: {e}. Falling back to mock generation.")
        return mock_generate_invoices(low_stock_items)


@router.post("/run")
async def run_agent():
    db = get_db()

    # Find all low-stock inventory
    pipeline = [
        {"$match": {"$expr": {"$lt": ["$quantity", "$threshold"]}}},
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
                "product_id": 1,
                "size": 1,
                "quantity": 1,
                "threshold": 1,
                "vendor": 1,
                "reorder_quantity": 1,
                "product_name": "$product.name",
                "category": "$product.category",
            }
        },
    ]

    low_stock = [doc async for doc in db.inventory.aggregate(pipeline)]

    if not low_stock:
        return {"message": "✅ All inventory levels are healthy. No action needed.", "invoices_created": 0}

    # Generate invoices via AI or mock
    use_azure = bool(settings.azure_openai_endpoint and settings.azure_openai_key)
    if use_azure:
        print("🤖 Using Azure OpenAI for invoice generation...")
        recommendations = await azure_openai_generate_invoices(low_stock)
    else:
        print("🔧 Using rule-based mock (Azure OpenAI not configured)...")
        recommendations = mock_generate_invoices(low_stock)

    # Save invoices to DB
    invoice_docs = []
    for rec in recommendations:
        doc = {
            **rec,
            "status": "Pending",
            "created_at": datetime.utcnow().isoformat(),
            "generated_by": "Azure OpenAI" if use_azure else "Rule-Based Agent",
        }
        invoice_docs.append(doc)

    if invoice_docs:
        await db.invoices.insert_many(invoice_docs)

    # Email notification (best-effort)
    try:
        from utils.email import send_vendor_invoice_email
        await send_vendor_invoice_email(invoice_docs)
    except Exception as e:
        print(f"📧 Email skipped: {e}")

    return {
        "message": f"🤖 Agent ran successfully. {len(invoice_docs)} purchase order(s) raised.",
        "invoices_created": len(invoice_docs),
        "low_stock_items": len(low_stock),
        "generated_by": "Azure OpenAI" if use_azure else "Rule-Based Agent",
    }
