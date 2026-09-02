import { Link } from '@inertiajs/react'
import type { Shell as ShellProps } from '../types'
import { Shell } from '../components/Shell'
import { Icon } from '../components/Icon'
import { Button } from '../components/ui'

const REASONS: Record<string, string> = {
  gate: 'Your account does not have access to this admin.',
  view: 'You do not have permission to view this.',
  add: 'You do not have permission to create these.',
  change: 'You do not have permission to change this.',
  delete: 'You do not have permission to delete this.',
  action: 'You do not have permission to run that action.',
  page: 'You do not have permission to open this page.',
}

export default function Denied({ page }: { page: ShellProps & { reason: string } }) {
  return (
    <Shell title="Not permitted">
      <div className="mx-auto max-w-md py-16 text-center">
        <span className="mx-auto mb-3 grid h-10 w-10 place-items-center rounded-full bg-raised text-dim">
          <Icon name="lock" className="h-5 w-5" />
        </span>
        <h2 className="text-[15px] font-semibold">Not permitted</h2>
        <p className="mt-1 text-[12.5px] text-dim">{REASONS[page.reason] ?? REASONS.view}</p>
        <div className="mt-4">
          <Link href={page.site.prefix}>
            <Button icon="home">Back to the dashboard</Button>
          </Link>
        </div>
      </div>
    </Shell>
  )
}
