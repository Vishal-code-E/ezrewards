'use client'

import { useEffect, useState, useCallback } from 'react'
import { useParams }    from 'next/navigation'
import { apiGet }       from '@/lib/api'
import { ReportResponse } from '@/types/index'
import SummaryCards    from '@/components/reports/SummaryCards'
import ReportTable     from '@/components/reports/ReportTable'
import ExportButton    from '@/components/reports/ExportButton'
import { Select }      from '@/components/ui/Select'
import { Button }      from '@/components/ui/Button'
//import ChatPanel       from '@/components/reports/ChatPanel'
import EmbeddedChat from '@/components/reports/EmbeddedChat'
import Link from 'next/link'


const REPORT_LABELS: Record<string, string> = {
  'invitations':            'Invitation Status',
  'recognition':            'Recognition Activity',
  'recognition/given':      'Recognition Given',
  'recognition/received':   'Recognition Received',
  'seats':                  'Active Seat Usage',
  'redemptions':            'Voucher Redemption',
  'wallet':                 'Wallet Balance',
  'wallet/transactions':    'Wallet Transactions',
  'payments':               'Payment History',
  'onboarding':             'Employee Onboarding',
  'subscription':           'Subscription Billing',
  'emails':                 'Email Notifications',
}

const PAGE_SIZE = 5

export default function ReportPage() {
  const params  = useParams()
  const slugArr = Array.isArray(params.slug) ? params.slug : [params.slug]
  const slugKey = slugArr.join('/')
  const apiPath = `/api/reports/${slugKey}`
  const title   = REPORT_LABELS[slugKey] ?? slugKey

  const [data,       setData]       = useState<Record<string, unknown>[]>([])
  const [summary,    setSummary]    = useState<Record<string, unknown> | undefined>()
  const [meta,       setMeta]       = useState<{ total: number; total_pages: number; page: number } | null>(null)
  const [loading,    setLoading]    = useState(true)
  const [error,      setError]      = useState<string | null>(null)
  const [page,       setPage]       = useState(1)
  const [status,     setStatus]     = useState('')
  const [department, setDepartment] = useState('')

  const fetchReport = useCallback(async () => {
    setLoading(true)
    setError(null)

    const queryParams: Record<string, string> = {
      page:      String(page),
      page_size: String(PAGE_SIZE),
    }
    if (status)     queryParams.status     = status
    if (department) queryParams.department = department

    try {
      const res = await apiGet<ReportResponse<Record<string, unknown>>>(apiPath, queryParams)
      setData(res.data)
      setSummary(res.summary as Record<string, unknown>)
      setMeta({
        total:       res.meta.total,
        total_pages: res.meta.total_pages,
        page:        res.meta.page,
      })
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load report.')
    } finally {
      setLoading(false)
    }
  }, [apiPath, page, status, department])

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchReport()
  }, [fetchReport])

  const filterParams: Record<string, string> = {}
  if (status)     filterParams.status     = status
  if (department) filterParams.department = department

  return (
    <div>

      {/* Page header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <Link
            href="/reports"
            className="inline-flex items-center gap-1.5 text-xs text-slate-500
                 hover:text-indigo-600 transition-colors mb-2 group"
         >
           <svg
             className="w-3.5 h-3.5 group-hover:-translate-x-0.5 transition-transform"
             fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
          </svg>
           All Reports
          </Link>
          <h1 className="text-xl font-semibold text-slate-900">{title}</h1>
          {meta && (
            <p className="mt-0.5 text-sm text-slate-500">
              {meta.total.toLocaleString('en-IN')} records found
            </p>
          )}
        </div>
        <ExportButton apiPath={apiPath} params={filterParams} />
      </div>

      {/* Summary cards */}
      <SummaryCards summary={summary} loading={loading} />

      {/* Filters */}
      <div className="flex items-end gap-3 mb-4">
        <Select
          label="Status"
          value={status}
          onChange={(e) => { setStatus(e.target.value); setPage(1) }}
          className="w-40"
        >
          <option value="">All</option>
          <option value="Pending">Pending</option>
          <option value="Accepted">Accepted</option>
          <option value="Expired">Expired</option>
          <option value="Cancelled">Cancelled</option>
        </Select>

        <Select
          label="Department"
          value={department}
          onChange={(e) => { setDepartment(e.target.value); setPage(1) }}
          className="w-44"
        >
          <option value="">All Departments</option>
          <option value="Engineering">Engineering</option>
          <option value="Product">Product</option>
          <option value="HR">HR</option>
          <option value="Finance">Finance</option>
          <option value="Sales">Sales</option>
        </Select>

        {(status || department) && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => { setStatus(''); setDepartment(''); setPage(1) }}
          >
            Clear filters
          </Button>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="mb-4 rounded-lg bg-red-50 border border-red-100 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Table */}
      <ReportTable data={data} loading={loading} />

      <EmbeddedChat reportContext={slugKey} />

      {/* Pagination */}
      {meta && meta.total_pages > 1 && (
        <div className="flex items-center justify-between mt-4">
          <p className="text-xs text-slate-500">
            Page {meta.page} of {meta.total_pages}
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page === 1}
              onClick={() => setPage((p) => p - 1)}
            >
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={page === meta.total_pages}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </Button>
          </div>
        </div>
      )}

      {/* <ChatPanel reportContext={slugKey} /> */}

    </div>
  )
}

