'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { useNearWallet } from '@/contexts/near-wallet'
import Link from 'next/link'
import { createApiClient, streamChat, type Workspace, type Session, type Message } from '@/lib/api-client'
import { MessageBubble } from './message-bubble'

type Props = {
  workspace: Workspace
  sessions: Session[]
  initialMessages: Message[]
  sessionId: string
}

function groupSessionsByDate(sessions: Session[]) {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const yesterday = new Date(today)
  yesterday.setDate(yesterday.getDate() - 1)
  const lastWeek = new Date(today)
  lastWeek.setDate(lastWeek.getDate() - 7)

  const groups: { label: string; items: Session[] }[] = [
    { label: 'Today', items: [] },
    { label: 'Yesterday', items: [] },
    { label: 'Last 7 days', items: [] },
    { label: 'Older', items: [] },
  ]

  sessions.forEach((s) => {
    const date = new Date(s.updated_at)
    date.setHours(0, 0, 0, 0)
    if (date >= today) groups[0].items.push(s)
    else if (date >= yesterday) groups[1].items.push(s)
    else if (date >= lastWeek) groups[2].items.push(s)
    else groups[3].items.push(s)
  })

  return groups.filter((g) => g.items.length > 0)
}

export function ChatInterface({ workspace, sessions: initialSessions, initialMessages, sessionId }: Props) {
  const router = useRouter()
  const { accountId } = useNearWallet()

  const [messages, setMessages] = useState<Message[]>(initialMessages)
  const [sessions, setSessions] = useState<Session[]>(initialSessions)
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [streamingContent, setStreamingContent] = useState('')

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const userMsgAddedRef = useRef(false)

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages, streamingContent, scrollToBottom])

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current
    if (!textarea) return
    textarea.style.height = 'auto'
    textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px'
  }, [input])

  const sendMessage = async () => {
    if (!input.trim() || loading || !accountId) return

    const text = input.trim()
    setInput('')
    setLoading(true)
    setStreamingContent('')
    userMsgAddedRef.current = false

    try {
      const response = await streamChat(accountId, workspace.id, sessionId, text)

      if (!response.ok || !response.body) throw new Error('Stream unavailable')

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() ?? ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const event = JSON.parse(line.slice(6))

            if (event.type === 'start') {
              setMessages((prev) => [...prev, event.user_message])
              userMsgAddedRef.current = true
            } else if (event.type === 'token') {
              setStreamingContent((prev) => prev + event.text)
            } else if (event.type === 'done') {
              setStreamingContent('')
              setMessages((prev) => [...prev, event.assistant_message])
              setSessions((prev) =>
                prev.map((s) =>
                  s.id === sessionId
                    ? { ...s, title: event.session_title ?? s.title, message_count: s.message_count + 2 }
                    : s,
                ),
              )
            }
          } catch {
            // malformed event — skip
          }
        }
      }
    } catch (err) {
      console.error('Stream error, falling back to sync:', err)
      // Fallback: only add messages that were NOT already added via streaming
      try {
        const api = createApiClient(accountId)
        const res = await api.post(
          `/api/v1/workspaces/${workspace.id}/sessions/${sessionId}/chat`,
          { message: text },
        )
        const { user_message, assistant_message, session_title } = res.data
        setMessages((prev) => [
          ...prev,
          // Skip user_message if already added via stream's 'start' event
          ...(userMsgAddedRef.current ? [] : [user_message]),
          assistant_message,
        ])
        setSessions((prev) =>
          prev.map((s) =>
            s.id === sessionId
              ? { ...s, title: session_title ?? s.title, message_count: s.message_count + 2 }
              : s,
          ),
        )
      } catch (fallbackErr) {
        console.error('Fallback also failed:', fallbackErr)
      }
    } finally {
      setLoading(false)
      setStreamingContent('')
      textareaRef.current?.focus()
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    // Limit consecutive blank lines to 2 (keeps paste clean)
    const cleaned = e.target.value.replace(/\n{3,}/g, '\n\n')
    setInput(cleaned)
  }

  const createNewSession = async () => {
    try {
      if (!accountId) return

      const api = createApiClient(accountId)
      const res = await api.post(`/api/v1/workspaces/${workspace.id}/sessions/`, {
        title: 'New session',
      })

      setSessions((prev) => [res.data, ...prev])
      router.push(`/workspace/${workspace.id}/chat/${res.data.id}`)
    } catch (err) {
      console.error('Failed to create session:', err)
    }
  }

  const sessionGroups = groupSessionsByDate(sessions)
  const agentName = workspace.agent_profile?.name ?? 'Coding Partner'
  const agentModel = workspace.agent_profile?.model ?? 'gpt-4o'

  return (
    <div className="flex h-screen bg-gray-950 text-white overflow-hidden">
      {/* ── Sessions Sidebar ─────────────────────────────────────────────── */}
      <aside
        className={`${
          sidebarOpen ? 'w-60' : 'w-0'
        } transition-all duration-200 overflow-hidden border-r border-white/10 flex flex-col shrink-0`}
      >
        <div className="flex flex-col h-full py-4 px-3">
          {/* Workspace name */}
          <div className="px-2 mb-4">
            <Link
              href="/workspace"
              className="flex items-center gap-2 group"
            >
              <div className="w-6 h-6 rounded-md bg-gradient-to-br from-fuchsia-400 to-violet-600 flex items-center justify-center shrink-0 overflow-hidden">
                <img src="/logo.png" alt="AgentEvo" className="w-5 h-5 object-contain" />
              </div>
              <span className="font-semibold text-sm truncate group-hover:text-fuchsia-400 transition-colors">
                {workspace.name}
              </span>
            </Link>
          </div>

          {/* New session */}
          <button
            onClick={createNewSession}
            className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-gray-400 hover:text-white hover:bg-white/5 transition-colors mb-2 w-full text-left"
          >
            <span className="text-base leading-none">+</span>
            New session
          </button>

          {/* Session groups */}
          <div className="flex-1 overflow-y-auto space-y-4 mt-2">
            {sessionGroups.map((group) => (
              <div key={group.label}>
                <p className="text-xs text-gray-600 font-medium px-3 mb-1 uppercase tracking-wider">
                  {group.label}
                </p>
                {group.items.map((s) => (
                  <Link
                    key={s.id}
                    href={`/workspace/${workspace.id}/chat/${s.id}`}
                    className={`block px-3 py-2 rounded-lg text-sm transition-colors truncate ${
                      s.id === sessionId
                        ? 'bg-white/10 text-white'
                        : 'text-gray-400 hover:text-white hover:bg-white/5'
                    }`}
                  >
                    {s.title}
                  </Link>
                ))}
              </div>
            ))}

            {sessions.length === 0 && (
              <p className="text-xs text-gray-600 px-3">No sessions yet</p>
            )}
          </div>

          {/* Bottom: account + settings */}
          <div className="border-t border-white/10 pt-3 mt-3 space-y-1">
            <Link
              href={`/workspace/${workspace.id}/settings`}
              className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm text-gray-400 hover:text-white hover:bg-white/5 transition-colors"
            >
              <span>⚙️</span>
              Agent settings
            </Link>
            <div className="flex items-center gap-2.5 px-3 py-2">
              <div className="w-6 h-6 rounded-full bg-gradient-to-br from-fuchsia-400 to-violet-600 flex items-center justify-center text-xs font-bold shrink-0">
                N
              </div>
              <span className="text-sm text-gray-500 truncate">
                {accountId
                  ? accountId.length > 16
                    ? accountId.slice(0, 6) + '…' + accountId.slice(-4)
                    : accountId
                  : 'Account'}
              </span>
            </div>
          </div>
        </div>
      </aside>

      {/* ── Main Chat Area ───────────────────────────────────────────────── */}
      <div className="flex flex-col flex-1 min-w-0">
        {/* Header */}
        <header className="flex items-center justify-between px-4 py-3 border-b border-white/10 shrink-0">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-white/5 transition-colors"
              aria-label="Toggle sidebar"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
            <div className="flex items-center gap-2">
              <img src="/logo.png" alt="AgentEvo" className="w-8 h-8 object-contain drop-shadow-[0_0_6px_rgba(255,106,0,0.4)]" />
              <div>
                <span className="text-sm font-medium">{agentName}</span>
                <span className="ml-2 text-xs text-gray-500 font-mono">{agentModel}</span>
              </div>
            </div>
          </div>

          {workspace.tech_stack.length > 0 && (
            <div className="hidden sm:flex items-center gap-1.5">
              {workspace.tech_stack.slice(0, 4).map((tech) => (
                <span
                  key={tech}
                  className="text-xs bg-white/5 border border-white/10 px-2 py-0.5 rounded text-gray-400"
                >
                  {tech}
                </span>
              ))}
              {workspace.tech_stack.length > 4 && (
                <span className="text-xs text-gray-500">
                  +{workspace.tech_stack.length - 4}
                </span>
              )}
            </div>
          )}
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto">
          <div className="max-w-3xl mx-auto px-4 py-6 space-y-6">
            {messages.length === 0 && (
              <div className="text-center pt-16">
                <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-fuchsia-400 to-violet-600 flex items-center justify-center mx-auto mb-4 shadow-xl shadow-fuchsia-500/20 overflow-hidden">
                  <img src="/logo.png" alt="AgentEvo" className="w-12 h-12 object-contain" />
                </div>
                <h2 className="text-xl font-semibold mb-2">
                  {agentName} — ready to build
                </h2>
                <p className="text-gray-400 text-sm max-w-sm mx-auto leading-relaxed">
                  Working in{' '}
                  <span className="text-white font-medium">{workspace.name}</span>
                  {workspace.tech_stack.length > 0 && (
                    <>
                      {' '}·{' '}
                      <span className="text-gray-500">
                        {workspace.tech_stack.slice(0, 3).join(', ')}
                      </span>
                    </>
                  )}
                  . What are we building today?
                </p>
                <div className="mt-6 flex flex-wrap gap-2 justify-center">
                  {[
                    'Plan a new feature',
                    'Debug this error',
                    'Review my code',
                    'Write a function',
                    'Explain this concept',
                    'Refactor this module',
                  ].map((prompt) => (
                    <button
                      key={prompt}
                      onClick={() => setInput(prompt)}
                      className="text-xs bg-white/5 border border-white/10 hover:border-fuchsia-500/30 hover:bg-fuchsia-500/5 px-3 py-2 rounded-lg text-gray-400 hover:text-white transition-all"
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((msg) => (
              <MessageBubble
                key={msg.id}
                message={msg}
                workspaceId={workspace.id}
                sessionId={sessionId}
              />
            ))}

            {streamingContent && (
              <div className="flex gap-3">
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-fuchsia-400 to-violet-600 shrink-0 flex items-center justify-center mt-0.5 overflow-hidden">
                  <img src="/logo.png" alt="AgentEvo" className="w-6 h-6 object-contain" />
                </div>
                <div className="max-w-[78%] bg-white/5 border border-white/10 rounded-2xl rounded-tl-sm px-4 py-3 text-sm leading-relaxed text-gray-100">
                  <span className="whitespace-pre-wrap">{streamingContent}</span>
                  <span className="inline-block w-0.5 h-4 bg-fuchsia-400 animate-pulse ml-0.5 align-middle" />
                </div>
              </div>
            )}

            {loading && !streamingContent && (
              <div className="flex gap-3">
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-fuchsia-400 to-violet-600 shrink-0 flex items-center justify-center mt-0.5 overflow-hidden">
                  <img src="/logo.png" alt="AgentEvo" className="w-6 h-6 object-contain" />
                </div>
                <div className="bg-white/5 border border-white/10 rounded-2xl rounded-tl-sm px-4 py-3">
                  <div className="flex gap-1 items-center h-5">
                    <span className="w-1.5 h-1.5 rounded-full bg-fuchsia-400 animate-bounce [animation-delay:-0.3s]" />
                    <span className="w-1.5 h-1.5 rounded-full bg-fuchsia-400 animate-bounce [animation-delay:-0.15s]" />
                    <span className="w-1.5 h-1.5 rounded-full bg-fuchsia-400 animate-bounce" />
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Input area */}
        <div className="shrink-0 border-t border-white/10 px-4 py-4">
          <div className="max-w-3xl mx-auto">
            <div className="flex gap-3 items-end bg-white/5 border border-white/10 rounded-2xl px-4 py-3 focus-within:border-fuchsia-500/40 focus-within:bg-white/[0.07] transition-all">
              <textarea
                ref={textareaRef}
                value={input}
                onChange={handleInputChange}
                onKeyDown={handleKeyDown}
                placeholder={
                  workspace.tech_stack.length > 0
                    ? `Ask about ${workspace.tech_stack.slice(0, 2).join(', ')}, paste code, describe a task…`
                    : 'Describe a task, paste code, or ask a question…'
                }
                className="flex-1 bg-transparent resize-none outline-none text-white placeholder-gray-500 text-sm leading-relaxed min-h-[24px] max-h-[200px]"
                rows={1}
                disabled={loading}
                // eslint-disable-next-line jsx-a11y/no-autofocus
                autoFocus
              />
              <button
                onClick={sendMessage}
                disabled={loading || !input.trim()}
                className="w-8 h-8 rounded-xl bg-fuchsia-500 hover:bg-fuchsia-400 disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center transition-all shrink-0 shadow-lg shadow-fuchsia-500/30"
                aria-label="Send message"
              >
                {loading ? (
                  <span className="flex gap-0.5 items-center">
                    <span className="w-1 h-1 rounded-full bg-white animate-bounce [animation-delay:-0.2s]" />
                    <span className="w-1 h-1 rounded-full bg-white animate-bounce [animation-delay:-0.1s]" />
                    <span className="w-1 h-1 rounded-full bg-white animate-bounce" />
                  </span>
                ) : (
                  <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                  </svg>
                )}
              </button>
            </div>
            <p className="text-xs text-gray-600 text-center mt-2">
              ↵ Send &nbsp;·&nbsp; ⇧↵ New line
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
