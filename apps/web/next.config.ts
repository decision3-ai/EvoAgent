import type { NextConfig } from 'next'

/** Standalone is for Docker/VPS; Vercel uses its own Next runtime. */
const nextConfig: NextConfig = {
  ...(process.env.VERCEL ? {} : { output: 'standalone' }),
  devIndicators: false,
}

export default nextConfig
