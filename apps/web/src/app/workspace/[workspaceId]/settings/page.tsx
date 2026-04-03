'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useNearWallet } from '@/contexts/near-wallet'
import Link from 'next/link'
import { createApiClient, updateWorkspace, type Workspace } from '@/lib/api-client'

const TECH_OPTIONS = [
  'TypeScript', 'Python', 'Rust', 'Go', 'Java',
  'Next.js', 'React', 'Vue', 'FastAPI', 'Django',
  'Node.js', 'PostgreSQL', 'MongoDB', 'Redis', 'Docker',
]

const MODELS = [
  { id: 'claude-haiku-4-5-20251001', label: 'AgentEvo Fast',     provider: 'v1', desc: 'Fastest responses, ideal for everyday coding tasks' },
  { id: 'claude-sonnet-4-5-20250929', label: 'AgentEvo Balanced', provider: 'v2', desc: 'Best balance of speed and reasoning quality' },
  { id: 'claude-sonnet-4-6',          label: 'AgentEvo Pro',      provider: 'v3', desc: 'Latest model, highest quality responses' },
  { id: 'claude-opus-4-5-20251101',   label: 'AgentEvo Max',      provider: 'v4', desc: 'Most powerful, best for complex architecture tasks' },
]

type SaveStatus = 'idle' | 'saving' | 'saved' | 'error'

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="border border-white/10 rounded-2xl p-6 space-y-5">
      <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">{title}</h2>
      {children}
    </div>
  )
}

function SaveBar({ status, onSave, onCancel }: { status: SaveStatus; onSave: () => void; onCancel: () => void }) {
  return (
    <div className="flex items-center gap-4">
      <button
        onClick={onSave}
        disabled={status === 'saving'}
        className="bg-sky-500 hover:bg-sky-400 disabled:opacity-50 disabled:cursor-not-allowed text-white px-8 py-3 rounded-xl font-semibold transition-all shadow-lg shadow-sky-500/25"
      >
        {status === 'saving' ? 'Saving…' : 'Save changes'}
      </button>
      {status === 'saved' && (
        <span className="text-sm text-green-400 flex items-center gap-1.5">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
          </svg>
          Saved
        </span>
      )}
      {status === 'error' && (
        <span className="text-sm text-red-400">Failed to save. Try again.</span>
      )}
      <button
        onClick={onCancel}
        className="text-sm text-gray-400 hover:text-white transition-colors ml-auto"
      >
        Cancel
      </button>
    </div>
  )
}

