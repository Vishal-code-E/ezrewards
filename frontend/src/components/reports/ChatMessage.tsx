interface ChatMessageProps {
  role: 'user' | 'assistant'
  content: string
  toolUsed?: string
}

export default function ChatMessage({ role, content, toolUsed }: ChatMessageProps) {
  const isUser = role === 'user'

  return (
    <div className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
          isUser
            ? 'bg-indigo-600 text-white rounded-br-sm'
            : 'bg-white border border-slate-200 text-slate-800 rounded-bl-sm'
        }`}
      >
        {content}
      </div>

      {/* Tool badge — shown under assistant messages only */}
      {!isUser && toolUsed && (
        <span className="mt-1 text-xs text-slate-400 px-1">
          Used: {toolUsed.replace(/_/g, ' ')}
        </span>
      )}
    </div>
  )
}