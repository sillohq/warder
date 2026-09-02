import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { Link, router, usePage } from '@inertiajs/react'
import type { Shell as ShellProps } from '../types'
import { cn } from '../lib/cn'
import { applyMode, nextMode, readMode, resolved, type Mode } from '../lib/theme'
import { Icon } from './Icon'
import { IconButton, Menu, MenuItem } from './ui'

/**
 * The frame every screen sits in: navigation, search, the user menu, flash
 * messages, and the command palette.
 *
 * The palette is primary navigation, not a bonus. An admin with forty
 * resources has a sidebar nobody reads to the bottom of, and the people who
 * live in it reach for ⌘K by the second week.
 */
export function Shell({ children, title }: { children: ReactNode; title?: string }) {
  const page = usePage().props as unknown as ShellProps
  const [open, setOpen] = useState(false)
  const [palette, setPalette] = useState(false)
  const [mode, setMode] = useState<Mode>('system')

  useEffect(() => setMode(readMode()), [])

  useEffect(() => {
    const keys = (event: KeyboardEvent) => {
      const typing = /^(INPUT|TEXTAREA|SELECT)$/.test((event.target as HTMLElement)?.tagName ?? '')
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        setPalette(true)
      }
      if (event.key === '/' && !typing && !event.metaKey && !event.ctrlKey) {
        const box = document.querySelector<HTMLInputElement>('[data-wd-search]')
        if (box) {
          event.preventDefault()
          box.focus()
        }
      }
    }
    document.addEventListener('keydown', keys)
    return () => document.removeEventListener('keydown', keys)
  }, [])

  const toggle = () => {
    const next = nextMode(resolved(mode))
    setMode(next)
    applyMode(next)
  }

  return (
    <div className="min-h-screen bg-bg text-ink">
      <a
        href="#wd-main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-[var(--radius-wd-sm)] focus:bg-surface focus:px-4 focus:py-2.5 focus:ring-1 focus:ring-edge"
      >
        Skip to content
      </a>

      <Sidebar site={page.site} nav={page.nav} open={open} onClose={() => setOpen(false)} />

      <div className="md:pl-[var(--spacing-sidebar)]">
        <header className="sticky top-0 z-30 flex h-[var(--spacing-header)] items-center gap-3 border-b border-line bg-bg/95 px-5 backdrop-blur-sm md:px-page">
          <IconButton icon="more" label="Menu" onClick={() => setOpen((v) => !v)} className="-ml-2 md:hidden" />

          <button
            type="button"
            onClick={() => setPalette(true)}
            className="hidden h-9 items-center gap-2.5 rounded-[var(--radius-wd-sm)] px-3 text-[13px] text-dim ring-1 ring-line transition-colors hover:bg-raised hover:text-ink sm:inline-flex"
          >
            <Icon name="search" className="h-4 w-4" />
            Jump to…
            <kbd className="ml-3 rounded bg-raised px-1.5 py-0.5 font-mono text-[10.5px] text-faint">⌘K</kbd>
          </button>

          <div className="flex-1" />

          <IconButton
            icon={resolved(mode) === 'dark' ? 'sun' : 'moon'}
            label={resolved(mode) === 'dark' ? 'Switch to light' : 'Switch to dark'}
            onClick={toggle}
          />

          {page.user && (
            <Menu
              trigger={
                <button
                  type="button"
                  className="flex h-9 items-center gap-2 rounded-[var(--radius-wd-sm)] pl-1 pr-2 text-[13px] font-medium transition-colors hover:bg-raised"
                >
                  <span className="grid h-7 w-7 place-items-center rounded-full bg-accent text-[11px] font-bold uppercase text-on-accent">
                    {page.user.label.slice(0, 1)}
                  </span>
                  <span className="hidden max-w-36 truncate sm:inline">{page.user.label}</span>
                  <Icon name="chevronDown" className="h-3.5 w-3.5 text-faint" />
                </button>
              }
            >
              {(close) => (
                <>
                  <div className="border-b border-line px-4 pb-3 pt-2">
                    <p className="truncate text-[13.5px] font-semibold text-ink">{page.user!.label}</p>
                    {page.user!.email && <p className="truncate text-[12px] text-dim">{page.user!.email}</p>}
                    {page.user!.superuser && (
                      <span className="mt-2 inline-flex rounded-full bg-accent/12 px-2 py-0.5 text-[10.5px] font-bold uppercase tracking-wide text-accent">
                        Superuser
                      </span>
                    )}
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

        <main id="wd-main">
          <Flash messages={page.flash} />
          <div className={cn('mx-auto w-full px-5 py-page md:px-page', page.site.wide ? '' : 'max-w-[1560px]')}>
            {title && <h1 className="sr-only">{title}</h1>}
            {children}
          </div>
          {page.site.footer && (
            <footer className="border-t border-line px-5 py-5 text-[12.5px] text-faint md:px-page">{page.site.footer}</footer>
          )}
        </main>
      </div>

      {palette && <Palette nav={page.nav} onClose={() => setPalette(false)} />}
    </div>
  )
}

function Sidebar({
  site,
  nav,
  open,
  onClose,
}: {
  site: ShellProps['site']
  nav: ShellProps['nav']
  open: boolean
  onClose: () => void
}) {
  const here = typeof window !== 'undefined' ? window.location.pathname : ''
  return (
    <>
      {open && <div className="fixed inset-0 z-30 bg-black/40 md:hidden" onClick={onClose} />}
      <nav
        className={cn(
          'fixed inset-y-0 left-0 z-40 flex w-[var(--spacing-sidebar)] flex-col border-r border-line bg-bg',
          'transition-transform md:translate-x-0',
          open ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        <Link
          href={site.prefix}
          className="flex h-[var(--spacing-header)] shrink-0 items-center gap-2.5 border-b border-line px-5"
        >
          {site.logo ? (
            <img src={site.logo} alt="" className="h-7 w-7 rounded-[var(--radius-wd-sm)] object-contain" />
          ) : (
            <span className="grid h-7 w-7 shrink-0 place-items-center rounded-[var(--radius-wd-sm)] bg-accent text-[13px] font-extrabold text-on-accent">
              {site.brand.slice(0, 1)}
            </span>
          )}
          <span className="truncate text-[15px] font-bold tracking-tight">{site.brand}</span>
        </Link>

        <div className="wd-scroll-y flex-1 overflow-y-auto px-3 py-4">
          {nav.map((group) => (
            <div key={group.label || '_'} className="mb-5 last:mb-0">
              {group.label && <p className="wd-eyebrow px-3 pb-2">{group.label}</p>}
              <div className="space-y-0.5">
                {group.items.map((item) => {
                  const active = here === item.href || here.startsWith(`${item.href}/`)
                  return (
                    <Link
                      key={item.key}
                      href={item.href}
                      onClick={onClose}
                      className={cn(
                        'group flex items-center gap-2.5 rounded-[var(--radius-wd-sm)] px-3 py-2.5 text-[13.5px] font-medium transition-colors',
                        active
                          ? 'bg-accent/10 font-semibold text-accent'
                          : 'text-dim hover:bg-raised hover:text-ink',
                      )}
                    >
                      <Icon
                        name={item.icon ?? (item.kind === 'page' ? 'file' : 'database')}
                        className={cn('h-4 w-4 shrink-0', active ? 'opacity-100' : 'opacity-55 group-hover:opacity-100')}
                      />
                      <span className="truncate">{item.label}</span>
                    </Link>
                  )
                })}
              </div>
            </div>
          ))}
        </div>

        <div className="shrink-0 border-t border-line px-5 py-4 text-[11.5px] text-faint">
          Warder
        </div>
      </nav>
    </>
  )
}

const TONES: Record<string, string> = {
  success: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20',
  warning: 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20',
  danger: 'bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/20',
  neutral: 'bg-raised text-ink border-line',
}

function Flash({ messages }: { messages: ShellProps['flash'] }) {
  const [gone, setGone] = useState<number[]>([])
  if (!messages?.length) return null
  return (
    <div>
      {messages.map((flash, i) =>
        gone.includes(i) ? null : (
          <div
            key={i}
            role="status"
            className={cn(
              'wd-in flex items-center gap-3 border-b px-5 py-3.5 text-[13.5px] font-medium md:px-page',
              TONES[flash.tone] ?? TONES.neutral,
            )}
          >
            <Icon name={flash.tone === 'success' ? 'check' : 'alert'} className="h-4 w-4 shrink-0" />
            <span className="flex-1">{flash.message}</span>
            <button type="button" onClick={() => setGone((d) => [...d, i])} aria-label="Dismiss" className="opacity-60 hover:opacity-100">
              <Icon name="x" className="h-4 w-4" />
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
    return flat.filter(
      (item) => item.label.toLowerCase().includes(needle) || item.group.toLowerCase().includes(needle),
    )
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
    <div className="fixed inset-0 z-50 bg-black/50 p-4 pt-[12vh] backdrop-blur-[2px]" onMouseDown={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Command palette"
        onMouseDown={(event) => event.stopPropagation()}
        className="wd-in mx-auto w-full max-w-xl overflow-hidden rounded-[var(--radius-wd)] bg-surface ring-1 ring-edge shadow-[0_24px_64px_-16px_rgb(0_0_0/0.6)]"
      >
        <div className="flex items-center gap-3 border-b border-line px-5">
          <Icon name="search" className="h-4.5 w-4.5 shrink-0 text-faint" />
          <input
            autoFocus
            value={term}
            onChange={(event) => setTerm(event.target.value)}
            placeholder="Jump to a resource or a page…"
            className="h-14 w-full bg-transparent text-[15px] outline-none placeholder:text-faint"
          />
          <kbd className="shrink-0 rounded bg-raised px-1.5 py-0.5 font-mono text-[10.5px] text-faint">esc</kbd>
        </div>
        <div className="wd-scroll-y max-h-[22rem] overflow-y-auto py-2">
          {items.length === 0 && (
            <p className="px-5 py-10 text-center text-[13.5px] text-dim">Nothing matches “{term}”.</p>
          )}
          {items.map((item, i) => (
            <button
              key={item.key}
              type="button"
              onMouseEnter={() => setCursor(i)}
              onClick={() => {
                onClose()
                router.visit(item.href)
              }}
              className={cn(
                'flex w-full items-center gap-3 px-5 py-3 text-left text-[13.5px] transition-colors',
                i === cursor ? 'bg-raised text-ink' : 'text-dim',
              )}
            >
              <Icon name={item.icon ?? 'database'} className="h-4 w-4 shrink-0 opacity-60" />
              <span className="flex-1 truncate font-medium">{item.label}</span>
              {item.group && <span className="shrink-0 text-[11.5px] text-faint">{item.group}</span>}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
