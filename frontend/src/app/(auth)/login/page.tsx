'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { supabase } from '@/lib/supabase'

export default function LoginPage() {
  const router = useRouter()
  const [email, setEmail]       = useState('')
  const [password, setPassword] = useState('')
  const [error, setError]       = useState<string | null>(null)
  const [loading, setLoading]   = useState(false)
  const [checking, setChecking] = useState(true)

  // If a session already exists, skip login entirely
  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session) {
        router.replace('/')
      } else {
        setChecking(false)
      }
    })
  }, [router])

  async function handleLogin(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setError(null)
    setLoading(true)

    const { error: authError } = await supabase.auth.signInWithPassword({
      email: email.trim().toLowerCase(),
      password,
    })

    if (authError) {
      const message = authError.message === '{}'
        ? 'Unable to connect to the server. Please try again in a moment.'
        : authError.message
      setError(message)
      setLoading(false)
      return
    }

    router.push('/')
  }

  // Avoid flashing the form to an already-authenticated user
  if (checking) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-white">
        <div className="w-5 h-5 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  return (
    <div className="min-h-screen flex">

      {/* ── Left: brand panel (hidden on mobile) ── */}
      <div className="hidden lg:flex lg:w-[420px] xl:w-[480px] bg-slate-900 flex-shrink-0
                      flex-col justify-between p-12 relative overflow-hidden">

        {/* Decorative rings — the "recognition" motif */}
        <div className="absolute -top-24 -right-24 w-96 h-96 rounded-full border border-slate-700/50" />
        <div className="absolute -top-10 -right-10 w-64 h-64 rounded-full border border-indigo-800/60" />
        <div className="absolute -bottom-20 -left-20 w-80 h-80 rounded-full border border-slate-700/40" />
        <div className="absolute bottom-10 -left-6  w-52 h-52 rounded-full bg-indigo-900/20" />

        {/* Logo */}
        <div className="relative z-10 flex items-center gap-3">
          <div className="w-9 h-9 bg-indigo-600 rounded-lg flex items-center justify-center">
            <span className="text-white font-bold text-sm">Ez</span>
          </div>
          <span className="text-white font-semibold text-lg tracking-tight">EzRewards</span>
        </div>

        {/* Tagline */}
        <div className="relative z-10 space-y-4">
          <h1 className="text-4xl font-bold text-white leading-snug">
            Recognition that<br />
            <span className="text-indigo-400">resonates.</span>
          </h1>
          <p className="text-slate-400 text-base leading-relaxed max-w-xs">
            Build a culture of appreciation where every contribution gets seen, celebrated, and rewarded.
          </p>
        </div>

        {/* Footer */}
        <p className="relative z-10 text-slate-600 text-sm">Powered by Evolutyz Corp</p>
      </div>

      {/* ── Right: form panel ── */}
      <div className="flex-1 flex items-center justify-center bg-white px-6 py-12">
        <div className="w-full max-w-[400px] space-y-8">

          {/* Mobile logo */}
          <div className="lg:hidden flex items-center gap-3">
            <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-xs">Ez</span>
            </div>
            <span className="text-slate-900 font-semibold">EzRewards</span>
          </div>

          {/* Heading */}
          <div>
            <h2 className="text-2xl font-bold text-slate-900">Sign in to your workspace</h2>
            <p className="mt-1.5 text-sm text-slate-500">Enter your credentials to continue</p>
          </div>

          {/* Form */}
          <form onSubmit={handleLogin} className="space-y-5" noValidate>

            <div className="space-y-1.5">
              <label htmlFor="email" className="block text-sm font-medium text-slate-700">
                Work email
              </label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@company.com"
                className="block w-full rounded-lg border border-slate-200 bg-slate-50 px-4 py-2.5
                           text-sm text-slate-900 placeholder:text-slate-400
                           focus:outline-none focus:bg-white focus:border-indigo-500
                           focus:ring-2 focus:ring-indigo-500/20 transition-colors"
              />
            </div>

            <div className="space-y-1.5">
              <label htmlFor="password" className="block text-sm font-medium text-slate-700">
                Password
              </label>
              <input
                id="password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="block w-full rounded-lg border border-slate-200 bg-slate-50 px-4 py-2.5
                           text-sm text-slate-900 placeholder:text-slate-400
                           focus:outline-none focus:bg-white focus:border-indigo-500
                           focus:ring-2 focus:ring-indigo-500/20 transition-colors"
              />
            </div>

            {/* Inline error — no page reload */}
            {error && (
              <div className="flex items-start gap-2.5 rounded-lg bg-red-50 border border-red-100 px-4 py-3">
                <svg className="w-4 h-4 text-red-500 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
                <p className="text-sm text-red-700">{error}</p>
              </div>
            )}

            <button
              type="submit"
              disabled={loading || !email || !password}
              className="w-full flex items-center justify-center gap-2 rounded-lg bg-indigo-600
                         px-4 py-2.5 text-sm font-semibold text-white
                         hover:bg-indigo-700 focus:outline-none focus:ring-2
                         focus:ring-indigo-500 focus:ring-offset-2
                         disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? (
                <>
                  <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Signing in…
                </>
              ) : (
                'Sign in'
              )}
            </button>
          </form>

          <p className="text-center text-xs text-slate-400">
            Having trouble? Contact your workspace admin.
          </p>
        </div>
      </div>
    </div>
  )
}