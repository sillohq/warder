import { useState } from 'react'
import { router } from '@inertiajs/react'
import type { LoginPage } from '../types'
import { Button, Error, Input, Label } from '../components/ui'
import { Icon } from '../components/Icon'

export default function Login({ page }: { page: LoginPage }) {
  const [identity, setIdentity] = useState('')
  const [secret, setSecret] = useState('')
  const [reveal, setReveal] = useState(false)
  const [busy, setBusy] = useState(false)

  const submit = (event: React.FormEvent) => {
    event.preventDefault()
    setBusy(true)
    router.post(
      `${page.site.prefix}/login`,
      { [page.field]: identity, password: secret },
      { onFinish: () => setBusy(false) },
    )
  }

  return (
    <div className="grid min-h-screen place-items-center bg-bg px-5 py-12">
      <form onSubmit={submit} className="w-full max-w-[24rem]">
        <div className="mb-7 flex flex-col items-center gap-3 text-center">
          <span className="grid h-12 w-12 place-items-center rounded-[var(--radius-wd)] bg-accent text-[19px] font-extrabold text-on-accent shadow-sm">
            {page.brand.slice(0, 1)}
          </span>
          <div>
            <h1 className="text-[20px] font-extrabold tracking-tight">{page.brand}</h1>
            <p className="mt-1 text-[13px] text-dim">{page.message ?? 'Sign in to continue.'}</p>
          </div>
        </div>

        <div className="space-y-5 rounded-[var(--radius-wd)] bg-surface p-6 ring-1 ring-line shadow-[0_1px_2px_rgb(0_0_0/0.06)]">
          <div>
            <Label htmlFor="wd-identity" required>
              {page.field === 'email' ? 'Email address' : 'Username'}
            </Label>
            <Input
              id="wd-identity"
              autoFocus
              autoComplete="username"
              type={page.field === 'email' ? 'email' : 'text'}
              value={identity}
              onChange={(event) => setIdentity(event.target.value)}
              invalid={Boolean(page.errors.__all__)}
              placeholder={page.field === 'email' ? 'you@example.com' : 'your username'}
            />
          </div>

          <div>
            <Label htmlFor="wd-secret" required>
              Password
            </Label>
            <div className="relative">
              <Input
                id="wd-secret"
                type={reveal ? 'text' : 'password'}
                autoComplete="current-password"
                value={secret}
                onChange={(event) => setSecret(event.target.value)}
                invalid={Boolean(page.errors.__all__)}
                className="pr-11"
              />
              <button
                type="button"
                onClick={() => setReveal((v) => !v)}
                aria-label={reveal ? 'Hide password' : 'Show password'}
                className="absolute right-2 top-1/2 grid h-8 w-8 -translate-y-1/2 place-items-center rounded text-faint transition-colors hover:text-ink"
              >
                <Icon name="eye" className="h-4 w-4" />
              </button>
            </div>
          </div>

          {page.errors.__all__ && <Error>{page.errors.__all__}</Error>}

          <Button type="submit" style="primary" size="lg" disabled={busy} className="w-full">
            {busy ? 'Signing in…' : 'Sign in'}
          </Button>
        </div>

        <p className="mt-6 flex items-center justify-center gap-1.5 text-[12px] text-faint">
          <Icon name="lock" className="h-3.5 w-3.5" />
          {page.title}
        </p>
      </form>
    </div>
  )
}
