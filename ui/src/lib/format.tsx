import type { ColumnSpec, Json } from '../types'
import { cn } from './cn'
import { Icon } from '../components/Icon'

// Formatting lives here, and only here.
//
// Python extracts values — which columns exist for this person, which rows they
// may see, what each cell holds. The browser formats them, because the browser
// is the only side that knows the viewer's locale, their timezone and how wide
// the column is. Sending "£1,234.50" from the server means guessing all three.

const BADGES: Record<string, string> = {
  green: 'bg-emerald-500/12 text-emerald-700 dark:text-emerald-400 ring-emerald-500/25',
  red: 'bg-red-500/12 text-red-700 dark:text-red-400 ring-red-500/25',
  amber: 'bg-amber-500/15 text-amber-700 dark:text-amber-400 ring-amber-500/25',
  blue: 'bg-blue-500/12 text-blue-700 dark:text-blue-400 ring-blue-500/25',
  violet: 'bg-violet-500/12 text-violet-700 dark:text-violet-400 ring-violet-500/25',
  zinc: 'bg-zinc-500/12 text-zinc-700 dark:text-zinc-300 ring-zinc-500/25',
}

const UNITS_BINARY = ['B', 'KiB', 'MiB', 'GiB', 'TiB']
const UNITS_DECIMAL = ['B', 'KB', 'MB', 'GB', 'TB']

export function Cell({ column, value }: { column: ColumnSpec; value: Json }) {
  const empty = <span className="text-dim">{column.empty}</span>
  if (value === null || value === undefined || value === '') return empty

  const { kind, options } = column.format
  const opt = <T,>(name: string, fallback: T): T => (options[name] as T) ?? fallback

  switch (kind) {
    case 'badge': {
      const colors = opt<Record<string, string>>('colors', {})
      const labels = opt<Record<string, string>>('labels', {})
      const key = String(value)
      const tone = BADGES[colors[key] ?? opt('default', 'zinc')] ?? BADGES.zinc
      return (
        <span className={cn('inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium ring-1 ring-inset', tone)}>
          {labels[key] ?? humanise(key)}
        </span>
      )
    }

    case 'bool': {
      const [yes, no] = opt<[string, string]>('labels', ['Yes', 'No'])
      const on = Boolean(value)
      const style = opt<string>('style', 'icon')
      if (style === 'text') return <>{on ? yes : no}</>
      if (style === 'dot') {
        return <span className={cn('inline-block h-2 w-2 rounded-full', on ? 'bg-emerald-500' : 'bg-zinc-400')} title={on ? yes : no} />
      }
      return (
        <span title={on ? yes : no} className={on ? 'text-emerald-600 dark:text-emerald-400' : 'text-dim'}>
          <Icon name={on ? 'check' : 'x'} className="h-3.5 w-3.5" />
        </span>
      )
    }

    case 'money':
      return <span className="wd-num">{money(Number(value), opt('currency', 'USD'), opt('precision', 2))}</span>

    case 'number': {
      const shown = new Intl.NumberFormat(undefined, {
        minimumFractionDigits: opt('precision', 0),
        maximumFractionDigits: opt('precision', 0),
        useGrouping: opt('grouping', true),
      }).format(Number(value))
      return <span className="wd-num">{opt('prefix', '')}{shown}{opt('suffix', '')}</span>
    }

    case 'percent': {
      const scale = opt('of', 1)
      return <span className="wd-num">{new Intl.NumberFormat(undefined, { style: 'percent', maximumFractionDigits: opt('precision', 0) }).format(Number(value) / scale)}</span>
    }

    case 'bytes':
      return <span className="wd-num">{bytes(Number(value), opt('binary', true))}</span>

    case 'duration':
      return <span className="wd-num">{duration(Number(value), opt('unit', 'seconds'), opt('style', 'short'))}</span>

    case 'date': {
      const style = opt<string>('style', 'date')
      const exact = absolute(String(value), style === 'relative' ? 'datetime' : style)
      if (style !== 'relative') return <span className="wd-num">{exact}</span>
      return (
        <span className="wd-num" title={opt('tooltip', true) ? exact : undefined}>
          {relative(String(value))}
        </span>
      )
    }

    case 'code':
      return <code className="rounded bg-raised px-1.5 py-0.5 font-mono text-[11.5px]">{String(value)}</code>

    case 'json':
      return <code className="font-mono text-[11.5px] text-dim">{truncate(JSON.stringify(value), 60)}</code>

    case 'tags': {
      const items = Array.isArray(value) ? value : [value]
      const limit = opt<number | null>('limit', 3) ?? items.length
      const tone = BADGES[opt('color', 'zinc')] ?? BADGES.zinc
      return (
        <span className="flex flex-wrap gap-1">
          {items.slice(0, limit).map((item, i) => (
            <span key={i} className={cn('inline-flex rounded px-1.5 py-0.5 text-[11px] ring-1 ring-inset', tone)}>{label(item)}</span>
          ))}
          {items.length > limit && <span className="text-dim text-[11px] self-center">+{items.length - limit}</span>}
        </span>
      )
    }

    case 'progress': {
      const pct = Math.max(0, Math.min(100, (Number(value) / opt('max', 100)) * 100))
      return (
        <span className="flex items-center gap-2">
          <span className="h-1.5 w-20 overflow-hidden rounded-full bg-raised">
            <span className="block h-full rounded-full bg-accent" style={{ width: `${pct}%` }} />
          </span>
          <span className="wd-num text-dim text-[11px]">{Math.round(pct)}%</span>
        </span>
      )
    }

    case 'rating': {
      const max = opt('max', 5)
      return (
        <span className="text-amber-500" aria-label={`${value} out of ${max}`}>
          {'★'.repeat(Math.round(Number(value)))}
          <span className="text-dim">{'★'.repeat(Math.max(0, max - Math.round(Number(value))))}</span>
        </span>
      )
    }

    case 'color':
      return (
        <span className="inline-flex items-center gap-1.5">
          <span className="h-3.5 w-3.5 rounded ring-1 ring-line" style={{ background: String(value) }} />
          <code className="font-mono text-[11.5px]">{String(value)}</code>
        </span>
      )

    case 'image':
    case 'avatar': {
      const src = typeof value === 'object' && value ? String((value as Record<string, Json>).label ?? '') : String(value)
      const size = opt<number>('size', kind === 'avatar' ? 24 : 32)
      if (kind === 'avatar') {
        return (
          <span className="inline-flex items-center gap-2">
            <span className="grid shrink-0 place-items-center rounded-full bg-raised text-[10px] font-medium uppercase text-dim" style={{ width: size, height: size }}>
              {initials(label(value))}
            </span>
            <span className="truncate">{label(value)}</span>
          </span>
        )
      }
      return <img src={src} alt="" width={size} height={size} loading="lazy" className={cn('object-cover', rounding(opt<string>('rounded', 'md')))} style={{ width: size, height: size }} />
    }

    case 'markdown':
    case 'html':
      // Sanitised on the way out of Python, and still not injected as HTML
      // here. A cell is one line in a table; the detail page is where prose
      // belongs.
      return <span className="text-dim">{truncate(stripTags(String(value)), 80)}</span>

    default: {
      const text = label(value)
      const clip = opt<number | null>('truncate', null)
      return <span className={cn(opt('mono', false) && 'font-mono wd-num text-[11.5px]')}>{clip ? truncate(text, clip) : text}</span>
    }
  }
}

