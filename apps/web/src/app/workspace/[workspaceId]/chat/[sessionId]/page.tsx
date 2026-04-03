'use client'

import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { useNearWallet } from '@/contexts/near-wallet'
import {
  fetchWorkspaces,
  fetchSessions,
  fetchMessages,
  type Workspace,
  type Session,
  type Message,
} from '@/lib/api-client'
import { ChatInterface } from '@/components/chat/chat-interface'

export default function ChatPage() {
  const { workspaceId, sessionId } = useParams<{ workspaceId: string; sessionId: string }>()
  const router = useRouter()
  const { accountId, isConnected, isLoading } = useNearWallet()

  const [workspace, setWorkspace] = useState<Workspace | null>(null)
  const [sessions, setSessions] = useState<Session[]>([])
  const [messages, setMessages] = useState<Message[]>([])
  const [ready, setReady] = useState(false)

  useEffect(() => {
    if (isLoading) return
    if (!isConnected || !accountId) {
      router.replace('/')
      return
    }

    const load = async () => {
      const [workspaces, sess, msgs] = await Promise.all([
        fetchWorkspaces(accountId).catch(() => [] as Workspace[]),
        fetchSessions(accountId, workspaceId).catch(() => [] as Session[]),
        fetchMessages(accountId, workspaceId, sessionId).catch(() => [] as Message[]),
      ])

      const ws = workspaces.find((w) => w.id === workspaceId)
      if (!ws) {
        router.replace('/workspace')
        return
      }

      setWorkspace(ws)
      setSessions(sess)
      setMessages(msgs)
      setReady(true)
    }

    load()
  }, [isLoading, isConnected, accountId, workspaceId, sessionId, router])

  if (!ready || !workspace) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-sky-400 to-violet-600 animate-pulse shadow-lg shadow-sky-500/20" />
          <div className="space-y-2 w-40">
            <div className="h-2 rounded-full bg-white/10 animate-pulse" />
            <div className="h-2 rounded-full bg-white/10 animate-pulse w-3/4 mx-auto" />
          </div>
        </div>
      </div>
    )
  }

  return (
    <ChatInterface
      workspace={workspace}
      sessions={sessions}
      initialMessages={messages}
      sessionId={sessionId}
    />
  )
}
