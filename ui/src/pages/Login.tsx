import { useState } from 'react'
import { router } from '@inertiajs/react'
import type { LoginPage } from '../types'
import { Button, Error, Input, Label } from '../components/ui'

export default function Login({ page }: { page: LoginPage }) {
  const [identity, setIdentity] = useState('')
  const [secret, setSecret] = useState('')
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
    <div className="grid min-h-screen place-items-center bg-bg px-4">
      <form onSubmit={submit} className="w-full max-w-[22rem]">
        <div className="mb-5 flex items-center gap-2">
          <span className="grid h-7 w-7 place-items-center rounded bg-accent text-[12px] font-bold text-white">
            {page.brand.slice(0, 1)}
          </span>
          <h1 className="text-[15px] font-semibold tracking-tight">{page.brand}</h1>
        </div>

        {page.message && <p className="mb-3 text-[12.5px] text-dim">{page.message}</p>}

        <div className="space-y-3 rounded-[var(--radius-wd)] bg-surface p-4 ring-1 ring-line">
          <div>
            <Label htmlFor="wd-identity" required>
              {page.field === 'email' ? 'Email' : 'Username'}
            </Label>
            <Input
              id="wd-identity"
              autoFocus
              autoComplete="username"
              type={page.field === 'email' ? 'email' : 'text'}
              value={identity}
              onChange={(event) => setIdentity(event.target.value)}
              invalid={Boolean(page.errors.__all__)}
            />
          </div>
          <div>
            <Label htmlFor="wd-secret" required>
              Password
            </Label>
            <Input
              id="wd-secret"
              type="password"
              autoComplete="current-password"
              value={secret}
              onChange={(event) => setSecret(event.target.value)}
              invalid={Boolean(page.errors.__all__)}
            />
          </div>

          {page.errors.__all__ && <Error>{page.errors.__all__}</Error>}

          <Button type="submit" style="primary" disabled={busy} className="w-full">
            {busy ? 'Signing in…' : 'Sign in'}
          </Button>
        </div>
      </form>
    </div>
  )
}
