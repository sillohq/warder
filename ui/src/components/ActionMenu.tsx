import { useState } from 'react'
import { router } from '@inertiajs/react'
import type { ActionSpec, Json } from '../types'
import { Button, Dialog, Menu, MenuItem } from './ui'
import { Icon } from './Icon'
import { FieldInput } from './Widgets'

/**
 * Running an action: confirm if it says to, collect input if it declares
 * fields, then post ids to the server.
 *
 * Ids and filters go up; the *queryset* stays on the server. That is what lets
 * "publish everything matching this filter" be one statement rather than forty
 * thousand requests.
 */
export function ActionBar({
  actions,
  endpoint,
  selected,
  filters,
}: {
  actions: ActionSpec[]
  endpoint: string
  selected: string[]
  filters: Record<string, string>
}) {
  const [pending, setPending] = useState<ActionSpec | null>(null)
  const primary = actions.filter((a) => a.style === 'primary' || a.style === 'danger').slice(0, 2)
  const overflow = actions.filter((a) => !primary.includes(a))

  const start = (action: ActionSpec) => {
    if (action.confirm || action.fields.length) setPending(action)
    else run(action, {})
  }

  const run = (action: ActionSpec, values: Record<string, Json>) => {
    router.post(
      `${endpoint}/actions/${action.key}`,
      { ids: selected, filters, values },
      { preserveScroll: true, onFinish: () => setPending(null) },
    )
  }

  const usable = (action: ActionSpec) =>
    action.selection === 'none' ||
    (action.selection === 'one' ? selected.length === 1 : selected.length > 0)

  if (!actions.length) return null

  return (
    <>
      {primary.map((action) => (
        <Button key={action.key} style={action.style} icon={action.icon} disabled={!usable(action)} onClick={() => start(action)}>
          {action.label}
        </Button>
      ))}

      {overflow.length > 0 && (
        <Menu
          trigger={
            <Button icon="more" aria-label="More actions">
              Actions
            </Button>
          }
          width="min-w-56"
        >
          {(close) =>
            overflow.map((action) => (
              <MenuItem
                key={action.key}
                icon={action.icon}
                danger={action.style === 'danger'}
                disabled={!usable(action)}
                hint={usable(action) ? undefined : 'select rows'}
                onClick={() => {
                  close()
                  if (usable(action)) start(action)
                }}
              >
                {action.label}
              </MenuItem>
            ))
          }
        </Menu>
      )}

      {pending && (
        <ActionDialog
          action={pending}
          count={selected.length}
          onClose={() => setPending(null)}
          onRun={(values) => run(pending, values)}
        />
      )}
    </>
  )
}

function ActionDialog({
  action,
  count,
  onClose,
  onRun,
}: {
  action: ActionSpec
  count: number
  onClose: () => void
  onRun: (values: Record<string, Json>) => void
}) {
  const [values, setValues] = useState<Record<string, Json>>({})
  const question = (action.confirm ?? `Run “${action.label}” on ${count} selected?`)
    .replace(/\{count\}/g, String(count))
    .replace(/\{n\}/g, String(count))

  return (
    <Dialog
      title={action.label}
      description={question}
      onClose={onClose}
      footer={
        <>
          <Button onClick={onClose}>Cancel</Button>
          <Button style={action.style === 'danger' ? 'danger' : 'primary'} onClick={() => onRun(values)}>
            {action.label}
          </Button>
        </>
      }
    >
      {action.fields.length > 0 && (
        <div className="space-y-5">
          {action.fields.map((field) => (
            <FieldInput
              key={field.name}
              field={field}
              value={values[field.name] ?? null}
              error={null}
              onChange={(next) => setValues((current) => ({ ...current, [field.name]: next }))}
            />
          ))}
        </div>
      )}
    </Dialog>
  )
}

/** The per-row menu: the row actions, plus edit and delete when allowed. */
export function RowMenu({
  actions,
  endpoint,
  id,
  can,
}: {
  actions: ActionSpec[]
  endpoint: string
  id: string
  can: Record<string, boolean>
}) {
  const [confirming, setConfirming] = useState(false)
  if (!actions.length && !can.change && !can.delete) return null

  return (
    <>
      <Menu
        trigger={
          <button
            type="button"
            aria-label="Row actions"
            className="grid h-9 w-9 place-items-center rounded-[var(--radius-wd-sm)] text-faint transition-colors hover:bg-raised hover:text-ink"
          >
            <Icon name="more" className="h-4 w-4" />
          </button>
        }
      >
        {(close) => (
          <>
            {can.change && (
              <MenuItem icon="edit" onClick={() => { close(); router.visit(`${endpoint}/${id}/edit`) }}>
                Edit
              </MenuItem>
            )}
            {actions.map((action) => (
              <MenuItem
                key={action.key}
                icon={action.icon}
                danger={action.style === 'danger'}
                onClick={() => {
                  close()
                  router.post(`${endpoint}/actions/${action.key}`, { ids: [id], values: {} }, { preserveScroll: true })
                }}
              >
                {action.label}
              </MenuItem>
            ))}
            {can.delete && (
              <MenuItem icon="trash" danger onClick={() => { close(); setConfirming(true) }}>
                Delete
              </MenuItem>
            )}
          </>
        )}
      </Menu>

      {confirming && (
        <Dialog
          title="Delete this row?"
          description="This cannot be undone."
          onClose={() => setConfirming(false)}
          footer={
            <>
              <Button onClick={() => setConfirming(false)}>Cancel</Button>
              <Button style="danger" onClick={() => router.delete(`${endpoint}/${id}`, { preserveScroll: true })}>
                Delete
              </Button>
            </>
          }
        />
      )}
    </>
  )
}
