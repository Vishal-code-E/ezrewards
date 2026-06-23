from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from app.config import settings


security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """
    Validates the Supabase JWT and extracts user context.
    Returns: { user_id, workspace_id, role, email }

    This is the identity layer — answers: WHO are you?
    RBAC (what can you do?) is handled by require_admin/require_manager below.
    """
    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",   # Supabase sets aud = "authenticated"
            options={"verify_exp": True},
        )
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired. Please log in again.",
        )
    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token.",
        )

    workspace_id = payload.get("workspace_id")
    user_role    = payload.get("user_role", "Employee")

    if not workspace_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No workspace associated with this account. Contact your Admin.",
        )

    return {
        "user_id":      payload["sub"],
        "workspace_id": workspace_id,
        "role":         user_role,
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