import { useEffect, useRef, useState } from 'react'
import type { FieldSpec, Json } from '../types'
import { cn } from '../lib/cn'
import { Error, Hint, Input, Label, Select, Switch, Textarea } from './ui'
import { Icon } from './Icon'

/**
 * One control per widget kind.
 *
 * The kind arrives in the props; the renderer never asks what the model column
 * is. Adding `Widget.rating()` in Python is a new case here and nothing else —
 * no template, no route, no per-resource wiring.
 */
export function FieldInput({
  field,
  value,
  error,
  onChange,
  endpoint,
}: {
  field: FieldSpec
  value: Json
  error: string | string[] | null
  onChange: (value: Json) => void
  endpoint?: string
}) {
  const id = `wd-${field.name}`
  const invalid = Boolean(error)
  const message = Array.isArray(error) ? error.join(' ') : error

  return (
    <div className={cn(field.span > 1 && `sm:col-span-${field.span}`)}>
      {field.widget.kind !== 'switch' && (
        <Label htmlFor={id} required={field.required}>
          {field.label}
        </Label>
      )}
      <Control id={id} field={field} value={value} invalid={invalid} onChange={onChange} endpoint={endpoint} />
      {field.help && !message && <Hint>{field.help}</Hint>}
      {message && <Error>{message}</Error>}
    </div>
  )
}

