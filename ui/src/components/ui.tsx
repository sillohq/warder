import { useEffect, useRef, useState, type ReactNode } from 'react'
import { cn } from '../lib/cn'
import { Icon } from './Icon'

// The primitives.
//
// Every measurement comes from a token, including the ones interfaces usually
// hard-code — row height, cell padding, page padding. That is what makes
// density="compact" a real setting rather than a smaller font, and it is why
// nothing below writes a pixel value for spacing that a person can feel.

const STYLES: Record<string, string> = {
  default: 'bg-surface text-ink ring-1 ring-inset ring-edge hover:bg-raised hover:ring-edge',
  primary: 'bg-accent text-on-accent hover:brightness-110 shadow-sm',
  danger: 'bg-transparent text-red-500 ring-1 ring-inset ring-red-500/50 hover:bg-red-500 hover:text-white hover:ring-red-500',
  ghost: 'bg-transparent text-dim hover:bg-raised hover:text-ink',
  quiet: 'bg-raised text-ink hover:bg-edge',
}

export function Button({
  children,
  style = 'default',
  size = 'md',
  icon,
  className,
  ...rest
}: {
  children?: ReactNode
  style?: string
  size?: 'sm' | 'md' | 'lg'
  icon?: string | null
} & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      type="button"
      {...rest}
      className={cn(
        'inline-flex items-center justify-center gap-2 rounded-[var(--radius-wd-sm)] font-semibold',
        'transition-[background,color,box-shadow,filter] duration-150 whitespace-nowrap',
        'disabled:pointer-events-none disabled:opacity-40',
        size === 'sm' && 'h-8 px-3 text-[12.5px]',
        size === 'md' && 'h-10 px-4 text-[13.5px]',
        size === 'lg' && 'h-11 px-6 text-[14.5px]',
        STYLES[style] ?? STYLES.default,
        className,
      )}
    >
      {icon && <Icon name={icon} className="h-4 w-4 shrink-0" />}
      {children}
    </button>
  )
}

/** A square icon-only button — row menus, toolbar toggles, pagination. */
export function IconButton({
  icon,
  label,
  active,
  className,
  ...rest
}: { icon: string; label: string; active?: boolean } & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      {...rest}
      className={cn(
        'grid h-9 w-9 shrink-0 place-items-center rounded-[var(--radius-wd-sm)] transition-colors',
        active ? 'bg-raised text-ink' : 'text-dim hover:bg-raised hover:text-ink',
        'disabled:pointer-events-none disabled:opacity-35',
        className,
      )}
    >
      <Icon name={icon} className="h-4 w-4" />
    </button>
  )
}

const FIELD =
  'w-full rounded-[var(--radius-wd-sm)] bg-sunken text-ink text-[var(--text-wd)] ' +
  'ring-1 ring-inset transition-shadow placeholder:text-faint ' +
  'disabled:bg-raised disabled:text-dim disabled:cursor-not-allowed'

export function Input({ className, invalid, ...rest }: { invalid?: boolean } & React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...rest}
      aria-invalid={invalid || undefined}
      className={cn(FIELD, 'h-10 px-3.5', invalid ? 'ring-red-500' : 'ring-line focus:ring-accent', className)}
    />
  )
}

export function Select({ className, invalid, children, ...rest }: { invalid?: boolean } & React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      {...rest}
      aria-invalid={invalid || undefined}
      className={cn(FIELD, 'h-10 appearance-none pl-3.5 pr-9', invalid ? 'ring-red-500' : 'ring-line focus:ring-accent', className)}
      style={{
        backgroundImage:
          "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23888' stroke-width='2' stroke-linecap='round'%3E%3Cpath d='m6 9 6 6 6-6'/%3E%3C/svg%3E\")",
        backgroundRepeat: 'no-repeat',
        backgroundPosition: 'right 10px center',
        backgroundSize: '15px',
      }}
    >
      {children}
    </select>
  )
}

