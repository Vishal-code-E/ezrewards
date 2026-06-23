import asyncpg
import logging
from datetime import datetime, timezone

from app.schemas.reports import (
    SubscriptionBillingRow,
    SubscriptionBillingSummary,
    ReportMeta,
    SubscriptionBillingResponse,
)

logger = logging.getLogger(__name__)


async def get_subscription_billing_report(
    workspace_id: str,
    db: asyncpg.Connection,
) -> SubscriptionBillingResponse:
    """
    Subscription Billing Report.

    Single-row report — one subscription per workspace.
    Joins live active user count from workspace_members.
    Payment summary from payments table.
    """

    # ── Subscription + live seat count ───────────────────────────────────────
    subscription_query = """
        SELECT
            s.billing_cycle,
            s.price_per_seat,
            s.purchased_seats,
            s.status,
            s.payment_method,
            s.renewal_date,
            s.current_period_start,
            s.current_period_end,
            s.gst_rate,
            -- Live active user count from workspace_members
            COUNT(wm.id) FILTER (
                WHERE wm.status    = 'Active'
                AND   wm.is_deleted = FALSE
            )                           AS active_users
        FROM subscriptions s
        LEFT JOIN workspace_members wm
              ON wm.workspace_id = s.workspace_id
        WHERE s.workspace_id = $1
        GROUP BY
            s.id, s.billing_cycle, s.price_per_seat,
            s.purchased_seats, s.status, s.payment_method,
            s.renewal_date, s.current_period_start,
            s.current_period_end, s.gst_rate
    """

    # ── Payment summary ───────────────────────────────────────────────────────
    payment_summary_query = """
        SELECT
            COALESCE(SUM(final_amount)
                FILTER (WHERE status = 'Paid'), 0)   AS total_paid,
            COUNT(*)                                  AS total_invoices,
            COUNT(*) FILTER (WHERE status = 'Failed') AS failed_payments,
            MAX(payment_date)
                FILTER (WHERE status = 'Paid')        AS last_payment_date,
            -- amount of the most recent paid invoice
            (
                SELECT final_amount
                FROM   payments
                WHERE  workspace_id = $1
                  AND  status       = 'Paid'
                ORDER BY payment_date DESC
                LIMIT 1
            )                                         AS last_payment_amount
        FROM payments
        WHERE workspace_id = $1
    """

    try:
        sub_row     = await db.fetchrow(subscription_query, workspace_id)
        payment_row = await db.fetchrow(payment_summary_query, workspace_id)
    except Exception as e:
        logger.error(
            f"Subscription billing report error | workspace={workspace_id} | {e}"
        )
        raise

    # ── Build subscription row ────────────────────────────────────────────────
    subscription = None
    if sub_row:
        purchased     = sub_row["purchased_seats"]
        active        = sub_row["active_users"] or 0
        price         = float(sub_row["price_per_seat"])
        monthly_amt   = purchased * price
        annual_amt    = (monthly_amt * 10
                        if sub_row["billing_cycle"] == "annual"
                        else None)

        subscription = SubscriptionBillingRow(
            billing_cycle        = sub_row["billing_cycle"],
            price_per_seat       = price,
            purchased_seats      = purchased,
            active_users         = active,
            available_seats      = max(0, purchased - active),
            status               = sub_row["status"],
            payment_method       = sub_row["payment_method"],
            renewal_date         = sub_row["renewal_date"],
            current_period_start = sub_row["current_period_start"],
            current_period_end   = sub_row["current_period_end"],
            gst_rate             = float(sub_row["gst_rate"]),
            monthly_amount       = monthly_amt,
            annual_amount        = annual_amt,
        )

    # ── Build payment summary ─────────────────────────────────────────────────
    summary = SubscriptionBillingSummary(
        total_paid_to_date  = float(payment_row["total_paid"]          or 0),
        total_invoices      = payment_row["total_invoices"]            or 0,
        failed_payments     = payment_row["failed_payments"]           or 0,
        last_payment_date   = payment_row["last_payment_date"],
        last_payment_amount = float(payment_row["last_payment_amount"] or 0)
                              if payment_row["last_payment_amount"] else None,
    )

    meta = ReportMeta(
        total        = 1 if subscription else 0,
        page         = 1,
        page_size    = 1,
        total_pages  = 1,
        generated_at = datetime.now(timezone.utc),
    )

    logger.info(
        f"Subscription billing report | workspace={workspace_id} "
        f"| status={sub_row['status'] if sub_row else 'no subscription'}"
    )

    return SubscriptionBillingResponse(
        subscription = subscription,
        summary      = summary,
        meta         = meta,
    )