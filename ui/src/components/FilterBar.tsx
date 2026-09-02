import { useEffect, useState } from 'react'
import type { FilterSpec, ListPage } from '../types'
import { cn } from '../lib/cn'
import { go } from '../lib/url'
import { Icon } from './Icon'
import { Input, Select } from './ui'

/**
 * The filter bar: one labelled control per filter, in a row that stays a row.
 *
 * Bare controls wrapping one per line was the old shape and it read as a pile.
 * These sit in their own bar, each under its name, so five filters look like
 * five filters rather than five unrelated boxes — and the bar scrolls sideways
 * rather than growing downwards and pushing the table off the screen.
 *
 * Every value lives in the URL. That is not an implementation detail: a
 * filtered list you cannot send to a colleague is one you rebuild every
 * morning.
 */
export function FilterBar({ page }: { page: ListPage }) {
  const search = page.filters.find((f) => f.kind === 'search')
  const rest = page.filters.filter((f) => f.kind !== 'search')
  const active = Object.keys(page.query.filters).filter((k) => page.query.filters[k])

  if (!search && !rest.length) return null

  return (
    <div className="mb-5 rounded-[var(--radius-wd)] bg-surface ring-1 ring-line">
      <div className="flex items-end gap-3 overflow-x-auto p-4">
        {search && (
          <Group label={search.label} className="min-w-64">
            <Search filter={search} value={page.query.filters.q ?? ''} />
          </Group>
        )}
        {rest.map((filter) => (
          <Group key={filter.key} label={filter.label} on={Boolean(page.query.filters[filter.key])}>
            <Control filter={filter} value={page.query.filters[filter.key] ?? ''} />
          </Group>
        ))}

        <div className="flex-1" />

        {active.length > 0 && (
          <button
            type="button"
            onClick={() => go(Object.fromEntries(page.filters.map((f) => [f.key, null])))}
            className="mb-[1px] inline-flex h-10 shrink-0 items-center gap-1.5 rounded-[var(--radius-wd-sm)] px-3 text-[12.5px] font-semibold text-accent transition-colors hover:bg-accent/10"
          >
            <Icon name="x" className="h-3.5 w-3.5" />
            Clear {active.length}
          </button>
        )}
      </div>
    </div>
  )
}

function Group({
  label,
  children,
  className,
  on,
}: {
  label: string
  children: React.ReactNode
  className?: string
  on?: boolean
}) {
  return (
    <div className={cn('flex shrink-0 flex-col gap-1.5', className)}>
      <span className={cn('wd-eyebrow', on && 'text-accent')}>{label}</span>
      {children}
    </div>
  )
}

function Search({ filter, value }: { filter: FilterSpec; value: string }) {
  const [term, setTerm] = useState(value)

  // Debounced, and only the rows are refetched: a partial reload keeps the
  // navigation, the filters and the scroll position exactly where they were.
  useEffect(() => {
    if (term === value) return
    const timer = setTimeout(
      () => go({ q: term || null }, { replace: true, only: ['rows', 'total', 'pages', 'query'] }),
      220,
    )
    return () => clearTimeout(timer)
  }, [term, value])

  useEffect(() => setTerm(value), [value])

  return (
    <div className="relative">
      <Icon name="search" className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-faint" />
      <Input
        data-wd-search
        value={term}
        onChange={(event) => setTerm(event.target.value)}
        placeholder={`${filter.label}…`}
        aria-label={filter.label}
        className="w-full pl-10 pr-9"
      />
      {term ? (
        <button
          type="button"
          aria-label="Clear search"
          onClick={() => setTerm('')}
          className="absolute right-2.5 top-1/2 -translate-y-1/2 text-faint hover:text-ink"
        >
          <Icon name="x" className="h-3.5 w-3.5" />
        </button>
      ) : (
        <kbd className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 rounded bg-raised px-1.5 py-0.5 font-mono text-[10.5px] text-faint">
          /
        </kbd>
      )}
    </div>
  )
}

function Control({ filter, value }: { filter: FilterSpec; value: string }) {
  const set = (next: string | null) => go({ [filter.key]: next })
  const on = Boolean(value)
  const ring = on ? 'ring-accent' : undefined

  switch (filter.kind) {
    case 'choice':
    case 'relation': {
      const choices = (filter.options.choices as [string, string][]) ?? []
      return (
        <Select value={value} onChange={(e) => set(e.target.value || null)} aria-label={filter.label} className={cn('w-44', ring)}>
          <option value="">Any</option>
          {choices.map(([option, label]) => (
            <option key={String(option)} value={String(option)}>
              {label}
            </option>
          ))}
        </Select>
      )
    }

    case 'bool':
    case 'exists': {
      const [yes, no] = (filter.options.labels as [string, string]) ?? ['Yes', 'No']
      return (
        <Select value={value} onChange={(e) => set(e.target.value || null)} aria-label={filter.label} className={cn('w-36', ring)}>
          <option value="">Any</option>
          <option value="true">{yes}</option>
          <option value="false">{no}</option>
        </Select>
      )
    }

    case 'date_range': {
      const presets = (filter.options.presets as string[]) ?? []
      return (
        <Select value={value} onChange={(e) => set(e.target.value || null)} aria-label={filter.label} className={cn('w-44', ring)}>
          <option value="">Any time</option>
          {presets.map((preset) => (
            <option key={preset} value={preset}>
              {PRESETS[preset] ?? preset}
            </option>
          ))}
        </Select>
      )
    }

    case 'toggle':
      return (
        <button
          type="button"
          onClick={() => set(on ? null : 'true')}
          className={cn(
            'inline-flex h-10 items-center gap-2 rounded-[var(--radius-wd-sm)] px-3.5 text-[13px] font-semibold transition-colors',
            on
              ? 'bg-accent text-on-accent'
              : 'bg-sunken text-dim ring-1 ring-inset ring-line hover:text-ink',
          )}
        >
          {on && <Icon name="check" className="h-3.5 w-3.5" />}
          {on ? 'On' : 'Off'}
        </button>
      )

    case 'number_range':
      return (
        <Input
          defaultValue={value}
          onBlur={(e) => set(e.target.value || null)}
          placeholder="10..50"
          aria-label={filter.label}
          className={cn('w-36', ring)}
        />
      )

    default:
      return (
        <Input
          defaultValue={value}
          onBlur={(e) => set(e.target.value || null)}
          placeholder="Contains…"
          aria-label={filter.label}
          className={cn('w-44', ring)}
        />
      )
  }
}

const PRESETS: Record<string, string> = {
  today: 'Today',
  yesterday: 'Yesterday',
  '7d': 'Last 7 days',
  '30d': 'Last 30 days',
  '90d': 'Last 90 days',
  month: 'This month',
  last_month: 'Last month',
  quarter: 'This quarter',
  ytd: 'Year to date',
  '12m': 'Last 12 months',
  all: 'All time',
}
