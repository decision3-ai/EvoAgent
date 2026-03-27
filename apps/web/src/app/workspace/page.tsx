'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useNearWallet } from '@/contexts/near-wallet'

export default function WorkspacePage() {
  const { accountId, isConnected, isLoading } = useNearWallet()
  const router = useRouter()

  useEffect(() => {
    if (isLoading) return
    if (!isConnected) {
      router.push('/')
      return
    }
    // Redirect to new workspace creation for now
    router.push('/workspace/new')
  }, [isConnected, isLoading, router])

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center">
      <div className="text-gray-400">Loading...</div>
    </div>
  )
}
