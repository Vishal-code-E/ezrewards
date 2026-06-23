from fastapi import APIRouter, Depends, Query
import asyncpg

from app.dependencies.auth import require_admin
from app.database import get_db
from app.schemas.reports import BaseReportFilters, ExportFormat
from app.services.reports.wallet_service import get_wallet_report

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get(
    "/wallet",
    summary="Wallet Balance & Utilization Report",
    description="Current balance, burn rate, projected empty date, monthly trend. Admin only.",
)
async def wallet_report(
    current_user: dict               = Depends(require_admin),
    db:           asyncpg.Connection = Depends(get_db),
):
    filters = BaseReportFilters()

    return await get_wallet_report(
        current_user["workspace_id"], filters, db
    )