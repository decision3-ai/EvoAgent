type Props = {
  className?: string
}

/** Shared app mark — same asset as landing nav (`/first.png`). */
export function BrandIcon({ className }: Props) {
  return (
    <img
      src="/first.png"
      alt="EVOAGENT"
      className={`shrink-0 object-contain ${className ?? 'h-9 w-9'}`}
    />
  )
}