function Control({
  id,
  field,
  value,
  invalid,
  onChange,
  endpoint,
}: {
  id: string
  field: FieldSpec
  value: Json
  invalid: boolean
  onChange: (value: Json) => void
  endpoint?: string
}) {
  const { kind, options } = field.widget
  const opt = <T,>(name: string, fallback: T): T => (options[name] as T) ?? fallback
  const disabled = !field.editable
  const text = value === null || value === undefined ? '' : String(value)

  switch (kind) {
    case 'hidden':
      return <input type="hidden" id={id} value={text} readOnly />

    case 'switch':
      return (
        <label className="flex items-center gap-2 text-[13px]">
          <Switch checked={Boolean(value)} disabled={disabled} onChange={onChange} />
          <span>{field.label}</span>
        </label>
      )

    case 'checkbox':
      if (!opt<[string, string][]>('choices', []).length) {
        return (
          <label className="flex items-center gap-2 text-[13px]">
            <input type="checkbox" id={id} checked={Boolean(value)} disabled={disabled} onChange={(e) => onChange(e.target.checked)} className="h-3.5 w-3.5 accent-[var(--wd-accent)]" />
            <span className="text-dim">{field.help ?? field.label}</span>
          </label>
        )
      }
      return (
        <div className="flex flex-wrap gap-3">
          {opt<[Json, string][]>('choices', []).map(([option, label]) => {
            const chosen = Array.isArray(value) && value.includes(option)
            return (
              <label key={String(option)} className="flex items-center gap-1.5 text-[13px]">
                <input
                  type="checkbox"
                  checked={chosen}
                  disabled={disabled}
                  onChange={() => {
                    const current = Array.isArray(value) ? value : []
                    onChange(chosen ? current.filter((v) => v !== option) : [...current, option])
                  }}
                  className="h-3.5 w-3.5 accent-[var(--wd-accent)]"
                />
                {label}
              </label>
            )
          })}
        </div>
      )

    case 'radio':
      return (
        <div className={cn('flex gap-3', opt('inline', false) ? 'flex-row flex-wrap' : 'flex-col')}>
          {opt<[Json, string][]>('choices', []).map(([option, label]) => (
            <label key={String(option)} className="flex items-center gap-1.5 text-[13px]">
              <input
                type="radio"
                name={field.name}
                checked={value === option}
                disabled={disabled}
                onChange={() => onChange(option)}
                className="h-3.5 w-3.5 accent-[var(--wd-accent)]"
              />
              {label}
            </label>
          ))}
        </div>
      )

    case 'select':
      return (
        <Select id={id} value={text} disabled={disabled} invalid={invalid} onChange={(e) => onChange(e.target.value || null)}>
          <option value="">{opt('clearable', true) ? '—' : `Choose a ${field.label.toLowerCase()}`}</option>
          {opt<[Json, string][]>('choices', []).map(([option, label]) => (
            <option key={String(option)} value={String(option)}>
              {label}
            </option>
          ))}
        </Select>
      )

    case 'textarea':
      return <Textarea id={id} rows={opt('rows', 4)} value={text} disabled={disabled} invalid={invalid} placeholder={field.placeholder ?? undefined} onChange={(e) => onChange(e.target.value)} />

    case 'markdown':
    case 'rich':
      return <Markdown id={id} value={text} height={opt('height', 320)} disabled={disabled} invalid={invalid} onChange={onChange} />

    case 'code':
    case 'json':
      return (
        <Textarea
          id={id}
          rows={Math.round(opt('height', 240) / 22)}
          value={kind === 'json' && value && typeof value === 'object' ? JSON.stringify(value, null, 2) : text}
          disabled={disabled}
          invalid={invalid}
          spellCheck={false}
          className="font-mono text-[12px]"
          onChange={(e) => {
            if (kind !== 'json') return onChange(e.target.value)
            try {
              onChange(JSON.parse(e.target.value))
            } catch {
              onChange(e.target.value)
            }
          }}
        />
      )

    case 'keyvalue':
      return <KeyValue value={value} disabled={disabled} onChange={onChange} keyLabel={opt('key_label', 'Key')} valueLabel={opt('value_label', 'Value')} />

    case 'password':
      return <Input id={id} type="password" autoComplete="new-password" value={text} disabled={disabled} invalid={invalid} placeholder={field.placeholder ?? 'Leave empty to keep the current password'} onChange={(e) => onChange(e.target.value)} />

    case 'number':
    case 'money':
    case 'range':
      return (
        <div className="flex items-center gap-2">
          <Input
            id={id}
            type={kind === 'range' ? 'range' : 'number'}
            className="wd-num"
            min={opt<number | undefined>('min', undefined)}
            max={opt<number | undefined>('max', undefined)}
            step={opt('step', 1)}
            value={text}
            disabled={disabled}
            invalid={invalid}
            onChange={(e) => onChange(e.target.value === '' ? null : Number(e.target.value))}
          />
          {(field.unit || kind === 'money') && <span className="shrink-0 text-[12px] text-dim">{field.unit ?? opt('currency', 'USD')}</span>}
        </div>
      )

    case 'date':
    case 'datetime':
    case 'time':
      return (
        <Input
          id={id}
          type={kind === 'datetime' ? 'datetime-local' : kind}
          className="wd-num"
          value={kind === 'datetime' ? text.slice(0, 16) : text.slice(0, kind === 'time' ? 8 : 10)}
          disabled={disabled}
          invalid={invalid}
          onChange={(e) => onChange(e.target.value || null)}
        />
      )

    case 'color':
      return (
        <div className="flex items-center gap-2">
          <input type="color" value={text || '#000000'} disabled={disabled} onChange={(e) => onChange(e.target.value)} className="h-8 w-10 cursor-pointer rounded ring-1 ring-line" />
          <Input value={text} disabled={disabled} invalid={invalid} onChange={(e) => onChange(e.target.value)} className="font-mono" />
        </div>
      )

    case 'tags':
      return <Tags value={value} disabled={disabled} onChange={onChange} />

    case 'file':
    case 'image':
      return <input id={id} type="file" accept={(opt<string[]>('accept', []) ?? []).join(',')} disabled={disabled} onChange={(e) => onChange(e.target.files?.[0] ? e.target.files[0].name : null)} className="text-[12.5px] text-dim file:mr-2 file:rounded file:border-0 file:bg-raised file:px-2 file:py-1 file:text-[12px] file:text-ink" />

    case 'relation':
      return <Relation id={id} field={field} value={value} disabled={disabled} invalid={invalid} onChange={onChange} endpoint={endpoint} />

    default:
      return (
        <div className="flex items-center">
          {opt('prefix', '') && <span className="shrink-0 rounded-l-[var(--radius-wd)] bg-raised px-2 py-[7px] text-[12px] text-dim ring-1 ring-inset ring-line">{opt('prefix', '')}</span>}
          <Input
            id={id}
            type={kind === 'email' ? 'email' : kind === 'url' ? 'url' : kind === 'phone' ? 'tel' : 'text'}
            value={text}
            disabled={disabled}
            invalid={invalid}
            placeholder={field.placeholder ?? undefined}
            autoFocus={field.autofocus}
            className={cn(opt('mono', false) && 'font-mono', opt('prefix', '') && 'rounded-l-none')}
            onChange={(e) => onChange(e.target.value)}
          />
          {field.unit && <span className="shrink-0 pl-2 text-[12px] text-dim">{field.unit}</span>}
        </div>
      )
  }
}

