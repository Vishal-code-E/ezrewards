import asyncpg
import logging
import math
from datetime import datetime, timezone

from app.schemas.reports import (
    RedemptionReportFilters,
    RedemptionReportRow,
    RedemptionSummary,
    ReportMeta,
    RedemptionReportResponse,
)

logger = logging.getLogger(__name__)


async def get_redemption_report(
    workspace_id: str,
    filters: RedemptionReportFilters,
    db: asyncpg.Connection,
) -> RedemptionReportResponse:

    filters.validate_dates()

    # ── WHERE conditions ──────────────────────────────────────────────────────
    conditions = ["r.workspace_id = $1"]
    params: list = [workspace_id]
    idx = 2

    if filters.status:
        conditions.append(f"r.status = ${idx}")
        params.append(filters.status)
        idx += 1

    if filters.voucher_brand:
        conditions.append(f"v.brand_name = ${idx}")
        params.append(filters.voucher_brand)
        idx += 1

    if filters.department:
        conditions.append(f"wm.department = ${idx}")
        params.append(filters.department)
        idx += 1

    if filters.start_date:
        conditions.append(f"r.created_at >= ${idx}")
        params.append(filters.start_date)
        idx += 1

    if filters.end_date:
        conditions.append(
            f"r.created_at <= ${idx}::date + interval '1 day'"
        )
        params.append(filters.end_date)
        idx += 1

    where = " AND ".join(conditions)

    # ── Summary query ─────────────────────────────────────────────────────────
    summary_query = f"""
        SELECT
            COUNT(*)                                              AS total,
            COUNT(*) FILTER (WHERE r.status = 'Completed')       AS completed,
            COUNT(*) FILTER (WHERE r.status = 'Failed')          AS failed,
            COUNT(*) FILTER (WHERE r.status = 'Pending')         AS pending,
            COALESCE(
                SUM(r.voucher_value)
                FILTER (WHERE r.status = 'Completed'), 0
            )                                                     AS total_value
        FROM redemptions r
        JOIN workspace_members wm
             ON wm.id = r.user_id
             AND wm.is_deleted = FALSE
        JOIN vouchers v
             ON v.id = r.voucher_id
        WHERE {where}
    """

    # ── Rows query ────────────────────────────────────────────────────────────
    rows_query = f"""
        SELECT
            r.id::text,
            wm.display_name   AS employee_name,
            wm.department,
            v.brand_name      AS voucher_brand,
            r.voucher_value,
            r.points_spent,
            r.status,
            r.failure_reason,
            r.created_at
        FROM redemptions r
        JOIN workspace_members wm
             ON wm.id = r.user_id
             AND wm.is_deleted = FALSE
        JOIN vouchers v
             ON v.id = r.voucher_id
        WHERE {where}
        ORDER BY r.created_at DESC
        LIMIT  ${idx} OFFSET ${idx + 1}
    """

    rows_params = params + [filters.page_size, filters.offset]

    try:
        summary_row = await db.fetchrow(summary_query, *params)
        rows_result = await db.fetch(rows_query, *rows_params)
    except Exception as e:
        logger.error(
            f"Redemption report error | workspace={workspace_id} | {e}"
        )
        raise

    # ── Build summary ─────────────────────────────────────────────────────────
    total     = summary_row["total"]     or 0
    completed = summary_row["completed"] or 0

    summary = RedemptionSummary(
        total_redemptions = total,
        completed         = completed,
        failed            = summary_row["failed"]      or 0,
        pending           = summary_row["pending"]     or 0,
        total_value       = float(summary_row["total_value"] or 0),
        success_rate      = round(
            (completed / total * 100) if total > 0 else 0.0, 1
        ),
    )

    # ── Build rows ────────────────────────────────────────────────────────────
    rows = [
        RedemptionReportRow(
            id             = row["id"],
            employee_name  = row["employee_name"],
            department     = row["department"],
            voucher_brand  = row["voucher_brand"],
            voucher_value  = float(row["voucher_value"]),
            points_spent   = row["points_spent"],
            status         = row["status"],
            failure_reason = row["failure_reason"],
            created_at     = row["created_at"],
        )
        for row in rows_result
    ]

    meta = ReportMeta(
        total        = total,
        page         = filters.page,
        page_size    = filters.page_size,
        total_pages  = max(1, math.ceil(total / filters.page_size)),
        generated_at = datetime.now(timezone.utc),
    )

    logger.info(
        f"Redemption report | workspace={workspace_id} "
        f"| total={total} | success_rate={summary.success_rate}%"
    )

    return RedemptionReportResponse(data=rows, summary=summary, meta=meta)