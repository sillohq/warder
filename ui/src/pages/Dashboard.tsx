import type { CardSpec, DashboardPage, Json } from '../types'
import { Shell } from '../components/Shell'
import { cn } from '../lib/cn'
import { label, money, truncate } from '../lib/format'
import { Empty, Panel } from '../components/ui'
import { Icon } from '../components/Icon'

export default function Dashboard({ page }: { page: DashboardPage }) {
  if (!page.cards.length) {
    return (
      <Shell title={page.title}>
        <Empty title={page.title} description="No dashboard cards are declared yet." />
      </Shell>
    )
  }
  return (
    <Shell title={page.title}>
      <header className="mb-3">
        <h2 className="text-[16px] font-semibold tracking-tight">{page.title}</h2>
        {page.description && <p className="mt-0.5 text-[12.5px] text-dim">{page.description}</p>}
      </header>
      <div className="grid gap-3" style={{ gridTemplateColumns: `repeat(${page.columns}, minmax(0, 1fr))` }}>
        {page.cards.map((card) => (
          <div key={card.key} style={{ gridColumn: `span ${Math.min(card.span, page.columns)}` }}>
            <Card card={card} />
          </div>
        ))}
      </div>
    </Shell>
  )
}

function Card({ card }: { card: CardSpec }) {
  switch (card.kind) {
    case 'number': {
      const value = typeof card.data === 'object' && card.data ? (card.data as Record<string, Json>).value : card.data
      const delta = typeof card.data === 'object' && card.data ? (card.data as Record<string, Json>).delta : null
      const currency = card.options.currency as string | undefined
      return (
        <section className="rounded-[var(--radius-wd)] bg-surface p-3.5 ring-1 ring-line">
          <p className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-dim">
            <Icon name={card.icon} className="h-3.5 w-3.5" />
            {card.title}
          </p>
          <p className="wd-num mt-1.5 text-[24px] font-semibold leading-none tracking-tight">
            {currency ? money(Number(value ?? 0), currency, 2) : new Intl.NumberFormat().format(Number(value ?? 0))}
          </p>
          {delta !== null && delta !== undefined && (
            <p className={cn('wd-num mt-1 text-[11.5px]', Number(delta) >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400')}>
              {Number(delta) >= 0 ? '↑' : '↓'} {Math.abs(Number(delta))}%
            </p>
          )}
          {card.description && <p className="mt-1 text-[11.5px] text-dim">{card.description}</p>}
        </section>
      )
    }

    case 'chart': {
      const points = (Array.isArray(card.data) ? card.data : []) as { label: string; value: number }[]
      const peak = Math.max(1, ...points.map((p) => Number(p.value) || 0))
      return (
        <Panel title={card.title}>
          {points.length === 0 ? (
            <p className="py-6 text-center text-[12.5px] text-dim">No data.</p>
          ) : (
            <div className="flex h-32 items-end gap-1">
              {points.map((point, i) => (
                <div key={i} className="group flex flex-1 flex-col items-center justify-end gap-1" title={`${point.label}: ${point.value}`}>
                  <span className="w-full rounded-t bg-accent/70 transition-colors group-hover:bg-accent" style={{ height: `${(Number(point.value) / peak) * 100}%` }} />
                  <span className="w-full truncate text-center text-[10px] text-dim">{point.label}</span>
                </div>
              ))}
            </div>
          )}
        </Panel>
      )
    }

    case 'table':
    case 'list': {
      const rows = (Array.isArray(card.data) ? card.data : []) as Record<string, Json>[]
      const keys = rows.length ? Object.keys(rows[0]).slice(0, 4) : []
      return (
        <Panel
          title={card.title}
          actions={
            card.options.link ? (
              <a href={String(card.options.link)} className="inline-flex items-center gap-1 text-[11.5px] text-dim hover:text-ink">
                View all <Icon name="chevronRight" className="h-3 w-3" />
              </a>
            ) : undefined
          }
        >
          {rows.length === 0 ? (
            <p className="py-4 text-center text-[12.5px] text-dim">Nothing yet.</p>
          ) : (
            <div className="wd-scroll-x">
              <table className="w-full text-[12.5px]">
                <tbody>
                  {rows.map((row, i) => (
                    <tr key={i} className="border-b border-line last:border-0">
                      {keys.map((key) => (
                        <td key={key} className="truncate py-1.5 pr-3">
                          {truncate(label(row[key]), 40)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Panel>
      )
    }

    default:
      return (
        <Panel title={card.title}>
          <p className="text-[12.5px] text-dim">
            This card renders “{String(card.options.component ?? 'a component')}”, which your own build supplies.
          </p>
        </Panel>
      )
  }
}
