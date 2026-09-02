import type { Json, Shell as ShellProps } from '../types'
import { Shell } from '../components/Shell'
import { Panel } from '../components/ui'

/**
 * The fallback for a custom `Page` whose component your build supplies.
 *
 * It shows the props rather than a blank screen, because "the page rendered
 * nothing" is the hardest failure to diagnose and this at least proves the
 * route, the gate and the handler all worked.
 */
export default function CustomPage({ page }: { page: ShellProps & { title: string; description: string | null; page: Json } }) {
  return (
    <Shell title={page.title}>
      <header className="mb-3">
        <h2 className="text-[16px] font-semibold tracking-tight">{page.title}</h2>
        {page.description && <p className="mt-0.5 text-[12.5px] text-dim">{page.description}</p>}
      </header>
      <Panel title="Props">
        <pre className="wd-scroll-x font-mono text-[11.5px] leading-relaxed text-dim">{JSON.stringify(page.page, null, 2)}</pre>
        <p className="mt-3 border-t border-line pt-3 text-[12px] text-dim">
          Give this page a <code className="font-mono">component=</code> and supply it from your own build to replace this view.
        </p>
      </Panel>
    </Shell>
  )
}
