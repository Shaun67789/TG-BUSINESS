"""
FastAPI Admin Panel — main application.
Integrates bot webhook + admin web routes.
"""
from __future__ import annotations
import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from telegram import Update

from bot.config import BOT_TOKEN, WEBHOOK_PATH, SECRET_KEY
from bot.main import build_application, setup_webhook, get_app

from admin.routes import dashboard, orders, users, settings, referrals, broadcast, stats, auth

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

bot_app = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global bot_app
    logger.info("Starting bot application...")
    bot_app = build_application()
    await bot_app.initialize()
    await bot_app.start()
    await setup_webhook(bot_app)
    logger.info("Bot started and webhook configured.")
    yield
    logger.info("Shutting down bot...")
    await bot_app.stop()
    await bot_app.shutdown()


app = FastAPI(title="TG Business Admin", lifespan=lifespan)

# ── Middleware ──────────────────────────────────────────────────
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# ── Static & Templates ─────────────────────────────────────────
app.mount("/static", StaticFiles(directory="admin/static"), name="static")
templates = Jinja2Templates(directory="admin/templates")

# ── Webhook endpoint ───────────────────────────────────────────
@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, get_app().bot)
    await get_app().process_update(update)
    return JSONResponse({"ok": True})


# ── Health check ───────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok", "bot": "running"}


# ── Admin routes ───────────────────────────────────────────────
app.include_router(auth.router,       prefix="/admin",          tags=["Auth"])
app.include_router(dashboard.router,  prefix="/admin",          tags=["Dashboard"])
app.include_router(orders.router,     prefix="/admin/orders",   tags=["Orders"])
app.include_router(users.router,      prefix="/admin/users",    tags=["Users"])
app.include_router(settings.router,   prefix="/admin/settings", tags=["Settings"])
app.include_router(referrals.router,  prefix="/admin/referrals",tags=["Referrals"])
app.include_router(broadcast.router,  prefix="/admin/broadcast",tags=["Broadcast"])
app.include_router(stats.router,      prefix="/admin/stats",    tags=["Stats"])
