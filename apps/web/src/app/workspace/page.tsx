'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useNearWallet } from '@/contexts/near-wallet'
import { fetchWorkspaces, type Workspace } from '@/lib/api-client'

export default function WorkspacePage() {
  const { accountId, isConnected, isLoading } = useNearWallet()
  const router = useRouter()

  const [workspaces, setWorkspaces] = useState<Workspace[]>([])
  const [ready, setReady] = useState(false)

  useEffect(() => {
    if (isLoading) return
    if (!isConnected || !accountId) {
      router.replace('/')
      return
    }

    fetchWorkspaces(accountId)
      .then((ws) => {
        if (ws.length === 0) {
          router.replace('/workspace/new')
          return
        }
        setWorkspaces(ws)
        setReady(true)
      })
      .catch(() => {
        setReady(true)
      })
  }, [isLoading, isConnected, accountId, router])

  if (!ready) {
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
    <div className="min-h-screen bg-gray-950 text-white">
      <div className="max-w-4xl mx-auto px-6 py-12">
        {/* Header */}
        <div className="flex items-center justify-between mb-10">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-sky-400 to-violet-600 flex items-center justify-center font-bold shadow-lg">
              A
            </div>
            <span className="font-semibold text-lg tracking-tight">AgentEvo.io</span>
          </div>
          <Link
            href="/workspace/new"
            className="flex items-center gap-2 bg-sky-500 hover:bg-sky-400 text-white px-4 py-2 rounded-xl text-sm font-medium transition-all shadow-lg shadow-sky-500/25 hover:-translate-y-0.5"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            New Workspace
          </Link>
        </div>

        <h1 className="text-2xl font-bold mb-1">Your Workspaces</h1>
        <p className="text-gray-400 text-sm mb-8">
          Each workspace has its own coding partner, session history, and context.
        </p>

        {/* Workspace grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {workspaces.map((ws) => (
            <Link
              key={ws.id}
              href={`/workspace/${ws.id}`}
              className="group bg-white/5 border border-white/10 hover:border-sky-500/40 hover:bg-white/[0.07] rounded-2xl p-5 transition-all"
            >
              {/* Icon + name */}
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-sky-400 to-violet-600 flex items-center justify-center font-bold text-sm shrink-0 shadow-md">
                    {ws.name[0]?.toUpperCase() ?? 'W'}
                  </div>
                  <div>
                    <h2 className="font-semibold text-sm group-hover:text-sky-300 transition-colors">
                      {ws.name}
                    </h2>
                    {ws.is_default && (
                      <span className="text-xs text-gray-500">Default</span>
                    )}
                  </div>
                </div>
                <svg
                  className="w-4 h-4 text-gray-600 group-hover:text-sky-400 transition-colors mt-0.5 shrink-0"
                  fill="none" viewBox="0 0 24 24" stroke="currentColor"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M9 5l7 7-7 7" />
                </svg>
              </div>

              {/* Description */}
              {ws.description && (
                <p className="text-xs text-gray-400 mb-3 leading-relaxed line-clamp-2">
                  {ws.description}
                </p>
              )}

              {/* Tech stack */}
              {ws.tech_stack.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {ws.tech_stack.slice(0, 5).map((tech) => (
                    <span
                      key={tech}
                      className="text-xs bg-white/5 border border-white/10 px-2 py-0.5 rounded text-gray-400"
                    >
                      {tech}
                    </span>
                  ))}
                  {ws.tech_stack.length > 5 && (
                    <span className="text-xs text-gray-600">+{ws.tech_stack.length - 5}</span>
                  )}
                </div>
              )}
            </Link>
          ))}
        </div>
      </div>
    </div>
  )
}
