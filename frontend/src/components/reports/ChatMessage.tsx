import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface ChatMessageProps {
  role:      'user' | 'assistant'
  content:   string
  toolUsed?: string
}

export default function ChatMessage({ role, content, toolUsed }: ChatMessageProps) {
  const isUser = role === 'user'

  return (
    <div className={`flex items-start gap-2.5 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>

      {/* Avatar */}
      <div className={`w-6 h-6 rounded-lg flex items-center justify-center
                       flex-shrink-0 mt-0.5 ${
                         isUser
                           ? 'bg-slate-200'
                           : 'bg-indigo-600'
                       }`}>
        {isUser ? (
          <svg className="w-3.5 h-3.5 text-slate-600" fill="currentColor" viewBox="0 0 24 24">
            <path d="M7.5 6a4.5 4.5 0 119 0 4.5 4.5 0 01-9 0zM3.751 20.105a8.25 8.25 0 0116.498 0 .75.75 0 01-.437.695A18.683 18.683 0 0112 22.5c-2.786 0-5.433-.608-7.812-1.7a.75.75 0 01-.437-.695z" />
          </svg>
        ) : (
          <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 24 24">
            <path d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
          </svg>
        )}
      </div>

      <div className={`flex flex-col gap-1 max-w-[85%] ${isUser ? 'items-end' : 'items-start'}`}>

        {/* Message bubble */}
        <div className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${
          isUser
            ? 'bg-indigo-600 text-white rounded-tr-sm'
            : 'bg-white border border-slate-200 text-slate-800 rounded-tl-sm shadow-sm'
        }`}>
          {isUser ? (
            <p>{content}</p>
          ) : (
            <div className="prose prose-sm max-w-none">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  h1: ({ children }) => (
                    <h1 className="text-sm font-bold text-slate-900 mt-3 mb-1.5 first:mt-0">
                      {children}
                    </h1>
                  ),
                  h2: ({ children }) => (
                    <h2 className="text-sm font-bold text-slate-900 mt-2.5 mb-1 first:mt-0">
                      {children}
                    </h2>
                  ),
                  h3: ({ children }) => (
                    <h3 className="text-xs font-semibold text-slate-700 uppercase tracking-wide mt-2 mb-1 first:mt-0">
                      {children}
                    </h3>
                  ),
                  p: ({ children }) => (
                    <p className="mb-2 last:mb-0 text-slate-700 leading-relaxed">
                      {children}
                    </p>
                  ),
                  strong: ({ children }) => (
                    <strong className="font-semibold text-slate-900">{children}</strong>
                  ),
                  em: ({ children }) => (
                    <em className="text-slate-500 not-italic text-xs">{children}</em>
                  ),
                  ul: ({ children }) => (
                    <ul className="space-y-1 mb-2 last:mb-0 pl-1">{children}</ul>
                  ),
                  ol: ({ children }) => (
                    <ol className="space-y-1 mb-2 last:mb-0 pl-1 list-decimal list-inside">
                      {children}
                    </ol>
                  ),
                  li: ({ children }) => (
                    <li className="flex items-start gap-2 text-slate-700">
                      <span className="w-1 h-1 bg-indigo-400 rounded-full mt-2 flex-shrink-0" />
                      <span>{children}</span>
                    </li>
                  ),
                  table: ({ children }) => (
                    <div className="overflow-x-auto my-3 rounded-xl border border-slate-200 shadow-sm">
                      <table className="w-full text-xs border-collapse">{children}</table>
                    </div>
                  ),
                  thead: ({ children }) => (
                    <thead className="bg-indigo-50">{children}</thead>
                  ),
                  th: ({ children }) => (
                    <th className="px-3 py-2 text-left text-xs font-semibold text-indigo-700 whitespace-nowrap border-b border-indigo-100">
                      {children}
                    </th>
                  ),
                  tbody: ({ children }) => (
                    <tbody className="divide-y divide-slate-100">{children}</tbody>
                  ),
                  tr: ({ children }) => (
                    <tr className="hover:bg-slate-50 transition-colors">{children}</tr>
                  ),
                  td: ({ children }) => (
                    <td className="px-3 py-2 text-slate-700 whitespace-nowrap">
                      {children}
                    </td>
                  ),
                  hr: () => <hr className="my-3 border-slate-200" />,
                  blockquote: ({ children }) => (
                    <blockquote className="border-l-2 border-indigo-300 pl-3 my-2 text-slate-600 italic">
                      {children}
                    </blockquote>
                  ),
                  code: ({ children }) => (
                    <code className="bg-slate-100 text-indigo-600 px-1.5 py-0.5 rounded-md text-xs font-mono">
                      {children}
                    </code>
                  ),
                }}
              >
                {content}
              </ReactMarkdown >
            </div>
          )}
        </div>

        {/* Tool badge */}
        {!isUser && toolUsed && (
          <div className="flex items-center gap-1.5 px-1">
            <div className="w-1.5 h-1.5 bg-emerald-400 rounded-full" />
            <span className="text-xs text-slate-400">
              {toolUsed.split(',').map(t => t.trim().replace(/_/g, ' ')).join(' · ')}
            </span>
          </div>
        )}
      </div>
    </div>
  )
}