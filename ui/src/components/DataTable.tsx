import { Link } from '@inertiajs/react'
import type { ColumnSpec, ListPage, RowSpec } from '../types'
import { cn } from '../lib/cn'
import { Cell } from '../lib/format'
import { go, nextSort, sortDirection } from '../lib/url'
import { Icon } from './Icon'
import { Empty, IconButton } from './ui'

/**
 * The table.
 *
 * Generic over the column spec and nothing else — it has never heard of a Post.
 * Sorting, selection and paging all travel through the URL, so the back button
 * works and a filtered view is a link you can send somebody.
 *
 * Row height, cell padding and every other measurement come from the theme, so
 * `density="compact"` is a genuinely tighter table rather than smaller text.
 */
export function DataTable({
  page,
  selected,
  onSelect,
  hidden,
  rowMenu,
}: {
  page: ListPage
  selected: string[]
  onSelect: (ids: string[]) => void
  hidden?: string[]
  rowMenu?: (row: RowSpec) => React.ReactNode
}) {
  const columns = page.columns.filter((column) => !hidden?.includes(column.key))
  const { rows, query } = page
  const ids = rows.map((row) => String(row.id))
  const allChosen = ids.length > 0 && ids.every((id) => selected.includes(id))

  if (!rows.length) {
    return (
      <div className="rounded-[var(--radius-wd)] bg-surface ring-1 ring-line">
        <Empty title={page.empty.title} description={page.empty.description} icon={page.empty.icon ?? 'database'} />
      </div>
    )
  }

  return (
    <div className="wd-scroll-x overflow-hidden rounded-[var(--radius-wd)] bg-surface ring-1 ring-line shadow-[var(--wd-shadow)]">
      <table className="w-full border-collapse text-[var(--text-wd)]">
        <thead className={cn('bg-surface', page.stickyHeader && 'sticky top-[var(--spacing-header)] z-10')}>
          <tr className="border-b border-line">
            {page.selectable && (
              <th scope="col" className="w-12 pl-cell">
                <input
                  type="checkbox"
                  checked={allChosen}
                  aria-label="Select every row on this page"
                  onChange={() => onSelect(allChosen ? [] : ids)}
                  className="h-4 w-4 cursor-pointer accent-[var(--wd-accent)]"
                />
              </th>
            )}
            {columns.map((column) => (
              <Header key={column.key} column={column} sort={query.sort} />
            ))}
            {rowMenu && <th scope="col" className="w-14" />}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const chosen = selected.includes(String(row.id))
            return (
              <tr
                key={String(row.id)}
                className={cn(
                  'wd-row border-b border-line transition-colors last:border-0',
                  chosen ? 'bg-accent/[0.06]' : 'hover:bg-raised/70',
                )}
              >
                {page.selectable && (
                  <td className="pl-cell">
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
                      className="h-4 w-4 cursor-pointer accent-[var(--wd-accent)]"
                    />
                  </td>
                )}
                {columns.map((column) => (
                  <td
                    key={column.key}
                    className={cn(
                      'wd-cell',
                      column.align === 'right' && 'text-right',
                      column.align === 'center' && 'text-center',
                      column.wrap ? 'py-3 align-top leading-relaxed' : 'truncate whitespace-nowrap',
                      column.sticky && 'sticky left-0 bg-surface',
                    )}
                    style={column.width ? { width: column.width, maxWidth: column.width } : undefined}
                  >
                    {column.link ? (
                      <Link
                        href={row.href}
                        className="font-semibold text-ink underline-offset-4 transition-colors hover:text-accent hover:underline"
                      >
                        <Cell column={column} value={row.cells[column.key]} />
                      </Link>
                    ) : (
                      <Cell column={column} value={row.cells[column.key]} />
                    )}
                  </td>
                ))}
                {rowMenu && <td className="pr-2 text-right">{rowMenu(row)}</td>}
              </tr>
            )
          })}
        </tbody>
        {Object.keys(page.totals).length > 0 && (
          <tfoot>
            <tr className="border-t-2 border-edge bg-raised/60">
              {page.selectable && <td />}
              {columns.map((column) => (
                <td
                  key={column.key}
                  className={cn(
                    'wd-cell py-3 text-[11.5px] font-bold uppercase tracking-wide text-faint',
                    column.align === 'right' && 'text-right',
                  )}
                >
                  {page.totals[column.key] ?? ''}
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
  const base = 'wd-cell py-3.5 text-left text-[11px] font-bold uppercase tracking-[0.07em] text-faint'

  if (!column.sortable || !column.sort) {
    return (
      <th
        scope="col"
        className={cn(base, column.align === 'right' && 'text-right', column.align === 'center' && 'text-center')}
        title={column.help ?? undefined}
      >
        {column.label}
      </th>
    )
  }

  return (
    <th
      scope="col"
      className={cn(base, 'p-0', column.align === 'right' && 'text-right')}
      aria-sort={direction === 'asc' ? 'ascending' : direction === 'desc' ? 'descending' : 'none'}
    >
      <button
        type="button"
        onClick={() => go({ sort: nextSort(sort, column.sort!) })}
        className={cn(
          'wd-cell flex w-full items-center gap-1.5 py-3.5 text-[11px] font-bold uppercase tracking-[0.07em] transition-colors hover:text-ink',
          direction ? 'text-ink' : 'text-faint',
          column.align === 'right' && 'flex-row-reverse',
        )}
        title={column.help ?? `Sort by ${column.label}`}
      >
        {column.label}
        <Icon
          name={direction === 'desc' ? 'chevronDown' : 'chevronUp'}
          className={cn('h-3.5 w-3.5', direction ? 'opacity-100' : 'opacity-0')}
        />
      </button>
    </th>
  )
}

export function Pagination({ page }: { page: ListPage }) {
  const { query, total, pages } = page
  const from = total === 0 ? 0 : query.page * query.perPage - query.perPage + 1
  const to = Math.min(total, query.page * query.perPage)

  return (
    <div className="mt-5 flex flex-wrap items-center justify-between gap-4 text-[13px] text-dim">
      <p className="wd-num">
        <span className="font-semibold text-ink">
          {from.toLocaleString()}–{to.toLocaleString()}
        </span>{' '}
        of {total.toLocaleString()}
      </p>
      <div className="flex items-center gap-3">
        <label className="flex items-center gap-2">
          <span className="sr-only">Rows per page</span>
          <select
            value={query.perPage}
            onChange={(event) => go({ per_page: event.target.value })}
            className="h-9 rounded-[var(--radius-wd-sm)] bg-sunken px-2.5 text-[12.5px] ring-1 ring-inset ring-line"
          >
            {page.perPageOptions.map((n) => (
              <option key={n} value={n}>
                {n} per page
              </option>
            ))}
          </select>
        </label>
        <div className="flex items-center gap-1">
          <IconButton
            icon="chevronLeft"
            label="Previous page"
            disabled={query.page <= 1}
            onClick={() => go({ page: query.page - 1 })}
            className="ring-1 ring-line"
          />
          <span className="wd-num px-2 font-medium text-ink">
            {query.page} / {pages}
          </span>
          <IconButton
            icon="chevronRight"
            label="Next page"
            disabled={query.page >= pages}
            onClick={() => go({ page: query.page + 1 })}
            className="ring-1 ring-line"
          />
        </div>
      </div>
    </div>
  )
}
