"""
Email utility — sends real emails via SMTP when credentials are configured,
falls back to console preview for local dev.
"""
import smtplib
import ssl
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from concurrent.futures import ThreadPoolExecutor
from config import get_settings
from datetime import datetime

settings = get_settings()
_executor = ThreadPoolExecutor(max_workers=3)


# ── Core SMTP sender (runs in thread pool) ────────────────────────────────────

def _smtp_send(to: str, subject: str, html: str, text: str):
    if not settings.mail_username or not settings.mail_password:
        print(f"\n{'='*60}")
        print(f"📧 EMAIL PREVIEW (configure SMTP in .env to send for real)")
        print(f"To: {to}  |  Subject: {subject}")
        print(f"{'='*60}")
        print(text)
        print(f"{'='*60}\n")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = settings.mail_from
    msg["To"]      = to
    msg.attach(MIMEText(text, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html",  "utf-8"))

    ctx = ssl.create_default_context()
    try:
        if settings.mail_ssl_tls:
            with smtplib.SMTP_SSL(settings.mail_server, settings.mail_port, context=ctx, timeout=15) as srv:
                srv.login(settings.mail_username, settings.mail_password)
                srv.sendmail(settings.mail_from, [to], msg.as_string())
        else:
            with smtplib.SMTP(settings.mail_server, settings.mail_port, timeout=15) as srv:
                if settings.mail_starttls:
                    srv.starttls(context=ctx)
                srv.login(settings.mail_username, settings.mail_password)
                srv.sendmail(settings.mail_from, [to], msg.as_string())
        print(f"✅ Email sent → {to} | {subject}")
    except Exception as exc:
        print(f"❌ SMTP error ({exc}). Falling back to console preview.\nTo: {to}\n{text}")


async def _send(to: str, subject: str, html: str, text: str):
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(_executor, _smtp_send, to, subject, html, text)


# ── Order confirmation email ──────────────────────────────────────────────────

async def send_order_confirmation_email(order: dict):
    order_id     = order.get("order_id", "")
    customer     = order.get("customer_name", "Customer")
    email        = order.get("customer_email", "")
    items        = order.get("items", [])
    total        = order.get("total_amount", 0)
    status       = order.get("status", "Confirmed")
    created_at   = order.get("created_at", "")[:10]

    if not email or email == "guest@demo.com":
        return  # no valid email to send to

    items_html = "".join(
        f"<tr style='border-bottom:1px solid #f0f0f0'>"
        f"<td style='padding:8px 0'>{i.get('name','')}</td>"
        f"<td style='padding:8px;text-align:center'>{i.get('size','')}</td>"
        f"<td style='padding:8px;text-align:center'>{i.get('quantity','')}</td>"
        f"<td style='padding:8px;text-align:right'>₹{i.get('price',0):,.0f}</td>"
        f"</tr>"
        for i in items
    )
    items_text = "\n".join(
        f"  • {i.get('name','')} | Size: {i.get('size','')} | Qty: {i.get('quantity','')} | ₹{i.get('price',0):,.0f}"
        for i in items
    )

    subject = f"✅ Order Confirmed — {order_id} | TechnoSport"

    html = f"""
<!DOCTYPE html>
<html><body style="margin:0;padding:0;font-family:'Helvetica Neue',Arial,sans-serif;background:#f8fafc">
<div style="max-width:560px;margin:32px auto;background:#fff;border-radius:16px;overflow:hidden;border:1px solid #e2e8f0">
  <!-- Header -->
  <div style="background:linear-gradient(135deg,#6366F1,#818CF8);padding:28px 32px">
    <p style="margin:0;font-size:20px;font-weight:700;color:#fff;letter-spacing:-0.5px">TechnoSport</p>
    <p style="margin:4px 0 0;font-size:13px;color:rgba(255,255,255,0.8)">Order Confirmed 🎉</p>
  </div>
  <!-- Body -->
  <div style="padding:28px 32px">
    <p style="font-size:16px;font-weight:600;color:#0f172a;margin:0 0 4px">Hi {customer}!</p>
    <p style="font-size:13px;color:#64748b;margin:0 0 20px">Thanks for shopping with us. Your order has been confirmed.</p>

    <div style="background:#f8fafc;border-radius:10px;padding:16px 20px;margin-bottom:20px;border:1px solid #e2e8f0">
      <p style="margin:0 0 6px;font-size:11px;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:0.06em">Order ID</p>
      <p style="margin:0;font-size:18px;font-weight:800;color:#6366F1;font-family:monospace">{order_id}</p>
      <p style="margin:4px 0 0;font-size:12px;color:#64748b">Placed on {created_at}</p>
    </div>

    <table style="width:100%;border-collapse:collapse;margin-bottom:20px">
      <thead>
        <tr style="background:#f1f5f9">
          <th style="padding:8px 0;text-align:left;font-size:11px;color:#64748b;text-transform:uppercase;font-weight:700">Item</th>
          <th style="padding:8px;text-align:center;font-size:11px;color:#64748b;text-transform:uppercase;font-weight:700">Size</th>
          <th style="padding:8px;text-align:center;font-size:11px;color:#64748b;text-transform:uppercase;font-weight:700">Qty</th>
          <th style="padding:8px;text-align:right;font-size:11px;color:#64748b;text-transform:uppercase;font-weight:700">Price</th>
        </tr>
      </thead>
      <tbody>{items_html}</tbody>
    </table>

    <div style="border-top:2px solid #6366F1;padding-top:14px;display:flex;justify-content:space-between">
      <span style="font-size:14px;font-weight:600;color:#64748b">Total Amount</span>
      <span style="font-size:18px;font-weight:800;color:#0f172a">₹{total:,.0f}</span>
    </div>

    <div style="margin:20px 0;padding:14px 16px;background:#f0fdf4;border-radius:8px;border:1px solid #bbf7d0">
      <p style="margin:0;font-size:13px;color:#15803d;font-weight:500">
        🚚 Expected delivery: <strong>3–5 business days</strong>
      </p>
    </div>

    <p style="font-size:12px;color:#94a3b8;margin:0">
      For any help, reply to this email or chat with our support assistant on the website.
      Save your Order ID <strong>{order_id}</strong> for tracking.
    </p>
  </div>
  <!-- Footer -->
  <div style="background:#f8fafc;padding:16px 32px;border-top:1px solid #e2e8f0;text-align:center">
    <p style="margin:0;font-size:11px;color:#94a3b8">TechnoSport · Performance Sportswear · support@technosport.in</p>
  </div>
</div>
</body></html>
"""

    text = f"""Order Confirmed — {order_id}

Hi {customer},

Thank you for your order! Here are your order details:

Order ID : {order_id}
Date     : {created_at}
Status   : {status}

Items:
{items_text}

Total: ₹{total:,.0f}

Expected delivery: 3–5 business days.
Keep your Order ID handy for tracking via our chatbot.

— TechnoSport Support
"""
    await _send(email, subject, html, text)


# ── Vendor invoice email ──────────────────────────────────────────────────────

async def send_vendor_invoice_email(invoices: list):
    to = settings.vendor_email
    count = len(invoices)
    subject = f"[TechnoSport] {count} New AI-Generated Purchase Order{'s' if count > 1 else ''}"

    rows_html = "".join(
        f"<tr style='border-bottom:1px solid #f0f0f0'>"
        f"<td style='padding:8px 0'>{inv.get('product_name','')}</td>"
        f"<td style='padding:8px;text-align:center'>{', '.join(inv.get('sizes',[]))}</td>"
        f"<td style='padding:8px;text-align:center'>{inv.get('quantity',0)}</td>"
        f"<td style='padding:8px;text-align:center'>₹{inv.get('estimated_cost',0):,}</td>"
        f"<td style='padding:8px;text-align:center'><span style='color:{'#dc2626' if inv.get('priority')=='HIGH' else '#d97706'};font-weight:700'>{inv.get('priority','MEDIUM')}</span></td>"
        f"</tr>"
        for inv in invoices
    )
    text_rows = "\n".join(
        f"  {i+1}. {inv.get('product_name','')} | Sizes: {', '.join(inv.get('sizes',[]))} | "
        f"Qty: {inv.get('quantity',0)} | ₹{inv.get('estimated_cost',0):,} | {inv.get('priority','MEDIUM')} priority"
        for i, inv in enumerate(invoices)
    )

    html = f"""
<!DOCTYPE html><html><body style="font-family:'Helvetica Neue',Arial,sans-serif;background:#f8fafc;padding:0;margin:0">
<div style="max-width:600px;margin:32px auto;background:#fff;border-radius:16px;overflow:hidden;border:1px solid #e2e8f0">
  <div style="background:linear-gradient(135deg,#0f172a,#1e293b);padding:24px 32px">
    <p style="margin:0;font-size:18px;font-weight:700;color:#e2e8f0">TechnoSport Vendor Hub</p>
    <p style="margin:4px 0 0;font-size:13px;color:#94a3b8">{count} Purchase Order{'s' if count>1 else ''} — Action Required</p>
  </div>
  <div style="padding:28px 32px">
    <p style="font-size:14px;color:#0f172a">Our AI inventory agent has raised the following purchase orders:</p>
    <table style="width:100%;border-collapse:collapse">
      <thead><tr style="background:#f1f5f9">
        <th style="padding:8px 0;text-align:left;font-size:11px;color:#64748b;text-transform:uppercase">Product</th>
        <th style="padding:8px;text-align:center;font-size:11px;color:#64748b;text-transform:uppercase">Sizes</th>
        <th style="padding:8px;text-align:center;font-size:11px;color:#64748b;text-transform:uppercase">Qty</th>
        <th style="padding:8px;text-align:center;font-size:11px;color:#64748b;text-transform:uppercase">Cost (est.)</th>
        <th style="padding:8px;text-align:center;font-size:11px;color:#64748b;text-transform:uppercase">Priority</th>
      </tr></thead>
      <tbody>{rows_html}</tbody>
    </table>
    <p style="font-size:12px;color:#94a3b8;margin-top:20px">
      Please confirm receipt and expected delivery timeline via the Vendor Hub portal.
    </p>
  </div>
</div>
</body></html>
"""
    text = f"TechnoSport — {count} Purchase Order(s)\n\n{text_rows}\n\nPlease confirm receipt."
    await _send(to, subject, html, text)


# ── Support ticket notification ───────────────────────────────────────────────

async def send_ticket_notification_email(ticket: dict):
    to = settings.support_email
    tid = ticket.get("ticket_id", "")
    subject = f"[TechnoSport] New Support Ticket {tid}"
    summary = ticket.get("issue_summary", "")
    created = ticket.get("created_at", "")[:16].replace("T", " ")

    html = f"""
<div style="font-family:Arial,sans-serif;max-width:500px;margin:0 auto;padding:24px;background:#fff;border:1px solid #e2e8f0;border-radius:12px">
  <h2 style="color:#EF4444;margin:0 0 4px">New Support Ticket</h2>
  <p style="font-family:monospace;font-size:18px;font-weight:700;color:#0f172a">{tid}</p>
  <p style="color:#64748b;font-size:13px;margin:12px 0">Created: {created}</p>
  <div style="background:#fef2f2;border-radius:8px;padding:14px;border:1px solid #fecaca">
    <p style="font-size:13px;color:#374151;margin:0">{summary}</p>
  </div>
  <p style="font-size:12px;color:#94a3b8;margin-top:16px">Login to the Vendor Hub to manage this ticket.</p>
</div>
"""
    text = f"New Support Ticket: {tid}\nCreated: {created}\n\nSummary:\n{summary}"
    await _send(to, subject, html, text)


# ── Feedback email ────────────────────────────────────────────────────────────

async def send_feedback_email(feedback: dict):
    stars = "⭐" * feedback.get("rating", 0)
    to = settings.support_email
    subject = f"[TechnoSport] Customer Feedback — {stars} ({feedback.get('rating',0)}/5)"
    text = (
        f"Customer: {feedback.get('customer_name','Anonymous')}\n"
        f"Email: {feedback.get('customer_email','N/A')}\n"
        f"Order: {feedback.get('order_id','N/A')}\n"
        f"Rating: {stars}\n"
        f"Comment: {feedback.get('comment','')}"
    )
    html = f"<pre style='font-family:Arial,sans-serif'>{text}</pre>"
    await _send(to, subject, html, text)
