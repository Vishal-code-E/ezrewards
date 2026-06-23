// ── API Response envelope (mirrors FastAPI ReportResponse) ──────────────────

export interface ReportMeta {
  total:        number
  page:         number
  page_size:    number
  total_pages:  number
  generated_at: string
  workspace_id: string
}

export interface ReportResponse<T> {
  success:    boolean
  data:       T[]
  meta:       ReportMeta
  summary?:   Record<string, unknown>
  request_id: string
}

export interface ApiErrorResponse {
  success:    false
  error_code: string
  message:    string
  details?:   { field: string; message: string }[]
  request_id: string
  timestamp:  string
}

// ── EzRewards domain types ───────────────────────────────────────────────────

export type UserRole = 'Admin' | 'Manager' | 'Employee' | 'RegionalHRLead'

export type InviteStatus  = 'Pending' | 'Accepted' | 'Expired' | 'Cancelled'
export type MemberStatus  = 'Active'  | 'Invited'  | 'Inactive' | 'Deactivated'
export type WalletTxnType = 'Credit'  | 'Debit'
export type PaymentStatus = 'Paid'    | 'Pending'  | 'Failed'  | 'Refunded'