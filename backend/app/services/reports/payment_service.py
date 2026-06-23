import asyncpg
import logging
import math
from datetime import datetime, timezone

from app.schemas.reports import (
    PaymentReportFilters,
    PaymentReportRow,
    PaymentSummary,
    ReportMeta,
    PaymentReportResponse,
)

logger = logging.getLogger(__name__)


async def get_payment_report(
    workspace_id: str,
    filters: PaymentReportFilters,
    db: asyncpg.Connection,
) -> PaymentReportResponse:

    filters.validate_dates()

    # ── WHERE conditions ──────────────────────────────────────────────────────
    conditions = ["p.workspace_id = $1"]
    params: list = [workspace_id]
    idx = 2

    if filters.status:
        conditions.append(f"p.status = ${idx}")
        params.append(filters.status)
        idx += 1

    if filters.billing_cycle:
        conditions.append(f"p.billing_cycle = ${idx}")
        params.append(filters.billing_cycle)
        idx += 1

    if filters.payment_method:
        conditions.append(f"p.payment_method = ${idx}")
        params.append(filters.payment_method)
        idx += 1

    if filters.start_date:
        conditions.append(f"p.payment_date >= ${idx}")
        params.append(filters.start_date)
        idx += 1

    if filters.end_date:
        conditions.append(
            f"p.payment_date <= ${idx}::date + interval '1 day'"
        )
        params.append(filters.end_date)
        idx += 1

    where = " AND ".join(conditions)

    # ── Summary query ─────────────────────────────────────────────────────────
    summary_query = f"""
        SELECT
            COUNT(*)                                              AS total_invoices,
            COALESCE(SUM(final_amount)
                FILTER (WHERE status = 'Paid'),    0)            AS total_paid,
            COALESCE(SUM(final_amount)
                FILTER (WHERE status = 'Pending'), 0)            AS total_pending,
            COALESCE(SUM(final_amount)
                FILTER (WHERE status = 'Failed'),  0)            AS total_failed,
            COALESCE(SUM(gst_amount)
                FILTER (WHERE status = 'Paid'),    0)            AS total_gst_paid
        FROM payments p
        WHERE {where}
    """

    # ── Rows query ────────────────────────────────────────────────────────────
    # LEFT JOIN workspace_members for verifier name (bank transfer only)
    rows_query = f"""
        SELECT
            p.id::text,
            p.invoice_number,
            p.billing_cycle,
            p.purchased_seats,
            p.base_amount,
            p.discount_amount,
            p.gst_amount,
            p.final_amount,
            p.payment_method,
            p.status,
            p.payment_date,
            wm.display_name     AS verified_by
        FROM payments p
        LEFT JOIN workspace_members wm
              ON wm.id = p.verified_by
              AND wm.is_deleted = FALSE
        WHERE {where}
        ORDER BY p.created_at DESC
        LIMIT  ${idx} OFFSET ${idx + 1}
    """

    rows_params = params + [filters.page_size, filters.offset]

    try:
        summary_row = await db.fetchrow(summary_query, *params)
        rows_result = await db.fetch(rows_query, *rows_params)
    except Exception as e:
        logger.error(
            f"Payment report error | workspace={workspace_id} | {e}"
        )
        raise

    # ── Build summary ─────────────────────────────────────────────────────────
    summary = PaymentSummary(
        total_invoices = summary_row["total_invoices"] or 0,
        total_paid     = float(summary_row["total_paid"]     or 0),
        total_pending  = float(summary_row["total_pending"]  or 0),
        total_failed   = float(summary_row["total_failed"]   or 0),
        total_gst_paid = float(summary_row["total_gst_paid"] or 0),
    )

    # ── Build rows ────────────────────────────────────────────────────────────
    rows = [
        PaymentReportRow(
            id              = row["id"],
            invoice_number  = row["invoice_number"],
            billing_cycle   = row["billing_cycle"],
            purchased_seats = row["purchased_seats"],
            base_amount     = float(row["base_amount"]),
            discount_amount = float(row["discount_amount"]),
            gst_amount      = float(row["gst_amount"]),
            final_amount    = float(row["final_amount"]),
            payment_method  = row["payment_method"],
            status          = row["status"],
            payment_date    = row["payment_date"],
            verified_by     = row["verified_by"],
        )
        for row in rows_result
    ]

    meta = ReportMeta(
        total        = summary.total_invoices,
        page         = filters.page,
        page_size    = filters.page_size,
        total_pages  = max(1, math.ceil(
            summary.total_invoices / filters.page_size
        )),
        generated_at = datetime.now(timezone.utc),
    )

    logger.info(
        f"Payment report | workspace={workspace_id} "
        f"| invoices={summary.total_invoices} | paid={summary.total_paid}"
    )

    return PaymentReportResponse(data=rows, summary=summary, meta=meta)