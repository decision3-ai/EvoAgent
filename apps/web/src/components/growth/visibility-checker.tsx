'use client'

import { useState } from 'react'
import Link from 'next/link'
import { CheckCircle2, Loader2, XCircle } from 'lucide-react'
import {
  checkVisibility,
  VisibilityCheckError,
  type VisibilityReport,
} from '@/lib/api-client'

type Check = {
  label: string
  passed: boolean
  explanation: string
}

// Recommendation sub-check passes at 50/100 or higher
const RECOMMENDATION_PASS = 50

function buildChecks(r: VisibilityReport): Check[] {
  const blockedBots = r.bots.filter((b) => !b.allowed).map((b) => b.bot)
  const missingTags = [
    !r.json_ld && 'JSON-LD schema',
    !r.meta_description && 'meta description',
    !r.h1 && 'H1 heading',
  ].filter((t): t is string => Boolean(t))

  return [
    {
      label: 'AI crawler access',
      passed: r.ai_blocked_count === 0,
      explanation:
        r.ai_blocked_count === 0
          ? r.robots_found
            ? 'robots.txt allows GPTBot, ClaudeBot, PerplexityBot, Google-Extended and CCBot.'
            : 'No robots.txt found, so AI crawlers are not blocked.'
          : `robots.txt blocks ${blockedBots.join(', ')}.`,
    },
    {
      label: 'llms.txt',
      passed: r.llms_txt,
      explanation: r.llms_txt
        ? r.llms_full_txt
          ? '/llms.txt and /llms-full.txt are both present.'
          : '/llms.txt is present. Adding /llms-full.txt would help further.'
        : 'No /llms.txt found. This file gives AI models a concise summary of your site.',
    },
    {
      label: 'Structured data',
      passed: missingTags.length === 0,
      explanation:
        missingTags.length === 0
          ? 'Homepage has JSON-LD schema, a meta description and an H1 heading.'
          : `Homepage is missing: ${missingTags.join(', ')}.`,
    },
    {
      label: 'Readable content',
      passed: r.content_readable,
      explanation: r.content_readable
        ? `Homepage has ${r.content_length.toLocaleString()} characters of readable text.`
        : `Only ${r.content_length.toLocaleString()} characters of readable text (500+ needed).`,
    },
    {
      label: 'AI recommendation',
      passed: r.recommendation_score >= RECOMMENDATION_PASS,
      explanation:
        r.recommendation_reasons[0] ??
        `Estimated likelihood AI assistants recommend you: ${r.recommendation_score}/100.`,
    },
  ]
}

function errorMessage(err: unknown): string {
  if (!(err instanceof VisibilityCheckError)) return 'Something went wrong. Please try again.'
  switch (err.status) {
    case null:
      return 'Could not reach the server. Check your connection and try again.'
    case 400:
      return err.message || 'That domain is not valid. Enter a domain like example.com.'
    case 422:
      return 'Please enter a domain like example.com.'
    case 429:
      return 'Too many checks from your network. Please try again in an hour.'
    case 503:
      return 'We have reached our daily limit of free checks. Please try again tomorrow.'
    default:
      return 'The check failed on our side. Please try again in a moment.'
  }
}

function scoreColor(score: number): string {
  if (score >= 70) return 'text-[#00B4A0]'
  if (score >= 40) return 'text-amber-400'
  return 'text-red-400'
}

function scoreLabel(score: number): string {
  if (score >= 70) return 'Good AI visibility'
  if (score >= 40) return 'Partial AI visibility'
  return 'Poor AI visibility'
}

