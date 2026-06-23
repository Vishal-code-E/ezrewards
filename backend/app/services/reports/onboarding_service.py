import asyncpg
import logging
import math
from datetime import datetime, timezone

from app.schemas.reports import (
    OnboardingReportFilters,
    OnboardingReportRow,
    OnboardingSummary,
    ReportMeta,
    OnboardingReportResponse,
)

logger = logging.getLogger(__name__)


async def get_onboarding_report(
    workspace_id: str,
    filters: OnboardingReportFilters,
    db: asyncpg.Connection,
) -> OnboardingReportResponse:
    """
    Employee Onboarding Report.

    Joins invitations → workspace_members on email to show full
    invite-to-activation funnel per employee.

    days_to_activate = accepted_at - created_at (in days).
    Only populated when invite status is Accepted.
    """

    filters.validate_dates()

    # ── WHERE conditions ──────────────────────────────────────────────────────
    conditions = ["i.workspace_id = $1"]
    params: list = [workspace_id]
    idx = 2

    if filters.status:
        conditions.append(f"i.status = ${idx}")
        params.append(filters.status)
        idx += 1

    if filters.source:
        conditions.append(f"i.source = ${idx}")
        params.append(filters.source)
        idx += 1

    if filters.department:
        conditions.append(f"i.department = ${idx}")
        params.append(filters.department)
        idx += 1

    if filters.start_date:
        conditions.append(f"i.created_at >= ${idx}")
        params.append(filters.start_date)
        idx += 1

    if filters.end_date:
        conditions.append(
            f"i.created_at <= ${idx}::date + interval '1 day'"
        )
        params.append(filters.end_date)
        idx += 1

    where = " AND ".join(conditions)

    # ── Summary query ─────────────────────────────────────────────────────────
    summary_query = f"""
        SELECT
            COUNT(*)                                                  AS total_invited,
            COUNT(*) FILTER (WHERE i.status = 'Accepted')            AS total_active,
            COUNT(*) FILTER (WHERE i.status = 'Pending')             AS total_pending,
            COUNT(*) FILTER (WHERE i.status = 'Expired')             AS total_expired,
            COUNT(*) FILTER (WHERE i.status = 'Cancelled')           AS total_cancelled,
            -- avg days from invite sent to invite accepted
            -- EXTRACT(EPOCH) gives seconds, divide by 86400 for days
            AVG(
                EXTRACT(EPOCH FROM (i.accepted_at - i.created_at))
                / 86400.0
            ) FILTER (WHERE i.accepted_at IS NOT NULL)                AS avg_days_to_activate
        FROM invitations i
        WHERE {where}
    """

    # ── Rows query ────────────────────────────────────────────────────────────
    # LEFT JOIN workspace_members — member row may not exist yet
    # (pending/expired invites have no member row)
    rows_query = f"""
        SELECT
            i.email,
            i.display_name,
            i.department,
            i.role,
            i.status                                        AS invite_status,
            wm.status                                       AS member_status,
            i.source,
            i.invite_count,
            i.created_at                                    AS invited_at,
            i.expires_at,
            wm.activated_at,
            CASE
                WHEN i.accepted_at IS NOT NULL THEN
                    EXTRACT(EPOCH FROM (i.accepted_at - i.created_at))
                    / 86400.0
                ELSE NULL
            END::int                                        AS days_to_activate
        FROM invitations i
        LEFT JOIN workspace_members wm
              ON wm.email        = i.email
              AND wm.workspace_id = i.workspace_id
              AND wm.is_deleted   = FALSE
        WHERE {where}
        ORDER BY i.created_at DESC
        LIMIT  ${idx} OFFSET ${idx + 1}
    """

    rows_params = params + [filters.page_size, filters.offset]

    try:
        summary_row = await db.fetchrow(summary_query, *params)
        rows_result = await db.fetch(rows_query, *rows_params)
    except Exception as e:
        logger.error(
            f"Onboarding report error | workspace={workspace_id} | {e}"
        )
        raise

    # ── Build summary ─────────────────────────────────────────────────────────
    total   = summary_row["total_invited"] or 0
    active  = summary_row["total_active"]  or 0
    avg_days = summary_row["avg_days_to_activate"]

    summary = OnboardingSummary(
        total_invited        = total,
        total_active         = active,
        total_pending        = summary_row["total_pending"]   or 0,
        total_expired        = summary_row["total_expired"]   or 0,
        total_cancelled      = summary_row["total_cancelled"] or 0,
        activation_rate      = round(
            (active / total * 100) if total > 0 else 0.0, 1
        ),
        avg_days_to_activate = round(float(avg_days), 1) if avg_days else None,
    )

    # ── Build rows ────────────────────────────────────────────────────────────
    rows = [
        OnboardingReportRow(
            email            = row["email"],
            display_name     = row["display_name"],
            department       = row["department"],
            role             = row["role"],
            invite_status    = row["invite_status"],
            member_status    = row["member_status"],
            source           = row["source"],
            invite_count     = row["invite_count"],
            invited_at       = row["invited_at"],
            expires_at       = row["expires_at"],
            activated_at     = row["activated_at"],
            days_to_activate = row["days_to_activate"],
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
        f"Onboarding report | workspace={workspace_id} "
        f"| total={total} | activation_rate={summary.activation_rate}%"
    )

    return OnboardingReportResponse(data=rows, summary=summary, meta=meta)