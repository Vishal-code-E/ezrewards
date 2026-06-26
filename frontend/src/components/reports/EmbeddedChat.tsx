'use client'

import { useState, useRef, useEffect } from 'react'
import { apiPost } from '@/lib/api'
import ChatMessage from './ChatMessage'
import { Content } from 'next/font/google'

interface Message {
  role:      'user' | 'assistant'
  content:   string
  toolUsed?: string
}

interface HistoryEntry {
  role:    'user' | 'assistant'
  content: string
}

interface ChatResponse {
  success:    boolean
  answer:     string
  tool_used:  string
  request_id: string
}

interface EmbeddedChatProps {
  reportContext?: string
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

const SUGGESTED_QUESTIONS_ALL = [
  'What is the wallet balance and burn rate?',
  'Which department has the most recognitions this month?',
  'How many pending invitations are there?',
  'Show me the top 5 most recognized employees',
]

const SUGGESTED_QUESTIONS_MAP: Record<string, string[]> = {
  'invitations':          ['How many invitations are pending?', 'What is the acceptance rate?', 'How many have expired?'],
  'recognition':          ['How many recognitions this month?', 'What is the participation rate?', 'Which badge is most used?'],
  'recognition/given':    ['Who gives the most recognition?', 'Show top 5 recognizers this month'],
  'recognition/received': ['Who is most recognized?', 'Show top 5 recipients this month'],
  'seats':                ['How many seats are available?', 'What is the seat utilization rate?'],
  'redemptions':          ['How many vouchers redeemed?', 'Which brand is most popular?', 'Any failed redemptions?'],
  'wallet':               ['What is the current balance?', 'When will the wallet run out?', 'What is the monthly burn rate?'],
  'wallet/transactions':  ['Show recent transactions', 'How many credits vs debits?', 'What was the last recharge amount?'],
  'payments':             ['Show payment history', 'Any failed payments?', 'What is the total billed this year?'],
}

function getWelcomeMessage(reportContext?: string): string {
  if (!reportContext) {
    return "Ask me anything about your workspace data. I can query across all 9 reports and give you combined insights."
  }
  const name = REPORT_LABELS[reportContext] ?? reportContext
  return `I'm focused on the **${name}** report. Ask me anything about this data — I'll give you a precise, data-driven answer.`
}

export default function EmbeddedChat({ reportContext }: EmbeddedChatProps) {
  const [messages, setMessages] = useState<Message[]>([
    { role: 'assistant', content: getWelcomeMessage(reportContext) },
  ])
  const [input,   setInput]   = useState('')
  const [loading, setLoading] = useState(false)
  const [history, setHistory] = useState<HistoryEntry[]>([])
  const bottomRef = useRef<HTMLDivElement>(null)

  const suggestedQuestions = reportContext
    ? (SUGGESTED_QUESTIONS_MAP[reportContext] ?? SUGGESTED_QUESTIONS_ALL)
    : SUGGESTED_QUESTIONS_ALL

  const showSuggestions = messages.length === 1

  useEffect(() => {
    setMessages([{ role: 'assistant', content: getWelcomeMessage(reportContext) }])
    setHistory([])
  }, [reportContext])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function handleSend(messageText?: string) {
    const message = (messageText ?? input).trim()
    if (!message || loading) return

    setMessages((prev) => [...prev, { role: 'user', content: message }])
    setInput('')
    setLoading(true)

    try {
      const res = await apiPost<ChatResponse>('/api/chat/reports', {
        message,
        report_context: reportContext ?? null,
        history,
      })
      setMessages((prev) => [
        ...prev,
        {
          role:     'assistant',
          content:  res.answer,
          toolUsed: res.tool_used,
        },
      ])

      const truncated = res.answer.length > 500
        ? res.answer.slice(0,500) + '...'
        : res.answer

        setHistory((prev) => {
        const updated = [
          ...prev,
          { role: 'user' as const,      content: message  },
          { role: 'assistant' as const, content: message  },
        ]
        return updated.slice(-6)

    })
    } catch (err: unknown) {
      setMessages((prev) => [
        ...prev,
        {
          role:    'assistant',
          content: err instanceof Error ? err.message : 'Something went wrong. Please try again.',
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
    <div className="mt-10">
      {/* Section label */}
      <div className="flex items-center gap-3 mb-4">
        <div className="flex items-center gap-2">
          <div className="w-1 h-5 bg-indigo-600 rounded-full" />
          <h2 className="text-sm font-semibold text-slate-900">
            {reportContext ? 'Report Assistant' : 'Analytics Assistant'}
          </h2>
        </div>
        <span className={`text-xs font-medium px-2.5 py-0.5 rounded-full ${
          reportContext
            ? 'bg-indigo-50 text-indigo-600 border border-indigo-100'
            : 'bg-emerald-50 text-emerald-700 border border-emerald-100'
        }`}>
          {reportContext
            ? `Focused: ${REPORT_LABELS[reportContext] ?? reportContext}`
            : 'All 12 reports'}
        </span>
        {!reportContext && (
          <span className="text-xs text-slate-400">· Multi-tool enabled</span>
        )}
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm">

        {/* Messages area */}
        <div className="min-h-[320px] max-h-[560px] overflow-y-auto px-5 py-5 space-y-4 bg-slate-50/40">
          {messages.map((msg, i) => (
            <ChatMessage
              key={i}
              role={msg.role}
              content={msg.content}
              toolUsed={msg.toolUsed}
            />
          ))}

          {/* Suggested question chips */}
          {showSuggestions && (
            <div className="pt-1">
              <p className="text-xs text-slate-400 mb-2 font-medium">Try asking:</p>
              <div className="flex flex-wrap gap-2">
                {suggestedQuestions.map((q) => (
                  <button
                    key={q}
                    onClick={() => handleSend(q)}
                    className="text-xs bg-white hover:bg-indigo-50 text-slate-600
                               hover:text-indigo-600 border border-slate-200
                               hover:border-indigo-200 rounded-lg px-3 py-1.5
                               transition-all duration-150 text-left shadow-sm"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Loading indicator */}
          {loading && (
            <div className="flex items-start gap-2.5">
              <div className="w-6 h-6 bg-indigo-600 rounded-lg flex items-center
                              justify-center flex-shrink-0 mt-0.5">
                <svg className="w-3 h-3 text-white animate-pulse" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
                </svg>
              </div>
              <div className="bg-white border border-slate-200 rounded-2xl rounded-bl-sm px-4 py-3 shadow-sm">
                <div className="flex gap-1 items-center">
                  <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce [animation-delay:-0.3s]" />
                  <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce [animation-delay:-0.15s]" />
                  <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce" />
                </div>
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* Input area */}
        <div className="px-4 py-3 bg-white border-t border-slate-100">
          <div className="flex items-center gap-3">
            <div className="flex-1 flex items-center gap-2 bg-slate-50 rounded-xl
                            px-4 py-2.5 border border-slate-200
                            focus-within:border-indigo-400 focus-within:bg-white
                            focus-within:ring-3 focus-within:ring-indigo-500/10
                            transition-all duration-150">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={
                  reportContext
                    ? `Ask about ${REPORT_LABELS[reportContext] ?? reportContext}...`
                    : 'Ask about any report — I can combine data from multiple sources...'
                }
                disabled={loading}
                className="flex-1 bg-transparent text-sm text-slate-900
                           placeholder:text-slate-400 focus:outline-none
                           disabled:opacity-50 min-w-0"
              />
            </div>
            <button
              onClick={() => handleSend()}
              disabled={loading || !input.trim()}
              className="h-10 px-4 bg-indigo-600 text-white text-sm font-medium
                         rounded-xl hover:bg-indigo-700 disabled:opacity-40
                         disabled:cursor-not-allowed transition-colors
                         flex items-center gap-2 flex-shrink-0"
            >
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.269 20.876L5.999 12zm0 0h7.5" />
              </svg>
              Ask
            </button>
          </div>
          <p className="text-xs text-slate-400 mt-2 text-center">
            Press <kbd className="bg-slate-100 text-slate-500 px-1 py-0.5 rounded text-xs font-mono">Enter</kbd> to send
          </p>
        </div>
      </div>
    </div>
  )
}