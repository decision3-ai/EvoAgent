import Link from 'next/link'

export default function Home() {
  return (
    <main className="min-h-screen bg-black text-white flex flex-col items-center justify-center px-6">
      <div className="flex flex-col items-center gap-8 text-center">
        <div className="flex flex-col items-center gap-3">
          <img
            src="/first.png"
            alt="EvoAgent"
            className="h-40 w-40 object-contain"
          />
          <h1 className="text-4xl font-bold tracking-tight">Beyond Coding.</h1>
        </div>
        <p className="text-gray-400 text-sm max-w-[400px] leading-relaxed">
          Your development partner for continuous evolution.
        </p>
        <Link
          href="/login"
          className="mt-2 border border-white/30 bg-transparent text-white px-8 py-3 rounded-lg font-semibold text-sm hover:bg-white hover:text-black transition-all"
        >
          Start Evolving →
        </Link>
      </div>
    </main>
  )
}
