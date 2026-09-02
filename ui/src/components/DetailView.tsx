import type { DetailPage, Json, PanelSpec } from '../types'
import { cn } from '../lib/cn'
import { humanise, label } from '../lib/format'
import { Icon } from './Icon'
import { Panel } from './ui'

/**
 * One row, in panels.
 *
 * Four kinds, and the difference between the middle two is the one worth
 * knowing: an *inline* panel edits child rows and saves with the parent; a
 * *related* panel is a read-only window onto rows that belong to themselves and
 * links out to their own screens.
 */
export function DetailView({ page, slots }: { page: DetailPage; slots: Record<string, string> }) {
  const main = page.panels.filter((p) => p.span !== 'side')
  const side = page.panels.filter((p) => p.span === 'side')

  if (!side.length) {
    return <div className="space-y-4">{main.map((panel) => <PanelBody key={panel.key} panel={panel} slots={slots} />)}</div>
  }
  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_20rem]">
      <div className="space-y-4">{main.map((panel) => <PanelBody key={panel.key} panel={panel} slots={slots} />)}</div>
      <div className="space-y-4">{side.map((panel) => <PanelBody key={panel.key} panel={panel} slots={slots} />)}</div>
    </div>
  )
}

function PanelBody({ panel, slots }: { panel: PanelSpec; slots: Record<string, string> }) {
  switch (panel.kind) {
    case 'fields': {
      const values = (panel.options.values as Record<string, Json>) ?? {}
      const names = (panel.options.names as string[]) ?? Object.keys(values)
      return (
        <Panel title={panel.title}>
          <dl className="divide-y divide-line">
            {names.map((name) => (
              <div key={name} className="grid grid-cols-[minmax(8rem,14rem)_1fr] gap-3 py-2 text-[13px] first:pt-0 last:pb-0">
                <dt className="text-dim">{humanise(name)}</dt>
                <dd className="min-w-0 break-words">{label(values[name] ?? null) || <span className="text-dim">—</span>}</dd>
              </div>
            ))}
          </dl>
        </Panel>
      )
    }

    case 'related':
    case 'inline': {
      const rows = (panel.options.rows as { id: Json; label: string; href?: string }[]) ?? []
      return (
        <Panel
          title={panel.title}
          actions={
            panel.options.href ? (
              <a href={String(panel.options.href)} className="inline-flex items-center gap-1 text-[11.5px] text-dim hover:text-ink">
                View all <Icon name="chevronRight" className="h-3 w-3" />
              </a>
            ) : undefined
          }
        >
          {rows.length === 0 ? (
            <p className="py-2 text-[12.5px] text-dim">Nothing here.</p>
          ) : (
            <ul className="divide-y divide-line">
              {rows.map((row) => (
                <li key={String(row.id)} className="py-2 text-[13px] first:pt-0 last:pb-0">
                  {row.href ? (
                    <a href={row.href} className="hover:underline">
                      {row.label}
                    </a>
                  ) : (
                    row.label
                  )}
                </li>
              ))}
            </ul>
          )}
        </Panel>
      )
    }

    case 'text':
      return (
        <Panel title={panel.title}>
          <div className="whitespace-pre-wrap text-[13px] leading-relaxed">{String(panel.options.body ?? '')}</div>
        </Panel>
      )

    case 'custom':
    default: {
      const mounted = panel.component && slots[panel.component]
      return (
        <Panel title={panel.title}>
          <p className={cn('text-[12.5px]', mounted ? 'text-ink' : 'text-dim')}>
            {mounted
              ? `Slot “${panel.component}” is registered but not bundled in this build.`
              : `This panel renders “${panel.component}”, which your own build supplies.`}
          </p>
        </Panel>
      )
    }
  }
}
