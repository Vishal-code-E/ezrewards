import { supabase } from './supabase'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
console.log('[api.ts] API_URL =', API_URL)
//const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// ── Auth header ───────────────────────────────────────────────────────────────

async function getHeaders(): Promise<HeadersInit> {
  const { data: { session } } = await supabase.auth.getSession()
  

  if (!session?.access_token) {
    // Clear any stale state and redirect to login
    await supabase.auth.signOut()
    window.location.href = '/login'
    throw new Error('Not authenticated')
  }

  return {
    'Authorization': `Bearer ${session.access_token}`,
    'Content-Type':  'application/json',
  }
}

// ── Error shape from FastAPI ──────────────────────────────────────────────────

export class ApiError extends Error {
  constructor(
    public errorCode: string,
    message: string,
    public statusCode: number,
    public requestId?: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (res.ok) return res.json() as Promise<T>

  let body: { error_code?: string; message?: string; request_id?: string }
  try   { body = await res.json() }
  catch { body = {} }

  throw new ApiError(
    body.error_code  ?? 'UNKNOWN_ERROR',
    body.message     ?? `HTTP ${res.status}`,
    res.status,
    body.request_id,
  )
}

// ── Generic request helpers ───────────────────────────────────────────────────

export async function apiGet<T>(
  path: string,
  params?: Record<string, string | number | boolean | undefined>,
): Promise<T> {
  const headers = await getHeaders()
  const url     = new URL(`${API_URL}${path}`)

  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined) url.searchParams.set(k, String(v))
    })
  }

  const res = await fetch(url.toString(), { headers })
  return handleResponse<T>(res)
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const headers = await getHeaders()
  const res     = await fetch(`${API_URL}${path}`, {
    method:  'POST',
    headers,
    body:    JSON.stringify(body),
  })
  return handleResponse<T>(res)
}