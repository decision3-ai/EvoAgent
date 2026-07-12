'use client'

import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { useNearWallet } from '@/contexts/near-wallet'
import { submitFeedback, trackEvent } from '@/lib/api-client'
import type { Message } from '@/lib/api-client'

function CopyButton({ text, className = '', onCopy }: { text: string; className?: string; onCopy?: () => void }) {
  const [copied, setCopied] = useState(false)

  const copy = async () => {
    await navigator.clipboard.writeText(text)
    onCopy?.()
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <button
      onClick={copy}
      className={`flex items-center gap-1.5 text-xs transition-colors ${
        copied ? 'text-white' : 'text-gray-500 hover:text-gray-200'
      } ${className}`}
      aria-label={copied ? 'Copied' : 'Copy'}
    >
      {copied ? (
        <>
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
          </svg>
          Copied
        </>
      ) : (
        <>
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8}
              d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
          </svg>
          Copy
        </>
      )}
    </button>
  )
}

function CodeBlock({ content, language, onCopy }: { content: string; language?: string; onCopy?: () => void }) {
  return (
    <div className="my-3 rounded-xl overflow-hidden border border-white/[0.12] bg-gray-900/70 shadow-lg">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-white/[0.04] border-b border-white/[0.08]">
        <span className="text-xs font-mono font-medium text-gray-400 tracking-wide">
          {language ?? 'code'}
        </span>
        <CopyButton text={content} onCopy={onCopy} />
      </div>
      {/* Code — max-height + both-axis scroll for long blocks */}
      <pre className="p-4 overflow-x-auto overflow-y-auto max-h-80 scrollbar-thin">
        <code className="text-sm font-mono text-gray-200 leading-6 block">{content}</code>
      </pre>
    </div>
  )
}

// Renders markdown + fenced code blocks (CodeBlock for ``` fences)
function renderRaw(
  content: string,
  onCodeCopy?: (index: number, language: string) => void,
): React.ReactNode {
  let blockIndex = 0
  return (
    <ReactMarkdown
      components={{
        pre: ({ children }) => <>{children}</>,
        p: ({ children, ...rest }) => (
          <p className="whitespace-pre-wrap" {...rest}>
            {children}
          </p>
        ),
        code: ({ className, children, ...rest }) => {
          const text = String(children)
          const match = /language-(\w+)/.exec(className || '')
          if (match) {
            const idx = blockIndex++
            const lang = match[1]
            return (
              <CodeBlock
                content={text.replace(/\n$/, '')}
                language={lang}
                onCopy={onCodeCopy ? () => onCodeCopy(idx, lang) : undefined}
              />
            )
          }
          if (text.endsWith('\n')) {
            const idx = blockIndex++
            return (
              <CodeBlock
                content={text.replace(/\n$/, '')}
                language={undefined}
                onCopy={onCodeCopy ? () => onCodeCopy(idx, '') : undefined}
              />
            )
          }
          return (
            <code className={className} {...rest}>
              {children}
            </code>
          )
        },
      }}
    >
      {content}
    </ReactMarkdown>
  )
}

const SECTIONS = {
  PLAN:        { label: 'Plan',        className: 'text-gray-300 border-white/20 bg-white/5' },
  CODE:        { label: 'Code',        className: 'text-gray-300 border-white/20 bg-white/5' },
  EXPLANATION: { label: 'Explanation', className: 'text-gray-300 border-white/20 bg-white/5' },
} as const

type SectionKey = keyof typeof SECTIONS

function parseAndRender(
  content: string,
  onCodeCopy?: (index: number, language: string) => void,
): React.ReactNode {
  const sectionRegex = /\*\*(PLAN|CODE|EXPLANATION):\*\*/g
  const chunks: Array<{ type: SectionKey | null; text: string }> = []
  let lastIndex = 0
  let lastType: SectionKey | null = null
  let match

  while ((match = sectionRegex.exec(content)) !== null) {
    const text = content.slice(lastIndex, match.index).trim()
    if (text) chunks.push({ type: lastType, text })
    lastType = match[1] as SectionKey
    lastIndex = match.index + match[0].length
  }

  const remaining = content.slice(lastIndex).trim()
  if (remaining) chunks.push({ type: lastType, text: remaining })

  // No structured sections — render as plain
  if (chunks.length === 0 || (chunks.length === 1 && chunks[0].type === null)) {
    return renderRaw(content, onCodeCopy)
  }

  return (
    <div className="space-y-3">
      {chunks.map((chunk, i) => {
        const meta = chunk.type ? SECTIONS[chunk.type] : null
        return (
          <div key={i}>
            {meta && (
              <span className={`inline-flex items-center text-xs font-semibold px-2 py-0.5 rounded border mb-2 ${meta.className}`}>
                {meta.label}
              </span>
            )}
            <div>{renderRaw(chunk.text, onCodeCopy)}</div>
          </div>
        )
      })}
    </div>
  )
}

function renderContent(
  content: string,
  onCodeCopy?: (index: number, language: string) => void,
): React.ReactNode {
  return parseAndRender(content, onCodeCopy)
}

function extractCodeBlocks(content: string): string[] {
  const blocks: string[] = []
  const regex = /```(?:\w*)\n?([\s\S]*?)```/g
  let match
  while ((match = regex.exec(content)) !== null) {
    if (match[1].trim()) blocks.push(match[1].trim())
  }
  return blocks
}