export default function SettingsPage() {
  const params = useParams()
  const router = useRouter()
  const { accountId } = useNearWallet()
  const workspaceId = params.workspaceId as string

  const [workspace, setWorkspace] = useState<Workspace | null>(null)

  // Workspace fields
  const [wsName, setWsName] = useState('')
  const [wsDescription, setWsDescription] = useState('')
  const [wsTechStack, setWsTechStack] = useState<string[]>([])
  const [wsStatus, setWsStatus] = useState<SaveStatus>('idle')

  // Agent fields
  const [agentName, setAgentName] = useState('')
  const [model, setModel] = useState('claude-haiku-4-5-20251001')
  const [systemPrompt, setSystemPrompt] = useState('')
  const [temperature, setTemperature] = useState(0.7)
  const [agentStatus, setAgentStatus] = useState<SaveStatus>('idle')

  useEffect(() => {
    if (!accountId) return
    const api = createApiClient(accountId)
    api.get(`/api/v1/workspaces/${workspaceId}`).then((res) => {
      const ws: Workspace = res.data
      setWorkspace(ws)
      setWsName(ws.name)
      setWsDescription(ws.description ?? '')
      setWsTechStack(ws.tech_stack)
      if (ws.agent_profile) {
        setAgentName(ws.agent_profile.name)
        setModel(ws.agent_profile.model)
        setSystemPrompt(ws.agent_profile.system_prompt)
        setTemperature(ws.agent_profile.temperature)
      }
    })
  }, [workspaceId, accountId])

  const toggleTech = (tech: string) =>
    setWsTechStack((prev) => prev.includes(tech) ? prev.filter((t) => t !== tech) : [...prev, tech])

  const saveWorkspace = async () => {
    if (!accountId || !wsName.trim()) return
    setWsStatus('saving')
    try {
      await updateWorkspace(accountId, workspaceId, {
        name: wsName.trim(),
        description: wsDescription.trim() || null,
        tech_stack: wsTechStack,
      })
      setWsStatus('saved')
      setTimeout(() => setWsStatus('idle'), 2500)
    } catch {
      setWsStatus('error')
      setTimeout(() => setWsStatus('idle'), 3000)
    }
  }

  const saveAgent = async () => {
    if (!accountId) return
    setAgentStatus('saving')
    try {
      const api = createApiClient(accountId)
      await api.patch(`/api/v1/workspaces/${workspaceId}/agent`, {
        name: agentName,
        model,
        system_prompt: systemPrompt,
        temperature,
      })
      setAgentStatus('saved')
      setTimeout(() => setAgentStatus('idle'), 2500)
    } catch {
      setAgentStatus('error')
      setTimeout(() => setAgentStatus('idle'), 3000)
    }
  }

  if (!workspace) {
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
      <div className="max-w-2xl mx-auto px-6 py-10">
        {/* Breadcrumb */}
        <div className="flex items-center gap-2 text-sm text-gray-400 mb-8">
          <Link href="/workspace" className="hover:text-white transition-colors">Workspaces</Link>
          <span>/</span>
          <Link href={`/workspace/${workspaceId}`} className="hover:text-white transition-colors">
            {workspace.name}
          </Link>
          <span>/</span>
          <span className="text-white">Settings</span>
        </div>

        <h1 className="text-2xl font-bold mb-1">Settings</h1>
        <p className="text-gray-400 text-sm mb-8">
          Configure your workspace and coding partner.
        </p>

        <div className="space-y-6">
          {/* ── Workspace ── */}
          <Section title="Workspace">
            <div>
              <label className="block text-sm font-medium mb-2">
                Name <span className="text-red-400">*</span>
              </label>
              <input
                type="text"
                value={wsName}
                onChange={(e) => setWsName(e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-sky-500/50 transition-colors"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">
                Description{' '}
                <span className="text-gray-500 font-normal">(optional)</span>
              </label>
              <textarea
                value={wsDescription}
                onChange={(e) => setWsDescription(e.target.value)}
                rows={2}
                placeholder="What are you building?"
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-sky-500/50 transition-colors resize-none text-sm"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-3">
                Tech stack{' '}
                <span className="text-gray-500 font-normal">(helps your coding partner)</span>
              </label>
              <div className="flex flex-wrap gap-2">
                {TECH_OPTIONS.map((tech) => {
                  const active = wsTechStack.includes(tech)
                  return (
                    <button
                      key={tech}
                      type="button"
                      onClick={() => toggleTech(tech)}
                      className={`px-3 py-1.5 rounded-lg text-sm transition-all ${
                        active
                          ? 'bg-sky-500/20 border border-sky-500/50 text-sky-300'
                          : 'bg-white/5 border border-white/10 text-gray-400 hover:border-white/20 hover:text-white'
                      }`}
                    >
                      {tech}
                    </button>
                  )
                })}
              </div>
            </div>

            <SaveBar status={wsStatus} onSave={saveWorkspace} onCancel={() => router.back()} />
          </Section>

          {/* ── Coding Partner ── */}
          <Section title="Coding Partner">
            <div>
              <label className="block text-sm font-medium mb-2">Agent name</label>
              <input
                type="text"
                value={agentName}
                onChange={(e) => setAgentName(e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-sky-500/50 transition-colors"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-3">Model</label>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {MODELS.map((m) => (
                  <button
                    key={m.id}
                    onClick={() => setModel(m.id)}
                    className={`text-left p-4 rounded-xl border transition-all ${
                      model === m.id
                        ? 'border-sky-500/50 bg-sky-500/10'
                        : 'border-white/10 bg-white/5 hover:border-white/20'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-medium text-sm">{m.label}</span>
                      <span className="text-xs text-gray-500">{m.provider}</span>
                    </div>
                    <p className="text-xs text-gray-400">{m.desc}</p>
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">
                Temperature —{' '}
                <span className="text-sky-400 font-mono">{temperature.toFixed(1)}</span>
              </label>
              <p className="text-xs text-gray-500 mb-3">
                Lower = more focused. Higher = more creative.
              </p>
              <input
                type="range" min="0" max="1" step="0.1"
                value={temperature}
                onChange={(e) => setTemperature(parseFloat(e.target.value))}
                className="w-full accent-sky-500"
              />
              <div className="flex justify-between text-xs text-gray-600 mt-1">
                <span>Precise (0.0)</span>
                <span>Creative (1.0)</span>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">System prompt</label>
              <p className="text-xs text-gray-500 mb-3">
                Defines persona, priorities, and communication style.
              </p>
              <textarea
                value={systemPrompt}
                onChange={(e) => setSystemPrompt(e.target.value)}
                rows={10}
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white text-sm font-mono focus:outline-none focus:border-sky-500/50 transition-colors resize-none leading-relaxed"
              />
            </div>

            <SaveBar status={agentStatus} onSave={saveAgent} onCancel={() => router.back()} />
          </Section>
        </div>
      </div>
    </div>
  )
}
