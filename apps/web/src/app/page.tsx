import Link from 'next/link'
import { ConnectWalletButton } from '@/components/near/connect-wallet-button'
import { SecurityToast } from '@/components/near/security-toast'

const features = [
  {
    icon: '⚡',
    title: 'Instant Deployment',
    desc: 'Go from zero to deployed agent in under 60 seconds. No infrastructure headaches.',
  },
  {
    icon: '🧬',
    title: 'Genetic Evolution',
    desc: 'Agents improve through interaction feedback. The best traits survive and compound.',
  },
  {
    icon: '📊',
    title: 'Fitness Tracking',
    desc: 'Real-time metrics on agent performance, generation history, and improvement velocity.',
  },
  {
    icon: '🔗',
    title: 'LangGraph Powered',
    desc: 'Built on LangGraph for stateful, multi-step reasoning with full observability.',
  },
  {
    icon: '🔒',
    title: 'Secure by Default',
    desc: 'Data isolation, encrypted memory, and role-based access for every agent.',
  },
  {
    icon: '🌐',
    title: 'API First',
    desc: 'Every feature accessible via REST API. Build on top of AgentEvo from day one.',
  },
]

const steps = [
  { num: '01', title: 'Create', desc: 'Define your agent with a base model and initial system prompt.' },
  { num: '02', title: 'Interact', desc: 'Users chat with the agent. Every exchange is stored and analyzed.' },
  { num: '03', title: 'Evaluate', desc: 'Feedback scores drive a fitness metric per agent and generation.' },
  { num: '04', title: 'Evolve', desc: 'The LangGraph pipeline refines prompts and behavior automatically.' },
]

