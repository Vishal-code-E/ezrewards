'use client'

import { useRouter } from 'next/navigation'

interface ReportCardProps {
  label: string
  description: string
  icon: string
  slug: string
}

export default function ReportCard({ label, description, icon, slug }: ReportCardProps) {
  const router = useRouter()

  return (
    <button
      onClick={() => router.push(`/reports/${slug}`)}
      className="group w-full text-left bg-white rounded-xl border border-slate-200
                 p-5 hover:border-indigo-300 hover:shadow-md transition-all duration-150"
    >
      <div className="flex items-start gap-4">

        {/* Icon */}
        <div className="w-10 h-10 rounded-lg bg-indigo-50 flex items-center justify-center
                        flex-shrink-0 group-hover:bg-indigo-100 transition-colors">
          <span className="text-xl">{icon}</span>
        </div>

        {/* Text */}
        <div className="min-w-0">
          <p className="text-sm font-semibold text-slate-900 group-hover:text-indigo-600
                        transition-colors">
            {label}
          </p>
          <p className="mt-0.5 text-xs text-slate-500 leading-relaxed">
            {description}
          </p>
        </div>

      </div>
    </button>
  )
}