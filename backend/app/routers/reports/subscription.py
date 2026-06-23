from fastapi import APIRouter, Depends
import asyncpg

from app.dependencies.auth import require_admin
from app.database import get_db
from app.services.reports.subscription_service import (
    get_subscription_billing_report,
)

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get(
    "/subscription",
    summary="Subscription Billing Report",
    description="Current subscription state, seat usage, and payment summary. Admin only.",
)
async def subscription_billing_report(
    current_user: dict               = Depends(require_admin),
    db:           asyncpg.Connection = Depends(get_db),
):
    return await get_subscription_billing_report(
        current_user["workspace_id"], db
    )
