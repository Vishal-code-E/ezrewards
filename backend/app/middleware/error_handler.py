import uuid
import logging
import traceback
from datetime import datetime, timezone

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import asyncpg

from app.exceptions.base import EzRewardsException

logger = logging.getLogger(__name__)


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", f"req_{uuid.uuid4().hex[:8]}")


def _envelope(error_code: str, message: str, request_id: str, details=None) -> dict:
    return {
        "success":    False,
        "error_code": error_code,
        "message":    message,
        "details":    details,
        "request_id": request_id,
        "timestamp":  datetime.now(timezone.utc).isoformat(),
    }


async def ezrewards_exception_handler(request: Request, exc: EzRewardsException) -> JSONResponse:
    rid = _request_id(request)
    level = logger.error if exc.status_code >= 500 else logger.warning
    level(f"[{rid}] {exc.error_code}: {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content=_envelope(exc.error_code, exc.message, rid, exc.details),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    rid = _request_id(request)
    details = [{"field": ".".join(str(l) for l in e["loc"] if l != "body"), "message": e["msg"]} for e in exc.errors()]
    logger.warning(f"[{rid}] Validation error on {request.url.path}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=_envelope("FILTER_INVALID", "One or more parameters are invalid.", rid, details),
    )


async def database_exception_handler(request: Request, exc: asyncpg.PostgresError) -> JSONResponse:
    rid = _request_id(request)
    logger.error(f"[{rid}] DB error: {type(exc).__name__}: {exc}")
    code, msg, status_code = "DB_ERROR", "A database error occurred.", 500
    if isinstance(exc, asyncpg.UniqueViolationError):
        code, msg, status_code = "DB_DUPLICATE", "A record with this information already exists.", 409
    elif isinstance(exc, asyncpg.CheckViolationError):
        code, msg, status_code = "DB_CONSTRAINT", "This operation violates a business rule.", 409
    elif isinstance(exc, asyncpg.ForeignKeyViolationError):
        code, msg, status_code = "DB_REFERENCE", "Referenced record does not exist.", 409
    return JSONResponse(status_code=status_code, content=_envelope(code, msg, rid))


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    rid = _request_id(request)
    logger.critical(f"[{rid}] Unhandled: {str(exc)}\n{traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content=_envelope("INTERNAL_SERVER_ERROR", "An unexpected error occurred. Our team has been notified.", rid),
    )