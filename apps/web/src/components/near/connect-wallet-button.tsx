'use client'

import { useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useNearWallet } from '@/contexts/near-wallet'
import { EmailAuthModal } from '@/components/auth/email-auth-modal'

type Props = {
  className?: string
  variant?: 'primary' | 'ghost'
}

export function ConnectWalletButton({ className = '', variant = 'primary' }: Props) {
  const { accountId, isConnected, isLoading, isEmailAuth, disconnect } = useNearWallet()
  const [showEmailModal, setShowEmailModal] = useState(false)
  const router = useRouter()
  const hasMounted = useRef(false)

  useEffect(() => {
    if (!hasMounted.current) {
      hasMounted.current = true
      return
    }
    if (isConnected && accountId) {
      router.push('/workspace')
    }
  }, [isConnected, accountId, router])

  if (isLoading) {
    return <div className={`h-9 w-36 rounded-lg bg-white/5 animate-pulse ${className}`} />
  }

  if (isConnected && accountId) {
    const label = isEmailAuth
      ? accountId.length > 30
        ? accountId.slice(0, 12) + '…'
        : accountId
      : accountId.length > 20
        ? accountId.slice(0, 8) + '…' + accountId.slice(-6)
        : accountId

    return (
      <div className="flex items-center gap-2">
        <div className="flex items-center gap-1.5 bg-green-500/10 border border-green-500/20 rounded-lg px-3 py-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-green-400" />
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

  return (
    <>
      {showEmailModal && <EmailAuthModal onClose={() => setShowEmailModal(false)} />}

      <div className={`flex items-center gap-2 ${className}`}>
        {/* Primary: email login */}
        <button
          onClick={() => setShowEmailModal(true)}
          className={`flex items-center gap-2 bg-fuchsia-500 hover:bg-fuchsia-400 text-white px-4 py-2 rounded-lg transition-all font-medium text-sm shadow-lg shadow-fuchsia-500/25 hover:-translate-y-0.5 ${variant === 'ghost' ? 'bg-transparent text-gray-400 hover:text-white shadow-none' : ''}`}
        >
          Sign in
        </button>

        {/* NEAR wallet — coming in V2 */}
        <span className="text-xs text-gray-600 hidden sm:inline">
          NEAR Wallet — <span className="text-fuchsia-700">V2</span>
        </span>
      </div>
    </>
  )
}
