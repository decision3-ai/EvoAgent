'use client'

import { useState } from 'react'
import type { Message } from '@/lib/api-client'

function CodeBlock({ content, language }: { content: string; language?: string }) {
  const [copied, setCopied] = useState(false)

  const copy = async () => {
    await navigator.clipboard.writeText(content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="my-3 rounded-xl overflow-hidden border border-white/10">
      <div className="flex items-center justify-between px-4 py-2 bg-white/5 border-b border-white/10">
        <span className="text-xs text-gray-400 font-mono">{language ?? 'code'}</span>
        <button
          onClick={copy}
          className="text-xs text-gray-400 hover:text-white transition-colors"
        >
          {copied ? '✓ Copied' : 'Copy'}
        </button>
      </div>
      <pre className="p-4 overflow-x-auto bg-gray-900/60">
        <code className="text-sm font-mono text-gray-200 leading-relaxed">{content}</code>
      </pre>
    </div>
  )
}

function renderContent(content: string) {
  const parts: React.ReactNode[] = []
  const codeBlockRegex = /```(\w*)\n?([\s\S]*?)```/g
  let lastIndex = 0
  let match

  while ((match = codeBlockRegex.exec(content)) !== null) {
    if (match.index > lastIndex) {
      parts.push(
        <span key={lastIndex} className="whitespace-pre-wrap">
          {content.slice(lastIndex, match.index)}
        </span>,
      )
    }
    parts.push(
      <CodeBlock key={match.index} language={match[1] || undefined} content={match[2].trim()} />,
    )
    lastIndex = match.index + match[0].length
  }

  if (lastIndex < content.length) {
    parts.push(
      <span key={lastIndex} className="whitespace-pre-wrap">
        {content.slice(lastIndex)}
      </span>,
    )
  }

  return parts.length > 0 ? parts : <span className="whitespace-pre-wrap">{content}</span>
}

export function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'} group`}>
      {/* Avatar */}
      <div
        className={`w-8 h-8 rounded-full shrink-0 flex items-center justify-center text-sm font-bold mt-0.5 ${
          isUser
            ? 'bg-sky-500/20 border border-sky-500/30 text-sky-400'
            : 'bg-gradient-to-br from-sky-400 to-violet-600 text-white shadow-lg'
        }`}
      >
        {isUser ? 'Y' : 'A'}
      </div>

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
              ? 'bg-sky-500/15 border border-sky-500/20 text-white rounded-tr-sm'
              : 'bg-white/5 border border-white/10 text-gray-100 rounded-tl-sm'
          }`}
        >
          {renderContent(message.content)}
        </div>

        <span className="text-xs text-gray-600 opacity-0 group-hover:opacity-100 transition-opacity">
          {new Date(message.created_at).toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit',
          })}
        </span>
      </div>
    </div>
  )
}
