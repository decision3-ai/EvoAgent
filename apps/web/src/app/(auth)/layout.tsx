import { BrandIcon } from '@/components/brand-icon'

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center relative overflow-hidden">
      {/* Background glows */}
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-fuchsia-500/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute top-2/3 left-1/3 w-[300px] h-[300px] bg-violet-500/10 rounded-full blur-3xl pointer-events-none" />

      <div className="relative z-10 w-full flex flex-col items-center gap-8 px-4">
        {/* Logo */}
        <a href="/" className="flex items-center gap-2.5">
          <BrandIcon className="h-9 w-9" />
          <span className="font-semibold text-xl text-white tracking-tight">EVOAGENT</span>
        </a>

        {children}
      </div>
    </div>
  )
}
