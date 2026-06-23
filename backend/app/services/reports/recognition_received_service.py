import asyncpg
import logging
import math
from datetime import datetime, timezone

from app.schemas.reports import (
    RecognitionReceivedFilters,
    RecognitionReceivedRow,
    RecognitionReceivedSummary,
    ReportMeta,
    RecognitionReceivedResponse,
)

logger = logging.getLogger(__name__)


async def get_recognition_received_report(
    workspace_id: str,
    filters: RecognitionReceivedFilters,
    db: asyncpg.Connection,
) -> RecognitionReceivedResponse:

    filters.validate_dates()

    # ── WHERE conditions ──────────────────────────────────────────────────────
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
    summary_query = f"""
        SELECT
            COUNT(DISTINCT r.recipient_id) AS total_active_receivers,
            COUNT(*)                       AS total_recognitions
        FROM recognitions r
        JOIN workspace_members wm
             ON wm.id            = r.recipient_id
             AND wm.workspace_id = r.workspace_id
             AND wm.is_deleted   = FALSE
        WHERE {where}
    """

    # ── Rows query ────────────────────────────────────────────────────────────
    rows_query = f"""
        SELECT
            wm.id::text                        AS member_id,
            wm.display_name,
            wm.department,
            wm.role,
            COUNT(r.id)                        AS recognitions_received,
            COUNT(DISTINCT r.sender_id)        AS unique_senders,
            MAX(r.created_at)                  AS last_received_at,
            (
                SELECT b.name
                FROM   recognitions r2
                JOIN   badges b ON b.id = r2.badge_id
                WHERE  r2.recipient_id  = wm.id
                  AND  r2.workspace_id  = $1
                  AND  b.id IS NOT NULL
                GROUP  BY b.name
                ORDER  BY COUNT(*) DESC
                LIMIT  1
            )                                  AS most_received_badge
        FROM recognitions r
        JOIN workspace_members wm
             ON wm.id            = r.recipient_id
             AND wm.workspace_id = r.workspace_id
             AND wm.is_deleted   = FALSE
        WHERE {where}
        GROUP BY wm.id, wm.display_name, wm.department, wm.role
        ORDER BY recognitions_received DESC, wm.display_name ASC
        LIMIT  ${idx} OFFSET ${idx + 1}
    """

    rows_params = params + [filters.page_size, filters.offset]

    try:
        summary_row = await db.fetchrow(summary_query, *params)
        rows_result = await db.fetch(rows_query, *rows_params)
    except Exception as e:
        logger.error(
            f"Recognition received report error | workspace={workspace_id} | {e}"
        )
        raise

    # ── Build summary ─────────────────────────────────────────────────────────
    total_receivers = summary_row["total_active_receivers"] or 0
    total_recs      = summary_row["total_recognitions"]     or 0
    top_row         = rows_result[0] if rows_result else None

    summary = RecognitionReceivedSummary(
        total_active_receivers     = total_receivers,
        total_recognitions         = total_recs,
        avg_received_per_recipient = round(
            total_recs / total_receivers if total_receivers > 0 else 0.0, 2
        ),
        top_recipient_name  = top_row["display_name"]          if top_row else None,
        top_recipient_count = top_row["recognitions_received"]  if top_row else 0,
    )

    # ── Build rows ────────────────────────────────────────────────────────────
    rows = [
        RecognitionReceivedRow(
            member_id             = row["member_id"],
            display_name          = row["display_name"],
            department            = row["department"],
            role                  = row["role"],
            recognitions_received = row["recognitions_received"],
            unique_senders        = row["unique_senders"],
            last_received_at      = row["last_received_at"],
            most_received_badge   = row["most_received_badge"],
        )
        for row in rows_result
    ]

    # ── Build meta ────────────────────────────────────────────────────────────
    meta = ReportMeta(
        total        = total_receivers,
        page         = filters.page,
        page_size    = filters.page_size,
        total_pages  = max(1, math.ceil(total_receivers / filters.page_size)),
        generated_at = datetime.now(timezone.utc),
    )

    logger.info(
        f"Recognition received report | workspace={workspace_id} "
        f"| receivers={total_receivers} | total={total_recs}"
    )

    return RecognitionReceivedResponse(data=rows, summary=summary, meta=meta)