import { useState } from 'react'
import type { FormPage, Json, SectionSpec } from '../types'
import { cn } from '../lib/cn'
import { holds } from '../lib/condition'
import { Icon } from './Icon'
import { FieldInput } from './Widgets'

/**
 * Sections, fields, widgets — and the conditions that decide which of them are
 * on the form right now.
 *
 * `show=` is evaluated here against the current values, so a field appears the
 * instant its condition becomes true rather than after a round trip. The server
 * evaluates the same condition before it writes, so a hidden field is not
 * merely hidden.
 */
export function FormRenderer({
  page,
  values,
  errors,
  onChange,
}: {
  page: FormPage
  values: Record<string, Json>
  errors: Record<string, string | string[]>
  onChange: (name: string, value: Json) => void
}) {
  const endpoint = page.resource.href
  const render = (section: SectionSpec) => (
    <Section key={section.key} section={section} values={values} errors={errors} onChange={onChange} endpoint={endpoint} />
  )

  if (page.layout === 'split' && page.sidebar.length) {
    return (
      <div className="grid gap-4 lg:grid-cols-[1fr_20rem]">
        <div className="space-y-4">{page.sections.map(render)}</div>
        <div className="space-y-4">{page.sidebar.map(render)}</div>
      </div>
    )
  }
  return <div className="space-y-4">{[...page.sections, ...page.sidebar].map(render)}</div>
}

function Section({
  section,
  values,
  errors,
  onChange,
  endpoint,
}: {
  section: SectionSpec
  values: Record<string, Json>
  errors: Record<string, string | string[]>
  onChange: (name: string, value: Json) => void
  endpoint: string
}) {
  const [open, setOpen] = useState(!section.collapsed)
  if (!holds(section.show, values)) return null

  const fields = section.fields.filter((field) => !field.hidden && holds(field.show, values))
  if (!fields.length) return null

  // A section holding a field that failed validation is opened whatever its
  // declaration says: an error you cannot see is an error you cannot fix.
  const broken = fields.some((field) => errors[field.name])
  const expanded = open || broken

  return (
    <section className="rounded-[var(--radius-wd)] bg-surface ring-1 ring-line">
      {section.title && (
        <header className="flex items-center justify-between border-b border-line px-3.5 py-2.5">
          <div className="min-w-0">
            <h2 className="flex items-center gap-1.5 text-[12px] font-semibold uppercase tracking-wide text-ink">
              <Icon name={section.icon} className="h-3.5 w-3.5 text-dim" />
              {section.title}
            </h2>
            {section.description && <p className="mt-0.5 text-[11.5px] text-dim">{section.description}</p>}
          </div>
          {section.collapsed && (
            <button type="button" onClick={() => setOpen((v) => !v)} aria-expanded={expanded} className="grid h-6 w-6 place-items-center rounded text-dim hover:bg-raised">
              <Icon name={expanded ? 'chevronUp' : 'chevronDown'} className="h-3.5 w-3.5" />
            </button>
          )}
        </header>
      )}

      {expanded && (
        <div className={cn('grid gap-3.5 p-3.5', section.columns === 2 && 'sm:grid-cols-2', section.columns >= 3 && 'sm:grid-cols-3')}>
          {fields.map((field) => (
            <FieldInput
              key={field.name}
              field={field}
              value={values[field.name] ?? null}
              error={errors[field.name] ?? null}
              onChange={(next) => onChange(field.name, next)}
              endpoint={endpoint}
            />
          ))}
        </div>
      )}
    </section>
  )
}
