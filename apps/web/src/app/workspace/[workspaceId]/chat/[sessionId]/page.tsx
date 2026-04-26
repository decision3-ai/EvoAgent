'use client'

import { useEffect, useState, useCallback } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { useNearWallet } from '@/contexts/near-wallet'
import {
  fetchWorkspaces,
  fetchSessions,
  fetchMessages,
  fetchWorkspaceStatus,
  type Workspace,
  type Session,
  type Message,
  type WorkspaceStatus,
} from '@/lib/api-client'
import { ChatInterface } from '@/components/chat/chat-interface'

function useCountdown(targetIso: string | null) {
  const [secondsLeft, setSecondsLeft] = useState<number>(0)

  useEffect(() => {
    if (!targetIso) return
    const target = new Date(targetIso).getTime()
    const tick = () => {
      const diff = Math.max(0, Math.floor((target - Date.now()) / 1000))
      setSecondsLeft(diff)
    }
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [targetIso])

  const hours = Math.floor(secondsLeft / 3600)
  const minutes = Math.floor((secondsLeft % 3600) / 60)
  const seconds = secondsLeft % 60

  return { secondsLeft, hours, minutes, seconds }
}

function MaintenancePage({
  status,
  onReady,
}: {
  status: WorkspaceStatus
  onReady: () => void
}) {
  const { secondsLeft, hours, minutes, seconds } = useCountdown(status.next_available)
  const evolved = status.message === 'evolved'

  // When countdown reaches zero, trigger a re-check
  useEffect(() => {
    if (!evolved && secondsLeft === 0 && status.next_available) {
      const timer = setTimeout(onReady, 3000)
      return () => clearTimeout(timer)
    }
  }, [secondsLeft, evolved, status.next_available, onReady])

  const pad = (n: number) => String(n).padStart(2, '0')

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center relative overflow-hidden">
      {/* Background glow */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full bg-fuchsia-900/20 blur-3xl" />
      </div>

      <div className="relative z-10 flex flex-col items-center gap-8 px-6 text-center max-w-md">
        {/* Logo pulse */}
        <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-fuchsia-400 to-violet-600 shadow-lg shadow-fuchsia-500/30 flex items-center justify-center animate-pulse">
          <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
          </svg>
        </div>

        {evolved ? (
          <>
            <div>
              <h1 className="text-2xl font-semibold text-white mb-2">
                Your agent evolved overnight.
              </h1>
              <p className="text-gray-400 text-lg">Ready to help 🚀</p>
            </div>
            <button
              onClick={onReady}
              className="px-6 py-3 rounded-xl bg-gradient-to-r from-fuchsia-500 to-violet-600 text-white font-medium hover:from-fuchsia-400 hover:to-violet-500 transition-all shadow-lg shadow-fuchsia-500/20"
            >
              Start chatting
            </button>
          </>
        ) : (
          <>
            <div>
              <h1 className="text-2xl font-semibold text-white mb-2">
                Your agent is evolving tonight.
              </h1>
              <p className="text-gray-400 text-lg">Come back in a bit ☕</p>
            </div>

            {status.next_available && secondsLeft > 0 && (
              <div className="flex gap-4">
                {[
                  { label: 'HR', value: pad(hours) },
                  { label: 'MIN', value: pad(minutes) },
                  { label: 'SEC', value: pad(seconds) },
                ].map(({ label, value }) => (
                  <div key={label} className="flex flex-col items-center gap-1">
                    <div className="w-16 h-16 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center">
                      <span className="text-2xl font-mono font-semibold text-white">{value}</span>
                    </div>
                    <span className="text-xs text-gray-500 tracking-widest">{label}</span>
                  </div>
                ))}
              </div>
            )}

            {secondsLeft === 0 && status.next_available && (
              <p className="text-gray-400 text-sm animate-pulse">Checking status…</p>
            )}
          </>
        )}
      </div>
    </div>
  )
}

export default function ChatPage() {
  const { workspaceId, sessionId } = useParams<{ workspaceId: string; sessionId: string }>()
  const router = useRouter()
  const { accountId, isConnected, isLoading } = useNearWallet()

  const [workspace, setWorkspace] = useState<Workspace | null>(null)
  const [sessions, setSessions] = useState<Session[]>([])
  const [messages, setMessages] = useState<Message[]>([])
  const [workspaceStatus, setWorkspaceStatus] = useState<WorkspaceStatus | null>(null)
  const [ready, setReady] = useState(false)

  const loadStatus = useCallback(async () => {
    if (!accountId) return
    const s = await fetchWorkspaceStatus(accountId, workspaceId).catch(() => null)
    setWorkspaceStatus(s)
  }, [accountId, workspaceId])

  useEffect(() => {
    if (isLoading) return
    if (!isConnected || !accountId) {
      router.replace('/')
      return
    }

    const load = async () => {
      const [workspaces, sess, msgs, status] = await Promise.all([
        fetchWorkspaces(accountId).catch(() => [] as Workspace[]),
        fetchSessions(accountId, workspaceId).catch(() => [] as Session[]),
        fetchMessages(accountId, workspaceId, sessionId).catch(() => [] as Message[]),
        fetchWorkspaceStatus(accountId, workspaceId).catch(() => null),
      ])

      const ws = workspaces.find((w) => w.id === workspaceId)
      if (!ws) {
        router.replace('/workspace')
        return
      }

      setWorkspace(ws)
      setSessions(sess)
      setMessages(msgs)
      setWorkspaceStatus(status)
      setReady(true)
    }

    load()
  }, [isLoading, isConnected, accountId, workspaceId, sessionId, router])

  // Poll status every 30s while in maintenance
  useEffect(() => {
    if (!ready || !workspaceStatus?.maintenance_mode) return
    const id = setInterval(loadStatus, 30_000)
    return () => clearInterval(id)
  }, [ready, workspaceStatus?.maintenance_mode, loadStatus])

  if (!ready || !workspace) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-fuchsia-400 to-violet-600 animate-pulse shadow-lg shadow-fuchsia-500/20" />
          <div className="space-y-2 w-40">
            <div className="h-2 rounded-full bg-white/10 animate-pulse" />
            <div className="h-2 rounded-full bg-white/10 animate-pulse w-3/4 mx-auto" />
          </div>
        </div>
      </div>
    )
  }

  if (workspaceStatus?.maintenance_mode || workspaceStatus?.message === 'evolved') {
    return (
      <MaintenancePage
        status={workspaceStatus}
        onReady={async () => {
          await loadStatus()
          // If maintenance is fully cleared, dismiss the page
          setWorkspaceStatus((prev) =>
            prev ? { ...prev, maintenance_mode: false, message: '' } : prev,
          )
        }}
      />
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
