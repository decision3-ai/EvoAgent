import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // Override fuchsia → orange palette
        fuchsia: {
          300: '#ffcc55',
          400: '#ffaa00',
          500: '#ff6a00',
          600: '#e05500',
          700: '#cc4400',
        },
        // Override violet → deep blue palette
        violet: {
          500: '#3a2fad',
          600: '#2a1f9d',
          700: '#1a0f8d',
        },
        // Override dark grays → dark blue palette
        gray: {
          800: '#111840',
          900: '#0d1235',
          950: '#0a0f2e',
        },
        brand: {
          50: '#f0f9ff',
          100: '#e0f2fe',
          400: '#38bdf8',
          500: '#0ea5e9',
          600: '#0284c7',
          700: '#0369a1',
          900: '#0c4a6e',
        },
        evo: {
          purple: '#7c3aed',
          violet: '#8b5cf6',
        },
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'fade-in': 'fadeIn 0.5s ease-in-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
}

export default config
