import asyncpg
import asyncio
import logging
import math
from datetime import datetime, timezone
from app.schemas.reports import (
    RecognitionReportFilters,
    RecognitionReportRow,
    RecognitionSummary,
    ReportMeta,
    RecognitionReportResponse,
)
from app.exceptions.base import DatabaseTimeoutException

logger = logging.getLogger(__name__)


async def get_recognition_activity_report(
    workspace_id: str,
    filters: RecognitionReportFilters,
    db: asyncpg.Connection,
) -> RecognitionReportResponse:

    filters.validate_dates()

    # ── Build shared WHERE conditions ─────────────────────────────────────────
    # workspace_id is always $1 — first condition, never skipped
    conditions = ["r.workspace_id = $1"]
    params: list = [workspace_id]
    idx = 2

    if filters.start_date:
        conditions.append(f"r.created_at >= ${idx}")
        params.append(filters.start_date)
        idx += 1

    if filters.end_date:
        conditions.append(f"r.created_at <= ${idx}::date + interval '1 day'")
        params.append(filters.end_date)
        idx += 1

    if filters.badge_id:
        conditions.append(f"r.badge_id = ${idx}::uuid")
        params.append(filters.badge_id)
        idx += 1

    if filters.sender_id:
        conditions.append(f"r.sender_id = ${idx}::uuid")
        params.append(filters.sender_id)
        idx += 1

    if filters.recipient_id:
        conditions.append(f"r.recipient_id = ${idx}::uuid")
        params.append(filters.recipient_id)
        idx += 1

    if filters.department:
        # Filter by sender OR recipient department
        conditions.append(
            f"(sender.department = ${idx} OR recipient.department = ${idx})"
        )
        params.append(filters.department)
        idx += 1

    where = " AND ".join(conditions)

    # ── Summary query ─────────────────────────────────────────────────────────
    # Participation: employees who gave OR received / total active employees
    # UNION deduplicates — someone who both gave and received counts once
    summary_query = f"""
        WITH active_members AS (
            SELECT COUNT(*) AS total
            FROM   workspace_members
            WHERE  workspace_id = $1
              AND  status     = 'Active'
              AND  is_deleted = FALSE
        ),
        participants AS (
            SELECT sender_id    AS member_id
            FROM   recognitions r
            JOIN   workspace_members sender
                   ON sender.id = r.sender_id AND sender.is_deleted = FALSE
            JOIN   workspace_members recipient
                   ON recipient.id = r.recipient_id AND recipient.is_deleted = FALSE
            WHERE  {where}

            UNION

            SELECT recipient_id AS member_id
            FROM   recognitions r
            JOIN   workspace_members sender
                   ON sender.id = r.sender_id AND sender.is_deleted = FALSE
            JOIN   workspace_members recipient
                   ON recipient.id = r.recipient_id AND recipient.is_deleted = FALSE
            WHERE  {where}
        ),
        top_badge AS (
            SELECT b.name
            FROM   recognitions r
            JOIN   workspace_members sender
                   ON sender.id = r.sender_id AND sender.is_deleted = FALSE
            JOIN   workspace_members recipient
                   ON recipient.id = r.recipient_id AND recipient.is_deleted = FALSE
            JOIN   badges b ON b.id = r.badge_id
            WHERE  {where}
            GROUP  BY b.name
            ORDER  BY COUNT(*) DESC
            LIMIT  1
        )
        SELECT
            -- Core counts
            (SELECT COUNT(*) FROM recognitions r
             JOIN workspace_members sender
                  ON sender.id = r.sender_id AND sender.is_deleted = FALSE
             JOIN workspace_members recipient
                  ON recipient.id = r.recipient_id AND recipient.is_deleted = FALSE
             WHERE {where})                                        AS total_recognitions,

            (SELECT COUNT(DISTINCT sender_id) FROM recognitions r
             JOIN workspace_members sender
                  ON sender.id = r.sender_id AND sender.is_deleted = FALSE
             JOIN workspace_members recipient
                  ON recipient.id = r.recipient_id AND recipient.is_deleted = FALSE
             WHERE {where})                                        AS unique_senders,

            (SELECT COUNT(DISTINCT recipient_id) FROM recognitions r
             JOIN workspace_members sender
                  ON sender.id = r.sender_id AND sender.is_deleted = FALSE
             JOIN workspace_members recipient
                  ON recipient.id = r.recipient_id AND recipient.is_deleted = FALSE
             WHERE {where})                                        AS unique_recipients,

            -- Participation rate
            (SELECT COUNT(*) FROM participants)                    AS participant_count,
            (SELECT total FROM active_members)                     AS active_count,

            -- Top badge
            (SELECT name FROM top_badge)                           AS top_badge
    """

    # ── Rows query ────────────────────────────────────────────────────────────
    # Two aliases for workspace_members — this is the key pattern
    rows_query = f"""
        SELECT
            r.id::text,
            sender.display_name                  AS sender_name,
            sender.department                    AS sender_department,
            recipient.display_name               AS recipient_name,
            recipient.department                 AS recipient_dept,
            b.name                               AS badge_name,
            b.color                              AS badge_color,
            r.message,
            r.created_at
        FROM   recognitions r
        JOIN   workspace_members sender
               ON sender.id = r.sender_id
               AND sender.is_deleted = FALSE
        JOIN   workspace_members recipient
               ON recipient.id = r.recipient_id
               AND recipient.is_deleted = FALSE
        LEFT JOIN badges b
               ON b.id = r.badge_id
        WHERE  {where}
        ORDER  BY r.created_at DESC
        LIMIT  ${idx} OFFSET ${idx + 1}
    """

    rows_params = params + [filters.page_size, filters.offset]

    try:
        async with asyncio.timeout(10.0):
            summary_row = await db.fetchrow(summary_query, *params)
            rows_result = await db.fetch(rows_query, *rows_params)
    except asyncio.TimeoutError:
        logger.error(f"Recognition report timed out | workspace={workspace_id}")
        raise DatabaseTimeoutException()

    # ── Build summary ─────────────────────────────────────────────────────────
    total       = summary_row["total_recognitions"] or 0
    active      = summary_row["active_count"]       or 0
    participants = summary_row["participant_count"] or 0

    participation_rate = round(
        (participants / active * 100) if active > 0 else 0.0, 1
    )
    avg_per_user = round(
        (total / active) if active > 0 else 0.0, 2
    )

    summary = RecognitionSummary(
        total_recognitions  = total,
        unique_senders      = summary_row["unique_senders"]    or 0,
        unique_recipients   = summary_row["unique_recipients"] or 0,
        participation_rate  = participation_rate,
        top_badge           = summary_row["top_badge"],
        avg_per_active_user = avg_per_user,
    )

    # ── Build rows ────────────────────────────────────────────────────────────
    rows = [
        RecognitionReportRow(
            id                = row["id"],
            sender_name       = row["sender_name"],
            sender_department = row["sender_department"],
            recipient_name    = row["recipient_name"],
            recipient_dept    = row["recipient_dept"],
            badge_name        = row["badge_name"],
            badge_color       = row["badge_color"],
            message           = row["message"],
            created_at        = row["created_at"],
        )
        for row in rows_result
    ]

    # ── Build meta ────────────────────────────────────────────────────────────
    meta = ReportMeta(
        total        = total,
        page         = filters.page,
        page_size    = filters.page_size,
        total_pages  = max(1, math.ceil(total / filters.page_size)),
        generated_at = datetime.now(timezone.utc),
    )

    logger.info(
        f"Recognition report | workspace={workspace_id} "
        f"| total={total} | participants={participants}/{active}"
    )

    return RecognitionReportResponse(data=rows, summary=summary, meta=meta)