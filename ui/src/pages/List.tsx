import { useEffect, useState } from 'react'
import { Link } from '@inertiajs/react'
import type { ListPage } from '../types'
import { Shell } from '../components/Shell'
import { DataTable, Pagination } from '../components/DataTable'
import { FilterBar } from '../components/FilterBar'
import { ActionBar, RowMenu } from '../components/ActionMenu'
import { Button, IconButton, Menu, MenuItem, MenuLabel } from '../components/ui'
import { Icon } from '../components/Icon'

export default function List({ page }: { page: ListPage }) {
  const [selected, setSelected] = useState<string[]>([])
  const [hidden, setHidden] = useState<string[]>([])

  // Which columns you hide is a preference of yours about this screen, so it
  // lives in this browser rather than in the URL or on the account.
  const key = `warder.columns.${page.resource.slug}`
  useEffect(() => {
    try {
      const stored = localStorage.getItem(key)
      if (stored) setHidden(JSON.parse(stored))
    } catch {
      // A private window, or blocked site data. Showing every column is a fine
      // answer to not knowing.
    }
  }, [key])

  const hide = (next: string[]) => {
    setHidden(next)
    try {
      localStorage.setItem(key, JSON.stringify(next))
    } catch {
      // Same again: the table is already right, it just will not be remembered.
    }
  }

  const toggleable = page.columns.filter((column) => column.toggle)
  const filtered = new URLSearchParams(
    Object.entries(page.query.filters).filter(([, v]) => v) as [string, string][],
  ).toString()

  return (
    <Shell title={page.resource.plural}>
      <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          <h2 className="wd-title">{page.resource.plural}</h2>
          <p className="mt-1.5 text-[13px] text-dim">
            {page.description ?? (
              <span className="wd-num">
                {page.total.toLocaleString()} {page.total === 1 ? page.resource.label.toLowerCase() : page.resource.plural.toLowerCase()}
              </span>
            )}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <ActionBar
            actions={page.actions}
            endpoint={page.resource.href}
            selected={selected}
            filters={page.query.filters}
          />

          {toggleable.length > 1 && (
            <Menu
              trigger={<IconButton icon="columns" label="Columns" className="ring-1 ring-line" />}
              width="min-w-56"
            >
              {() => (
                <>
                  <MenuLabel>Columns</MenuLabel>
                  {toggleable.map((column) => {
                    const shown = !hidden.includes(column.key)
                    return (
                      <MenuItem
                        key={column.key}
                        icon={shown ? 'check' : null}
                        onClick={() =>
                          hide(shown ? [...hidden, column.key] : hidden.filter((k) => k !== column.key))
                        }
                      >
                        {column.label}
                      </MenuItem>
                    )
                  })}
                  {hidden.length > 0 && (
                    <>
                      <div className="my-1.5 border-t border-line" />
                      <MenuItem icon="refresh" onClick={() => hide([])}>
                        Show all
                      </MenuItem>
                    </>
                  )}
                </>
              )}
            </Menu>
          )}

          {page.export && (
            <Menu trigger={<IconButton icon="download" label="Export" className="ring-1 ring-line" />}>
              {() => (
                <>
                  <MenuLabel>Export what you are looking at</MenuLabel>
                  <a href={`${page.resource.href}/export?format=csv&${filtered}`} download>
                    <MenuItem icon="file-text">CSV</MenuItem>
                  </a>
                  <a href={`${page.resource.href}/export?format=json&${filtered}`} download>
                    <MenuItem icon="code">JSON</MenuItem>
                  </a>
                </>
              )}
            </Menu>
          )}

          {page.can.add && (
            <Link href={`${page.resource.href}/new`}>
              <Button style="primary" icon="plus">
                New {page.resource.label.toLowerCase()}
              </Button>
            </Link>
          )}
        </div>
      </header>

      {page.filters.length > 0 && <FilterBar page={page} />}

      {selected.length > 0 && (
        <div className="wd-in mb-4 flex flex-wrap items-center gap-4 rounded-[var(--radius-wd)] bg-accent/[0.08] px-5 py-3.5 ring-1 ring-inset ring-accent/20">
          <span className="wd-num text-[13.5px] font-semibold text-ink">
            {selected.length} selected
          </span>
          <span className="text-[13px] text-dim">Pick an action above, or</span>
          <button
            type="button"
            onClick={() => setSelected([])}
            className="text-[13px] font-semibold text-accent underline-offset-4 hover:underline"
          >
            clear the selection
          </button>
        </div>
      )}

      <DataTable
        page={page}
        selected={selected}
        onSelect={setSelected}
        hidden={hidden}
        rowMenu={
          page.rowActions.length || page.can.change || page.can.delete
            ? (row) => (
                <RowMenu
                  actions={page.rowActions}
                  endpoint={page.resource.href}
                  id={String(row.id)}
                  can={page.can}
                />
              )
            : undefined
        }
      />

      <Pagination page={page} />

      {hidden.length > 0 && (
        <p className="mt-3 flex items-center gap-1.5 text-[12px] text-faint">
          <Icon name="eye" className="h-3.5 w-3.5" />
          {hidden.length} column{hidden.length === 1 ? '' : 's'} hidden
        </p>
      )}
    </Shell>
  )
}
