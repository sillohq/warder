import { useState } from 'react'
import { Link, router } from '@inertiajs/react'
import type { DetailPage } from '../types'
import { Shell } from '../components/Shell'
import { DetailView } from '../components/DetailView'
import { Button, Dialog, Menu, MenuItem } from '../components/ui'

export default function Detail({ page }: { page: DetailPage }) {
  const [confirming, setConfirming] = useState(false)

  return (
    <Shell title={page.title}>
      <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          <nav className="mb-1.5 flex items-center gap-1.5 text-[12px] font-medium text-faint">
            <Link href={page.resource.href} className="transition-colors hover:text-accent">
              {page.resource.plural}
            </Link>
            <span aria-hidden="true">/</span>
            <span className="wd-num text-dim">{String(page.id)}</span>
          </nav>
          <h2 className="wd-title truncate">{page.title}</h2>
          {page.subtitle && <p className="mt-1.5 text-[13px] text-dim">{page.subtitle}</p>}
        </div>
        <div className="flex items-center gap-2.5">
          {page.actions.length > 0 && (
            <Menu trigger={<Button icon="more">Actions</Button>}>
              {(close) =>
                page.actions.map((action) => (
                  <MenuItem
                    key={action.key}
                    icon={action.icon}
                    danger={action.style === 'danger'}
                    onClick={() => {
                      close()
                      router.post(`${page.resource.href}/actions/${action.key}`, { ids: [page.id], values: {} })
                    }}
                  >
                    {action.label}
                  </MenuItem>
                ))
              }
            </Menu>
          )}
          {page.can.delete && (
            <Button style="ghost" icon="trash" onClick={() => setConfirming(true)}>
              Delete
            </Button>
          )}
          {page.can.change && (
            <Link href={`${page.resource.href}/${page.id}/edit`}>
              <Button style="primary" icon="edit">
                Edit
              </Button>
            </Link>
          )}
        </div>
      </header>

      <DetailView page={page} />

      {confirming && (
        <Dialog
          title={`Delete ${page.title}?`}
          description="This cannot be undone."
          onClose={() => setConfirming(false)}
          footer={
            <>
              <Button onClick={() => setConfirming(false)}>Cancel</Button>
              <Button style="danger" onClick={() => router.delete(`${page.resource.href}/${page.id}`)}>
                Delete
              </Button>
            </>
          }
        />
      )}
    </Shell>
  )
}