export default function Home() {
  return (
    <main className="min-h-screen bg-gray-950 text-white overflow-x-hidden">
      <SecurityToast />
      {/* Nav */}
      <nav className="sticky top-0 z-50 border-b border-white/10 bg-gray-950/80 backdrop-blur-md px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-sky-400 to-violet-600 flex items-center justify-center font-bold text-sm shadow-lg">
              A
            </div>
            <span className="font-semibold text-lg tracking-tight">AgentEvo.io</span>
          </div>
          <div className="hidden md:flex items-center gap-6 text-sm text-gray-400">
            <a href="#features" className="hover:text-white transition-colors">Features</a>
            <a href="#how-it-works" className="hover:text-white transition-colors">How it Works</a>
            <a href="#pricing" className="hover:text-white transition-colors">Pricing</a>
          </div>
          <div className="flex items-center gap-3">
            <ConnectWalletButton />
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="max-w-7xl mx-auto px-6 pt-24 pb-20 text-center relative">
        {/* Background glow */}
        <div className="absolute inset-0 -z-10 overflow-hidden">
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-sky-500/10 rounded-full blur-3xl" />
          <div className="absolute top-1/2 left-1/3 -translate-x-1/2 -translate-y-1/2 w-[400px] h-[400px] bg-violet-500/10 rounded-full blur-3xl" />
        </div>

        <div className="inline-flex items-center gap-2 bg-white/5 border border-white/10 rounded-full px-4 py-1.5 text-sm text-sky-400 mb-8">
          <span className="w-2 h-2 rounded-full bg-sky-400 animate-pulse" />
          Now in Early Access — v0.1
        </div>

        <h1 className="text-5xl sm:text-7xl font-bold tracking-tight mb-6 gradient-text">
          AI Agents That<br />Actually Evolve
        </h1>

        <p className="text-xl text-gray-400 max-w-2xl mx-auto mb-10 leading-relaxed">
          Build, deploy, and evolve AI agents that grow smarter with every interaction.
          No static prompts. No manual tuning. Just continuous evolution.
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <ConnectWalletButton className="px-8 py-3.5 rounded-xl text-lg shadow-xl hover:shadow-sky-400/40 hover:-translate-y-0.5" />
          <a
            href="#how-it-works"
            className="w-full sm:w-auto border border-white/20 hover:border-white/40 text-white px-8 py-3.5 rounded-xl font-semibold text-lg transition-all hover:bg-white/5"
          >
            See How It Works →
          </a>
        </div>

        {/* Stats bar */}
        <div className="mt-16 grid grid-cols-3 gap-8 max-w-lg mx-auto">
          {[
            { value: '10x', label: 'Faster Iteration' },
            { value: '∞', label: 'Evolution Cycles' },
            { value: '< 60s', label: 'To First Agent' },
          ].map((stat) => (
            <div key={stat.label}>
              <div className="text-2xl font-bold text-sky-400">{stat.value}</div>
              <div className="text-xs text-gray-500 mt-1">{stat.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Features Grid */}
      <section id="features" className="max-w-7xl mx-auto px-6 py-24">
        <div className="text-center mb-14">
          <h2 className="text-3xl sm:text-4xl font-bold mb-4">Everything agents need to grow</h2>
          <p className="text-gray-400 max-w-xl mx-auto">
            A complete platform for creating agents that learn from feedback and evolve autonomously.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {features.map((f) => (
            <div
              key={f.title}
              className="glass-card rounded-2xl p-6 hover:border-sky-500/30 hover:bg-white/[0.07] transition-all group"
            >
              <div className="text-3xl mb-4">{f.icon}</div>
              <h3 className="font-semibold text-lg mb-2 group-hover:text-sky-300 transition-colors">
                {f.title}
              </h3>
              <p className="text-gray-400 text-sm leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* How it Works */}
      <section id="how-it-works" className="max-w-7xl mx-auto px-6 py-24">
        <div className="text-center mb-14">
          <h2 className="text-3xl sm:text-4xl font-bold mb-4">The Evolution Loop</h2>
          <p className="text-gray-400 max-w-xl mx-auto">
            Four steps. Continuous improvement. No manual intervention required.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {steps.map((step, i) => (
            <div key={step.num} className="relative">
              {i < steps.length - 1 && (
                <div className="hidden lg:block absolute top-8 left-full w-full h-px bg-gradient-to-r from-white/20 to-transparent z-10" />
              )}
              <div className="glass-card rounded-2xl p-6">
                <div className="text-sky-400 font-mono text-sm font-bold mb-3">{step.num}</div>
                <h3 className="font-semibold text-lg mb-2">{step.title}</h3>
                <p className="text-gray-400 text-sm leading-relaxed">{step.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="max-w-7xl mx-auto px-6 py-24">
        <div className="glass-card rounded-3xl p-12 text-center relative overflow-hidden glow-sky">
          <div className="absolute inset-0 -z-10 bg-gradient-to-br from-sky-500/10 via-transparent to-violet-500/10" />
          <h2 className="text-3xl sm:text-4xl font-bold mb-4">
            Ready to evolve your agents?
          </h2>
          <p className="text-gray-400 mb-8 max-w-lg mx-auto">
            Join the early access program and start building agents that never stop improving.
          </p>
          <Link
            href="/dashboard"
            className="inline-flex bg-sky-500 hover:bg-sky-400 text-white px-10 py-4 rounded-xl font-semibold text-lg transition-all shadow-xl shadow-sky-500/30 hover:-translate-y-0.5"
          >
            Get Early Access — It&apos;s Free
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/10 px-6 py-8">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 text-gray-500 text-sm">
          <div className="flex items-center gap-2">
            <div className="w-5 h-5 rounded bg-gradient-to-br from-sky-400 to-violet-600" />
            <span>AgentEvo.io</span>
          </div>
          <p>© 2026 AgentEvo.io — Built with LangGraph, FastAPI & Next.js</p>
          <div className="flex gap-6">
            <a href="#" className="hover:text-gray-300 transition-colors">Privacy</a>
            <a href="#" className="hover:text-gray-300 transition-colors">Terms</a>
            <a href="#" className="hover:text-gray-300 transition-colors">GitHub</a>
          </div>
        </div>
      </footer>
    </main>
  )
}
