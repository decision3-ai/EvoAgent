import {
  setupWalletSelector,
  type WalletModuleFactory,
} from '@near-wallet-selector/core'
import { setupMyNearWallet } from '@near-wallet-selector/my-near-wallet'
import { setupMeteorWallet } from '@near-wallet-selector/meteor-wallet'
import { setupHereWallet } from '@near-wallet-selector/here-wallet'
import { setupIntearWallet } from '@near-wallet-selector/intear-wallet'
import { setupNearMobileWallet } from '@near-wallet-selector/near-mobile-wallet'

// Start on testnet — one string swap to go to mainnet
export const NEAR_NETWORK_ID = 'testnet' as const

// Contract IDs — testnet za razvoj, mainnet za produkciju
export const CONTRACT_ID_TESTNET = 'evoagent.testnet'
export const CONTRACT_ID_MAINNET = 'evoagent.near'

export const AGENTEVO_CONTRACT_ID =
  NEAR_NETWORK_ID === 'testnet' ? CONTRACT_ID_TESTNET : CONTRACT_ID_MAINNET

export async function initWalletSelector() {
  const selector = await setupWalletSelector({
    network: NEAR_NETWORK_ID,
    modules: [
      setupMyNearWallet(),
      setupMeteorWallet(),
      setupHereWallet(),
      setupIntearWallet(),
      setupNearMobileWallet(),
    ] as WalletModuleFactory[],
  })
  return selector
}