// ------------------------------------------------------------------ pieces

function Markdown({ id, value, height, disabled, invalid, onChange }: { id: string; value: string; height: number; disabled: boolean; invalid: boolean; onChange: (v: Json) => void }) {
  const [preview, setPreview] = useState(false)
  return (
    <div className="rounded-[var(--radius-wd)] ring-1 ring-inset ring-line">
      <div className="flex items-center justify-end gap-1 border-b border-line px-2 py-1">
        <button type="button" onClick={() => setPreview(false)} className={cn('rounded px-2 py-0.5 text-[11.5px]', !preview ? 'bg-raised text-ink' : 'text-dim')}>
          Write
        </button>
        <button type="button" onClick={() => setPreview(true)} className={cn('rounded px-2 py-0.5 text-[11.5px]', preview ? 'bg-raised text-ink' : 'text-dim')}>
          Preview
        </button>
      </div>
      {preview ? (
        <div className="overflow-auto whitespace-pre-wrap p-2.5 text-[13px] leading-relaxed" style={{ height }}>
          {value || <span className="text-dim">Nothing to preview.</span>}
        </div>
      ) : (
        <textarea
          id={id}
          value={value}
          disabled={disabled}
          aria-invalid={invalid || undefined}
          onChange={(e) => onChange(e.target.value)}
          style={{ height }}
          className="w-full resize-y bg-transparent p-2.5 font-mono text-[12.5px] leading-relaxed outline-none"
        />
      )}
    </div>
  )
}

function Tags({ value, disabled, onChange }: { value: Json; disabled: boolean; onChange: (v: Json) => void }) {
  const items = Array.isArray(value) ? (value as Json[]) : []
  const [draft, setDraft] = useState('')
  return (
    <div className="flex flex-wrap items-center gap-1.5 rounded-[var(--radius-wd)] bg-surface p-1.5 ring-1 ring-inset ring-line">
      {items.map((item, i) => (
        <span key={i} className="inline-flex items-center gap-1 rounded bg-raised px-1.5 py-0.5 text-[11.5px]">
          {String(item)}
          {!disabled && (
            <button type="button" aria-label={`Remove ${item}`} onClick={() => onChange(items.filter((_, j) => j !== i))} className="text-dim hover:text-ink">
              <Icon name="x" className="h-3 w-3" />
            </button>
          )}
        </span>
      ))}
      <input
        value={draft}
        disabled={disabled}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && draft.trim()) {
            e.preventDefault()
            onChange([...items, draft.trim()])
            setDraft('')
          }
          if (e.key === 'Backspace' && !draft && items.length) onChange(items.slice(0, -1))
        }}
        placeholder={items.length ? '' : 'Type and press Enter'}
        className="min-w-24 flex-1 bg-transparent px-1 text-[13px] outline-none placeholder:text-dim"
      />
    </div>
  )
}

