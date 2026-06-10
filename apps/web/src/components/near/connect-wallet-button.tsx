'use client'

import { useState } from 'react'
import { useNearWallet } from '@/contexts/near-wallet'
import { EmailAuthModal } from '@/components/auth/email-auth-modal'

type Props = {
  className?: string
  variant?: 'primary' | 'ghost'
}

export function ConnectWalletButton({ className = '', variant = 'primary' }: Props) {
  const { accountId, isConnected, isLoading, isEmailAuth, isNearAuth, connect, disconnect } = useNearWallet()
  const [showEmailModal, setShowEmailModal] = useState(false)

  if (isLoading) {
    return <div className={`h-9 w-36 rounded-lg bg-white/5 animate-pulse ${className}`} />
  }

  if (isConnected && accountId) {
    let label: string
    if (isNearAuth) {
      // accountId is a JWT — we don't display it; show the NEAR account from cookie instead
      const nearCookie = typeof document !== 'undefined'
        ? document.cookie.split('; ').find((c) => c.startsWith('near_account_id='))?.split('=')[1] ?? 'NEAR'
        : 'NEAR'
      label = nearCookie.length > 20
        ? nearCookie.slice(0, 8) + '…' + nearCookie.slice(-6)
        : nearCookie
    } else if (isEmailAuth) {
      label = accountId.length > 30 ? accountId.slice(0, 12) + '…' : accountId
    } else {
      label = accountId.length > 20
        ? accountId.slice(0, 8) + '…' + accountId.slice(-6)
        : accountId
    }

    return (
      <div className="flex items-center gap-2">
        <div className="flex items-center gap-1.5 bg-green-500/10 border border-green-500/20 rounded-lg px-3 py-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-green-400" />
          {isNearAuth && (
            <span className="text-xs text-green-500/70 font-mono mr-1">NEAR</span>
          )}
          <span className="text-sm text-green-300 font-mono">{label}</span>
        </div>
        <button
          onClick={disconnect}
          className="text-xs text-gray-500 hover:text-red-400 transition-colors px-2 py-1.5"
        >
          {isEmailAuth ? 'Sign out' : 'Disconnect'}
        </button>
      </div>
    )
  }

  const isGhost = variant === 'ghost'
  const baseBtn = 'flex items-center gap-2 px-4 py-2 rounded-lg transition-all font-medium text-sm hover:-translate-y-0.5'

  return (
    <>
      {showEmailModal && <EmailAuthModal onClose={() => setShowEmailModal(false)} />}

      <div className={`flex items-center gap-2 ${className}`}>
        {/* Email sign-in */}
        <button
          onClick={() => setShowEmailModal(true)}
          className={`${baseBtn} ${
            isGhost
              ? 'bg-transparent text-gray-400 hover:text-white shadow-none'
              : 'bg-fuchsia-500 hover:bg-fuchsia-400 text-white shadow-lg shadow-fuchsia-500/25'
          }`}
        >
          Sign in
        </button>

        {/* NEAR wallet sign-in */}
        <button
          onClick={connect}
          className="flex items-center gap-1.5 border border-white/10 hover:border-white/25 text-gray-400 hover:text-white px-3 py-2 rounded-lg transition-all text-sm hover:-translate-y-0.5"
          title="Sign in with NEAR wallet"
        >
          <svg width="14" height="14" viewBox="0 0 32 32" fill="currentColor" aria-hidden="true">
            <path d="M20.42 5.33L17.22 10.4a.51.51 0 00.72.7l3.17-2.7a.19.19 0 01.32.14V23.5a.19.19 0 01-.34.12l-9.5-13.42A2.27 2.27 0 009.72 9H9a2.17 2.17 0 00-2.17 2.17v9.66A2.17 2.17 0 009 23a2.2 2.2 0 001.85-1l3.2-5.07a.51.51 0 00-.72-.7L10.16 19a.19.19 0 01-.32-.14V8.5a.19.19 0 01.34-.12l9.5 13.42A2.27 2.27 0 0021.85 23H23a2.17 2.17 0 002.17-2.17v-9.66A2.17 2.17 0 0023 9a2.2 2.2 0 00-1.58.67z"/>
          </svg>
          NEAR
        </button>
      </div>
    </>
  )
}
