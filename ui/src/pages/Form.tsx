import { useState } from 'react'
import { Link, router } from '@inertiajs/react'
import type { FormPage, Json } from '../types'
import { Shell } from '../components/Shell'
import { FormRenderer } from '../components/FormRenderer'
import { Button, Dialog, Error } from '../components/ui'

export default function Form({ page }: { page: FormPage }) {
  const [values, setValues] = useState<Record<string, Json>>(page.values)
  const [saving, setSaving] = useState(false)
  const [confirming, setConfirming] = useState(false)

  const target = page.mode === 'add' ? page.resource.href : `${page.resource.href}/${page.id}`
  const whole = page.errors.__all__

  const submit = (event: React.FormEvent) => {
    event.preventDefault()
    setSaving(true)
    router.post(target, values as Record<string, never>, {
      onFinish: () => setSaving(false),
      preserveScroll: true,
    })
  }

  return (
    <Shell title={page.mode === 'add' ? `New ${page.resource.label}` : `Edit ${page.label}`}>
      <form onSubmit={submit} className="mx-auto w-full" style={{ maxWidth: WIDTHS[page.width] }}>
        <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
          <div className="min-w-0">
            <nav className="mb-1.5 flex items-center gap-1.5 text-[12px] font-medium text-faint">
              <Link href={page.resource.href} className="transition-colors hover:text-accent">
                {page.resource.plural}
              </Link>
              <span aria-hidden="true">/</span>
              <span className="text-dim">{page.mode === 'add' ? 'New' : 'Edit'}</span>
            </nav>
            <h2 className="wd-title truncate">
              {page.mode === 'add' ? `New ${page.resource.label.toLowerCase()}` : page.label}
            </h2>
            {page.description && <p className="mt-1.5 text-[13px] text-dim">{page.description}</p>}
          </div>
          <div className="flex items-center gap-2.5">
            {page.can.delete && (
              <Button style="ghost" icon="trash" onClick={() => setConfirming(true)}>
                Delete
              </Button>
            )}
            {page.cancel && (
              <Link href={page.resource.href}>
                <Button>Cancel</Button>
              </Link>
            )}
            <Button type="submit" style="primary" disabled={saving} icon={saving ? undefined : 'check'}>
              {saving ? 'Saving…' : page.submit}
            </Button>
          </div>
        </header>

        {whole && (
          <div className="mb-5 rounded-[var(--radius-wd)] bg-red-500/10 px-5 py-4 ring-1 ring-inset ring-red-500/25">
            <Error>{whole}</Error>
          </div>
        )}

        <FormRenderer
          page={page}
          values={values}
          errors={page.errors}
          onChange={(name, value) => setValues((current) => ({ ...current, [name]: value }))}
        />
      </form>

      {confirming && (
        <Dialog
          title={`Delete ${page.label}?`}
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

const WIDTHS: Record<string, string> = {
  narrow: '34rem',
  normal: '48rem',
  wide: '64rem',
  full: '100%',
}
