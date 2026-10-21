import type { Metadata } from 'next'
import Link from 'next/link'
import { BrandIcon } from '@/components/brand-icon'
import { VisibilityChecker } from '@/components/growth/visibility-checker'

const TITLE = 'AI Visibility Checker — EvoAgent'
const DESCRIPTION =
  'Free check: can ChatGPT, Claude, Perplexity and Gemini read and recommend your website? Get a 0-100 AI visibility score and the top 3 fixes in under a minute.'

export const metadata: Metadata = {
  title: TITLE,
  description: DESCRIPTION,
  alternates: { canonical: 'https://evoagent.io/ai-visibility' },
  openGraph: {
    title: TITLE,
    description: DESCRIPTION,
    type: 'website',
    url: 'https://evoagent.io/ai-visibility',
    siteName: 'EvoAgent',
  },
  twitter: {
    card: 'summary',
    title: TITLE,
    description: DESCRIPTION,
  },
}

export default function AiVisibilityPage() {
  return (
    <main className="min-h-screen bg-black text-white">
      <header className="mx-auto flex max-w-3xl items-center px-4 py-5 sm:px-6">
        <Link href="/" className="flex items-center gap-2.5">
          <BrandIcon className="h-8 w-8" />
          <span className="font-semibold tracking-tight">EVOAGENT</span>
        </Link>
      </header>

      <section className="mx-auto max-w-3xl px-4 pb-20 pt-6 sm:px-6 sm:pt-12">
        <p className="mb-3 text-xs font-semibold uppercase tracking-widest text-[#00B4A0]">
          Free tool
        </p>
        <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">AI Visibility Checker</h1>
        <p className="mt-3 max-w-xl text-sm leading-relaxed text-gray-400 sm:text-base">
          Find out whether AI assistants like ChatGPT, Claude, Perplexity and Gemini can crawl,
          understand and recommend your website.
        </p>

        <div className="mt-8">
          <VisibilityChecker />
        </div>
      </section>
    </main>
  )
}
