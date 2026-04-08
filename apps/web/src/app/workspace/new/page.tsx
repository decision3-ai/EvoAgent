'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useNearWallet } from '@/contexts/near-wallet'
import { createApiClient } from '@/lib/api-client'

const TECH_OPTIONS = [
  'TypeScript', 'Python', 'Rust', 'Go', 'Java',
  'Next.js', 'React', 'Vue', 'FastAPI', 'Django',
  'Node.js', 'PostgreSQL', 'MongoDB', 'Redis', 'Docker',
]

export default function NewWorkspacePage() {
  const router = useRouter()
  const { accountId } = useNearWallet()

  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [selectedStack, setSelectedStack] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const toggleStack = (tech: string) => {
    setSelectedStack((prev) =>
      prev.includes(tech) ? prev.filter((t) => t !== tech) : [...prev, tech],
    )
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) return

    setLoading(true)
    setError('')

    try {
      if (!accountId) throw new Error('Not authenticated')

      const api = createApiClient(accountId)
      const res = await api.post('/api/v1/workspaces/', {
        name: name.trim(),
        description: description.trim() || null,
        tech_stack: selectedStack,
      })

      router.push(`/workspace/${res.data.id}`)
    } catch {
      setError('Failed to create workspace. Is the API running?')
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white flex items-center justify-center px-4">
      {/* Background glow */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-fuchsia-500/8 rounded-full blur-3xl" />
      </div>

      <div className="relative w-full max-w-lg">
        {/* Logo */}
        <div className="flex items-center gap-2.5 mb-10">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-fuchsia-400 to-violet-600 flex items-center justify-center shadow-lg overflow-hidden">
            <img src="/logo.png" alt="AgentEvo" className="w-7 h-7 object-contain" />
          </div>
          <span className="font-semibold text-xl tracking-tight">AgentEvo.io</span>
        </div>

        <h1 className="text-3xl font-bold mb-2">Set up your workspace</h1>
        <p className="text-gray-400 mb-8">
          Your workspace is where you and your coding partner will work together.
          You can always change these settings later.
        </p>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Name */}
          <div>
            <label className="block text-sm font-medium mb-2" htmlFor="name">
              Workspace name <span className="text-red-400">*</span>
            </label>
            <input
              id="name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. My SaaS Project"
              className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-fuchsia-500/50 focus:ring-1 focus:ring-fuchsia-500/30 transition-colors"
              required
              autoFocus
            />
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium mb-2" htmlFor="description">
              What are you building?{' '}
              <span className="text-gray-500 font-normal">(optional)</span>
            </label>
            <textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Brief description of your project or goal…"
              rows={3}
              className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-fuchsia-500/50 focus:ring-1 focus:ring-fuchsia-500/30 transition-colors resize-none"
            />
          </div>

          {/* Tech stack */}
          <div>
            <label className="block text-sm font-medium mb-3">
              Tech stack{' '}
              <span className="text-gray-500 font-normal">(optional — helps your partner)</span>
            </label>
            <div className="flex flex-wrap gap-2">
              {TECH_OPTIONS.map((tech) => {
                const active = selectedStack.includes(tech)
                return (
                  <button
                    key={tech}
                    type="button"
                    onClick={() => toggleStack(tech)}
                    className={`px-3 py-1.5 rounded-lg text-sm transition-all ${
                      active
                        ? 'bg-fuchsia-500/20 border border-fuchsia-500/50 text-fuchsia-300'
                        : 'bg-white/5 border border-white/10 text-gray-400 hover:border-white/20 hover:text-white'
                    }`}
                  >
                    {tech}
                  </button>
                )
              })}
            </div>
          </div>

          {error && (
            <p className="text-red-400 text-sm bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-3">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading || !name.trim()}
            className="w-full bg-fuchsia-500 hover:bg-fuchsia-400 disabled:opacity-50 disabled:cursor-not-allowed text-white py-3.5 rounded-xl font-semibold transition-all shadow-lg shadow-fuchsia-500/25 hover:-translate-y-0.5 disabled:hover:translate-y-0"
          >
            {loading ? 'Creating workspace…' : 'Create workspace & start building →'}
          </button>
        </form>
      </div>
    </div>
  )
}