export function VisibilityChecker() {
  const [domain, setDomain] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [report, setReport] = useState<VisibilityReport | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const value = domain.trim()
    if (!value || loading) return

    setLoading(true)
    setError('')
    setReport(null)
    try {
      setReport(await checkVisibility(value))
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-8">
      <form onSubmit={handleSubmit} className="flex flex-col gap-3 sm:flex-row">
        <label htmlFor="domain" className="sr-only">
          Website domain
        </label>
        <input
          id="domain"
          type="text"
          inputMode="url"
          autoComplete="url"
          autoCapitalize="none"
          spellCheck={false}
          value={domain}
          onChange={(e) => setDomain(e.target.value)}
          placeholder="example.com"
          maxLength={260}
          disabled={loading}
          className="w-full flex-1 rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-white placeholder-gray-500 transition-colors focus:border-[#00B4A0]/50 focus:outline-none focus:ring-1 focus:ring-[#00B4A0]/30 disabled:opacity-60"
        />
        <button
          type="submit"
          disabled={loading || !domain.trim()}
          className="rounded-xl bg-[#00B4A0] px-8 py-3 font-semibold text-white shadow-lg shadow-[#00B4A0]/25 transition-all hover:-translate-y-0.5 hover:bg-[#00C4B0] disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:translate-y-0"
        >
          {loading ? 'Checking…' : 'Check'}
        </button>
      </form>

      {loading && (
        <div
          role="status"
          className="flex items-start gap-3 rounded-xl border border-white/10 bg-white/5 px-4 py-4 text-sm text-gray-300"
        >
          <Loader2 className="mt-0.5 h-4 w-4 shrink-0 animate-spin text-[#00B4A0]" />
          <p>
            Checking robots.txt, llms.txt, structured data, readable content and how likely AI
            assistants are to recommend you. This can take up to 30 seconds.
          </p>
        </div>
      )}

      {error && (
        <p
          role="alert"
          className="rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-400"
        >
          {error}
        </p>
      )}

      {report && <VisibilityResults report={report} />}
    </div>
  )
}

function VisibilityResults({ report }: { report: VisibilityReport }) {
  const score = Math.max(0, Math.min(100, report.score))
  const checks = buildChecks(report)

  return (
    <div className="animate-fade-in space-y-8">
      <div className="rounded-2xl border border-white/10 bg-white/5 px-6 py-8 text-center">
        <p className="break-all text-sm text-gray-400">{report.domain}</p>
        <p className={`mt-2 text-7xl font-bold tabular-nums sm:text-8xl ${scoreColor(score)}`}>
          {score}
        </p>
        <p className="mt-1 text-sm text-gray-400">out of 100 · {scoreLabel(score)}</p>
      </div>

      <div>
        <h2 className="mb-3 text-lg font-semibold">Checks</h2>
        <ul className="divide-y divide-white/10 rounded-2xl border border-white/10 bg-white/5">
          {checks.map((c) => (
            <li key={c.label} className="flex gap-3 px-4 py-4 sm:px-5">
              {c.passed ? (
                <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-[#00B4A0]" aria-label="Pass" />
              ) : (
                <XCircle className="mt-0.5 h-5 w-5 shrink-0 text-red-400" aria-label="Fail" />
              )}
              <div className="min-w-0">
                <p className="font-medium">{c.label}</p>
                <p className="mt-0.5 text-sm text-gray-400">{c.explanation}</p>
              </div>
            </li>
          ))}
        </ul>
      </div>

      {report.top_3_fixes.length > 0 && (
        <div>
          <h2 className="mb-3 text-lg font-semibold">Top fixes</h2>
          <ol className="space-y-3">
            {report.top_3_fixes.map((f, i) => (
              <li
                key={f.issue}
                className="flex gap-4 rounded-2xl border border-white/10 bg-white/5 px-4 py-4 sm:px-5"
              >
                <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-[#00B4A0]/40 text-sm font-semibold text-[#00B4A0]">
                  {i + 1}
                </span>
                <div className="min-w-0">
                  <p className="font-medium">{f.issue}</p>
                  <p className="mt-0.5 text-sm text-gray-400">{f.fix}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      )}

      <div className="rounded-2xl border border-[#00B4A0]/30 bg-[#00B4A0]/5 px-6 py-8 text-center">
        <p className="text-lg font-semibold">EvoAgent can fix and maintain this for you</p>
        <p className="mx-auto mt-2 max-w-md text-sm text-gray-400">
          Your AI coding partner writes the llms.txt, schema and content changes, and keeps them up
          to date as your site evolves.
        </p>
        <Link
          href="/register"
          className="mt-5 inline-block rounded-xl bg-[#00B4A0] px-8 py-3 font-semibold text-white shadow-lg shadow-[#00B4A0]/25 transition-all hover:-translate-y-0.5 hover:bg-[#00C4B0]"
        >
          Sign up →
        </Link>
      </div>
    </div>
  )
}
