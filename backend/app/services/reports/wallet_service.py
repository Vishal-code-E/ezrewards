import asyncpg
import logging
import math
from datetime import datetime, timezone, timedelta
from typing import Optional

from app.schemas.reports import (
    BaseReportFilters,
    WalletReportRow,
    WalletSummary,
    ReportMeta,
    WalletReportResponse,
)

logger = logging.getLogger(__name__)


async def get_wallet_report(
    workspace_id: str,
    filters: BaseReportFilters,
    db: asyncpg.Connection,
) -> WalletReportResponse:
    """
    Wallet Balance & Utilization Report.

    Summary: current balance, burn rate, projected empty date.
    Rows:    monthly credit vs debit trend (last 6 months by default).
    """

    # ── Wallet summary — one row per workspace ────────────────────────────────
    wallet_query = """
        SELECT
            balance,
            total_recharged,
            total_consumed,
            low_balance_threshold
        FROM wallets
        WHERE workspace_id = $1
    """

    # ── Monthly trend — group transactions by month ───────────────────────────
    # TO_CHAR formats the timestamp into "YYYY-MM" for grouping
    trend_query = """
        SELECT
            TO_CHAR(created_at, 'YYYY-MM')              AS period,
            COALESCE(SUM(amount) FILTER (
                WHERE type = 'Credit'
            ), 0)                                        AS total_credited,
            COALESCE(SUM(amount) FILTER (
                WHERE type = 'Debit'
            ), 0)                                        AS total_debited
        FROM wallet_transactions
        WHERE workspace_id = $1
          AND status       = 'Completed'
          AND created_at  >= NOW() - INTERVAL '6 months'
        GROUP BY TO_CHAR(created_at, 'YYYY-MM')
        ORDER BY period ASC
    """

    # ── Avg monthly spend — last 3 months of debits ───────────────────────────
    # Used to project burn rate — more recent window = more accurate projection
    avg_spend_query = """
        SELECT
            COALESCE(SUM(amount), 0)                                AS total_debited_3m,
            COUNT(DISTINCT TO_CHAR(created_at, 'YYYY-MM'))          AS active_months
        FROM wallet_transactions
        WHERE workspace_id = $1
          AND type         = 'Debit'
          AND status       = 'Completed'
          AND created_at  >= NOW() - INTERVAL '3 months'
    """

    try:
        wallet_row    = await db.fetchrow(wallet_query, workspace_id)
        trend_result  = await db.fetch(trend_query, workspace_id)
        spend_row     = await db.fetchrow(avg_spend_query, workspace_id)
    except Exception as e:
        logger.error(f"Wallet report error | workspace={workspace_id} | {e}")
        raise

    # ── Build summary ─────────────────────────────────────────────────────────
    if not wallet_row:
        # Workspace exists but wallet not yet created
        balance   = 0.0
        recharged = 0.0
        consumed  = 0.0
        threshold = 10000.0
    else:
        balance   = float(wallet_row["balance"])
        recharged = float(wallet_row["total_recharged"])
        consumed  = float(wallet_row["total_consumed"])
        threshold = float(wallet_row["low_balance_threshold"])

    # Avg monthly spend from last 3 months — divide by months with actual activity
    total_3m       = float(spend_row["total_debited_3m"] or 0)
    active_months  = spend_row["active_months"] or 0
    avg_monthly    = round(total_3m / active_months, 2) if active_months > 0 else 0.0

    # Burn rate projection — how many days until balance hits zero
    daily_spend    = avg_monthly / 30 if avg_monthly > 0 else 0

    if daily_spend > 0 and balance > 0:
        days_left           = math.floor(balance / daily_spend)
        projected_empty     = (
            datetime.now(timezone.utc) + timedelta(days=days_left)
        ).strftime("%d %b %Y")
    else:
        days_left           = None
        projected_empty     = None

    summary = WalletSummary(
        current_balance      = balance,
        total_recharged      = recharged,
        total_consumed       = consumed,
        avg_monthly_spend    = avg_monthly,
        days_until_empty     = days_left,
        projected_empty_date = projected_empty,
        low_balance_alert    = balance < threshold,
    )

    # ── Build rows — monthly trend ────────────────────────────────────────────
    rows = [
        WalletReportRow(
            period         = row["period"],
            total_credited = float(row["total_credited"]),
            total_debited  = float(row["total_debited"]),
            net            = float(row["total_credited"]) - float(row["total_debited"]),
        )
        for row in trend_result
    ]

    meta = ReportMeta(
        total        = len(rows),
        page         = 1,
        page_size    = len(rows) or 1,
        total_pages  = 1,
        generated_at = datetime.now(timezone.utc),
    )

    logger.info(
        f"Wallet report | workspace={workspace_id} "
        f"| balance={balance} | days_left={days_left}"
    )

    return WalletReportResponse(data=rows, summary=summary, meta=meta)