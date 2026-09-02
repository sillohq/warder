import type { ComponentType } from 'react'
import { createRoot } from 'react-dom/client'
import { createInertiaApp } from '@inertiajs/react'
import './index.css'

import List from './pages/List'
import Form from './pages/Form'
import Detail from './pages/Detail'
import Dashboard from './pages/Dashboard'
import Login from './pages/Login'
import Denied from './pages/Denied'
import CustomPage from './pages/Page'

// Every page, resolved from a static map.
//
// Static rather than a glob import: the bundle is one file on purpose (see
// vite.config.ts), so there is nothing to load lazily, and a map means an
// unknown component name raises where it happened rather than rendering a
// blank screen.
const pages: Record<string, ComponentType<{ page: never }>> = {
  List,
  Form,
  Detail,
  Dashboard,
  Login,
  Denied,
  Page: CustomPage,
  // Embedding renders the same list; `admin.render` sends the same props.
  Embedded: List,
} as unknown as Record<string, ComponentType<{ page: never }>>

createInertiaApp({
  // Inertia spreads the page's props onto the component. Every page here reads
  // one `page` object instead, because a screen's props arrive as a whole and
  // destructuring twenty of them at each call site is noise.
  resolve: (name) => {
    const Component = pages[name]
    if (!Component) throw new Error(`Warder has no page component named "${name}".`)
    const Wrapped = (props: Record<string, unknown>) => <Component page={props as never} />
    Wrapped.displayName = `Warder(${name})`
    return Wrapped
  },
  setup({ el, App, props }) {
    createRoot(el).render(<App {...props} />)
  },
  progress: { color: 'var(--wd-accent, #4f46e5)', showSpinner: false },
})
