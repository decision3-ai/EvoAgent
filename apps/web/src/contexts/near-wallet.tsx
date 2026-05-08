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

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

type NearWalletContextType = {
  selector: WalletSelector | null
  accountId: string | null
  isConnected: boolean
  isLoading: boolean
  wasSessionCleared: boolean
  isEmailAuth: boolean
  connect: () => void
  disconnect: () => Promise<void>
  loginWithEmail: (email: string, password: string) => Promise<void>
  registerWithEmail: (email: string, password: string) => Promise<void>
}

const NearWalletContext = createContext<NearWalletContextType>({
  selector: null,
  accountId: null,
  isConnected: false,
  isLoading: true,
  wasSessionCleared: false,
  isEmailAuth: false,
  connect: () => {},
  disconnect: async () => {},
  loginWithEmail: async () => {},
  registerWithEmail: async () => {},
})

export function NearWalletProvider({ children }: { children: React.ReactNode }) {
  const [selector, setSelector] = useState<WalletSelector | null>(null)
  const [accountId, setAccountId] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [wasSessionCleared, setWasSessionCleared] = useState(false)
  const [isEmailAuth, setIsEmailAuth] = useState(false)

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
          // Don't overwrite accountId if email auth is active — the JWT stored
          // in localStorage is already set as accountId by the restore effect.
          if (localStorage.getItem('email_auth_token')) return
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
    if (isEmailAuth) {
      setAccountId(null)
      setIsEmailAuth(false)
      localStorage.removeItem('email_auth_token')
      return
    }
    if (!selector) return
    try {
      const wallet = await selector.wallet()
      await wallet.signOut()
    } catch (e) {
      console.error('Disconnect error:', e)
    }
    setAccountId(null)
    document.cookie = 'near_account_id=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT'
  }, [selector, isEmailAuth])

  const loginWithEmail = useCallback(async (email: string, password: string) => {
    const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail ?? 'Login failed')
    }
    const data = await res.json()
    localStorage.setItem('email_auth_token', data.access_token)
    setAccountId(data.access_token)
    setIsEmailAuth(true)
  }, [])

  const registerWithEmail = useCallback(async (email: string, password: string) => {
    const res = await fetch(`${API_BASE}/api/v1/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail ?? 'Registration failed')
    }
    const data = await res.json()
    localStorage.setItem('email_auth_token', data.access_token)
    setAccountId(data.access_token)
    setIsEmailAuth(true)
  }, [])

  // Restore email session on mount
  useEffect(() => {
    const stored = localStorage.getItem('email_auth_token')
    if (stored) {
      setAccountId(stored)
      setIsEmailAuth(true)
    }
  }, [])

  return (
    <NearWalletContext.Provider
      value={{
        selector,
        accountId,
        isConnected: !!accountId,
        isLoading,
        wasSessionCleared,
        isEmailAuth,
        connect,
        disconnect,
        loginWithEmail,
        registerWithEmail,
      }}
    >
      {children}
    </NearWalletContext.Provider>
  )
}

export const useNearWallet = () => useContext(NearWalletContext)
