from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from jwt import PyJWKClient
from app.config import settings
from app.database import get_db
import asyncpg

security = HTTPBearer()

JWKS_URL = f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json"
jwks_client = PyJWKClient(JWKS_URL)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: asyncpg.Connection = Depends(get_db),
) -> dict:
    """
    Validates the Supabase JWT and extracts user context.
    Returns: { user_id, workspace_id, role, email }

    Looks up workspace membership directly from DB instead of relying
    on JWT claims — more reliable with Supabase's new ES256 signing keys.
    """
    token = credentials.credentials

    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256", "HS256"],
            audience="authenticated",
            options={"verify_exp": True},
        )
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired. Please log in again.",
        )
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token.",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token.",
        )

    # Look up workspace membership directly from DB
    # More reliable than JWT claims with Supabase's new ES256 keys
    row = await db.fetchrow(
        """
        SELECT wm.workspace_id::text, wm.role
        FROM public.workspace_members wm
        WHERE wm.user_id = $1::uuid
          AND wm.status  = 'Active'
          AND wm.is_deleted = FALSE
        LIMIT 1
        """,
        user_id,
    )

    if not row:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No workspace associated with this account. Contact your Admin.",
        )

    return {
        "user_id":      user_id,
        "workspace_id": row["workspace_id"],
        "role":         row["role"],
        "email":        payload.get("email"),
    }


async def require_admin(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Reports are Admin-only. Attach this to any report router."""
    if current_user["role"] not in ("Admin", "RegionalHRLead"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin role required.",
        )
    return current_user


async def require_manager_or_above(
    current_user: dict = Depends(get_current_user),
) -> dict:
    if current_user["role"] not in ("Admin", "RegionalHRLead", "Manager"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Manager role or above required.",
        )
    return current_user