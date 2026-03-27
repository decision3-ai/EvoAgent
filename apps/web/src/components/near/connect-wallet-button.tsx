'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useNearWallet } from '@/contexts/near-wallet'

type Props = {
  className?: string
  variant?: 'primary' | 'ghost'
}

export function ConnectWalletButton({ className = '', variant = 'primary' }: Props) {
  const { accountId, isConnected, isLoading, connect, disconnect } = useNearWallet()
  const router = useRouter()

  useEffect(() => {
    if (isConnected && accountId) {
      router.push('/workspace')
    }
  }, [isConnected, accountId, router])

  if (isLoading) {
    return (
      <div
        className={`h-9 w-36 rounded-lg bg-white/5 animate-pulse ${className}`}
      />
    )
  }

  if (isConnected && accountId) {
    return (
      <div className="flex items-center gap-2">
        {/* NEAR account badge */}
        <div className="flex items-center gap-1.5 bg-green-500/10 border border-green-500/20 rounded-lg px-3 py-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-green-400" />
          <span className="text-sm text-green-300 font-mono">
            {accountId.length > 20
              ? accountId.slice(0, 8) + '…' + accountId.slice(-6)
              : accountId}
          </span>
        </div>

        <button
          onClick={disconnect}
          className="text-xs text-gray-500 hover:text-red-400 transition-colors px-2 py-1.5"
        >
          Disconnect
        </button>
      </div>
    )
  }

  if (variant === 'ghost') {
    return (
      <button
        onClick={connect}
        className={`text-sm text-gray-400 hover:text-white transition-colors px-3 py-2 ${className}`}
      >
        Connect Wallet
      </button>
    )
  }

  return (
    <button
      onClick={connect}
      className={`flex items-center gap-2 bg-sky-500 hover:bg-sky-400 text-white px-4 py-2 rounded-lg transition-all font-medium text-sm shadow-lg shadow-sky-500/25 hover:-translate-y-0.5 ${className}`}
    >
      {/* NEAR logo mark */}
      <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
        <path d="M17.76 3.27L14.1 8.85a.4.4 0 00.64.48l3.62-5.08a.4.4 0 01.64.48L12.4 13.7a.4.4 0 01-.8 0V6.25a.4.4 0 00-.8 0v7.45a.4.4 0 01-.8 0L3.4 4.73a.4.4 0 01.64-.48L7.66 9.33a.4.4 0 00.64-.48L4.24 3.27A2 2 0 001 5.07v13.86A2.07 2.07 0 003.07 21H20.93A2.07 2.07 0 0023 18.93V5.07a2 2 0 00-3.24-1.8z" />
      </svg>
      Connect NEAR Wallet
    </button>
  )
}
