'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useNearWallet } from '@/contexts/near-wallet'
import { createApiClient, fetchWorkspaces } from '@/lib/api-client'

export default function LoginPage() {
  const router = useRouter()
  const { loginWithEmail, connect } = useNearWallet()

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
      await loginWithEmail(email.trim(), password)
      // Token is now in localStorage — use it directly before React state settles
      const token = localStorage.getItem('email_auth_token')
      if (token) {
        const workspaces = await fetchWorkspaces(token)
        if (workspaces.length === 0) {
          const api = createApiClient(token)
          await api.post('/api/v1/workspaces/', { name: 'My First Project' })
        }
      }
      router.push('/workspace')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed')
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

        <h1 className="text-2xl font-bold mb-1">Sign in</h1>
        <p className="text-gray-400 text-sm mb-8">Welcome back. Enter your credentials to continue.</p>

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
            {loading ? 'Signing in…' : 'Sign in →'}
          </button>
        </form>

        <p className="text-center text-sm text-gray-500 mt-4">
          Don&apos;t have an account?{' '}
          <a href="/register" className="text-[#00D4AA] hover:underline">Register</a>
        </p>

        {/* Divider */}
        <div className="flex items-center gap-3 my-6">
          <div className="flex-1 border-t border-white/10" />
          <span className="text-xs text-gray-500">or</span>
          <div className="flex-1 border-t border-white/10" />
        </div>

        {/* NEAR wallet */}
        <button
          onClick={connect}
          className="w-full flex items-center justify-center gap-2 py-3 rounded-xl border border-white/10 text-gray-400 text-sm hover:border-white/20 hover:text-white transition-colors bg-white/3"
        >
          <svg width="18" height="18" viewBox="0 0 90 90" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M72.5 7.5L52.5 37.5L53.5 7.5H72.5Z" fill="currentColor" opacity="0.7" />
            <path d="M17.5 82.5L37.5 52.5L36.5 82.5H17.5Z" fill="currentColor" opacity="0.7" />
            <path d="M17.5 7.5H36.5L72.5 82.5H53.5L17.5 7.5Z" fill="currentColor" />
          </svg>
          Continue with NEAR wallet
        </button>
      </div>
    </div>
  )
}
