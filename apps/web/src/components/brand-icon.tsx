type Props = {
  className?: string
}

/** Official mark from `branding/web/logo.app.png` → served as `/logo.png`. */
export function BrandIcon({ className }: Props) {
  return (
    <img
      src="/logo.png"
      alt="EVOAGENT"
      className={`shrink-0 object-contain ${className ?? 'h-9 w-9'}`}
    />
  )
}
