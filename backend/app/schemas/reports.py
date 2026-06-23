from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime
from enum import Enum


class ExportFormat(str, Enum):
    json = "json"
    csv  = "csv"


class BaseReportFilters(BaseModel):
    start_date: Optional[date] = None
    end_date:   Optional[date] = None
    department: Optional[str]  = None
    page:       int            = Field(default=1, ge=1)
    page_size:  int            = Field(default=25, ge=1, le=250)
    export:     ExportFormat   = ExportFormat.json

    def validate_dates(self) -> None:
        if self.start_date and self.end_date:
            if self.start_date > self.end_date:
                from fastapi import HTTPException
                raise HTTPException(
                    status_code=422,
                    detail="start_date cannot be after end_date"
                )

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class InvitationReportFilters(BaseReportFilters):
    status: Optional[str] = None   # Pending | Accepted | Expired | Cancelled
    source: Optional[str] = None   # csv | single_invite


# ── Row shape returned to frontend ───────────────────────────────────────────

class InvitationReportRow(BaseModel):
    id:           str
    email:        str
    display_name: str
    department:   str
    role:         str
    status:       str
    source:       str
    invite_count: int
    invited_by:   Optional[str]    # display_name of admin who invited
    created_at:   datetime
    expires_at:   datetime
    accepted_at:  Optional[datetime]


# ── Summary cards shown above the table ──────────────────────────────────────

class InvitationSummary(BaseModel):
    total:           int
    accepted:        int
    pending:         int
    expired:         int
    cancelled:       int
    activation_rate: float          # accepted / total * 100


# ── Standard response envelope ────────────────────────────────────────────────

class ReportMeta(BaseModel):
    total:        int
    page:         int
    page_size:    int
    total_pages:  int
    generated_at: datetime


class InvitationReportResponse(BaseModel):
    success:  bool = True
    data:     List[InvitationReportRow]
    summary:  InvitationSummary
    meta:     ReportMeta

class RecognitionReportFilters(BaseReportFilters):
    badge_id:     Optional[str] = None
    sender_id:    Optional[str] = None
    recipient_id: Optional[str] = None


class RecognitionReportRow(BaseModel):
    id:                 str
    sender_name:        str
    sender_department:  str
    recipient_name:     str
    recipient_dept:     str
    badge_name:         Optional[str]
    badge_color:        Optional[str]
    message:            Optional[str]
    created_at:         datetime


class RecognitionSummary(BaseModel):
    total_recognitions:   int
    unique_senders:       int
    unique_recipients:    int
    participation_rate:   float    # (gave OR received) / active × 100
    top_badge:            Optional[str]
    avg_per_active_user:  float


class RecognitionReportResponse(BaseModel):
    success: bool = True
    data:    List[RecognitionReportRow]
    summary: RecognitionSummary
    meta:    ReportMeta

class RecognitionGivenFilters(BaseReportFilters):
    # inherits: start_date, end_date, department, page, page_size, export
    pass   # no extra filters needed for MVP


class RecognitionGivenRow(BaseModel):
    member_id:          str
    display_name:       str
    department:         str
    role:               str
    recognitions_given: int
    unique_recipients:  int
    last_given_at:      Optional[datetime]
    most_used_badge:    Optional[str]


class RecognitionGivenSummary(BaseModel):
    total_active_givers:    int    # members who gave at least one recognition
    total_recognitions:     int
    avg_given_per_giver:    float
    top_recognizer_name:    Optional[str]
    top_recognizer_count:   int


class RecognitionGivenResponse(BaseModel):
    success: bool = True
    data:    List[RecognitionGivenRow]
    summary: RecognitionGivenSummary
    meta:    ReportMeta

class RecognitionReceivedFilters(BaseReportFilters):
    pass


class RecognitionReceivedRow(BaseModel):
    member_id:              str
    display_name:           str
    department:             str
    role:                   str
    recognitions_received:  int
    unique_senders:         int
    last_received_at:       Optional[datetime]
    most_received_badge:    Optional[str]


class RecognitionReceivedSummary(BaseModel):
    total_active_receivers:  int
    total_recognitions:      int
    avg_received_per_recipient: float
    top_recipient_name:      Optional[str]
    top_recipient_count:     int


class RecognitionReceivedResponse(BaseModel):
    success: bool = True
    data:    List[RecognitionReceivedRow]
    summary: RecognitionReceivedSummary
    meta:    ReportMeta

class SeatUsageReportRow(BaseModel):
    department:       str
    active_users:     int
    inactive_users:   int
    invited_users:    int


class SeatUsageSummary(BaseModel):
    purchased_seats:    int
    active_users:       int
    available_seats:    int
    pending_invites:    int
    utilization_pct:    float


class SeatUsageResponse(BaseModel):
    success: bool = True
    data:    List[SeatUsageReportRow]   # breakdown by department
    summary: SeatUsageSummary
    meta:    ReportMeta

class RedemptionReportFilters(BaseReportFilters):
    status:       Optional[str] = None  # Completed | Failed | Pending | Refunded
    voucher_brand: Optional[str] = None


class RedemptionReportRow(BaseModel):
    id:             str
    employee_name:  str
    department:     str
    voucher_brand:  str
    voucher_value:  float
    points_spent:   int
    status:         str
    failure_reason: Optional[str]
    created_at:     datetime


class RedemptionSummary(BaseModel):
    total_redemptions:  int
    completed:          int
    failed:             int
    pending:            int
    total_value:        float
    success_rate:       float


class RedemptionReportResponse(BaseModel):
    success: bool = True
    data:    List[RedemptionReportRow]
    summary: RedemptionSummary
    meta:    ReportMeta