export function Textarea({ className, invalid, ...rest }: { invalid?: boolean } & React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      {...rest}
      aria-invalid={invalid || undefined}
      className={cn(FIELD, 'p-3.5 leading-relaxed resize-y', invalid ? 'ring-red-500' : 'ring-line focus:ring-accent', className)}
    />
  )
}

export function Switch({ checked, onChange, disabled }: { checked: boolean; onChange: (v: boolean) => void; disabled?: boolean }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={cn(
        'relative h-6 w-11 shrink-0 rounded-full transition-colors disabled:opacity-40',
        checked ? 'bg-accent' : 'bg-edge',
      )}
    >
      <span
        className={cn(
          'absolute top-[3px] h-[18px] w-[18px] rounded-full bg-white shadow-sm transition-transform',
          checked ? 'translate-x-[23px]' : 'translate-x-[3px]',
        )}
      />
    </button>
  )
}

export function Label({ children, required, htmlFor }: { children: ReactNode; required?: boolean; htmlFor?: string }) {
  return (
    <label htmlFor={htmlFor} className="mb-2 block text-[11.5px] font-bold uppercase tracking-[0.06em] text-faint">
      {children}
      {required && <span className="ml-1 text-accent" aria-hidden="true">*</span>}
    </label>
  )
}

export function Hint({ children }: { children: ReactNode }) {
  return <p className="mt-2 text-[12.5px] leading-relaxed text-dim">{children}</p>
}

export function Error({ children }: { children: ReactNode }) {
  return (
    <p role="alert" className="mt-2 flex items-start gap-1.5 text-[12.5px] font-medium text-red-500">
      <Icon name="alert" className="mt-[2px] h-3.5 w-3.5 shrink-0" />
      {children}
    </p>
  )
}

export function Panel({
  title,
  description,
  children,
  actions,
  className,
  flush,
}: {
  title?: ReactNode
  description?: ReactNode
  children: ReactNode
  actions?: ReactNode
  className?: string
  flush?: boolean
}) {
  return (
    <section className={cn('rounded-[var(--radius-wd)] bg-surface ring-1 ring-line shadow-[var(--wd-shadow)]', className)}>
      {(title || actions) && (
        <header className="flex items-start justify-between gap-4 border-b border-line px-5 py-4">
          <div className="min-w-0">
            <h2 className="truncate text-[14px] font-bold tracking-tight text-ink">{title}</h2>
            {description && <p className="mt-1 text-[12.5px] text-dim">{description}</p>}
          </div>
          {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
        </header>
      )}
      <div className={flush ? '' : 'p-5'}>{children}</div>
    </section>
  )
}

export function Empty({ title, description, action, icon = 'database' }: { title: string; description?: string | null; action?: ReactNode; icon?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 px-6 py-24 text-center">
      <span className="mb-1 text-faint opacity-40">
        <Icon name={icon} className="h-12 w-12" />
      </span>
      <p className="text-[16px] font-semibold text-ink">{title}</p>
      {description && <p className="max-w-sm text-[13.5px] leading-relaxed text-dim">{description}</p>}
      {action && <div className="mt-3">{action}</div>}
    </div>
  )
}

/** A dropdown that closes on outside click and on Escape. */
export function Menu({
  trigger,
  children,
  align = 'right',
  width = 'min-w-52',
}: {
  trigger: ReactNode
  children: (close: () => void) => ReactNode
  align?: 'left' | 'right'
  width?: string
}) {
  const [open, setOpen] = useState(false)
  const box = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const away = (event: MouseEvent) => {
      if (box.current && !box.current.contains(event.target as Node)) setOpen(false)
    }
    const escape = (event: KeyboardEvent) => event.key === 'Escape' && setOpen(false)
    document.addEventListener('mousedown', away)
    document.addEventListener('keydown', escape)
    return () => {
      document.removeEventListener('mousedown', away)
      document.removeEventListener('keydown', escape)
    }
  }, [open])

  return (
    <div ref={box} className="relative">
      <span onClick={() => setOpen((v) => !v)}>{trigger}</span>
      {open && (
        <div
          className={cn(
            'wd-in absolute z-40 mt-2 overflow-hidden rounded-[var(--radius-wd)] bg-surface py-1.5 ring-1 ring-edge',
            'shadow-[0_12px_36px_-12px_rgb(0_0_0/0.45)]',
            width,
            align === 'right' ? 'right-0' : 'left-0',
          )}
        >
          {children(() => setOpen(false))}
        </div>
      )}
    </div>
  )
}

