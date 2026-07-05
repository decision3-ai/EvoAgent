'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useNearWallet } from '@/contexts/near-wallet'
import { createApiClient } from '@/lib/api-client'

export default function RegisterPage() {
  const router = useRouter()
  const { registerWithEmail } = useNearWallet()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email.trim() || !password) return

    setLoading(true)
    setError('')

    try {
      await registerWithEmail(email.trim(), password)
      // Token is now in localStorage — use it directly before React state settles
      const token = localStorage.getItem('email_auth_token')
      if (token) {
        const api = createApiClient(token)
        const wsRes = await api.post('/api/v1/workspaces/', { name: 'My First Project' })
        const workspaceId = wsRes.data.id
        const sessRes = await api.post(`/api/v1/workspaces/${workspaceId}/sessions/`, { title: 'New session' })
        router.push(`/workspace/${workspaceId}/chat/${sessRes.data.id}`)
        return
      }
      router.push('/workspace')
    } catch (err) {
      console.error('Registration error:', err)
      setError(err instanceof Error ? err.message : 'Registration failed')
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white flex items-center justify-center px-4">
      {/* Background glow */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-[#00D4AA]/8 rounded-full blur-3xl" />
      </div>

      <div className="relative w-full max-w-sm">
        {/* Logo */}
        <div className="flex items-center gap-2.5 mb-10">
          <img src="/2.png" alt="EvoAgent" style={{ height: '48px', width: 'auto', objectFit: 'contain' }} />
          <span className="font-semibold text-xl tracking-tight">EVOAGENT</span>
        </div>

        <h1 className="text-2xl font-bold mb-1">Create account</h1>
        <p className="text-gray-400 text-sm mb-8">Get started with your AI coding partner.</p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-2" htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-[#00B4A0]/50 focus:ring-1 focus:ring-[#00B4A0]/30 transition-colors"
              required
              autoFocus
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-2" htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-[#00B4A0]/50 focus:ring-1 focus:ring-[#00B4A0]/30 transition-colors"
              required
            />
          </div>

          {error && (
            <p className="text-red-400 text-sm bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-3">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading || !email.trim() || !password}
            className="w-full bg-[#00B4A0] hover:bg-[#00C4B0] disabled:opacity-50 disabled:cursor-not-allowed text-white py-3.5 rounded-xl font-semibold transition-all shadow-lg shadow-[#00B4A0]/25 hover:-translate-y-0.5 disabled:hover:translate-y-0"
          >
            {loading ? 'Creating account…' : 'Create account →'}
          </button>
        </form>

        <p className="text-center text-sm text-gray-500 mt-4">
          Already have an account?{' '}
          <a href="/login" className="text-[#00D4AA] hover:underline">Sign in</a>
        </p>
      </div>
    </div>
  )
}
