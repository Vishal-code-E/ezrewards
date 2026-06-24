import { Skeleton } from '@/components/ui/Skeleton'

interface SummaryCardsProps {
  summary: Record<string, unknown> | undefined
  loading: boolean
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'number') {
    return value.toLocaleString('en-IN')
  }
  return String(value)
}

export default function SummaryCards({ summary, loading }: SummaryCardsProps) {
  if (loading) {
    return (
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
        {[...Array(4)].map((_, i) => (
          <Skeleton key={i} className="h-24" />
        ))}
      </div>
    )
  }

  if (!summary) return null

  const entries = Object.entries(summary).slice(0, 4)

  return (
    <div className="grid grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
      {entries.map(([key, value]) => (
        <div key={key} className="bg-white rounded-xl border border-slate-200 p-4">
          <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">
            {key.replace(/_/g, ' ')}
          </p>
          <p className="mt-1.5 text-2xl font-bold text-slate-900">
            {formatValue(value)}
          </p>
        </div>
      ))}
    </div>
  )
}