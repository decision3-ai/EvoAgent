'use client'

import React, {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
} from 'react'
import type { WalletSelector } from '@near-wallet-selector/core'
import { setupModal } from '@near-wallet-selector/modal-ui'
import { initWalletSelector, AGENTEVO_CONTRACT_ID } from '@/lib/near'

type NearWalletContextType = {
  selector: WalletSelector | null
  accountId: string | null
  isConnected: boolean
  isLoading: boolean
  wasSessionCleared: boolean
  connect: () => void
  disconnect: () => Promise<void>
}

const NearWalletContext = createContext<NearWalletContextType>({
  selector: null,
  accountId: null,
  isConnected: false,
  isLoading: true,
  wasSessionCleared: false,
  connect: () => {},
  disconnect: async () => {},
})

export function NearWalletProvider({ children }: { children: React.ReactNode }) {
  const [selector, setSelector] = useState<WalletSelector | null>(null)
  const [accountId, setAccountId] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [wasSessionCleared, setWasSessionCleared] = useState(false)

  useEffect(() => {
    initWalletSelector()
      .then(async (s) => {
        setSelector(s)

        // Security: auto-disconnect previous session on every page load
        const { accounts } = s.store.getState()
        const active = accounts.find((a) => a.active)
        if (active) {
          try {
            const wallet = await s.wallet()
            await wallet.signOut()
          } catch (e) {
            console.error('Auto-signout error:', e)
          }
          document.cookie = 'near_account_id=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT'
          setWasSessionCleared(true)
        }

        // Subscribe to wallet state changes (connect / disconnect)
        s.store.observable.subscribe((state) => {
          const active = state.accounts.find((a) => a.active)
          const id = active?.accountId ?? null
          setAccountId(id)
          if (id) {
            document.cookie = `near_account_id=${id}; path=/; SameSite=Lax`
          } else {
            document.cookie = 'near_account_id=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT'
          }
        })
      })
      .catch(console.error)
      .finally(() => setIsLoading(false))
  }, [])

  const connect = useCallback(() => {
    if (!selector) return
    const modal = setupModal(selector, { contractId: AGENTEVO_CONTRACT_ID })
    modal.show()
  }, [selector])

  const disconnect = useCallback(async () => {
    if (!selector) return
    try {
      const wallet = await selector.wallet()
      await wallet.signOut()
    } catch (e) {
      console.error('Disconnect error:', e)
    }
    setAccountId(null)
    document.cookie = 'near_account_id=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT'
  }, [selector])

  return (
    <NearWalletContext.Provider
      value={{
        selector,
        accountId,
        isConnected: !!accountId,
        isLoading,
        wasSessionCleared,
        connect,
        disconnect,
      }}
    >
      {children}
    </NearWalletContext.Provider>
  )
}

export const useNearWallet = () => useContext(NearWalletContext)
