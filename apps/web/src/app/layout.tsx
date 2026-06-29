import type { Metadata } from 'next'
import { Geist, Geist_Mono } from 'next/font/google'
import { NearWalletProvider } from '@/contexts/near-wallet'
import '@near-wallet-selector/modal-ui/styles.css'
import './globals.css'

const geistSans = Geist({
  variable: '--font-geist-sans',
  subsets: ['latin'],
})

const geistMono = Geist_Mono({
  variable: '--font-geist-mono',
  subsets: ['latin'],
})

export const metadata: Metadata = {
  title: 'EvoAgent — Beyond Coding',
  description:
    'Build, deploy, and evolve AI agents that grow smarter with every interaction. No static prompts. Just continuous evolution.',
  keywords: ['AI agents', 'NEAR blockchain', 'Web3', 'agent evolution'],
  authors: [{ name: 'EVOAGENT' }],
  openGraph: {
    title: 'EVOAGENT',
    description: 'AI Agents That Learn and Evolve',
    type: 'website',
    url: 'https://evoagent.io',
  },
  icons: {
    icon: '/3.png?v=4',
    shortcut: '/3.png?v=4',
    apple: '/3.png?v=4',
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="dark">
      <head>
        <link rel="icon" href="/3.png?v=4" />
      </head>
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased`}>
        <NearWalletProvider>
          {children}
        </NearWalletProvider>
      </body>
    </html>
  )
}