export function MessageBubble({
  message,
  workspaceId,
  sessionId,
  isLastAssistant = false,
}: {
  message: Message
  workspaceId: string
  sessionId: string
  isLastAssistant?: boolean
}) {
  const isUser = message.role === 'user'
  const { accountId } = useNearWallet()
  const [feedback, setFeedback] = useState<1 | 5 | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [feedbackError, setFeedbackError] = useState<string | null>(null)
  const [feedbackSaved, setFeedbackSaved] = useState(false)
  const [completed, setCompleted] = useState(false)
  const [completionSubmitting, setCompletionSubmitting] = useState(false)

  const handleCodeCopy = (codeBlockIndex: number, language: string) => {
    if (!accountId) return
    trackEvent(accountId, workspaceId, sessionId, message.id, 'code_copy', {
      code_block_index: codeBlockIndex,
      language,
    }).catch(() => {/* fire-and-forget */})
  }

  const handleFeedback = async (score: 1 | 5) => {
    if (!accountId || submitting || feedback !== null) return
    setSubmitting(true)
    setFeedbackError(null)
    try {
      await submitFeedback(accountId, workspaceId, sessionId, message.id, score)
      setFeedback(score)
      setFeedbackSaved(true)
      setTimeout(() => setFeedbackSaved(false), 3000)
    } catch {
      setFeedbackError('Ocjena nije spremljena — pokušaj ponovno')
    } finally {
      setSubmitting(false)
    }
  }

  const handleCompletion = async () => {
    if (!accountId || completionSubmitting || completed) return
    setCompletionSubmitting(true)
    try {
      await trackEvent(accountId, workspaceId, sessionId, null, 'completion', {})
      setCompleted(true)
    } finally {
      setCompletionSubmitting(false)
    }
  }

  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'} group`}>
      {/* Avatar */}
      {isUser ? (
        <div className="w-8 h-8 rounded-full shrink-0 flex items-center justify-center text-sm font-bold mt-0.5 bg-gray-800 border border-white/15 text-gray-300">
          Y
        </div>
      ) : (
        <img
          src="/3.png"
          alt=""
          className="mt-0.5 h-8 w-8 shrink-0 rounded-full object-cover ring-1 ring-white/10"
        />
      )}

      {/* Bubble */}
      <div className={`max-w-[78%] ${isUser ? 'items-end' : 'items-start'} flex flex-col gap-1`}>
        <div className="flex items-center gap-2 mb-0.5">
          <span className="text-xs text-gray-500">
            {isUser ? 'You' : 'Coding Partner'}
          </span>
          {message.latency_ms && (
            <span className="text-xs text-gray-600">{message.latency_ms}ms</span>
          )}
        </div>

        <div
          className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${
            isUser
              ? 'bg-white/10 border border-white/15 text-white rounded-tr-sm'
              : 'bg-white/5 border border-white/10 text-gray-100 rounded-tl-sm'
          }`}
        >
          {renderContent(message.content, isUser ? undefined : handleCodeCopy)}
        </div>

        {isLastAssistant && !isUser && (
          <div className="mt-2">
            <button
              onClick={handleCompletion}
              disabled={completed || completionSubmitting}
              className={`text-xs px-3 py-1.5 rounded-lg border transition-colors ${
                completed
                  ? 'border-white/20 bg-white/10 text-white cursor-not-allowed'
                  : 'border-white/10 bg-white/5 text-gray-400 hover:border-white/25 hover:bg-white/10 hover:text-white cursor-pointer'
              }`}
            >
              {completed ? '✅ Solved' : 'Did this solve it? ✅ Solved'}
            </button>
          </div>
        )}

        <div className="flex items-center gap-3">
          <span className="text-xs text-gray-600 opacity-0 group-hover:opacity-100 transition-opacity">
            {new Date(message.created_at).toLocaleTimeString([], {
              hour: '2-digit',
              minute: '2-digit',
            })}
          </span>

          {!isUser && (() => {
            const codeBlocks = extractCodeBlocks(message.content)
            return (
              <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                {/* Copy all code — only if message has code blocks */}
                {codeBlocks.length > 0 && (
                  <CopyButton
                    text={codeBlocks.join('\n\n')}
                    className="border border-white/10 rounded-lg px-2 py-1 bg-white/5 hover:bg-white/10"
                  />
                )}
                {/* Feedback */}
                <button
                  onClick={() => handleFeedback(5)}
                  disabled={submitting || feedback !== null}
                  className={`text-sm px-1.5 py-0.5 rounded transition-all cursor-pointer disabled:cursor-not-allowed ${
                    feedback === 5
                      ? 'text-green-500 scale-110'
                      : feedback === 1
                      ? 'text-gray-600 opacity-30'
                      : 'text-gray-600 hover:text-white'
                  }`}
                  aria-label="Thumbs up"
                >
                  👍
                </button>
                <button
                  onClick={() => handleFeedback(1)}
                  disabled={submitting || feedback !== null}
                  className={`text-sm px-1.5 py-0.5 rounded transition-all cursor-pointer disabled:cursor-not-allowed ${
                    feedback === 1
                      ? 'text-red-500 scale-110'
                      : feedback === 5
                      ? 'text-gray-600 opacity-30'
                      : 'text-gray-600 hover:text-white'
                  }`}
                  aria-label="Thumbs down"
                >
                  👎
                </button>
                {feedbackSaved && (
                  <span className="text-xs text-green-500">✓ Zabilježeno</span>
                )}
                {feedbackError && (
                  <span className="text-xs text-red-500">{feedbackError}</span>
                )}
              </div>
            )
          })()}
        </div>
      </div>
    </div>
  )
}
