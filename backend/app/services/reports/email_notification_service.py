import asyncpg
import logging
import math
from datetime import datetime, timezone

from app.schemas.reports import (
    EmailNotificationFilters,
    EmailNotificationRow,
    EmailNotificationSummary,
    ReportMeta,
    EmailNotificationResponse,
)

logger = logging.getLogger(__name__)


async def get_email_notification_report(
    workspace_id: str,
    filters: EmailNotificationFilters,
    db: asyncpg.Connection,
) -> EmailNotificationResponse:
    """
    Email Notification Report.

    Reads email_logs — the audit trail for every transactional
    email the system has sent. Delivery rate and open rate give
    HR admins visibility into whether employees are actually
    receiving and reading platform communications.
    """

    filters.validate_dates()

    # ── WHERE conditions ──────────────────────────────────────────────────────
    conditions = ["el.workspace_id = $1"]
    params: list = [workspace_id]
    idx = 2

    if filters.status:
        conditions.append(f"el.status = ${idx}")
        params.append(filters.status)
        idx += 1

    if filters.email_type:
        conditions.append(f"el.email_type = ${idx}")
        params.append(filters.email_type)
        idx += 1

    if filters.start_date:
        conditions.append(f"el.created_at >= ${idx}")
        params.append(filters.start_date)
        idx += 1

    if filters.end_date:
        conditions.append(
            f"el.created_at <= ${idx}::date + interval '1 day'"
        )
        params.append(filters.end_date)
        idx += 1

    where = " AND ".join(conditions)

    # ── Summary query ─────────────────────────────────────────────────────────
    summary_query = f"""
        SELECT
            COUNT(*)                                              AS total_sent,
            COUNT(*) FILTER (WHERE el.delivered_at IS NOT NULL)  AS delivered,
            COUNT(*) FILTER (WHERE el.opened_at IS NOT NULL)     AS opened,
            COUNT(*) FILTER (WHERE el.status = 'Bounced')        AS bounced,
            COUNT(*) FILTER (WHERE el.status = 'Failed')         AS failed
        FROM email_logs el
        WHERE {where}
    """

    # ── By-type breakdown ─────────────────────────────────────────────────────
    # Separate query — aggregate by email_type for the summary dict
    by_type_query = f"""
        SELECT
            el.email_type,
            COUNT(*)        AS count
        FROM email_logs el
        WHERE {where}
        GROUP BY el.email_type
        ORDER BY count DESC
    """

    # ── Rows query ────────────────────────────────────────────────────────────
    rows_query = f"""
        SELECT
            el.id::text,
            el.recipient_email,
            wm.display_name     AS recipient_name,
            el.email_type,
            el.subject,
            el.status,
            el.failure_reason,
            el.retry_count,
            el.sent_at,
            el.delivered_at,
            el.opened_at,
            el.created_at
        FROM email_logs el
        LEFT JOIN workspace_members wm
              ON wm.id = el.recipient_id
              AND wm.is_deleted = FALSE
        WHERE {where}
        ORDER BY el.created_at DESC
        LIMIT  ${idx} OFFSET ${idx + 1}
    """

    rows_params = params + [filters.page_size, filters.offset]

    try:
        summary_row  = await db.fetchrow(summary_query, *params)
        by_type_rows = await db.fetch(by_type_query, *params)
        rows_result  = await db.fetch(rows_query, *rows_params)
    except Exception as e:
        logger.error(
            f"Email notification report error | workspace={workspace_id} | {e}"
        )
        raise

    # ── Build summary ─────────────────────────────────────────────────────────
    total     = summary_row["total_sent"] or 0
    delivered = summary_row["delivered"]  or 0
    opened    = summary_row["opened"]     or 0

    summary = EmailNotificationSummary(
        total_sent    = total,
        delivered     = delivered,
        opened        = opened,
        bounced       = summary_row["bounced"] or 0,
        failed        = summary_row["failed"]  or 0,
        delivery_rate = round(
            (delivered / total * 100) if total > 0 else 0.0, 1
        ),
        open_rate     = round(
            (opened / delivered * 100) if delivered > 0 else 0.0, 1
        ),
        by_type       = {
            row["email_type"]: row["count"]
            for row in by_type_rows
        },
    )

    # ── Build rows ────────────────────────────────────────────────────────────
    rows = [
        EmailNotificationRow(
            id              = row["id"],
            recipient_email = row["recipient_email"],
            recipient_name  = row["recipient_name"],
            email_type      = row["email_type"],
            subject         = row["subject"],
            status          = row["status"],
            failure_reason  = row["failure_reason"],
            retry_count     = row["retry_count"],
            sent_at         = row["sent_at"],
            delivered_at    = row["delivered_at"],
            opened_at       = row["opened_at"],
            created_at      = row["created_at"],
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
        f"Email notification report | workspace={workspace_id} "
        f"| total={total} | delivery_rate={summary.delivery_rate}%"
    )

    return EmailNotificationResponse(data=rows, summary=summary, meta=meta)