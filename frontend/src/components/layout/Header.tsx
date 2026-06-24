'use client'

import { useEffect, useState } from 'react'
import { supabase } from '@/lib/supabase'

export default function Header() {
  const [email, setEmail] = useState<string | null>(null)

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setEmail(session?.user?.email ?? null)
    })
  }, [])

  return (
    <header className="h-14 bg-white border-b border-slate-200 flex items-center
                       justify-between px-6 flex-shrink-0">

      {/* Workspace name — hardcoded for now, real API later */}
      <div className="flex items-center gap-2">
        <span className="text-sm font-medium text-slate-900">Test Company</span>
        <span className="text-xs bg-indigo-50 text-indigo-600 font-medium px-2 py-0.5 rounded-full">
          Admin
        </span>
      </div>

      {/* User email */}
      {email && (
        <span className="text-xs text-slate-500">{email}</span>
      )}
    </header>
  )
}