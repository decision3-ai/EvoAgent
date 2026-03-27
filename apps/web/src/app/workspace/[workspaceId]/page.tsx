'use client'

import { useEffect } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { useNearWallet } from '@/contexts/near-wallet'
import { fetchSessions, createApiClient } from '@/lib/api-client'

export default function WorkspaceIndexPage() {
  const { workspaceId } = useParams<{ workspaceId: string }>()
  const router = useRouter()
  const { accountId, isConnected, isLoading } = useNearWallet()

  useEffect(() => {
    if (isLoading) return
    if (!isConnected || !accountId) {
      router.replace('/')
      return
    }

    const init = async () => {
      try {
        const sessions = await fetchSessions(accountId, workspaceId)

        if (sessions.length > 0) {
          const latest = sessions.find((s) => s.status === 'active') ?? sessions[0]
          router.replace(`/workspace/${workspaceId}/chat/${latest.id}`)
          return
        }

        const api = createApiClient(accountId)
        const res = await api.post(`/api/v1/workspaces/${workspaceId}/sessions/`, {
          title: 'New session',
        })
        router.replace(`/workspace/${workspaceId}/chat/${res.data.id}`)
      } catch {
        router.replace(`/workspace/${workspaceId}/chat/new`)
      }
    }

    init()
  }, [isLoading, isConnected, accountId, workspaceId, router])

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center">
      <div className="text-gray-400">Loading…</div>
    </div>
  )
}
