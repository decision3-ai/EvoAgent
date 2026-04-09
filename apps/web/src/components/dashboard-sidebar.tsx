'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useNearWallet } from '@/contexts/near-wallet'

const navItems = [
  { href: '/dashboard', label: 'Dashboard', icon: '⊞' },
  { href: '/agents', label: 'Agents', icon: '🤖' },
  { href: '/interactions', label: 'Interactions', icon: '💬' },
  { href: '/evolution', label: 'Evolution Log', icon: '🧬' },
  { href: '/settings', label: 'Settings', icon: '⚙️' },
]

export function DashboardSidebar() {
  const pathname = usePathname()
  const { accountId, disconnect } = useNearWallet()

  return (
    <aside className="w-56 border-r border-white/10 flex flex-col py-6 px-4 shrink-0 h-screen sticky top-0">
      {/* Logo */}
      <Link href="/" className="flex items-center gap-2.5 mb-8 px-2 group">
        <img src="/logo.png" alt="AgentEvo" className="h-8 w-8 object-contain drop-shadow-[0_0_6px_rgba(255,106,0,0.4)] group-hover:drop-shadow-[0_0_10px_rgba(255,106,0,0.6)] transition-all" />
        <span className="font-semibold tracking-tight">AgentEvo</span>
      </Link>

      {/* Nav */}
      <nav className="flex flex-col gap-1 text-sm flex-1">
        {navItems.map((item) => {
          const isActive = pathname === item.href

          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-2.5 px-3 py-2.5 rounded-lg transition-colors ${
                isActive
                  ? 'bg-fuchsia-500/15 text-fuchsia-400'
                  : 'text-gray-400 hover:text-white hover:bg-white/5'
              }`}
            >
              <span className="text-base">{item.icon}</span>
              {item.label}
            </Link>
          )
        })}
      </nav>

      {/* User section */}
      <div className="border-t border-white/10 pt-4 mt-4">
        <div className="flex items-center gap-3 px-2">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-fuchsia-400 to-violet-600 flex items-center justify-center text-xs font-bold shrink-0">
            N
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium text-white truncate">
              {accountId
                ? accountId.length > 18
                  ? accountId.slice(0, 8) + '…' + accountId.slice(-6)
                  : accountId
                : 'Not connected'}
            </p>
            <button
              onClick={disconnect}
              className="text-xs text-gray-500 hover:text-red-400 transition-colors"
            >
              Disconnect
            </button>
          </div>
        </div>
      </div>
    </aside>
  )
}
