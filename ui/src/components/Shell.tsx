import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { Link, router, usePage } from '@inertiajs/react'
import type { Shell as ShellProps } from '../types'
import { cn } from '../lib/cn'
import { Icon } from './Icon'
import { Menu, MenuItem } from './ui'

/**
 * The frame every screen sits in: navigation, the command palette, the user
 * menu, and flash messages.
 *
 * The palette is the primary navigation, not a bonus. An admin with forty
 * resources has a sidebar nobody reads to the bottom of, and the people who use
 * it all day reach for ⌘K by the second week.
 */
export function Shell({ children, title }: { children: ReactNode; title?: string }) {
  const page = usePage().props as unknown as ShellProps
  const [open, setOpen] = useState(false)
  const [palette, setPalette] = useState(false)

  useEffect(() => {
    const keys = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        setPalette(true)
      }
    }
    document.addEventListener('keydown', keys)
    return () => document.removeEventListener('keydown', keys)
  }, [])

  return (
    <div className="min-h-screen bg-bg text-ink">
      <a href="#wd-main" className="sr-only focus:not-sr-only focus:absolute focus:left-3 focus:top-3 focus:z-50 focus:rounded focus:bg-surface focus:px-3 focus:py-2 focus:ring-1 focus:ring-line">
        Skip to content
      </a>

      <header className="sticky top-0 z-30 flex h-11 items-center gap-2 border-b border-line bg-surface px-3">
        <button type="button" onClick={() => setOpen((v) => !v)} className="-ml-1 grid h-7 w-7 place-items-center rounded text-dim hover:bg-raised md:hidden" aria-label="Menu">
          <Icon name="more" />
        </button>
        <Link href={page.site.prefix} className="flex items-center gap-2 truncate font-semibold tracking-tight">
          {page.site.logo ? <img src={page.site.logo} alt="" className="h-4 w-auto" /> : <span className="grid h-5 w-5 place-items-center rounded bg-accent text-[10px] font-bold text-white">{page.site.brand.slice(0, 1)}</span>}
          <span className="truncate text-[13px]">{page.site.brand}</span>
        </Link>

        <div className="flex-1" />

        <button
          type="button"
          onClick={() => setPalette(true)}
          className="hidden h-7 items-center gap-2 rounded-[var(--radius-wd)] px-2 text-[12px] text-dim ring-1 ring-line hover:bg-raised sm:inline-flex"
        >
          <Icon name="search" className="h-3.5 w-3.5" />
          Search
          <kbd className="ml-2 rounded bg-raised px-1 py-0.5 font-mono text-[10px] text-dim">⌘K</kbd>
        </button>

        {page.user && (
          <Menu
            trigger={
              <button type="button" className="flex h-7 items-center gap-1.5 rounded-[var(--radius-wd)] px-1.5 text-[12.5px] hover:bg-raised">
                <span className="grid h-5 w-5 place-items-center rounded-full bg-raised text-[10px] font-medium uppercase text-dim">
                  {page.user.label.slice(0, 1)}
                </span>
                <span className="hidden max-w-32 truncate sm:inline">{page.user.label}</span>
                <Icon name="chevronDown" className="h-3 w-3 text-dim" />
              </button>
            }
          >
            {(close) => (
              <>
                <div className="border-b border-line px-3 pb-2 pt-1">
                  <p className="truncate text-[12.5px] font-medium">{page.user!.label}</p>
                  {page.user!.email && <p className="truncate text-[11.5px] text-dim">{page.user!.email}</p>}
                </div>
                <MenuItem
                  icon="logout"
                  onClick={() => {
                    close()
                    router.post(`${page.site.prefix}/logout`)
                  }}
                >
                  Sign out
                </MenuItem>
              </>
            )}
          </Menu>
        )}
      </header>

      <div className="flex">
        <Sidebar nav={page.nav} open={open} onClose={() => setOpen(false)} />
        <main id="wd-main" className="min-w-0 flex-1">
          <Flash messages={page.flash} />
          <div className={cn('mx-auto w-full px-4 py-4 md:px-6', page.site.wide ? '' : 'max-w-[1400px]')}>
            {title && <h1 className="sr-only">{title}</h1>}
            {children}
          </div>
          {page.site.footer && (
            <footer className="border-t border-line px-4 py-3 text-[11.5px] text-dim md:px-6">{page.site.footer}</footer>
          )}
        </main>
      </div>

      {palette && <Palette nav={page.nav} onClose={() => setPalette(false)} />}
    </div>
  )
}

