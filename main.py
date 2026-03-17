from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from database import connect_db, close_db
from routers import products, orders, inventory, agent, invoices, chatbot, feedback, tickets


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    yield
    await close_db()


app = FastAPI(
    title="Technosport POC API",
    description="Backend API for Technosport E-Commerce POC — Platform A, Platform B, and FAQ Chatbot",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow both frontend apps
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Platform A
        "http://localhost:3001",  # Platform B
        "http://localhost:3002",
        "*",  # For POC convenience
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(products.router)
app.include_router(orders.router)
app.include_router(inventory.router)
app.include_router(agent.router)
app.include_router(invoices.router)
app.include_router(chatbot.router)
app.include_router(feedback.router)
app.include_router(tickets.router)


@app.get("/", tags=["Health"])
async def root():
    return {
        "message": "Technosport POC API is running 🚀",
        "docs": "/docs",
        "platforms": {
            "platform_a": "http://localhost:3000",
            "platform_b": "http://localhost:3001",
        }
    }


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}
