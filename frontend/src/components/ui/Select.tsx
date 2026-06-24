interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string
}

export function Select({ label, className = '', ...props }: SelectProps) {
  return (
    <div className="flex flex-col gap-1">
      {label && (
        <label className="text-xs font-medium text-slate-600">{label}</label>
      )}
      <select
        className={`rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm
                    text-slate-900 focus:outline-none focus:border-indigo-500
                    focus:ring-2 focus:ring-indigo-500/20 transition-colors ${className}`}
        {...props}
      />
    </div>
  )
}