'use client'

import { Button } from '@/components/ui/Button'

interface ExportButtonProps {
  apiPath: string
  params: Record<string, string>
}

export default function ExportButton({ apiPath, params }: ExportButtonProps) {
  function handleExport() {
    const query = new URLSearchParams({ ...params, export: 'csv' }).toString()
    const url = `${process.env.NEXT_PUBLIC_API_URL}${apiPath}?${query}`
    window.open(url, '_blank')
  }

  return (
    <Button variant="outline" size="sm" onClick={handleExport}>
      <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
      </svg>
      Export CSV
    </Button>
  )
}