'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useNearWallet } from '@/contexts/near-wallet'
import { fetchWorkspaces, type Workspace } from '@/lib/api-client'

const NOISE_BG = `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.03'/%3E%3C/svg%3E")`

const glassCard: React.CSSProperties = {
  background: 'rgba(255,255,255,0.04)',
  border: '1px solid rgba(255,255,255,0.10)',
  borderRadius: '20px',
  padding: '28px',
  boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.08)',
}

const capabilities = [
  { icon: '⚡', title: 'Codes', text: 'Writes, debugs, and explains across any stack.' },
  { icon: '🧠', title: 'Learns', text: 'Remembers your patterns. Gets better every session.' },
  { icon: '🔄', title: 'Evolves', text: 'Powered by Decision3. Your agent improves itself.' },
]

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
        setWorkspaces(ws)
        setReady(true)
      })
      .catch(() => {
        setReady(true)
      })
  }, [isLoading, isConnected, accountId, router])

  if (!ready) {
    return (
      <div style={{ minHeight: '100vh', background: '#000', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px' }}>
          <div style={{ width: '48px', height: '48px', borderRadius: '16px', background: 'rgba(255,255,255,0.08)' }} />
          <div style={{ width: '160px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <div style={{ height: '8px', borderRadius: '99px', background: 'rgba(255,255,255,0.08)' }} />
            <div style={{ height: '8px', borderRadius: '99px', background: 'rgba(255,255,255,0.05)', width: '75%', margin: '0 auto' }} />
          </div>
        </div>
      </div>
    )
  }

  return (
    <div
      className="pb-24 md:pb-0"
      style={{ minHeight: '100vh', background: '#000', backgroundImage: NOISE_BG, color: 'white' }}
    >
      <div style={{ maxWidth: '896px', margin: '0 auto', padding: '48px 24px' }}>

        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '40px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <button className="md:hidden" style={{ padding: '8px', marginLeft: '-8px', color: 'rgba(156,163,175,1)', background: 'none', border: 'none', cursor: 'pointer' }}>
              <svg style={{ width: '24px', height: '24px' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
            <img src="/2.png" alt="EvoAgent" style={{ height: '80px', width: 'auto', objectFit: 'contain' }} />
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginRight: '16px' }}>
            <button
              onClick={() => { localStorage.clear(); router.push('/login') }}
              style={{ fontSize: '13px', color: 'rgba(156,163,175,1)', background: 'none', border: 'none', cursor: 'pointer', padding: '4px 8px' }}
            >
              Sign out
            </button>
            <Link
              href="/workspace/new"
              className="flex items-center gap-2 transition-all"
              style={{
                padding: '8px 16px',
                borderRadius: '12px',
                fontSize: '14px',
                fontWeight: '500',
                color: 'white',
                background: 'linear-gradient(135deg, rgba(255,255,255,0.08) 0%, rgba(255,255,255,0.03) 100%)',
                border: '1px solid rgba(255,255,255,0.15)',
                boxShadow: '0 8px 32px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.12), inset 0 -1px 0 rgba(0,0,0,0.2)',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'linear-gradient(135deg, rgba(255,255,255,0.12) 0%, rgba(255,255,255,0.06) 100%)'
                e.currentTarget.style.borderColor = 'rgba(255,255,255,0.25)'
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'linear-gradient(135deg, rgba(255,255,255,0.08) 0%, rgba(255,255,255,0.03) 100%)'
                e.currentTarget.style.borderColor = 'rgba(255,255,255,0.15)'
              }}
            >
              <svg style={{ width: '16px', height: '16px' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              New Workspace
            </Link>
          </div>
        </div>

        {workspaces.length === 0 ? (
          /* ── Empty state ──────────────────────────────────────────────── */
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', paddingTop: '48px', paddingBottom: '32px', gap: '40px' }}>

            {/* Hero text */}
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px' }}>
              <h1 style={{
                fontSize: '3.5rem',
                fontWeight: '800',
                letterSpacing: '-0.02em',
                margin: 0,
                background: 'linear-gradient(180deg, #fff 60%, rgba(255,255,255,0.7) 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                backgroundClip: 'text',
              }}>
                Your agent is ready.
              </h1>
              <p style={{ color: 'rgba(255,255,255,0.5)', fontSize: '1rem', maxWidth: '360px', lineHeight: '1.6', margin: 0 }}>
                Create a workspace. It starts learning from your first message.
              </p>
            </div>

            {/* CTA */}
            <Link
              href="/workspace/new"
              className="flex items-center justify-center gap-2 transition-all"
              style={{
                width: '320px',
                height: '56px',
                background: 'rgba(255,255,255,0.95)',
                color: '#000',
                fontWeight: '700',
                fontSize: '1rem',
                borderRadius: '14px',
                boxShadow: '0 0 40px rgba(255,255,255,0.15)',
                border: 'none',
                cursor: 'pointer',
                textDecoration: 'none',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'white'
                e.currentTarget.style.boxShadow = '0 0 60px rgba(255,255,255,0.25)'
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'rgba(255,255,255,0.95)'
                e.currentTarget.style.boxShadow = '0 0 40px rgba(255,255,255,0.15)'
              }}
            >
              <span>⚡</span> Create your first workspace
            </Link>

            {/* Capability cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px', width: '100%', maxWidth: '672px' }}>
              {capabilities.map((card) => (
                <div key={card.title} style={glassCard}>
                  <div style={{ fontSize: '2rem', marginBottom: '16px' }}>{card.icon}</div>
                  <h3 style={{ fontSize: '1.1rem', fontWeight: '700', color: 'white', marginBottom: '8px', margin: '0 0 8px 0' }}>{card.title}</h3>
                  <p style={{ fontSize: '0.875rem', color: 'rgba(255,255,255,0.5)', lineHeight: '1.6', margin: 0 }}>{card.text}</p>
                </div>
              ))}
            </div>

            {/* Footer */}
            <p style={{ color: 'rgba(255,255,255,0.2)', fontSize: '0.75rem', margin: 0 }}>
              Powered by Decision3 · Trust is only earned in the open.
            </p>
          </div>

        ) : (
          /* ── Workspace list ───────────────────────────────────────────── */
          <>
            <h1 style={{ fontSize: '1.5rem', fontWeight: '700', marginBottom: '4px' }}>Your Workspaces</h1>
            <p style={{ color: 'rgba(156,163,175,1)', fontSize: '14px', marginBottom: '32px' }}>
              Your evolving agent. Codes, learns, remembers — powered by Decision3.
            </p>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '16px' }}>
              {workspaces.map((ws) => (
                <Link
                  key={ws.id}
                  href={`/workspace/${ws.id}`}
                  className="group transition-all"
                  style={{
                    display: 'block',
                    borderRadius: '16px',
                    padding: '20px',
                    background: 'linear-gradient(135deg, rgba(255,255,255,0.08) 0%, rgba(255,255,255,0.03) 100%)',
                    border: '1px solid rgba(255,255,255,0.15)',
                    boxShadow: '0 8px 32px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.12), inset 0 -1px 0 rgba(0,0,0,0.2)',
                    textDecoration: 'none',
                    color: 'white',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = 'linear-gradient(135deg, rgba(255,255,255,0.12) 0%, rgba(255,255,255,0.06) 100%)'
                    e.currentTarget.style.borderColor = 'rgba(255,255,255,0.25)'
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = 'linear-gradient(135deg, rgba(255,255,255,0.08) 0%, rgba(255,255,255,0.03) 100%)'
                    e.currentTarget.style.borderColor = 'rgba(255,255,255,0.15)'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '12px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      <div style={{ width: '36px', height: '36px', borderRadius: '10px', overflow: 'hidden', flexShrink: 0, boxShadow: '0 0 0 1px rgba(255,255,255,0.1)' }}>
                        <img src="/2.png" alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                      </div>
                      <div>
                        <h2 style={{ fontWeight: '600', fontSize: '14px', color: 'white', margin: 0 }}>{ws.name}</h2>
                        {ws.is_default && (
                          <span style={{ fontSize: '12px', color: 'rgba(107,114,128,1)' }}>Default</span>
                        )}
                      </div>
                    </div>
                    <svg style={{ width: '16px', height: '16px', color: 'rgba(75,85,99,1)', flexShrink: 0, marginTop: '2px' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M9 5l7 7-7 7" />
                    </svg>
                  </div>

                  {ws.description && (
                    <p style={{ fontSize: '12px', color: 'rgba(156,163,175,1)', marginBottom: '12px', lineHeight: '1.6', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                      {ws.description}
                    </p>
                  )}

                  {ws.evo_points > 0 && (
                    <div style={{ marginBottom: '12px' }}>
                      <span style={{ fontSize: '12px', fontWeight: '600', color: 'rgba(209,213,219,1)', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', padding: '2px 8px', borderRadius: '99px' }}>
                        ⚡ {ws.evo_points} EP
                      </span>
                    </div>
                  )}

                  {ws.tech_stack.length > 0 && (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                      {ws.tech_stack.slice(0, 5).map((tech) => (
                        <span key={tech} style={{ fontSize: '12px', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', padding: '2px 8px', borderRadius: '4px', color: 'rgba(156,163,175,1)' }}>
                          {tech}
                        </span>
                      ))}
                      {ws.tech_stack.length > 5 && (
                        <span style={{ fontSize: '12px', color: 'rgba(75,85,99,1)' }}>+{ws.tech_stack.length - 5}</span>
                      )}
                    </div>
                  )}
                </Link>
              ))}
            </div>
          </>
        )}
      </div>

      {/* Mobile nav */}
      <nav className="md:hidden" style={{ position: 'fixed', bottom: 0, left: 0, right: 0, background: '#000', borderTop: '1px solid rgba(255,255,255,0.1)', padding: '12px 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', zIndex: 50 }}>
        <Link href="/" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px', color: 'rgba(107,114,128,1)', textDecoration: 'none' }}>
          <svg style={{ width: '24px', height: '24px' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
          </svg>
          <span style={{ fontSize: '10px', fontWeight: '500' }}>Home</span>
        </Link>
        <Link href="/workspace" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px', color: 'white', textDecoration: 'none' }}>
          <svg style={{ width: '24px', height: '24px' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
          </svg>
          <span style={{ fontSize: '10px', fontWeight: '500' }}>Workspaces</span>
        </Link>
        <Link href="/agents" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px', color: 'rgba(107,114,128,1)', textDecoration: 'none' }}>
          <svg style={{ width: '24px', height: '24px' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4M4 19h4m9-15v4m-2-2h4m-5 15l-3-4 3-4 3 4-3 4z" />
          </svg>
          <span style={{ fontSize: '10px', fontWeight: '500' }}>Agents</span>
        </Link>
        <Link href="#" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px', color: 'rgba(107,114,128,1)', textDecoration: 'none' }}>
          <svg style={{ width: '24px', height: '24px' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          <span style={{ fontSize: '10px', fontWeight: '500' }}>Settings</span>
        </Link>
      </nav>
    </div>
  )
}
