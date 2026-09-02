import type { Json, Shell as ShellProps } from '../types'
import { Shell } from '../components/Shell'
import { humanise, label, truncate } from '../lib/format'
import { Empty, Panel, Stat } from '../components/ui'

/**
 * A custom `Page`, rendered generically from whatever its handler returned.
 *
 * Not a placeholder and not a props dump. A handler that returns a mapping of
 * numbers gets a row of statistics; one that returns a list of records gets a
 * table; anything else gets a readable definition list. Supplying your own
 * component from your own build replaces this — but until you do, the page is
 * useful rather than apologetic.
 */
export default function CustomPage({
  page,
}: {
  page: ShellProps & { title: string; description: string | null; page: Json }
}) {
  const data = page.page
  const record = data && typeof data === 'object' && !Array.isArray(data) ? (data as Record<string, Json>) : null

  const numbers = record
    ? Object.entries(record).filter(([, v]) => typeof v === 'number')
    : []
  const tables = record
    ? Object.entries(record).filter(([, v]) => Array.isArray(v) && v.length > 0 && typeof v[0] === 'object')
    : []
  const rest = record
    ? Object.entries(record).filter(
        ([k]) => !numbers.some(([n]) => n === k) && !tables.some(([n]) => n === k),
      )
    : []

  const empty = !numbers.length && !tables.length && !rest.length && !Array.isArray(data)

  return (
    <Shell title={page.title}>
      <header className="mb-6">
        <h2 className="wd-title">{page.title}</h2>
        {page.description && <p className="mt-1.5 text-[13px] text-dim">{page.description}</p>}
      </header>

      {empty && <Empty title={page.title} description="This page returned nothing to show." icon="file" />}

      {numbers.length > 0 && (
        <div className="mb-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {numbers.map(([name, value]) => (
            <Stat key={name} label={humanise(name)} value={Number(value).toLocaleString()} />
          ))}
        </div>
      )}

      {tables.map(([name, value]) => (
        <div key={name} className="mb-5">
          <Table title={humanise(name)} rows={value as Record<string, Json>[]} />
        </div>
      ))}

      {Array.isArray(data) && data.length > 0 && typeof data[0] === 'object' && (
        <Table title={page.title} rows={data as Record<string, Json>[]} />
      )}

      {rest.length > 0 && (
        <Panel title="Details" flush>
          <dl className="divide-y divide-line">
            {rest.map(([name, value]) => (
              <div key={name} className="grid gap-1 px-5 py-4 sm:grid-cols-[minmax(9rem,15rem)_1fr] sm:gap-5">
                <dt className="text-[12.5px] font-semibold text-dim">{humanise(name)}</dt>
                <dd className="min-w-0 break-words text-[var(--text-wd)]">{label(value) || <span className="text-faint">—</span>}</dd>
              </div>
            ))}
          </dl>
        </Panel>
      )}
    </Shell>
  )
}

function Table({ title, rows }: { title: string; rows: Record<string, Json>[] }) {
  const keys = Object.keys(rows[0] ?? {}).slice(0, 6)
  return (
    <Panel title={title} description={`${rows.length.toLocaleString()} rows`} flush>
      <div className="wd-scroll-x">
        <table className="w-full border-collapse text-[13.5px]">
          <thead>
            <tr className="border-b border-line">
              {keys.map((key) => (
                <th key={key} className="wd-cell py-2.5 text-left text-[10.5px] font-bold uppercase tracking-[0.07em] text-faint">
                  {humanise(key)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.slice(0, 100).map((row, i) => (
              <tr key={i} className="border-b border-line last:border-0 hover:bg-raised/60">
                {keys.map((key) => (
                  <td key={key} className="wd-cell truncate py-3">
                    {truncate(label(row[key]), 60)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Panel>
  )
}
