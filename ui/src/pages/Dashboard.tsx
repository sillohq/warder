import { Link } from '@inertiajs/react'
import type { CardSpec, DashboardPage, Json } from '../types'
import { Shell } from '../components/Shell'
import { cn } from '../lib/cn'
import { label, money, truncate } from '../lib/format'
import { Chart, type Point } from '../components/Chart'
import { Empty, Panel, Stat } from '../components/ui'
import { Icon } from '../components/Icon'

export default function Dashboard({ page }: { page: DashboardPage }) {
  return (
    <Shell title={page.title}>
      <header className="mb-6">
        <h2 className="wd-title">{page.title}</h2>
        <p className="mt-1.5 text-[13px] text-dim">
          {page.description ?? 'Everything at a glance.'}
        </p>
      </header>

      {page.cards.length === 0 ? (
        <Empty
          title="No cards yet"
          description="Add Card.number, Card.chart or Card.table to a Dashboard and they appear here."
          icon="chart"
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {page.cards.map((card) => (
            <div
              key={card.key}
              className={cn(
                card.span >= 4 && 'lg:col-span-4',
                card.span === 3 && 'lg:col-span-3',
                card.span === 2 && 'sm:col-span-2',
              )}
            >
              <Card card={card} />
            </div>
          ))}
        </div>
      )}
    </Shell>
  )
}

function Card({ card }: { card: CardSpec }) {
  switch (card.kind) {
    case 'number': {
      const raw = card.data && typeof card.data === 'object' && !Array.isArray(card.data)
        ? (card.data as Record<string, Json>)
        : null
      const value = raw ? raw.value : card.data
      const delta = raw ? raw.delta : null
      const currency = card.options.currency as string | undefined
      const up = Number(delta) >= 0
      return (
        <Stat
          icon={card.icon}
          label={card.title}
          value={
            currency
              ? money(Number(value ?? 0), currency, 2)
              : Number(value ?? 0).toLocaleString()
          }
          sub={
            delta !== null && delta !== undefined ? (
              <span className={cn('wd-num font-semibold', up ? 'text-emerald-500' : 'text-red-500')}>
                {up ? '↑' : '↓'} {Math.abs(Number(delta))}%{' '}
                <span className="font-normal text-faint">{card.description ?? ''}</span>
              </span>
            ) : (
              card.description
            )
          }
        />
      )
    }

    case 'chart': {
      const points = (Array.isArray(card.data) ? card.data : []) as unknown as Point[]
      return (
        <Panel title={card.title} description={card.description}>
          <Chart
            points={points}
            kind={String(card.options.chart ?? 'bar')}
            currency={card.options.currency as string | undefined}
            height={card.span >= 3 ? 240 : 200}
          />
        </Panel>
      )
    }

    case 'table':
    case 'list': {
      const rows = (Array.isArray(card.data) ? card.data : []) as Record<string, Json>[]
      const keys = Object.keys(rows[0] ?? {}).slice(0, 4)
      const href = card.options.link ? String(card.options.link) : null
      return (
        <Panel
          title={card.title}
          description={card.description}
          flush
          actions={
            href ? (
              <Link href={href} className="inline-flex items-center gap-1 text-[12.5px] font-semibold text-accent hover:underline">
                View all <Icon name="chevronRight" className="h-3.5 w-3.5" />
              </Link>
            ) : undefined
          }
        >
          {rows.length === 0 ? (
            <p className="py-10 text-center text-[13px] text-faint">Nothing yet.</p>
          ) : (
            <div className="wd-scroll-x">
              <table className="w-full text-[13.5px]">
                <tbody>
                  {rows.map((row, i) => (
                    <tr key={i} className="border-b border-line last:border-0">
                      {keys.map((key) => (
                        <td key={key} className="wd-cell truncate py-3">
                          {truncate(label(row[key]), 44)}
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

    default: {
      const props = (card.data && typeof card.data === 'object' ? card.data : {}) as Record<string, Json>
      const entries = Object.entries(props)
      return (
        <Panel title={card.title} description={card.description}>
          {entries.length === 0 ? (
            <p className="py-6 text-center text-[13px] text-faint">
              Mount “{String(card.options.component ?? 'this component')}” from your own build.
            </p>
          ) : (
            <dl className="space-y-2.5">
              {entries.map(([name, value]) => (
                <div key={name} className="flex justify-between gap-4 text-[13.5px]">
                  <dt className="text-dim">{name}</dt>
                  <dd className="wd-num font-semibold">{label(value)}</dd>
                </div>
              ))}
            </dl>
          )}
        </Panel>
      )
    }
  }
}
