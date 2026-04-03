'use client'

import { useState, useEffect } from 'react'
import { useNearWallet } from '@/contexts/near-wallet'

export function SecurityToast() {
  const { wasSessionCleared, isLoading } = useNearWallet()
  const [visible, setVisible] = useState(false)
  const [dismissed, setDismissed] = useState(false)

  useEffect(() => {
    if (!isLoading && wasSessionCleared && !dismissed) {
      setVisible(true)
    }
  }, [isLoading, wasSessionCleared, dismissed])

  if (!visible) return null

  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 w-full max-w-md px-4 animate-in fade-in slide-in-from-bottom-4 duration-300">
      <div className="bg-gray-900 border border-amber-500/30 rounded-2xl p-5 shadow-2xl shadow-black/50 flex gap-4">
        {/* Icon */}
        <div className="shrink-0 w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-lg">
          🔒
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-amber-300 mb-1">
            Sigurnosna provjera
          </p>
          <p className="text-sm text-gray-400 leading-relaxed">
            Radi vaše sigurnosti, prethodna sesija je završena. Molimo vas da se ponovo prijavite NEAR walletom.
          </p>
        </div>

        {/* Close */}
        <button
          onClick={() => { setVisible(false); setDismissed(true) }}
          className="shrink-0 text-gray-600 hover:text-gray-400 transition-colors mt-0.5"
          aria-label="Zatvori"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>
  )
}