function Sidebar({ nav, open, onClose }: { nav: ShellProps['nav']; open: boolean; onClose: () => void }) {
  const here = typeof window !== 'undefined' ? window.location.pathname : ''
  return (
    <>
      {open && <div className="fixed inset-0 z-20 bg-black/30 md:hidden" onClick={onClose} />}
      <nav
        className={cn(
          'z-20 w-56 shrink-0 border-r border-line bg-surface',
          'fixed inset-y-0 left-0 top-11 overflow-y-auto transition-transform md:sticky md:top-11 md:h-[calc(100vh-2.75rem)] md:translate-x-0',
          open ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        <div className="p-2">
          {nav.map((group) => (
            <div key={group.label || '_'} className="mb-3">
              {group.label && (
                <p className="px-2 pb-1 pt-2 text-[10.5px] font-semibold uppercase tracking-wider text-dim">{group.label}</p>
              )}
              {group.items.map((item) => {
                const active = here === item.href || here.startsWith(`${item.href}/`)
                return (
                  <Link
                    key={item.key}
                    href={item.href}
                    onClick={onClose}
                    className={cn(
                      'flex items-center gap-2 rounded-[var(--radius-wd)] px-2 py-1.5 text-[12.5px]',
                      active ? 'bg-raised font-medium text-ink' : 'text-dim hover:bg-raised hover:text-ink',
                    )}
                  >
                    <Icon name={item.icon ?? (item.kind === 'page' ? 'file' : 'database')} className="h-3.5 w-3.5 shrink-0" />
                    <span className="truncate">{item.label}</span>
                  </Link>
                )
              })}
            </div>
          ))}
        </div>
      </nav>
    </>
  )
}

function Flash({ messages }: { messages: ShellProps['flash'] }) {
  const [dismissed, setDismissed] = useState<number[]>([])
  if (!messages?.length) return null
  const tones: Record<string, string> = {
    success: 'bg-emerald-500/10 text-emerald-800 dark:text-emerald-300 border-emerald-500/25',
    warning: 'bg-amber-500/10 text-amber-800 dark:text-amber-300 border-amber-500/25',
    danger: 'bg-red-500/10 text-red-800 dark:text-red-300 border-red-500/25',
    neutral: 'bg-raised text-ink border-line',
  }
  return (
    <div className="space-y-px">
      {messages.map((flash, i) =>
        dismissed.includes(i) ? null : (
          <div key={i} role="status" className={cn('flex items-center gap-2 border-b px-4 py-2 text-[12.5px] md:px-6', tones[flash.tone] ?? tones.neutral)}>
            <Icon name={flash.tone === 'danger' ? 'alert' : flash.tone === 'warning' ? 'alert' : 'check'} className="h-3.5 w-3.5 shrink-0" />
            <span className="flex-1">{flash.message}</span>
            <button type="button" onClick={() => setDismissed((d) => [...d, i])} aria-label="Dismiss" className="text-current opacity-60 hover:opacity-100">
              <Icon name="x" className="h-3.5 w-3.5" />
            </button>
          </div>
        ),
      )}
    </div>
  )
}

function Palette({ nav, onClose }: { nav: ShellProps['nav']; onClose: () => void }) {
  const [term, setTerm] = useState('')
  const [cursor, setCursor] = useState(0)

  const items = useMemo(() => {
    const flat = nav.flatMap((group) => group.items.map((item) => ({ ...item, group: group.label })))
    const needle = term.trim().toLowerCase()
    if (!needle) return flat
    return flat.filter((item) => item.label.toLowerCase().includes(needle) || item.group.toLowerCase().includes(needle))
  }, [nav, term])

  useEffect(() => setCursor(0), [term])

  useEffect(() => {
    const keys = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
      if (event.key === 'ArrowDown') {
        event.preventDefault()
        setCursor((c) => Math.min(c + 1, items.length - 1))
      }
      if (event.key === 'ArrowUp') {
        event.preventDefault()
        setCursor((c) => Math.max(c - 1, 0))
      }
      if (event.key === 'Enter' && items[cursor]) {
        onClose()
        router.visit(items[cursor].href)
      }
    }
    document.addEventListener('keydown', keys)
    return () => document.removeEventListener('keydown', keys)
  }, [items, cursor, onClose])

  return (
    <div className="fixed inset-0 z-50 bg-black/35 p-4 pt-[12vh]" onMouseDown={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Command palette"
        onMouseDown={(event) => event.stopPropagation()}
        className="mx-auto w-full max-w-lg overflow-hidden rounded-[var(--radius-wd)] bg-surface ring-1 ring-line shadow-[0_16px_48px_-16px_rgb(0_0_0/0.5)]"
      >
        <div className="flex items-center gap-2 border-b border-line px-3">
          <Icon name="search" className="h-4 w-4 shrink-0 text-dim" />
          <input
            autoFocus
            value={term}
            onChange={(event) => setTerm(event.target.value)}
            placeholder="Go to…"
            className="h-11 w-full bg-transparent text-[13px] outline-none placeholder:text-dim"
          />
        </div>
        <div className="max-h-80 overflow-y-auto py-1">
          {items.length === 0 && <p className="px-3 py-6 text-center text-[12.5px] text-dim">Nothing matches “{term}”.</p>}
          {items.map((item, i) => (
            <button
              key={item.key}
              type="button"
              onMouseEnter={() => setCursor(i)}
              onClick={() => {
                onClose()
                router.visit(item.href)
              }}
              className={cn('flex w-full items-center gap-2 px-3 py-2 text-left text-[12.5px]', i === cursor ? 'bg-raised' : '')}
            >
              <Icon name={item.icon ?? 'database'} className="h-3.5 w-3.5 shrink-0 text-dim" />
              <span className="flex-1 truncate">{item.label}</span>
              {item.group && <span className="text-[11px] text-dim">{item.group}</span>}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
