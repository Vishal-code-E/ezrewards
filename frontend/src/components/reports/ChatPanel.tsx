'use client'

import { useState, useRef, useEffect } from 'react'
import { apiPost } from '@/lib/api'
import ChatMessage from './ChatMessage'

interface Message {
  role:     'user' | 'assistant'
  content:  string
  toolUsed?: string
}

interface ChatResponse {
  success:    boolean
  answer:     string
  tool_used:  string
  request_id: string
}

interface ChatPanelProps {
  reportContext?: string   // e.g. "wallet", "invitations" — undefined = all reports
}

const REPORT_LABELS: Record<string, string> = {
  'invitations':          'Invitation Status',
  'recognition':          'Recognition Activity',
  'recognition/given':    'Recognition Given',
  'recognition/received': 'Recognition Received',
  'seats':                'Active Seat Usage',
  'redemptions':          'Voucher Redemption',
  'wallet':               'Wallet Balance',
  'wallet/transactions':  'Wallet Transactions',
  'payments':             'Payment History',
}

function getWelcomeMessage(reportContext?: string): string {
  if (!reportContext) {
    return 'Hi! Ask me anything across all reports — invitations, recognition, wallet, payments, and more. I can query multiple reports to answer complex questions.'
  }
  const name = REPORT_LABELS[reportContext] ?? reportContext
  return `Hi! I can answer questions about the ${name} report. Ask me anything about this data. For other reports, head back to the main Reports page.`
}

function getSubtitle(reportContext?: string): string {
  if (!reportContext) return 'Ask across all reports'
  const name = REPORT_LABELS[reportContext] ?? reportContext
  return `Scoped to: ${name}`
}

export default function ChatPanel({ reportContext }: ChatPanelProps) {
  const [open,     setOpen]     = useState(false)
  const [messages, setMessages] = useState<Message[]>([
    {
      role:    'assistant',
      content: getWelcomeMessage(reportContext),
    },
  ])
  const [input,   setInput]   = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  // Reset messages when context changes (navigating between report pages)
  useEffect(() => {
    setMessages([
      {
        role:    'assistant',
        content: getWelcomeMessage(reportContext),
      },
    ])
  }, [reportContext])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function handleSend() {
    const message = input.trim()
    if (!message || loading) return

    setMessages((prev) => [...prev, { role: 'user', content: message }])
    setInput('')
    setLoading(true)

    try {
      const res = await apiPost<ChatResponse>('/api/chat/reports', {
        message,
        report_context: reportContext ?? null,
      })
      setMessages((prev) => [
        ...prev,
        {
          role:     'assistant',
          content:  res.answer,
          toolUsed: res.tool_used,
        },
      ])
    } catch (err: unknown) {
      setMessages((prev) => [
        ...prev,
        {
          role:    'assistant',
          content: err instanceof Error
            ? err.message
            : 'Something went wrong. Please try again.',
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <>
      {/* Floating button */}
      <button
        onClick={() => setOpen((o) => !o)}
        aria-label="Open chat"
        className="fixed bottom-6 right-6 w-14 h-14 bg-indigo-600 text-white
                   rounded-full shadow-lg hover:bg-indigo-700 transition-colors
                   flex items-center justify-center z-50"
      >
        {open ? (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        ) : (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 01-2.555-.337A5.972 5.972 0 015.41 20.97a5.969 5.969 0 01-.474-.065 4.48 4.48 0 00.978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25z" />
          </svg>
        )}
      </button>

      {/* Chat panel */}
      {open && (
        <div className="fixed bottom-24 right-6 w-[400px] h-[540px] bg-white rounded-2xl
                        shadow-2xl border border-slate-200 flex flex-col z-50">

          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center flex-shrink-0">
                <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
                </svg>
              </div>
              <div>
                <p className="text-sm font-semibold text-slate-900">Reports Assistant</p>
                <p className="text-xs text-slate-500">{getSubtitle(reportContext)}</p>
              </div>
            </div>

            {/* Context badge */}
            {reportContext && (
              <span className="text-xs bg-indigo-50 text-indigo-600 font-medium px-2 py-0.5 rounded-full">
                Focused
              </span>
            )}
            {!reportContext && (
              <span className="text-xs bg-emerald-50 text-emerald-600 font-medium px-2 py-0.5 rounded-full">
                All reports
              </span>
            )}
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
            {messages.map((msg, i) => (
              <ChatMessage
                key={i}
                role={msg.role}
                content={msg.content}
                toolUsed={msg.toolUsed}
              />
            ))}

            {loading && (
              <div className="flex items-start">
                <div className="bg-white border border-slate-200 rounded-2xl rounded-bl-sm px-4 py-2.5">
                  <div className="flex gap-1 items-center h-4">
                    <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce [animation-delay:-0.3s]" />
                    <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce [animation-delay:-0.15s]" />
                    <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" />
                  </div>
                </div>
              </div>
            )}

            <div ref={bottomRef} />
          </div>

          {/* Input */}
          <div className="px-3 py-3 border-t border-slate-100">
            <div className="flex items-center gap-2 bg-slate-50 rounded-xl px-3 py-2
                            border border-slate-200 focus-within:border-indigo-500
                            focus-within:ring-2 focus-within:ring-indigo-500/20 transition-colors">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={
                  reportContext
                    ? `Ask about ${REPORT_LABELS[reportContext] ?? reportContext}...`
                    : 'Ask about any report...'
                }
                disabled={loading}
                className="flex-1 bg-transparent text-sm text-slate-900
                           placeholder:text-slate-400 focus:outline-none disabled:opacity-50"
              />
              <button
                onClick={handleSend}
                disabled={loading || !input.trim()}
                className="w-7 h-7 bg-indigo-600 rounded-lg flex items-center justify-center
                           hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed
                           transition-colors flex-shrink-0"
              >
                <svg className="w-3.5 h-3.5 text-white" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.269 20.876L5.999 12zm0 0h7.5" />
                </svg>
              </button>
            </div>
            <p className="text-xs text-slate-400 text-center mt-2">Press Enter to send</p>
          </div>
        </div>
      )}
    </>
  )
}