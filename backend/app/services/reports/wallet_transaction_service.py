import asyncpg
import logging
import math
from datetime import datetime, timezone

from app.schemas.reports import (
    WalletTransactionFilters,
    WalletTransactionRow,
    WalletTransactionSummary,
    ReportMeta,
    WalletTransactionResponse,
)

logger = logging.getLogger(__name__)


async def get_wallet_transaction_report(
    workspace_id: str,
    filters: WalletTransactionFilters,
    db: asyncpg.Connection,
) -> WalletTransactionResponse:
    """
    Wallet Transaction Report — full ledger view.

    Append-only read: every credit and debit in chronological order.
    Running balance_after snapshot captured at write time — no recomputation needed.
    """

    filters.validate_dates()

    # ── WHERE conditions ──────────────────────────────────────────────────────
    conditions = ["wt.workspace_id = $1"]
    params: list = [workspace_id]
    idx = 2

    if filters.type:
        conditions.append(f"wt.type = ${idx}")
        params.append(filters.type)
        idx += 1

    if filters.status:
        conditions.append(f"wt.status = ${idx}")
        params.append(filters.status)
        idx += 1

    if filters.start_date:
        conditions.append(f"wt.created_at >= ${idx}")
        params.append(filters.start_date)
        idx += 1

    if filters.end_date:
        conditions.append(
            f"wt.created_at <= ${idx}::date + interval '1 day'"
        )
        params.append(filters.end_date)
        idx += 1

    where = " AND ".join(conditions)

    # ── Summary query ─────────────────────────────────────────────────────────
    summary_query = f"""
        SELECT
            COALESCE(SUM(wt.amount) FILTER (
                WHERE wt.type = 'Credit' AND wt.status = 'Completed'
            ), 0)               AS total_credits,
            COALESCE(SUM(wt.amount) FILTER (
                WHERE wt.type = 'Debit' AND wt.status = 'Completed'
            ), 0)               AS total_debits,
            COUNT(*)            AS total_entries
        FROM wallet_transactions wt
        WHERE {where}
    """

    # ── Rows query ────────────────────────────────────────────────────────────
    # LEFT JOIN workspace_members to get the name of who initiated the transaction
    # NULL is fine — system-generated transactions have no created_by
    rows_query = f"""
        SELECT
            wt.id::text,
            wt.type,
            wt.amount,
            wt.balance_after,
            wt.payment_method,
            wt.status,
            wm.display_name     AS created_by,
            wt.created_at
        FROM wallet_transactions wt
        LEFT JOIN workspace_members wm
              ON wm.id = wt.created_by
              AND wm.is_deleted = FALSE
        WHERE {where}
        ORDER BY wt.created_at DESC
        LIMIT  ${idx} OFFSET ${idx + 1}
    """

    rows_params = params + [filters.page_size, filters.offset]

    try:
        summary_row = await db.fetchrow(summary_query, *params)
        rows_result = await db.fetch(rows_query, *rows_params)
    except Exception as e:
        logger.error(
            f"Wallet transaction report error | workspace={workspace_id} | {e}"
        )
        raise

    # ── Build summary ─────────────────────────────────────────────────────────
    total_credits = float(summary_row["total_credits"] or 0)
    total_debits  = float(summary_row["total_debits"]  or 0)
    total_entries = summary_row["total_entries"] or 0

    summary = WalletTransactionSummary(
        total_credits = total_credits,
        total_debits  = total_debits,
        net_movement  = round(total_credits - total_debits, 2),
        total_entries = total_entries,
    )

    # ── Build rows ────────────────────────────────────────────────────────────
    rows = [
        WalletTransactionRow(
            id             = row["id"],
            type           = row["type"],
            amount         = float(row["amount"]),
            balance_after  = float(row["balance_after"]),
            payment_method = row["payment_method"],
            status         = row["status"],
            created_by     = row["created_by"],
            created_at     = row["created_at"],
        )
        for row in rows_result
    ]

    meta = ReportMeta(
        total        = total_entries,
        page         = filters.page,
        page_size    = filters.page_size,
        total_pages  = max(1, math.ceil(total_entries / filters.page_size)),
        generated_at = datetime.now(timezone.utc),
    )

    logger.info(
        f"Wallet transaction report | workspace={workspace_id} "
        f"| entries={total_entries} | net={summary.net_movement}"
    )

    return WalletTransactionResponse(data=rows, summary=summary, meta=meta)