import asyncpg
import logging
import math
from datetime import datetime, timezone

from app.schemas.reports import (
    BaseReportFilters,
    SeatUsageReportRow,
    SeatUsageSummary,
    ReportMeta,
    SeatUsageResponse,
)

logger = logging.getLogger(__name__)


async def get_seat_usage_report(
    workspace_id: str,
    filters: BaseReportFilters,
    db: asyncpg.Connection,
) -> SeatUsageResponse:
    """
    Active Seat Usage Report.

    Summary: purchased seats vs active users, utilization %, available seats.
    Rows:    per-department breakdown of active / inactive / invited counts.
    """

    # ── Summary query ─────────────────────────────────────────────────────────
    # purchased_seats lives in subscriptions (one row per workspace)
    # active user count lives in workspace_members
    summary_query = """
        SELECT
            COALESCE(MAX(s.purchased_seats), 0)                     AS purchased_seats,

            COUNT(*) FILTER (
                WHERE wm.status = 'Active'
                AND   wm.is_deleted = FALSE
            )                                                       AS active_users,

            COUNT(*) FILTER (
                WHERE wm.status IN ('Invited')
                AND   wm.is_deleted = FALSE
            )                                                       AS pending_invites

        FROM workspace_members wm
        LEFT JOIN subscriptions s
              ON s.workspace_id = wm.workspace_id
        WHERE wm.workspace_id = $1
    """

    # ── Rows query — department breakdown ─────────────────────────────────────
    # One row per department showing status split
    rows_query = """
        SELECT
            department,
            COUNT(*) FILTER (WHERE status = 'Active'
                             AND   is_deleted = FALSE) AS active_users,
            COUNT(*) FILTER (WHERE status = 'Inactive'
                             AND   is_deleted = FALSE) AS inactive_users,
            COUNT(*) FILTER (WHERE status = 'Invited'
                             AND   is_deleted = FALSE) AS invited_users
        FROM workspace_members
        WHERE workspace_id = $1
          AND is_deleted   = FALSE
        GROUP BY department
        ORDER BY active_users DESC
        LIMIT  $2 OFFSET $3
    """

    try:
        summary_row = await db.fetchrow(summary_query, workspace_id)
        rows_result = await db.fetch(
            rows_query, workspace_id, filters.page_size, filters.offset
        )
    except Exception as e:
        logger.error(f"Seat usage report error | workspace={workspace_id} | {e}")
        raise

    # ── Build summary ─────────────────────────────────────────────────────────
    purchased = summary_row["purchased_seats"] or 0
    active    = summary_row["active_users"]    or 0
    pending   = summary_row["pending_invites"] or 0
    available = max(0, purchased - active)

    summary = SeatUsageSummary(
        purchased_seats = purchased,
        active_users    = active,
        available_seats = available,
        pending_invites = pending,
        utilization_pct = round(
            (active / purchased * 100) if purchased > 0 else 0.0, 1
        ),
    )

    # ── Build rows ────────────────────────────────────────────────────────────
    rows = [
        SeatUsageReportRow(
            department     = row["department"],
            active_users   = row["active_users"],
            inactive_users = row["inactive_users"],
            invited_users  = row["invited_users"],
        )
        for row in rows_result
    ]

    # Total for pagination = distinct departments
    total_depts_query = """
        SELECT COUNT(DISTINCT department)
        FROM   workspace_members
        WHERE  workspace_id = $1
          AND  is_deleted   = FALSE
    """
    total_depts = await db.fetchval(total_depts_query, workspace_id) or 0

    meta = ReportMeta(
        total        = total_depts,
        page         = filters.page,
        page_size    = filters.page_size,
        total_pages  = max(1, math.ceil(total_depts / filters.page_size)),
        generated_at = datetime.now(timezone.utc),
    )

    logger.info(
        f"Seat usage report | workspace={workspace_id} "
        f"| purchased={purchased} | active={active} | utilization={summary.utilization_pct}%"
    )

    return SeatUsageResponse(data=rows, summary=summary, meta=meta)