export function MenuItem({
  children,
  onClick,
  danger,
  icon,
  hint,
  disabled,
}: {
  children: ReactNode
  onClick?: () => void
  danger?: boolean
  icon?: string | null
  hint?: ReactNode
  disabled?: boolean
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={cn(
        'flex w-full items-center gap-2.5 px-4 py-2.5 text-left text-[13px] font-medium transition-colors',
        'disabled:pointer-events-none disabled:opacity-40',
        danger ? 'text-red-500 hover:bg-red-500/10' : 'text-dim hover:bg-raised hover:text-ink',
      )}
    >
      {icon !== undefined && <Icon name={icon} className="h-4 w-4 shrink-0" />}
      <span className="flex-1 truncate">{children}</span>
      {hint && <span className="shrink-0 text-[11px] text-faint">{hint}</span>}
    </button>
  )
}

export function MenuLabel({ children }: { children: ReactNode }) {
  return <p className="wd-eyebrow px-4 pb-1 pt-2">{children}</p>
}

/** A modal. Escape closes it, and the backdrop click is a close too. */
export function Dialog({
  title,
  description,
  children,
  onClose,
  footer,
  wide,
}: {
  title: string
  description?: ReactNode
  children?: ReactNode
  onClose: () => void
  footer: ReactNode
  wide?: boolean
}) {
  useEffect(() => {
    const escape = (event: KeyboardEvent) => event.key === 'Escape' && onClose()
    document.addEventListener('keydown', escape)
    return () => document.removeEventListener('keydown', escape)
  }, [onClose])

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/50 p-4 backdrop-blur-[2px]" onMouseDown={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onMouseDown={(event) => event.stopPropagation()}
        className={cn(
          'wd-in w-full rounded-[var(--radius-wd)] bg-surface ring-1 ring-edge',
          'shadow-[0_24px_64px_-16px_rgb(0_0_0/0.6)]',
          wide ? 'max-w-2xl' : 'max-w-lg',
        )}
      >
        <div className="p-6">
          <h2 className="text-[17px] font-bold tracking-tight text-ink">{title}</h2>
          {description && <div className="mt-2 text-[13.5px] leading-relaxed text-dim">{description}</div>}
          {children && <div className="mt-5">{children}</div>}
        </div>
        <div className="flex justify-end gap-2.5 border-t border-line px-6 py-4">{footer}</div>
      </div>
    </div>
  )
}

/** A small labelled statistic — dashboard tiles and detail sidebars. */
export function Stat({ label, value, sub, icon }: { label: string; value: ReactNode; sub?: ReactNode; icon?: string | null }) {
  return (
    <div className="rounded-[var(--radius-wd)] bg-surface p-5 ring-1 ring-line shadow-[var(--wd-shadow)] transition-shadow hover:ring-edge">
      <div className="flex items-center gap-2 text-faint">
        {icon && <Icon name={icon} className="h-4 w-4" />}
        <p className="wd-eyebrow">{label}</p>
      </div>
      <p className="wd-num mt-3 text-[32px] font-extrabold leading-none tracking-[-0.03em] text-ink">{value}</p>
      {sub && <div className="mt-2 text-[12.5px] text-dim">{sub}</div>}
    </div>
  )
}
