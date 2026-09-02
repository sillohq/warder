import { useId } from 'react'
import { cn } from '../lib/cn'

/**
 * A chart, drawn in the accent colour and nothing else.
 *
 * Four kinds, one data shape: `[{label, value}]`. That is all a dashboard card
 * sends, and all it should — Python counts the rows, the browser decides how
 * tall a bar is on this screen.
 *
 * The sizing is worth a note, because getting it wrong is invisible rather than
 * broken. A percentage height only resolves against a parent with a *definite*
 * height, and a flex child of an `items-end` row has neither — so bars sized
 * `height: 60%` silently collapse to nothing and the card renders empty. Every
 * bar here sits absolutely inside a `flex-1` track, which always has a height.
 *
 * Values are always readable. A number you have to hover to see is a number
 * nobody reads, and hovering is not available at all on a phone.
 */

export interface Point {
  label: string
  value: number
}

export function Chart({
  points,
  kind = 'bar',
  height = 200,
  currency,
}: {
  points: Point[]
  kind?: string
  height?: number
  currency?: string
}) {
  const clean = points.filter((p) => p && typeof p.value !== 'undefined')
  if (!clean.length) {
    return <p className="py-12 text-center text-[13px] text-faint">No data yet.</p>
  }
  if (kind === 'donut') return <Donut points={clean} height={height} />
  if (kind === 'line' || kind === 'area') {
    return <Line points={clean} height={height} area={kind === 'area'} currency={currency} />
  }
  return <Bars points={clean} height={height} currency={currency} />
}

// ------------------------------------------------------------------- shared

function short(value: number, currency?: string): string {
  if (currency) {
    try {
      return new Intl.NumberFormat(undefined, {
        style: 'currency',
        currency,
        notation: Math.abs(value) >= 10_000 ? 'compact' : 'standard',
        maximumFractionDigits: Math.abs(value) >= 10_000 ? 1 : 0,
      }).format(value)
    } catch {
      // An unknown currency code should not blank the chart.
    }
  }
  return new Intl.NumberFormat(undefined, {
    notation: Math.abs(value) >= 10_000 ? 'compact' : 'standard',
    maximumFractionDigits: 1,
  }).format(value)
}

/** A round number at or above the tallest point, so the axis reads cleanly. */
function ceiling(peak: number): number {
  if (peak <= 0) return 1
  const magnitude = 10 ** Math.floor(Math.log10(peak))
  for (const step of [1, 2, 2.5, 5, 10]) {
    const candidate = step * magnitude
    if (candidate >= peak) return candidate
  }
  return 10 * magnitude
}

function Grid({ top, currency }: { top: number; currency?: string }) {
  return (
    <div aria-hidden="true" className="pointer-events-none absolute inset-0">
      {[1, 0.75, 0.5, 0.25, 0].map((fraction) => (
        <div
          key={fraction}
          className="absolute inset-x-0 flex items-center gap-2"
          style={{ bottom: `${fraction * 100}%` }}
        >
          <span className="wd-num w-10 shrink-0 text-right text-[10px] text-faint">
            {fraction === 0 ? '0' : short(top * fraction, currency)}
          </span>
          <span
            className={cn(
              'h-px flex-1',
              fraction === 0 ? 'bg-edge' : 'bg-line',
            )}
          />
        </div>
      ))}
    </div>
  )
}

// --------------------------------------------------------------------- bars

function Bars({ points, height, currency }: { points: Point[]; height: number; currency?: string }) {
  const top = ceiling(Math.max(...points.map((p) => Number(p.value) || 0)))
  return (
    <div>
      <div className="relative" style={{ height }}>
        <Grid top={top} currency={currency} />
        {/* pl-12 clears the axis labels the grid draws. */}
        <div className="absolute inset-0 flex items-stretch gap-2 pl-12">
          {points.map((point, i) => {
            const value = Number(point.value) || 0
            const share = Math.max(0, value / top)
            return (
              <div key={i} className="group relative flex flex-1 flex-col justify-end">
                <span
                  // Absolute inside a definite-height track: a percentage
                  // height needs a parent that has one, or it collapses.
                  className="absolute inset-x-0 bottom-0 rounded-t-[3px] bg-accent transition-all group-hover:brightness-110"
                  style={{ height: value > 0 ? `max(3px, ${share * 100}%)` : '2px' }}
                />
                <span
                  className="wd-num pointer-events-none absolute inset-x-0 text-center text-[11px] font-bold text-ink"
                  style={{ bottom: `calc(${share * 100}% + 6px)` }}
                >
                  {short(value, currency)}
                </span>
                <span className="sr-only">
                  {point.label}: {value}
                </span>
              </div>
            )
          })}
        </div>
      </div>
      <div className="mt-2 flex gap-2 pl-12">
        {points.map((point, i) => (
          <span key={i} className="flex-1 truncate text-center text-[11px] text-dim" title={point.label}>
            {point.label}
          </span>
        ))}
      </div>
    </div>
  )
}

