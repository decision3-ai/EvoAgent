'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useNearWallet } from '@/contexts/near-wallet'
import Link from 'next/link'
import { createApiClient, type Workspace } from '@/lib/api-client'

const MODELS = [
  { id: 'gpt-4o', label: 'GPT-4o', provider: 'OpenAI', desc: 'Most capable, best for complex tasks' },
  { id: 'gpt-4o-mini', label: 'GPT-4o mini', provider: 'OpenAI', desc: 'Fast and cost-effective' },
  { id: 'claude-3-5-sonnet-20241022', label: 'Claude 3.5 Sonnet', provider: 'Anthropic', desc: 'Excellent at coding and reasoning' },
  { id: 'claude-3-haiku-20240307', label: 'Claude 3 Haiku', provider: 'Anthropic', desc: 'Fast and affordable' },
]

export default function SettingsPage() {
  const params = useParams()
  const router = useRouter()
  const { accountId } = useNearWallet()
  const workspaceId = params.workspaceId as string

  const [workspace, setWorkspace] = useState<Workspace | null>(null)
  const [agentName, setAgentName] = useState('')
  const [model, setModel] = useState('gpt-4o')
  const [systemPrompt, setSystemPrompt] = useState('')
  const [temperature, setTemperature] = useState(0.7)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    const load = async () => {
      if (!accountId) return
      const api = createApiClient(accountId)
      const res = await api.get(`/api/v1/workspaces/${workspaceId}`)
      const ws: Workspace = res.data
      setWorkspace(ws)
      if (ws.agent_profile) {
        setAgentName(ws.agent_profile.name)
        setModel(ws.agent_profile.model)
        setSystemPrompt(ws.agent_profile.system_prompt)
        setTemperature(ws.agent_profile.temperature)
      }
    }
    load()
  }, [workspaceId, accountId])

  const save = async () => {
    setSaving(true)
    try {
      if (!accountId) return
      const api = createApiClient(accountId)
      await api.patch(`/api/v1/workspaces/${workspaceId}/agent`, {
        name: agentName,
        model,
        system_prompt: systemPrompt,
        temperature,
      })
      setSaved(true)
      setTimeout(() => setSaved(false), 2500)
    } finally {
      setSaving(false)
    }
  }

  if (!workspace) {
    return (
      <div className="min-h-screen bg-gray-950 text-white flex items-center justify-center">
        <div className="text-gray-400">Loading…</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <div className="max-w-2xl mx-auto px-6 py-10">
        {/* Breadcrumb */}
        <div className="flex items-center gap-2 text-sm text-gray-400 mb-8">
          <Link href={`/workspace/${workspaceId}`} className="hover:text-white transition-colors">
            {workspace.name}
          </Link>
          <span>/</span>
          <span className="text-white">Agent Settings</span>
        </div>

        <h1 className="text-2xl font-bold mb-1">Coding Partner Config</h1>
        <p className="text-gray-400 text-sm mb-8">
          Customize how your coding partner thinks, communicates, and behaves.
        </p>

        <div className="space-y-8">
          {/* Agent name */}
          <div>
            <label className="block text-sm font-medium mb-2">Agent name</label>
            <input
              type="text"
              value={agentName}
              onChange={(e) => setAgentName(e.target.value)}
              className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-sky-500/50 transition-colors"
            />
          </div>

          {/* Model */}
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

          {/* Temperature */}
          <div>
            <label className="block text-sm font-medium mb-2">
              Temperature —{' '}
              <span className="text-sky-400 font-mono">{temperature.toFixed(1)}</span>
            </label>
            <p className="text-xs text-gray-500 mb-3">
              Lower = more focused and deterministic. Higher = more creative.
            </p>
            <input
              type="range"
              min="0"
              max="1"
              step="0.1"
              value={temperature}
              onChange={(e) => setTemperature(parseFloat(e.target.value))}
              className="w-full accent-sky-500"
            />
            <div className="flex justify-between text-xs text-gray-600 mt-1">
              <span>Precise (0.0)</span>
              <span>Creative (1.0)</span>
            </div>
          </div>

          {/* System prompt */}
          <div>
            <label className="block text-sm font-medium mb-2">System prompt</label>
            <p className="text-xs text-gray-500 mb-3">
              Defines your coding partner&apos;s persona, priorities, and communication style.
            </p>
            <textarea
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
              rows={10}
              className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white text-sm font-mono focus:outline-none focus:border-sky-500/50 transition-colors resize-none leading-relaxed"
            />
          </div>

          {/* Save button */}
          <div className="flex items-center gap-4">
            <button
              onClick={save}
              disabled={saving}
              className="bg-sky-500 hover:bg-sky-400 disabled:opacity-50 text-white px-8 py-3 rounded-xl font-semibold transition-all shadow-lg shadow-sky-500/25"
            >
              {saving ? 'Saving…' : 'Save changes'}
            </button>
            {saved && (
              <span className="text-sm text-green-400 flex items-center gap-1.5">
                ✓ Saved
              </span>
            )}
            <button
              onClick={() => router.back()}
              className="text-sm text-gray-400 hover:text-white transition-colors ml-auto"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