class WalletReportRow(BaseModel):
    period:         str       # e.g. "2025-06" for monthly grouping
    total_credited: float
    total_debited:  float
    net:            float     # credited - debited


class WalletSummary(BaseModel):
    current_balance:      float
    total_recharged:      float
    total_consumed:       float
    avg_monthly_spend:    float
    days_until_empty:     Optional[int]
    projected_empty_date: Optional[str]
    low_balance_alert:    bool


class WalletReportResponse(BaseModel):
    success: bool = True
    data:    List[WalletReportRow]    # monthly trend
    summary: WalletSummary
    meta:    ReportMeta

class WalletTransactionFilters(BaseReportFilters):
    type:   Optional[str] = None   # Credit | Debit
    status: Optional[str] = None   # Completed | Failed | Pending Payment


class WalletTransactionRow(BaseModel):
    id:             str
    type:           str
    amount:         float
    balance_after:  float
    payment_method: Optional[str]
    status:         str
    created_by:     Optional[str]   # display_name of admin who initiated
    created_at:     datetime


class WalletTransactionSummary(BaseModel):
    total_credits:  float
    total_debits:   float
    net_movement:   float
    total_entries:  int


class WalletTransactionResponse(BaseModel):
    success: bool = True
    data:    List[WalletTransactionRow]
    summary: WalletTransactionSummary
    meta:    ReportMeta

class PaymentReportFilters(BaseReportFilters):
    status:        Optional[str] = None  # Paid | Pending | Failed | Refunded
    billing_cycle: Optional[str] = None  # monthly | annual
    payment_method: Optional[str] = None # stripe | bank_transfer


class PaymentReportRow(BaseModel):
    id:             str
    invoice_number: Optional[str]
    billing_cycle:  str
    purchased_seats: int
    base_amount:    float
    discount_amount: float
    gst_amount:     float
    final_amount:   float
    payment_method: str
    status:         str
    payment_date:   Optional[datetime]
    verified_by:    Optional[str]    # display_name of admin who verified


class PaymentSummary(BaseModel):
    total_invoices:  int
    total_paid:      float
    total_pending:   float
    total_failed:    float
    total_gst_paid:  float


class PaymentReportResponse(BaseModel):
    success: bool = True
    data:    List[PaymentReportRow]
    summary: PaymentSummary
    meta:    ReportMeta

class OnboardingReportFilters(BaseReportFilters):
    status: Optional[str] = None   # Pending | Accepted | Expired | Cancelled
    source: Optional[str] = None   # csv | single_invite


class OnboardingReportRow(BaseModel):
    email:           str
    display_name:    str
    department:      str
    role:            str
    invite_status:   str
    member_status:   Optional[str]
    source:          str
    invite_count:    int
    invited_at:      datetime
    expires_at:      datetime
    activated_at:    Optional[datetime]
    days_to_activate: Optional[int]   # NULL if not yet activated


class OnboardingSummary(BaseModel):
    total_invited:      int
    total_active:       int
    total_pending:      int
    total_expired:      int
    total_cancelled:    int
    activation_rate:    float
    avg_days_to_activate: Optional[float]


class OnboardingReportResponse(BaseModel):
    success: bool = True
    data:    List[OnboardingReportRow]
    summary: OnboardingSummary
    meta:    ReportMeta

class SubscriptionBillingRow(BaseModel):
    billing_cycle:          str
    price_per_seat:         float
    purchased_seats:        int
    active_users:           int
    available_seats:        int
    status:                 str
    payment_method:         str
    renewal_date:           Optional[datetime]
    current_period_start:   Optional[datetime]
    current_period_end:     Optional[datetime]
    gst_rate:               float
    monthly_amount:         float   # purchased_seats × price_per_seat
    annual_amount:          Optional[float]  # monthly × 10 if annual


class SubscriptionBillingSummary(BaseModel):
    total_paid_to_date:     float
    total_invoices:         int
    failed_payments:        int
    last_payment_date:      Optional[datetime]
    last_payment_amount:    Optional[float]


class SubscriptionBillingResponse(BaseModel):
    success:      bool = True
    subscription: Optional[SubscriptionBillingRow]
    summary:      SubscriptionBillingSummary
    meta:         ReportMeta

class EmailNotificationFilters(BaseReportFilters):
    status:     Optional[str] = None  # Sent | Delivered | Bounced | Failed | Opened
    email_type: Optional[str] = None  # invite | recognition_notification | billing_alert | etc.


class EmailNotificationRow(BaseModel):
    id:                 str
    recipient_email:    str
    recipient_name:     Optional[str]
    email_type:         str
    subject:            Optional[str]
    status:             str
    failure_reason:     Optional[str]
    retry_count:        int
    sent_at:            Optional[datetime]
    delivered_at:       Optional[datetime]
    opened_at:          Optional[datetime]
    created_at:         datetime


class EmailNotificationSummary(BaseModel):
    total_sent:         int
    delivered:          int
    opened:             int
    bounced:            int
    failed:             int
    delivery_rate:      float   # delivered / total_sent × 100
    open_rate:          float   # opened / delivered × 100
    by_type:            dict    # { email_type: count }


class EmailNotificationResponse(BaseModel):
    success: bool = True
    data:    List[EmailNotificationRow]
    summary: EmailNotificationSummary
    meta:    ReportMeta

class ChatMessage(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)


class ChatResponse(BaseModel):
    success:     bool = True
    answer:      str
    tool_used:   Optional[str] = None    # which report was queried
    request_id:  str