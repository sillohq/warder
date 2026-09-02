// The shape Python sends.
//
// These types are the contract between `warder/props.py` and this bundle. They
// are written out rather than inferred because the renderer is generic: it
// never knows what a Post is, only what a badge column is — so the shape of a
// column is the only thing it can rely on.

export type Json = string | number | boolean | null | Json[] | { [k: string]: Json }

export interface FormatSpec {
  kind: string
  options: Record<string, Json>
}

export interface ColumnSpec {
  key: string
  label: string
  align: 'left' | 'center' | 'right'
  width: number | string | null
  link: boolean
  sort: string | null
  sortable: boolean
  format: FormatSpec
  help: string | null
  wrap: boolean
  empty: string
  sticky: boolean
  toggle: boolean
  relation: boolean
}

export interface FilterSpec {
  key: string
  kind: string
  label: string
  options: Record<string, Json>
}

export interface ActionSpec {
  key: string
  label: string
  icon: string | null
  style: 'default' | 'primary' | 'danger' | 'ghost'
  confirm: string | null
  selection: 'many' | 'one' | 'none'
  place: 'toolbar' | 'row' | 'both'
  description: string | null
  keyboard: string | null
  fields: FieldSpec[]
}

export interface WidgetSpec {
  kind: string
  options: Record<string, Json>
}

export interface ConditionSpec {
  field: string | null
  test: string
  value: Json
  conditions: (ConditionSpec | null)[]
}

export interface FieldSpec {
  name: string
  label: string
  help: string | null
  placeholder: string | null
  required: boolean
  editable: boolean
  hidden: boolean
  span: number
  unit: string | null
  autofocus: boolean
  show: ConditionSpec | null
  widget: WidgetSpec
}

export interface SectionSpec {
  key: string
  title: string
  description: string | null
  collapsed: boolean
  columns: number
  icon: string | null
  show: ConditionSpec | null
  fields: FieldSpec[]
}

export interface RowSpec {
  id: Json
  href: string
  label: string
  cells: Record<string, Json>
}

export interface ResourceSpec {
  slug: string
  label: string
  plural: string
  icon: string | null
  group: string | null
  href: string
  description: string | null
  pk: string
}

export interface NavGroup {
  label: string
  items: {
    key: string
    label: string
    href: string
    icon: string | null
    weight: number
    kind: 'resource' | 'page'
  }[]
}

export interface Shell {
  site: {
    title: string
    brand: string
    logo: string | null
    prefix: string
    footer: string | null
    wide: boolean
  }
  nav: NavGroup[]
  user: { id: Json; label: string; email: string | null; superuser: boolean } | null
  theme: { style: string; density: string; dark: boolean | string }
  slots: Record<string, string>
  flash: { tone: string; message: string }[]
}

export interface ListPage extends Shell {
  resource: ResourceSpec
  columns: ColumnSpec[]
  rows: RowSpec[]
  filters: FilterSpec[]
  actions: ActionSpec[]
  rowActions: ActionSpec[]
  query: { page: number; perPage: number; sort: string[]; filters: Record<string, string> }
  total: number
  pages: number
  perPageOptions: number[]
  selectable: boolean
  density: string
  stickyHeader: boolean
  totals: Record<string, string>
  empty: { title: string; description: string | null; icon: string | null; action?: ActionSpec | null }
  can: Record<string, boolean>
  export: boolean
  description: string | null
}

export interface FormPage extends Shell {
  resource: ResourceSpec
  sections: SectionSpec[]
  sidebar: SectionSpec[]
  values: Record<string, Json>
  errors: Record<string, string | string[]>
  submit: string
  layout: string
  width: string
  cancel: boolean
  mode: 'add' | 'change'
  id: Json
  label: string | null
  can: { delete: boolean }
  description: string | null
}

export interface PanelSpec {
  key: string
  kind: 'fields' | 'inline' | 'related' | 'custom' | 'text'
  title: string
  span: 'main' | 'side' | 'full'
  icon: string | null
  component: string | null
  options: Record<string, Json>
}

export interface DetailPage extends Shell {
  resource: ResourceSpec
  id: Json
  title: string
  subtitle: string | null
  layout: string
  panels: PanelSpec[]
  actions: ActionSpec[]
  can: { change: boolean; delete: boolean }
}

export interface CardSpec {
  key: string
  kind: 'number' | 'chart' | 'table' | 'list' | 'custom'
  title: string
  span: number
  icon: string | null
  description: string | null
  data: Json
  options: Record<string, Json>
}

export interface DashboardPage extends Shell {
  title: string
  columns: number
  cards: CardSpec[]
  description: string | null
}

export interface LoginPage extends Shell {
  title: string
  brand: string
  field: string
  message: string | null
  remember: boolean
  reset: boolean
  providers: string[]
  errors: Record<string, string>
}
