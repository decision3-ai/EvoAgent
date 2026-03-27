'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { DashboardSidebar } from '@/components/dashboard-sidebar'
import { useNearWallet } from '@/contexts/near-wallet'

export default function AgentsPage() {
  const router = useRouter()
  const { isConnected, isLoading } = useNearWallet()

  useEffect(() => {
    if (!isLoading && !isConnected) {
      router.replace('/')
    }
  }, [isConnected, isLoading, router])

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-950 text-white flex items-center justify-center">
        <div className="text-gray-400">Loading…</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white flex">
      <DashboardSidebar />

      <main className="flex-1 overflow-y-auto">
        <div className="max-w-5xl mx-auto px-8 py-8">
          {/* Header */}
          <div className="flex items-center justify-between mb-8">
            <div>
              <div className="flex items-center gap-2 text-gray-400 text-sm mb-2">
                <Link href="/dashboard" className="hover:text-white transition-colors">
                  Dashboard
                </Link>
                <span>/</span>
                <span className="text-white">Agents</span>
              </div>
              <h1 className="text-2xl font-bold">Agents</h1>
              <p className="text-gray-400 text-sm mt-1">
                Your AI agents and their evolution status
              </p>
            </div>
            <button className="bg-sky-500 hover:bg-sky-400 text-white px-5 py-2.5 rounded-lg font-medium transition-colors text-sm shadow-lg shadow-sky-500/20">
              + New Agent
            </button>
          </div>

          {/* Filter bar */}
          <div className="flex items-center gap-3 mb-6">
            {['All', 'Active', 'Evolving', 'Paused'].map((filter) => (
              <button
                key={filter}
                className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
                  filter === 'All'
                    ? 'bg-sky-500/15 text-sky-400'
                    : 'text-gray-400 hover:text-white hover:bg-white/5'
                }`}
              >
                {filter}
              </button>
            ))}
          </div>

          {/* Empty state */}
          <div className="bg-white/5 border border-white/10 rounded-2xl p-16 text-center">
            <div className="text-5xl mb-4">⚡</div>
            <h2 className="text-xl font-semibold mb-2">No agents yet</h2>
            <p className="text-gray-400 text-sm max-w-md mx-auto">
              Your agents will appear here once created. Each agent tracks its
              own generation, fitness score, and interaction history.
            </p>
            <div className="mt-8 flex items-center justify-center gap-6 text-sm text-gray-500">
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-sky-400" />
                Generation tracking
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-violet-400" />
                Fitness scoring
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-green-400" />
                Auto-evolution
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