function KeyValue({ value, disabled, onChange, keyLabel, valueLabel }: { value: Json; disabled: boolean; onChange: (v: Json) => void; keyLabel: string; valueLabel: string }) {
  const record = (value && typeof value === 'object' && !Array.isArray(value) ? value : {}) as Record<string, Json>
  const entries = Object.entries(record)
  const set = (next: [string, Json][]) => onChange(Object.fromEntries(next))
  return (
    <div className="space-y-1.5">
      {entries.map(([key, item], i) => (
        <div key={i} className="flex gap-1.5">
          <Input value={key} disabled={disabled} aria-label={keyLabel} onChange={(e) => set(entries.map(([k, v], j) => (j === i ? [e.target.value, v] : [k, v])))} className="w-1/3 font-mono" />
          <Input value={String(item ?? '')} disabled={disabled} aria-label={valueLabel} onChange={(e) => set(entries.map(([k, v], j) => (j === i ? [k, e.target.value] : [k, v])))} />
          {!disabled && (
            <button type="button" aria-label="Remove" onClick={() => set(entries.filter((_, j) => j !== i))} className="grid h-8 w-8 shrink-0 place-items-center rounded text-dim hover:bg-raised">
              <Icon name="x" className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      ))}
      {!disabled && (
        <button type="button" onClick={() => set([...entries, ['', '']])} className="inline-flex items-center gap-1 text-[12px] text-dim hover:text-ink">
          <Icon name="plus" className="h-3 w-3" /> Add
        </button>
      )}
    </div>
  )
}

/**
 * A relation picker that searches over the wire.
 *
 * Not a `<select>` of every row: the difference between a foreign key to
 * `Country` and one to `Customer` is four hundred thousand options.
 */
function Relation({ id, field, value, disabled, invalid, onChange, endpoint }: { id: string; field: FieldSpec; value: Json; disabled: boolean; invalid: boolean; onChange: (v: Json) => void; endpoint?: string }) {
  const [term, setTerm] = useState('')
  const [options, setOptions] = useState<{ id: Json; label: string }[]>([])
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const box = useRef<HTMLDivElement>(null)

  const chosen = options.find((o) => String(o.id) === String(value))
  const shown = chosen?.label ?? (value !== null && value !== undefined && value !== '' ? String(value) : '')

  useEffect(() => {
    if (!endpoint || !open) return
    setLoading(true)
    const controller = new AbortController()
    const timer = setTimeout(() => {
      fetch(`${endpoint}/options/${field.name}?q=${encodeURIComponent(term)}`, { signal: controller.signal, headers: { Accept: 'application/json' } })
        .then((response) => (response.ok ? response.json() : { options: [] }))
        .then((body) => setOptions(body.options ?? []))
        .catch(() => undefined)
        .finally(() => setLoading(false))
    }, 180)
    return () => {
      clearTimeout(timer)
      controller.abort()
    }
  }, [term, open, endpoint, field.name])

  useEffect(() => {
    const away = (event: MouseEvent) => {
      if (box.current && !box.current.contains(event.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', away)
    return () => document.removeEventListener('mousedown', away)
  }, [])

  if (!endpoint) {
    return <Input id={id} value={shown} disabled={disabled} invalid={invalid} onChange={(e) => onChange(e.target.value || null)} />
  }

  return (
    <div ref={box} className="relative">
      <button
        type="button"
        id={id}
        disabled={disabled}
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="listbox"
        aria-expanded={open}
        className={cn(
          'flex h-8 w-full items-center justify-between gap-2 rounded-[var(--radius-wd)] bg-surface px-2.5 text-left text-[13px] ring-1 ring-inset',
          invalid ? 'ring-red-500' : 'ring-line',
          disabled && 'bg-raised text-dim',
        )}
      >
        <span className={cn('truncate', !shown && 'text-dim')}>{shown || '—'}</span>
        <span className="flex shrink-0 items-center gap-1">
          {shown && !disabled && (
            <span
              role="button"
              tabIndex={0}
              aria-label="Clear"
              onClick={(event) => {
                event.stopPropagation()
                onChange(null)
              }}
              className="text-dim hover:text-ink"
            >
              <Icon name="x" className="h-3 w-3" />
            </span>
          )}
          <Icon name="chevronDown" className="h-3 w-3 text-dim" />
        </span>
      </button>

      {open && (
        <div className="absolute z-30 mt-1 w-full overflow-hidden rounded-[var(--radius-wd)] bg-surface ring-1 ring-line shadow-[0_8px_24px_-12px_rgb(0_0_0/0.3)]">
          <input
            autoFocus
            value={term}
            onChange={(event) => setTerm(event.target.value)}
            placeholder="Search…"
            className="h-8 w-full border-b border-line bg-transparent px-2.5 text-[13px] outline-none placeholder:text-dim"
          />
          <div role="listbox" className="max-h-56 overflow-y-auto py-1">
            {loading && <p className="px-3 py-2 text-[12px] text-dim">Searching…</p>}
            {!loading && !options.length && <p className="px-3 py-2 text-[12px] text-dim">No matches.</p>}
            {options.map((option) => (
              <button
                key={String(option.id)}
                type="button"
                role="option"
                aria-selected={String(option.id) === String(value)}
                onClick={() => {
                  onChange(option.id)
                  setOpen(false)
                }}
                className={cn('flex w-full items-center px-3 py-1.5 text-left text-[12.5px] hover:bg-raised', String(option.id) === String(value) && 'bg-raised')}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
