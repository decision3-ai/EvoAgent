'use client'

import React, {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
} from 'react'
import { useRouter, usePathname } from 'next/navigation'
import type { WalletSelector } from '@near-wallet-selector/core'
import { setupModal } from '@near-wallet-selector/modal-ui'
import { initWalletSelector, AGENTEVO_CONTRACT_ID } from '@/lib/near'

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

const NEAR_SIGN_MESSAGE = 'Sign in to evoagent.io'
const NEAR_RECIPIENT = 'evoagent.io'

type NearWalletContextType = {
  selector: WalletSelector | null
  accountId: string | null
  isConnected: boolean
  isLoading: boolean
  wasSessionCleared: boolean
  isEmailAuth: boolean
  isNearAuth: boolean
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
  isNearAuth: false,
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
  const [isNearAuth, setIsNearAuth] = useState(false)
  const [walletInitialized, setWalletInitialized] = useState(false)
  const router = useRouter()
  const pathname = usePathname()

  // ── NEAR auth helpers ──────────────────────────────────────────────────────

  async function completeNearAuth(
    walletAccountId: string,
    publicKey: string,
    signature: string,
    nonce: string,
  ) {
    const res = await fetch(`${API_BASE}/api/v1/auth/near/verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        account_id: walletAccountId,
        public_key: publicKey,
        signature,
        nonce,
        message: NEAR_SIGN_MESSAGE,
        recipient: NEAR_RECIPIENT,
      }),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({})) as { detail?: string }
      throw new Error(err.detail ?? 'NEAR auth failed')
    }
    const data = await res.json() as { access_token: string; account_id: string }
    localStorage.setItem('near_auth_token', data.access_token)
    setAccountId(data.access_token)
    setIsNearAuth(true)
    document.cookie = `near_account_id=${data.account_id}; path=/; SameSite=Lax`
    router.push('/workspace')
  }

  async function initiateNearSign(selectorInstance: WalletSelector, walletAccountId: string) {
    // Get one-time nonce from backend
    const nonceRes = await fetch(`${API_BASE}/api/v1/auth/near/nonce`, { method: 'POST' })
    if (!nonceRes.ok) throw new Error('Failed to get nonce')
    const { nonce } = await nonceRes.json() as { nonce: string }

    // Persist nonce for browser wallet redirect recovery
    localStorage.setItem('near_pending_sign', JSON.stringify({ nonce, accountId: walletAccountId }))

    const wallet = await selectorInstance.wallet()
    const signed = await wallet.signMessage({
      message: NEAR_SIGN_MESSAGE,
      nonce: Buffer.from(nonce, 'base64'),
      recipient: NEAR_RECIPIENT,
      callbackUrl: window.location.href,
    })

    if (signed) {
      // Injected wallet (Meteor, Here) — result available immediately
      await completeNearAuth(signed.accountId, signed.publicKey, signed.signature, nonce)
      localStorage.removeItem('near_pending_sign')
    }
    // If void: browser wallet (MyNearWallet) is redirecting — handled in callback effect below
  }

  // ── Init wallet selector (skip on landing page) ───────────────────────────

  useEffect(() => {
    if (pathname === '/' || walletInitialized) {
      setIsLoading(false)
      return
    }
    setWalletInitialized(true)
    initWalletSelector()
      .then(async (s) => {
        setSelector(s)

        // Security: clear any leftover wallet session on page load
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

        // Watch for wallet connections — trigger sign flow
        s.store.observable.subscribe(async (state) => {
          // Don't interfere with existing auth sessions
          if (localStorage.getItem('email_auth_token')) return
          if (localStorage.getItem('near_auth_token')) return
          // Don't trigger sign flow if we're recovering from a browser wallet redirect
          const searchParams = new URLSearchParams(window.location.search)
          if (searchParams.get('signature')) return

          const activeAccount = state.accounts.find((a) => a.active)
          if (activeAccount?.accountId) {
            try {
              await initiateNearSign(s, activeAccount.accountId)
            } catch (err) {
              console.error('NEAR sign flow error:', err)
            }
          } else {
            setAccountId(null)
            setIsNearAuth(false)
            document.cookie = 'near_account_id=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT'
          }
        })
      })
      .catch(console.error)
      .finally(() => setIsLoading(false))
  }, [pathname, walletInitialized]) // eslint-disable-line react-hooks/exhaustive-deps

  // ── Browser wallet callback (MyNearWallet redirect) ────────────────────────

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const sig = params.get('signature')
    const pubKey = params.get('publicKey')
    const cbAccountId = params.get('accountId')

    if (!sig || !pubKey || !cbAccountId) return

    const pending = localStorage.getItem('near_pending_sign')
    if (!pending) return

    const { nonce } = JSON.parse(pending) as { nonce: string }
    localStorage.removeItem('near_pending_sign')

    // Clean URL params
    const url = new URL(window.location.href)
    url.searchParams.delete('signature')
    url.searchParams.delete('publicKey')
    url.searchParams.delete('accountId')
    window.history.replaceState({}, '', url.toString())

    completeNearAuth(cbAccountId, pubKey, sig, nonce).catch(console.error)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // ── Restore sessions on mount ──────────────────────────────────────────────

  useEffect(() => {
    const emailToken = localStorage.getItem('email_auth_token')
    if (emailToken) {
      setAccountId(emailToken)
      setIsEmailAuth(true)
      return
    }
    const nearToken = localStorage.getItem('near_auth_token')
    if (nearToken) {
      setAccountId(nearToken)
      setIsNearAuth(true)
    }
  }, [])

  // ── Actions ────────────────────────────────────────────────────────────────

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
    if (isNearAuth) {
      setAccountId(null)
      setIsNearAuth(false)
      localStorage.removeItem('near_auth_token')
      document.cookie = 'near_account_id=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT'
      if (selector) {
        try {
          const wallet = await selector.wallet()
          await wallet.signOut()
        } catch {
          // wallet already disconnected
        }
      }
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
  }, [selector, isEmailAuth, isNearAuth])

  const loginWithEmail = useCallback(async (email: string, password: string) => {
    const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({})) as { detail?: string }
      throw new Error(err.detail ?? 'Login failed')
    }
    const data = await res.json() as { access_token: string }
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
      const err = await res.json().catch(() => ({})) as { detail?: string | Array<{ msg: string }> }
      const detail = err.detail
      const msg = Array.isArray(detail) ? detail.map((d) => d.msg).join(', ') : (detail ?? 'Registration failed')
      throw new Error(msg)
    }
    const data = await res.json() as { access_token: string }
    localStorage.setItem('email_auth_token', data.access_token)
    setAccountId(data.access_token)
    setIsEmailAuth(true)
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
        isNearAuth,
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
