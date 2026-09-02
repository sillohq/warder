import { Link } from '@inertiajs/react'
import type { ColumnSpec, DetailPage, Json, PanelSpec } from '../types'
import { cn } from '../lib/cn'
import { Cell, humanise, label } from '../lib/format'
import { Icon } from './Icon'
import { Empty, Panel } from './ui'

/**
 * One row, in panels.
 *
 * A related panel is a real table, drawn with the child resource's own columns
 * — so "Comments" on a post formats money and status exactly the way the
 * Comments screen does, and nobody declared it twice.
 */
export function DetailView({ page }: { page: DetailPage }) {
  const main = page.panels.filter((p) => p.span !== 'side')
  const side = page.panels.filter((p) => p.span === 'side')

  if (!side.length) {
    return <div className="space-y-5">{main.map((panel) => <Body key={panel.key} panel={panel} />)}</div>
  }
  return (
    <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_22rem]">
      <div className="space-y-5">{main.map((panel) => <Body key={panel.key} panel={panel} />)}</div>
      <div className="space-y-5">{side.map((panel) => <Body key={panel.key} panel={panel} />)}</div>
    </div>
  )
}

function Body({ panel }: { panel: PanelSpec }) {
  switch (panel.kind) {
    case 'fields':
      return <Fields panel={panel} />
    case 'related':
    case 'inline':
      return <Related panel={panel} />
    case 'text':
      return (
        <Panel title={panel.title}>
          <div className="whitespace-pre-wrap text-[var(--text-wd)] leading-[1.75] text-ink">
            {String(panel.options.body ?? '') || <span className="text-faint">Nothing here.</span>}
          </div>
        </Panel>
      )
    default:
      return <Custom panel={panel} />
  }
}

function Fields({ panel }: { panel: PanelSpec }) {
  const values = (panel.options.values as Record<string, Json>) ?? {}
  const names = (panel.options.names as string[]) ?? Object.keys(values)
  if (!names.length) return null
  return (
    <Panel title={panel.title} flush>
      <dl className="divide-y divide-line">
        {names.map((name) => {
          const value = values[name] ?? null
          const shown = label(value)
          return (
            <div key={name} className="grid gap-1 px-5 py-4 sm:grid-cols-[minmax(9rem,15rem)_1fr] sm:gap-5">
              <dt className="text-[12.5px] font-semibold text-dim">{humanise(name)}</dt>
              <dd className="min-w-0 break-words text-[var(--text-wd)] text-ink">
                {shown || <span className="text-faint">—</span>}
              </dd>
            </div>
          )
        })}
      </dl>
    </Panel>
  )
}

interface RelatedRow {
  id: Json
  label: string
  href?: string
  cells: Record<string, Json>
}

function Related({ panel }: { panel: PanelSpec }) {
  const rows = (panel.options.rows as unknown as RelatedRow[]) ?? []
  const columns = (panel.options.columns as unknown as ColumnSpec[]) ?? []
  const total = Number(panel.options.total ?? rows.length)
  const href = panel.options.href ? String(panel.options.href) : null

  return (
    <Panel
      title={panel.title}
      description={total > rows.length ? `Showing ${rows.length} of ${total.toLocaleString()}` : undefined}
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
        <Empty title="Nothing here yet" icon="database" />
      ) : (
        <div className="wd-scroll-x">
          <table className="w-full border-collapse text-[13.5px]">
            {columns.length > 1 && (
              <thead>
                <tr className="border-b border-line">
                  {columns.map((column) => (
                    <th
                      key={column.key}
                      className={cn(
                        'wd-cell py-2.5 text-left text-[10.5px] font-bold uppercase tracking-[0.07em] text-faint',
                        column.align === 'right' && 'text-right',
                      )}
                    >
                      {column.label}
                    </th>
                  ))}
                  <th className="w-10" />
                </tr>
              </thead>
            )}
            <tbody>
              {rows.map((row) => (
                <tr key={String(row.id)} className="border-b border-line transition-colors last:border-0 hover:bg-raised/60">
                  {columns.map((column, i) => (
                    <td
                      key={column.key}
                      className={cn('wd-cell py-3', column.align === 'right' && 'text-right', 'truncate')}
                    >
                      {i === 0 && row.href ? (
                        <Link href={row.href} className="font-semibold text-ink underline-offset-4 hover:text-accent hover:underline">
                          <Cell column={column} value={row.cells[column.key]} />
                        </Link>
                      ) : (
                        <Cell column={column} value={row.cells[column.key]} />
                      )}
                    </td>
                  ))}
                  <td className="pr-3 text-right">
                    {row.href && (
                      <Link href={row.href} className="text-faint hover:text-accent" aria-label={`Open ${row.label}`}>
                        <Icon name="chevronRight" className="h-4 w-4" />
                      </Link>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Panel>
  )
}

/**
 * A panel whose component your own build supplies.
 *
 * Until it does, the props are rendered as a table rather than as an apology:
 * the data is there, it is readable, and it proves the route, the gate and the
 * loader all worked.
 */
function Custom({ panel }: { panel: PanelSpec }) {
  const props = (panel.options.props as Record<string, Json>) ?? {}
  const entries = Object.entries(props)
  return (
    <Panel title={panel.title} flush>
      {entries.length === 0 ? (
        <Empty title={panel.title} description={`Mount “${panel.component}” from your own build to render this.`} icon="file" />
      ) : (
        <dl className="divide-y divide-line">
          {entries.map(([name, value]) => (
            <div key={name} className="grid gap-1 px-5 py-4 sm:grid-cols-[minmax(9rem,15rem)_1fr] sm:gap-5">
              <dt className="text-[12.5px] font-semibold text-dim">{humanise(name)}</dt>
              <dd className="wd-num min-w-0 break-words text-[var(--text-wd)] text-ink">{label(value)}</dd>
            </div>
          ))}
        </dl>
      )}
    </Panel>
  )
}
