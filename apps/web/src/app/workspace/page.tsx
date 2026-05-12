'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { BrandIcon } from '@/components/brand-icon'
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
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-fuchsia-400 to-violet-600 animate-pulse shadow-lg shadow-fuchsia-500/20" />
          <div className="space-y-2 w-40">
            <div className="h-2 rounded-full bg-white/10 animate-pulse" />
            <div className="h-2 rounded-full bg-white/10 animate-pulse w-3/4 mx-auto" />
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white pb-24 md:pb-0">
      <div className="max-w-4xl mx-auto px-6 py-12">
        {/* Header */}
        <div className="flex items-center justify-between mb-10">
          <div className="flex items-center gap-3">
            {/* Hamburger menu (mobile only) */}
            <button className="md:hidden p-2 -ml-2 text-gray-400 hover:text-white transition-colors">
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
            <BrandIcon className="h-9 w-9" />
            <span className="font-semibold text-lg tracking-tight">EVOAGENT</span>
          </div>
          <Link
            href="/workspace/new"
            className="flex items-center gap-2 bg-fuchsia-500 hover:bg-fuchsia-400 text-white px-4 py-2 rounded-xl text-sm font-medium transition-all shadow-lg shadow-fuchsia-500/25 hover:-translate-y-0.5"
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
              className="group bg-white/5 border border-white/10 hover:border-fuchsia-500/40 hover:bg-white/[0.07] rounded-2xl p-5 transition-all"
            >
              {/* Icon + name */}
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-xl overflow-hidden shrink-0 shadow-md ring-1 ring-white/10">
                    <img src="/2.png" alt="" className="h-full w-full object-cover" />
                  </div>
                  <div>
                    <h2 className="font-semibold text-sm group-hover:text-fuchsia-300 transition-colors">
                      {ws.name}
                    </h2>
                    {ws.is_default && (
                      <span className="text-xs text-gray-500">Default</span>
                    )}
                  </div>
                </div>
                <svg
                  className="w-4 h-4 text-gray-600 group-hover:text-fuchsia-400 transition-colors mt-0.5 shrink-0"
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

              {/* EvoPoints */}
              {ws.evo_points > 0 && (
                <div className="flex items-center gap-1.5 mb-3">
                  <span className="text-xs font-semibold text-fuchsia-400 bg-fuchsia-500/10 border border-fuchsia-500/20 px-2 py-0.5 rounded-full">
                    ⚡ {ws.evo_points} EP
                  </span>
                </div>
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

      {/* Bottom Navigation (Mobile only) */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 bg-gray-900 border-t border-white/10 px-6 py-3 flex items-center justify-between z-50">
        <Link href="/" className="flex flex-col items-center gap-1 text-gray-500 hover:text-fuchsia-400 transition-colors">
          <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
          </svg>
          <span className="text-[10px] font-medium">Home</span>
        </Link>
        <Link href="/workspace" className="flex flex-col items-center gap-1 text-fuchsia-400 transition-colors">
          <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
          </svg>
          <span className="text-[10px] font-medium">Workspaces</span>
        </Link>
        <Link href="/agents" className="flex flex-col items-center gap-1 text-gray-500 hover:text-fuchsia-400 transition-colors">
          <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4M4 19h4m9-15v4m-2-2h4m-5 15l-3-4 3-4 3 4-3 4z" />
          </svg>
          <span className="text-[10px] font-medium">Agents</span>
        </Link>
        <Link href="#" className="flex flex-col items-center gap-1 text-gray-500 hover:text-fuchsia-400 transition-colors">
          <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          <span className="text-[10px] font-medium">Settings</span>
        </Link>
      </nav>
    </div>
  )
}
