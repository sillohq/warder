import { Link } from '@inertiajs/react'
import type { ColumnSpec, ListPage, RowSpec } from '../types'
import { cn } from '../lib/cn'
import { Cell } from '../lib/format'
import { go, nextSort, sortDirection } from '../lib/url'
import { Icon } from './Icon'
import { Empty } from './ui'

/**
 * The table.
 *
 * Generic over the column spec and nothing else — it has never heard of a Post.
 * Sorting, selection and paging all travel through the URL, so the back button
 * works and a filtered view is a link you can send someone.
 */
export function DataTable({
  page,
  selected,
  onSelect,
  rowMenu,
}: {
  page: ListPage
  selected: string[]
  onSelect: (ids: string[]) => void
  rowMenu?: (row: RowSpec) => React.ReactNode
}) {
  const { columns, rows, query } = page
  const ids = rows.map((row) => String(row.id))
  const allChosen = ids.length > 0 && ids.every((id) => selected.includes(id))

  if (!rows.length) {
    return (
      <div className="rounded-[var(--radius-wd)] bg-surface ring-1 ring-line">
        <Empty title={page.empty.title} description={page.empty.description} />
      </div>
    )
  }

  return (
    <div className="wd-scroll-x rounded-[var(--radius-wd)] bg-surface ring-1 ring-line">
      <table className="w-full border-collapse text-[13px]">
        <thead className={cn('bg-surface', page.stickyHeader && 'sticky top-11 z-10')}>
          <tr className="border-b border-line">
            {page.selectable && (
              <th scope="col" className="w-9 px-3">
                <input
                  type="checkbox"
                  checked={allChosen}
                  aria-label="Select all on this page"
                  onChange={() => onSelect(allChosen ? [] : ids)}
                  className="h-3.5 w-3.5 accent-[var(--wd-accent)]"
                />
              </th>
            )}
            {columns.map((column) => (
              <Header key={column.key} column={column} sort={query.sort} />
            ))}
            {rowMenu && <th scope="col" className="w-9" />}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const chosen = selected.includes(String(row.id))
            return (
              <tr
                key={String(row.id)}
                className={cn('wd-row border-b border-line last:border-0', chosen ? 'bg-accent/[0.06]' : 'hover:bg-raised/60')}
              >
                {page.selectable && (
                  <td className="px-3">
                    <input
                      type="checkbox"
                      checked={chosen}
                      aria-label={`Select ${row.label}`}
                      onChange={() =>
                        onSelect(
                          chosen
                            ? selected.filter((id) => id !== String(row.id))
                            : [...selected, String(row.id)],
                        )
                      }
                      className="h-3.5 w-3.5 accent-[var(--wd-accent)]"
                    />
                  </td>
                )}
                {columns.map((column) => (
                  <td
                    key={column.key}
                    className={cn(
                      'px-3',
                      column.align === 'right' && 'text-right',
                      column.align === 'center' && 'text-center',
                      column.wrap ? 'py-2 align-top' : 'truncate whitespace-nowrap',
                      column.sticky && 'sticky left-0 bg-surface',
                    )}
                    style={column.width ? { width: column.width, maxWidth: column.width } : undefined}
                  >
                    {column.link ? (
                      <Link href={row.href} className="font-medium text-ink underline-offset-2 hover:underline">
                        <Cell column={column} value={row.cells[column.key]} />
                      </Link>
                    ) : (
                      <Cell column={column} value={row.cells[column.key]} />
                    )}
                  </td>
                ))}
                {rowMenu && <td className="px-1 text-right">{rowMenu(row)}</td>}
              </tr>
            )
          })}
        </tbody>
        {Object.keys(page.totals).length > 0 && (
          <tfoot>
            <tr className="border-t border-line bg-raised/50">
              {page.selectable && <td />}
              {columns.map((column) => (
                <td key={column.key} className={cn('px-3 py-1.5 text-[11.5px] font-medium text-dim', column.align === 'right' && 'text-right')}>
                  {page.totals[column.key] ? page.totals[column.key].toUpperCase() : ''}
                </td>
              ))}
              {rowMenu && <td />}
            </tr>
          </tfoot>
        )}
      </table>
    </div>
  )
}

function Header({ column, sort }: { column: ColumnSpec; sort: string[] }) {
  const direction = sortDirection(sort, column.sort)
  const base = 'px-3 text-left text-[11px] font-semibold uppercase tracking-wide text-dim'

  if (!column.sortable || !column.sort) {
    return (
      <th scope="col" className={cn(base, column.align === 'right' && 'text-right', column.align === 'center' && 'text-center')} title={column.help ?? undefined}>
        {column.label}
      </th>
    )
  }

  return (
    <th scope="col" className={cn(base, column.align === 'right' && 'text-right')} aria-sort={direction === 'asc' ? 'ascending' : direction === 'desc' ? 'descending' : 'none'}>
      <button
        type="button"
        onClick={() => go({ sort: nextSort(sort, column.sort!) })}
        className={cn('inline-flex h-8 items-center gap-1 hover:text-ink', column.align === 'right' && 'flex-row-reverse')}
        title={column.help ?? `Sort by ${column.label}`}
      >
        {column.label}
        <Icon name={direction === 'desc' ? 'chevronDown' : 'chevronUp'} className={cn('h-3 w-3', direction ? 'text-ink' : 'opacity-0')} />
      </button>
    </th>
  )
}

export function Pagination({ page }: { page: ListPage }) {
  const { query, total, pages } = page
  const from = total === 0 ? 0 : query.page * query.perPage - query.perPage + 1
  const to = Math.min(total, query.page * query.perPage)

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 pt-3 text-[12px] text-dim">
      <p className="wd-num">
        {from.toLocaleString()}–{to.toLocaleString()} of {total.toLocaleString()}
      </p>
      <div className="flex items-center gap-2">
        <label className="flex items-center gap-1.5">
          <span className="sr-only">Rows per page</span>
          <select
            value={query.perPage}
            onChange={(event) => go({ per_page: event.target.value })}
            className="h-7 rounded-[var(--radius-wd)] bg-surface px-1.5 text-[12px] ring-1 ring-inset ring-line"
          >
            {page.perPageOptions.map((n) => (
              <option key={n} value={n}>
                {n} / page
              </option>
            ))}
          </select>
        </label>
        <div className="flex items-center gap-1">
          <button
            type="button"
            disabled={query.page <= 1}
            onClick={() => go({ page: query.page - 1 })}
            className="grid h-7 w-7 place-items-center rounded-[var(--radius-wd)] ring-1 ring-line disabled:opacity-40"
            aria-label="Previous page"
          >
            <Icon name="chevronLeft" className="h-3.5 w-3.5" />
          </button>
          <span className="wd-num px-1">
            {query.page} / {pages}
          </span>
          <button
            type="button"
            disabled={query.page >= pages}
            onClick={() => go({ page: query.page + 1 })}
            className="grid h-7 w-7 place-items-center rounded-[var(--radius-wd)] ring-1 ring-line disabled:opacity-40"
            aria-label="Next page"
          >
            <Icon name="chevronRight" className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    </div>
  )
}
