import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
import asyncpg

from app.config import settings
from app.database import init_pool, close_pool
from app.middleware.error_handler import (
    ezrewards_exception_handler,
    validation_exception_handler,
    database_exception_handler,
    generic_exception_handler,
)
from app.exceptions.base import EzRewardsException
from app.routers.reports import recognition
from app.routers.reports import invitations
from app.routers.reports import recognition_given
from app.routers.reports import recognition_received
from app.routers.reports import seat_usage
from app.routers.reports import redemptions
from app.routers.reports import wallet
from app.routers.reports import wallet_transactions
from app.routers.reports import payments
from app.routers.reports import onboarding
from app.routers.reports import subscription
from app.routers.reports import email_notifications
from app.routers import chat 

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────
    logger.info("Initialising database pool...")
    await init_pool()
    logger.info("Database pool ready.")
    yield
    # ── Shutdown ─────────────────────────────
    logger.info("Closing database pool...")
    await close_pool()
    logger.info("Shutdown complete.")


app = FastAPI(
    title="EzRewards API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)

# ── Exception handlers ────────────────────────────────────────────────────────
app.add_exception_handler(EzRewardsException,       ezrewards_exception_handler)
app.add_exception_handler(RequestValidationError,   validation_exception_handler)
app.add_exception_handler(asyncpg.PostgresError,    database_exception_handler)
app.add_exception_handler(Exception,                generic_exception_handler)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(recognition.router, prefix="/api/reports", tags=["Reports"])
app.include_router(invitations.router, prefix="/api/reports", tags=["Reports"])
app.include_router(recognition_given.router, prefix="/api/reports", tags=["Reports"])
app.include_router(recognition_received.router, prefix="/api/reports", tags=["Reports"])
app.include_router(seat_usage.router, prefix="/api/reports", tags=["Reports"])
app.include_router(redemptions.router, prefix="/api/reports", tags=["Reports"])
app.include_router(wallet.router, prefix="/api/reports", tags=["Reports"])
app.include_router(wallet_transactions.router, prefix="/api/reports", tags=["Reports"])
app.include_router(payments.router, prefix="/api/reports", tags=["Reports"])
app.include_router(onboarding.router, prefix="/api/reports", tags=["Reports"])
app.include_router(subscription.router, prefix="/api/reports", tags=["Reports"])
app.include_router(email_notifications.router, prefix="/api/reports", tags=["Reports"])
app.include_router(chat.router, prefix="/api", tags=["Chat"])



@app.get("/health", tags=["Health"])
async def health():
    return {
        "status":      "ok",
        "environment": settings.ENVIRONMENT,
        "version":     "1.0.0",
    }

