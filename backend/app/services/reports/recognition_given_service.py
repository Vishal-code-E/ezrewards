import asyncpg
import logging
import math
from datetime import datetime, timezone
from typing import Optional

from app.schemas.reports import (
    RecognitionGivenFilters,
    RecognitionGivenRow,
    RecognitionGivenSummary,
    ReportMeta,
    RecognitionGivenResponse,
)
from app.exceptions.base import DatabaseTimeoutException

logger = logging.getLogger(__name__)


async def get_recognition_given_report(
    workspace_id: str,
    filters: RecognitionGivenFilters,
    db: asyncpg.Connection,
) -> RecognitionGivenResponse:

    filters.validate_dates()

    # ── WHERE conditions ──────────────────────────────────────────────────────
    # Note: conditions apply to the recognitions table (aliased r)
    # and the sender workspace_members (aliased wm)
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

    if filters.department:
        conditions.append(f"wm.department = ${idx}")
        params.append(filters.department)
        idx += 1

    where = " AND ".join(conditions)

    # ── Summary query ─────────────────────────────────────────────────────────
    # One row back — aggregated across all senders
    summary_query = f"""
        SELECT
            COUNT(DISTINCT r.sender_id)    AS total_active_givers,
            COUNT(*)                       AS total_recognitions
        FROM recognitions r
        JOIN workspace_members wm
             ON wm.id           = r.sender_id
             AND wm.workspace_id = r.workspace_id
             AND wm.is_deleted   = FALSE
        WHERE {where}
    """

    # ── Rows query ────────────────────────────────────────────────────────────
    # One row per sender — grouped, ranked by count
    # Subquery gets most used badge per sender (can't GROUP BY in outer GROUP BY)
    rows_query = f"""
        SELECT
            wm.id::text                        AS member_id,
            wm.display_name,
            wm.department,
            wm.role,
            COUNT(r.id)                        AS recognitions_given,
            COUNT(DISTINCT r.recipient_id)     AS unique_recipients,
            MAX(r.created_at)                  AS last_given_at,
            (
                SELECT b.name
                FROM   recognitions r2
                JOIN   badges b ON b.id = r2.badge_id
                WHERE  r2.sender_id    = wm.id
                  AND  r2.workspace_id = $1
                  AND  b.id IS NOT NULL
                GROUP  BY b.name
                ORDER  BY COUNT(*) DESC
                LIMIT  1
            )                                  AS most_used_badge
        FROM recognitions r
        JOIN workspace_members wm
             ON wm.id           = r.sender_id
             AND wm.workspace_id = r.workspace_id
             AND wm.is_deleted   = FALSE
        WHERE {where}
        GROUP BY wm.id, wm.display_name, wm.department, wm.role
        ORDER BY recognitions_given DESC, wm.display_name ASC
        LIMIT  ${idx} OFFSET ${idx + 1}
    """

    rows_params = params + [filters.page_size, filters.offset]

    try:
        summary_row  = await db.fetchrow(summary_query, *params)
        rows_result  = await db.fetch(rows_query, *rows_params)
    except Exception as e:
        logger.error(f"Recognition given report error | workspace={workspace_id} | {e}")
        raise

    # ── Build summary ─────────────────────────────────────────────────────────
    total_givers = summary_row["total_active_givers"] or 0
    total_recs   = summary_row["total_recognitions"]  or 0

    top_row = rows_result[0] if rows_result else None

    summary = RecognitionGivenSummary(
        total_active_givers  = total_givers,
        total_recognitions   = total_recs,
        avg_given_per_giver  = round(total_recs / total_givers, 2) if total_givers > 0 else 0.0,
        top_recognizer_name  = top_row["display_name"]       if top_row else None,
        top_recognizer_count = top_row["recognitions_given"] if top_row else 0,
    )

    # ── Build rows ────────────────────────────────────────────────────────────
    rows = [
        RecognitionGivenRow(
            member_id          = row["member_id"],
            display_name       = row["display_name"],
            department         = row["department"],
            role               = row["role"],
            recognitions_given = row["recognitions_given"],
            unique_recipients  = row["unique_recipients"],
            last_given_at      = row["last_given_at"],
            most_used_badge    = row["most_used_badge"],
        )
        for row in rows_result
    ]

    meta = ReportMeta(
        total        = total_givers,
        page         = filters.page,
        page_size    = filters.page_size,
        total_pages  = max(1, math.ceil(total_givers / filters.page_size)),
        generated_at = datetime.now(timezone.utc),
    )

    logger.info(
        f"Recognition given report | workspace={workspace_id} "
        f"| givers={total_givers} | total={total_recs}"
    )

    return RecognitionGivenResponse(data=rows, summary=summary, meta=meta)