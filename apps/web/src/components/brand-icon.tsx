type Props = {
  className?: string
  labelClassName?: string
}

/** Text placeholder until final logo asset — do not use image files here. */
export function BrandIcon({ className, labelClassName }: Props) {
  return (
    <div
      className={`flex shrink-0 items-center justify-center bg-gradient-to-br from-fuchsia-400 to-violet-600 text-white shadow-lg ${className ?? 'h-9 w-9 rounded-lg text-sm'}`}
      aria-hidden
    >
      <span className={`select-none font-mono font-semibold tracking-tight ${labelClassName ?? ''}`}>
        eVo
      </span>
    </div>
  )
}
