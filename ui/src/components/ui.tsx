import { useEffect, useRef, useState, type ReactNode } from 'react'
import { cn } from '../lib/cn'
import { Icon } from './Icon'

// The primitives, kept deliberately few.
//
// Console style: hairline borders instead of shadows, one accent used only for
// focus and primary actions, 13px text, and nothing that moves unless it is
// telling you something changed.

const STYLES: Record<string, string> = {
  default: 'bg-surface text-ink ring-1 ring-inset ring-line hover:bg-raised',
  primary: 'bg-accent text-white hover:opacity-90',
  danger: 'bg-red-600 text-white hover:bg-red-700',
  ghost: 'text-dim hover:bg-raised hover:text-ink',
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
  style?: keyof typeof STYLES | string
  size?: 'sm' | 'md'
  icon?: string | null
} & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      type="button"
      {...rest}
      className={cn(
        'inline-flex items-center justify-center gap-1.5 rounded-[var(--radius-wd)] font-medium transition-colors',
        'disabled:pointer-events-none disabled:opacity-45',
        size === 'sm' ? 'h-7 px-2 text-[12px]' : 'h-8 px-2.5 text-[13px]',
        STYLES[style] ?? STYLES.default,
        className,
      )}
    >
      <Icon name={icon} className="h-3.5 w-3.5 shrink-0" />
      {children}
    </button>
  )
}

export function Input({ className, invalid, ...rest }: { invalid?: boolean } & React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...rest}
      aria-invalid={invalid || undefined}
      className={cn(
        'h-8 w-full rounded-[var(--radius-wd)] bg-surface px-2.5 text-[13px] text-ink',
        'ring-1 ring-inset placeholder:text-dim',
        invalid ? 'ring-red-500' : 'ring-line',
        'disabled:bg-raised disabled:text-dim',
        className,
      )}
    />
  )
}

export function Select({ className, invalid, children, ...rest }: { invalid?: boolean } & React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      {...rest}
      aria-invalid={invalid || undefined}
      className={cn(
        'h-8 w-full appearance-none rounded-[var(--radius-wd)] bg-surface px-2.5 pr-7 text-[13px] text-ink',
        'ring-1 ring-inset',
        invalid ? 'ring-red-500' : 'ring-line',
        className,
      )}
      style={{
        backgroundImage:
          "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%236b7280' stroke-width='2' stroke-linecap='round'%3E%3Cpath d='m6 9 6 6 6-6'/%3E%3C/svg%3E\")",
        backgroundRepeat: 'no-repeat',
        backgroundPosition: 'right 6px center',
        backgroundSize: '14px',
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
      className={cn(
        'w-full rounded-[var(--radius-wd)] bg-surface p-2.5 text-[13px] leading-relaxed text-ink',
        'ring-1 ring-inset placeholder:text-dim',
        invalid ? 'ring-red-500' : 'ring-line',
        className,
      )}
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
        'relative h-[18px] w-8 shrink-0 rounded-full transition-colors disabled:opacity-45',
        checked ? 'bg-accent' : 'bg-zinc-300 dark:bg-zinc-700',
      )}
    >
      <span
        className={cn(
          'absolute top-[2px] h-[14px] w-[14px] rounded-full bg-white transition-transform',
          checked ? 'translate-x-[16px]' : 'translate-x-[2px]',
        )}
      />
    </button>
  )
}

export function Label({ children, required, htmlFor }: { children: ReactNode; required?: boolean; htmlFor?: string }) {
  return (
    <label htmlFor={htmlFor} className="mb-1 block text-[12px] font-medium text-ink">
      {children}
      {required && <span className="ml-0.5 text-red-500" aria-hidden="true">*</span>}
    </label>
  )
}

export function Hint({ children }: { children: ReactNode }) {
  return <p className="mt-1 text-[11.5px] leading-snug text-dim">{children}</p>
}

export function Error({ children }: { children: ReactNode }) {
  return (
    <p role="alert" className="mt-1 flex items-start gap-1 text-[11.5px] text-red-600 dark:text-red-400">
      <Icon name="alert" className="mt-[1px] h-3 w-3 shrink-0" />
      {children}
    </p>
  )
}

export function Panel({ title, children, actions, className }: { title?: ReactNode; children: ReactNode; actions?: ReactNode; className?: string }) {
  return (
    <section className={cn('rounded-[var(--radius-wd)] bg-surface ring-1 ring-line', className)}>
      {(title || actions) && (
        <header className="flex h-10 items-center justify-between gap-3 border-b border-line px-3">
          <h2 className="truncate text-[12px] font-semibold tracking-wide text-ink uppercase">{title}</h2>
          {actions}
        </header>
      )}
      <div className="p-3">{children}</div>
    </section>
  )
}

export function Empty({ title, description, action }: { title: string; description?: string | null; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 px-6 py-16 text-center">
      <p className="text-[14px] font-medium text-ink">{title}</p>
      {description && <p className="max-w-sm text-[12.5px] text-dim">{description}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  )
}

/** A dropdown that closes on outside click and on Escape. */
export function Menu({ trigger, children, align = 'right' }: { trigger: ReactNode; children: (close: () => void) => ReactNode; align?: 'left' | 'right' }) {
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
            'absolute z-30 mt-1 min-w-44 overflow-hidden rounded-[var(--radius-wd)] bg-surface py-1 ring-1 ring-line',
            'shadow-[0_8px_24px_-12px_rgb(0_0_0/0.3)]',
            align === 'right' ? 'right-0' : 'left-0',
          )}
        >
          {children(() => setOpen(false))}
        </div>
      )}
    </div>
  )
}

export function MenuItem({ children, onClick, danger, icon }: { children: ReactNode; onClick?: () => void; danger?: boolean; icon?: string | null }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'flex w-full items-center gap-2 px-3 py-1.5 text-left text-[12.5px]',
        danger ? 'text-red-600 hover:bg-red-500/10 dark:text-red-400' : 'text-ink hover:bg-raised',
      )}
    >
      <Icon name={icon} className="h-3.5 w-3.5 shrink-0" />
      {children}
    </button>
  )
}

/** A modal that traps Escape and returns focus. Used for confirmations. */
export function Dialog({ title, description, children, onClose, footer }: { title: string; description?: ReactNode; children?: ReactNode; onClose: () => void; footer: ReactNode }) {
  useEffect(() => {
    const escape = (event: KeyboardEvent) => event.key === 'Escape' && onClose()
    document.addEventListener('keydown', escape)
    return () => document.removeEventListener('keydown', escape)
  }, [onClose])

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/35 p-4" onMouseDown={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onMouseDown={(event) => event.stopPropagation()}
        className="w-full max-w-md rounded-[var(--radius-wd)] bg-surface ring-1 ring-line shadow-[0_16px_48px_-16px_rgb(0_0_0/0.45)]"
      >
        <div className="p-4">
          <h2 className="text-[14px] font-semibold text-ink">{title}</h2>
          {description && <div className="mt-1.5 text-[12.5px] text-dim">{description}</div>}
          {children && <div className="mt-3">{children}</div>}
        </div>
        <div className="flex justify-end gap-2 border-t border-line px-4 py-3">{footer}</div>
      </div>
    </div>
  )
}
