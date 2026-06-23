import asyncpg
import asyncio
import logging
from typing import Optional
from datetime import date

from app.schemas.reports import (
    InvitationReportFilters,
    InvitationReportRow,
    InvitationSummary,
    ReportMeta,
    InvitationReportResponse,
)
from app.exceptions.base import DatabaseTimeoutException

logger = logging.getLogger(__name__)


async def get_invitation_report(
    workspace_id: str,
    filters: InvitationReportFilters,
    db: asyncpg.Connection,
) -> InvitationReportResponse:
    """
    Invitation Status Report — Phase 1 MVP.

    Returns:
      - Summary: total, accepted, pending, expired, cancelled, activation_rate
      - Rows:    paginated invitation records with inviter name
    """

    # Validate date range before hitting DB
    filters.validate_dates()

    # ── Build dynamic WHERE conditions ────────────────────────────────────────
    # workspace_id is ALWAYS first — never skip this
    conditions = ["i.workspace_id = $1"]
    params: list = [workspace_id]
    param_index = 2   # $1 is taken by workspace_id

    if filters.status:
        conditions.append(f"i.status = ${param_index}")
        params.append(filters.status)
        param_index += 1

    if filters.source:
        conditions.append(f"i.source = ${param_index}")
        params.append(filters.source)
        param_index += 1

    if filters.department:
        conditions.append(f"i.department = ${param_index}")
        params.append(filters.department)
        param_index += 1

    if filters.start_date:
        conditions.append(f"i.created_at >= ${param_index}")
        params.append(filters.start_date)
        param_index += 1

    if filters.end_date:
        conditions.append(f"i.created_at <= ${param_index}::date + interval '1 day'")
        params.append(filters.end_date)
        param_index += 1

    where_clause = " AND ".join(conditions)

    # ── Run summary and rows concurrently ─────────────────────────────────────
    summary_query = f"""
        SELECT
            COUNT(*)                                              AS total,
            COUNT(*) FILTER (WHERE i.status = 'Accepted')        AS accepted,
            COUNT(*) FILTER (WHERE i.status = 'Pending')         AS pending,
            COUNT(*) FILTER (WHERE i.status = 'Expired')         AS expired,
            COUNT(*) FILTER (WHERE i.status = 'Cancelled')       AS cancelled
        FROM invitations i
        LEFT JOIN workspace_members wm
            ON wm.email = i.email
            AND wm.workspace_id = i.workspace_id
            AND wm.is_deleted = FALSE
        WHERE {where_clause}
    """

    rows_query = f"""
        SELECT
            i.id::text,
            i.email,
            i.display_name,
            i.department,
            i.role,
            i.status,
            i.source,
            i.invite_count,
            inviter.display_name      AS invited_by,
            i.created_at,
            i.expires_at,
            i.accepted_at
        FROM invitations i
        LEFT JOIN workspace_members inviter
            ON inviter.id = i.invited_by
            AND inviter.is_deleted = FALSE
        LEFT JOIN workspace_members wm
            ON wm.email = i.email
            AND wm.workspace_id = i.workspace_id
            AND wm.is_deleted = FALSE
        WHERE {where_clause}
        ORDER BY i.created_at DESC
        LIMIT ${param_index} OFFSET ${param_index + 1}
    """

    rows_params = params + [filters.page_size, filters.offset]

    try:
        async with asyncio.timeout(10.0):
            summary_result = await db.fetchrow(summary_query, *params)
            rows_result    = await db.fetch(rows_query, *rows_params)

    except asyncio.TimeoutError:
        logger.error(f"Invitation report query timed out for workspace {workspace_id}")
        raise DatabaseTimeoutException()

    # ── Build summary ─────────────────────────────────────────────────────────
    total    = summary_result["total"]    or 0
    accepted = summary_result["accepted"] or 0

    summary = InvitationSummary(
        total           = total,
        accepted        = accepted,
        pending         = summary_result["pending"]   or 0,
        expired         = summary_result["expired"]   or 0,
        cancelled       = summary_result["cancelled"] or 0,
        activation_rate = round((accepted / total * 100), 1) if total > 0 else 0.0,
    )

    # ── Build rows ────────────────────────────────────────────────────────────
    rows = [
        InvitationReportRow(
            id           = row["id"],
            email        = row["email"],
            display_name = row["display_name"],
            department   = row["department"],
            role         = row["role"],
            status       = row["status"],
            source       = row["source"],
            invite_count = row["invite_count"],
            invited_by   = row["invited_by"],
            created_at   = row["created_at"],
            expires_at   = row["expires_at"],
            accepted_at  = row["accepted_at"],
        )
        for row in rows_result
    ]

    # ── Build meta ────────────────────────────────────────────────────────────
    from datetime import datetime, timezone
    import math

    meta = ReportMeta(
        total       = total,
        page        = filters.page,
        page_size   = filters.page_size,
        total_pages = max(1, math.ceil(total / filters.page_size)),
        generated_at = datetime.now(timezone.utc),
    )

    logger.info(
        f"Invitation report generated | workspace={workspace_id} "
        f"| total={total} | page={filters.page}"
    )

    return InvitationReportResponse(
        data    = rows,
        summary = summary,
        meta    = meta,
    )