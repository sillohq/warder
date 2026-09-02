import { useState } from 'react'
import { Link } from '@inertiajs/react'
import type { ListPage } from '../types'
import { Shell } from '../components/Shell'
import { DataTable, Pagination } from '../components/DataTable'
import { FilterBar } from '../components/FilterBar'
import { ActionBar, RowMenu } from '../components/ActionMenu'
import { Button } from '../components/ui'

export default function List({ page }: { page: ListPage }) {
  const [selected, setSelected] = useState<string[]>([])

  return (
    <Shell title={page.resource.plural}>
      <header className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <h2 className="text-[16px] font-semibold tracking-tight">{page.resource.plural}</h2>
          {page.description && <p className="mt-0.5 text-[12.5px] text-dim">{page.description}</p>}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <ActionBar
            actions={page.actions}
            endpoint={page.resource.href}
            selected={selected}
            filters={page.query.filters}
          />
          {page.can.add && (
            <Link href={`${page.resource.href}/new`}>
              <Button style="primary" icon="plus">
                New {page.resource.label.toLowerCase()}
              </Button>
            </Link>
          )}
        </div>
      </header>

      {page.filters.length > 0 && (
        <div className="mb-3">
          <FilterBar page={page} />
        </div>
      )}

      {selected.length > 0 && (
        <div className="mb-2 flex items-center gap-3 rounded-[var(--radius-wd)] bg-accent/[0.07] px-3 py-2 text-[12.5px]">
          <span className="wd-num font-medium">{selected.length} selected</span>
          <button type="button" onClick={() => setSelected([])} className="text-dim underline-offset-2 hover:underline">
            Clear
          </button>
        </div>
      )}

      <DataTable
        page={page}
        selected={selected}
        onSelect={setSelected}
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
    </Shell>
  )
}