// ---------------------------------------------------------------- primitives

export function label(value: Json): string {
  if (value === null || value === undefined) return ''
  if (typeof value === 'object' && !Array.isArray(value)) {
    const record = value as Record<string, Json>
    return String(record.label ?? record.id ?? '')
  }
  if (Array.isArray(value)) return value.map(label).join(', ')
  return String(value)
}

export function money(amount: number, currency: string, precision: number): string {
  try {
    return new Intl.NumberFormat(undefined, { style: 'currency', currency, minimumFractionDigits: precision, maximumFractionDigits: precision }).format(amount)
  } catch {
    return amount.toFixed(precision)
  }
}

export function bytes(size: number, binary: boolean): string {
  const step = binary ? 1024 : 1000
  const units = binary ? UNITS_BINARY : UNITS_DECIMAL
  let value = size
  let unit = 0
  while (value >= step && unit < units.length - 1) {
    value /= step
    unit += 1
  }
  return `${value.toFixed(unit === 0 ? 0 : 1)} ${units[unit]}`
}

export function duration(value: number, unit: string, style: string): string {
  let seconds = value
  if (unit === 'milliseconds') seconds = value / 1000
  if (unit === 'minutes') seconds = value * 60
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const rest = Math.floor(seconds % 60)
  if (style === 'long') {
    const parts = []
    if (hours) parts.push(`${hours} hour${hours === 1 ? '' : 's'}`)
    if (minutes) parts.push(`${minutes} minute${minutes === 1 ? '' : 's'}`)
    if (rest || !parts.length) parts.push(`${rest} second${rest === 1 ? '' : 's'}`)
    return parts.join(' ')
  }
  if (hours) return `${hours}h ${minutes}m`
  if (minutes) return `${minutes}m ${rest}s`
  return `${rest}s`
}

export function absolute(iso: string, style: string): string {
  const at = new Date(iso)
  if (Number.isNaN(at.getTime())) return iso
  if (style === 'iso') return at.toISOString()
  if (style === 'time') return at.toLocaleTimeString()
  if (style === 'datetime') return at.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
  return at.toLocaleDateString(undefined, { dateStyle: 'medium' })
}

const SPANS: [number, Intl.RelativeTimeFormatUnit][] = [
  [60, 'second'],
  [3600, 'minute'],
  [86400, 'hour'],
  [604800, 'day'],
  [2629800, 'week'],
  [31557600, 'month'],
  [Infinity, 'year'],
]

export function relative(iso: string): string {
  const at = new Date(iso)
  if (Number.isNaN(at.getTime())) return iso
  const seconds = (at.getTime() - Date.now()) / 1000
  const magnitude = Math.abs(seconds)
  let divisor = 1
  let unit: Intl.RelativeTimeFormatUnit = 'second'
  for (let i = 0; i < SPANS.length; i += 1) {
    if (magnitude < SPANS[i][0]) {
      unit = SPANS[i][1]
      divisor = i === 0 ? 1 : SPANS[i - 1][0]
      break
    }
  }
  const format = new Intl.RelativeTimeFormat(undefined, { numeric: 'auto' })
  return format.format(Math.round(seconds / divisor), unit)
}

export function truncate(text: string, at: number): string {
  return text.length > at ? `${text.slice(0, at).trimEnd()}…` : text
}

export function humanise(text: string): string {
  const words = text.replace(/[_-]+/g, ' ').trim()
  return words.charAt(0).toUpperCase() + words.slice(1)
}

export function initials(name: string): string {
  return name.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]).join('')
}

function stripTags(html: string): string {
  return html.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim()
}

function rounding(name: string): string {
  return { none: 'rounded-none', sm: 'rounded-sm', md: 'rounded-md', full: 'rounded-full' }[name] ?? 'rounded-md'
}