// --------------------------------------------------------------- line / area

function Line({
  points,
  height,
  area,
  currency,
}: {
  points: Point[]
  height: number
  area: boolean
  currency?: string
}) {
  const id = useId()
  const top = ceiling(Math.max(...points.map((p) => Number(p.value) || 0)))
  const width = 100
  const step = points.length > 1 ? width / (points.length - 1) : 0
  const at = (point: Point, i: number) => ({
    x: points.length > 1 ? i * step : width / 2,
    y: 100 - (Math.max(0, Number(point.value) || 0) / top) * 100,
  })
  const path = points.map((p, i) => at(p, i)).map(({ x, y }) => `${x},${y}`).join(' ')

  return (
    <div>
      <div className="relative" style={{ height }}>
        <Grid top={top} currency={currency} />
        <div className="absolute inset-0 pl-12">
          <svg
            viewBox="0 0 100 100"
            preserveAspectRatio="none"
            className="h-full w-full overflow-visible"
            role="img"
            aria-label={points.map((p) => `${p.label}: ${p.value}`).join(', ')}
          >
            {area && (
              <>
                <defs>
                  <linearGradient id={`wd-fill-${id}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="var(--wd-accent)" stopOpacity="0.28" />
                    <stop offset="100%" stopColor="var(--wd-accent)" stopOpacity="0.02" />
                  </linearGradient>
                </defs>
                <polygon points={`0,100 ${path} 100,100`} fill={`url(#wd-fill-${id})`} />
              </>
            )}
            <polyline
              points={path}
              fill="none"
              stroke="var(--wd-accent)"
              strokeWidth="2"
              vectorEffect="non-scaling-stroke"
              strokeLinejoin="round"
              strokeLinecap="round"
            />
            {points.map((point, i) => {
              const { x, y } = at(point, i)
              return (
                <circle
                  key={i}
                  cx={x}
                  cy={y}
                  r="3"
                  fill="var(--wd-surface)"
                  stroke="var(--wd-accent)"
                  strokeWidth="2"
                  vectorEffect="non-scaling-stroke"
                />
              )
            })}
          </svg>
        </div>
      </div>
      <div className="mt-2 flex gap-2 pl-12">
        {points.map((point, i) => (
          <span key={i} className="flex-1 truncate text-center text-[11px] text-dim" title={point.label}>
            {point.label}
          </span>
        ))}
      </div>
    </div>
  )
}

// -------------------------------------------------------------------- donut

/** The accent, then five neighbours of it. One hue family, six steps. */
const SLICES = [
  'var(--wd-accent)',
  'color-mix(in oklab, var(--wd-accent) 72%, var(--wd-surface))',
  'color-mix(in oklab, var(--wd-accent) 52%, var(--wd-surface))',
  'color-mix(in oklab, var(--wd-accent) 36%, var(--wd-surface))',
  'color-mix(in oklab, var(--wd-accent) 24%, var(--wd-surface))',
  'color-mix(in oklab, var(--wd-accent) 14%, var(--wd-surface))',
]

function Donut({ points, height }: { points: Point[]; height: number }) {
  const total = points.reduce((sum, point) => sum + Math.max(0, Number(point.value) || 0), 0)
  const radius = 15.9155 // circumference 100, so dasharray is a percentage
  let offset = 25 // start at twelve o'clock

  return (
    <div className="flex flex-wrap items-center gap-6">
      <svg viewBox="0 0 42 42" style={{ height, width: height }} role="img" aria-label="Donut chart">
        <circle cx="21" cy="21" r={radius} fill="none" stroke="var(--wd-raised)" strokeWidth="5" />
        {total > 0 &&
          points.map((point, i) => {
            const share = (Math.max(0, Number(point.value) || 0) / total) * 100
            const slice = (
              <circle
                key={i}
                cx="21"
                cy="21"
                r={radius}
                fill="none"
                stroke={SLICES[i % SLICES.length]}
                strokeWidth="5"
                strokeDasharray={`${share} ${100 - share}`}
                strokeDashoffset={offset}
              />
            )
            offset -= share
            return slice
          })}
        <text
          x="21"
          y="21"
          textAnchor="middle"
          dominantBaseline="central"
          className="wd-num"
          style={{ fontSize: '6px', fontWeight: 800, fill: 'var(--wd-ink)' }}
        >
          {short(total)}
        </text>
      </svg>

      <ul className="min-w-40 flex-1 space-y-2">
        {points.map((point, i) => (
          <li key={i} className="flex items-center gap-2.5 text-[12.5px]">
            <span
              className="h-2.5 w-2.5 shrink-0 rounded-full"
              style={{ background: SLICES[i % SLICES.length] }}
            />
            <span className="flex-1 truncate text-dim">{point.label}</span>
            <span className="wd-num font-semibold text-ink">{short(Number(point.value) || 0)}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}
