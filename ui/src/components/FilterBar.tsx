import { useEffect, useState } from 'react'
import type { FilterSpec, ListPage } from '../types'
import { cn } from '../lib/cn'
import { go } from '../lib/url'
import { Icon } from './Icon'
import { Button, Input, Select } from './ui'

/**
 * One control per filter kind, and the state lives in the URL.
 *
 * The search box debounces; everything else applies on change. A select that
 * waits for you to press a button is a select you press twice.
 */
export function FilterBar({ page }: { page: ListPage }) {
  const search = page.filters.find((f) => f.kind === 'search')
  const rest = page.filters.filter((f) => f.kind !== 'search')
  const active = Object.keys(page.query.filters).filter((k) => k !== 'q').length

  return (
    <div className="flex flex-wrap items-center gap-2">
      {search && <Search filter={search} value={page.query.filters.q ?? ''} />}
      {rest.map((filter) => (
        <Control key={filter.key} filter={filter} value={page.query.filters[filter.key] ?? ''} />
      ))}
      {active > 0 && (
        <Button
          size="sm"
          style="ghost"
          icon="x"
          onClick={() => go(Object.fromEntries(rest.map((f) => [f.key, null])))}
        >
          Clear {active}
        </Button>
      )}
    </div>
  )
}

function Search({ filter, value }: { filter: FilterSpec; value: string }) {
  const [term, setTerm] = useState(value)

  // Debounced, and only the rows are re-fetched: a partial reload keeps the
  // nav, the filters and the scroll position exactly where they were.
  useEffect(() => {
    if (term === value) return
    const timer = setTimeout(() => go({ q: term || null }, { replace: true, only: ['rows', 'total', 'pages', 'query'] }), 220)
    return () => clearTimeout(timer)
  }, [term, value])

  useEffect(() => setTerm(value), [value])

  return (
    <div className="relative">
      <Icon name="search" className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-dim" />
      <Input
        value={term}
        onChange={(event) => setTerm(event.target.value)}
        placeholder={filter.label}
        aria-label={filter.label}
        className="w-56 pl-8"
      />
    </div>
  )
}

function Control({ filter, value }: { filter: FilterSpec; value: string }) {
  const set = (next: string | null) => go({ [filter.key]: next })

  switch (filter.kind) {
    case 'choice':
    case 'relation': {
      const choices = (filter.options.choices as [string, string][]) ?? []
      return (
        <Select value={value} onChange={(event) => set(event.target.value || null)} aria-label={filter.label} className="w-auto min-w-36">
          <option value="">{filter.label}: any</option>
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
        <Select value={value} onChange={(event) => set(event.target.value || null)} aria-label={filter.label} className="w-auto min-w-32">
          <option value="">{filter.label}: any</option>
          <option value="true">{yes}</option>
          <option value="false">{no}</option>
        </Select>
      )
    }

    case 'date_range': {
      const presets = (filter.options.presets as string[]) ?? []
      return (
        <Select value={value} onChange={(event) => set(event.target.value || null)} aria-label={filter.label} className="w-auto min-w-36">
          <option value="">{filter.label}: any</option>
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
        <Button
          size="sm"
          style={value ? 'primary' : 'default'}
          onClick={() => set(value ? null : 'true')}
          className={cn(value && 'ring-0')}
        >
          {filter.label}
        </Button>
      )

    case 'number_range':
      return (
        <Input
          defaultValue={value}
          onBlur={(event) => set(event.target.value || null)}
          placeholder={`${filter.label} (10..50)`}
          aria-label={filter.label}
          className="w-40"
        />
      )

    default:
      return (
        <Input
          defaultValue={value}
          onBlur={(event) => set(event.target.value || null)}
          placeholder={filter.label}
          aria-label={filter.label}
          className="w-40"
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
