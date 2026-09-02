# Changelog

All notable changes to Warder are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[semantic versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **The declaration layer.** Every screen, column, filter, action, permission
  and theme is a frozen value: comparable, printable, generatable in a loop, and
  extendable with `.with_()`, which appends parts and replaces keywords rather
  than mutating.
- **`Admin`**, the site registry — resources, pages, cards, roles and slots,
  with navigation grouped and ordered, and the permissions a deployment can
  grant derived from what is registered.
- **`Admin.check()`**, which finds everything wrong that needs no database:
  duplicate column and filter keys, filters that would share a query parameter,
  totals over columns that do not exist, actions with colliding names, form
  fields declared twice, and conditions naming a field that is not on the form.
  Every problem carries the file and line the declaration was written on.
- **Four permission layers** — `Gate` for entry, `Access` for a model, `Access`
  plus `Scope` for a row, `Access` on a `Column` or `Field` for a value — over
  the existing `sillo.permissions` tables. `Role` compiles to a group.
- **`Auth`, `Session`, `Login`, `MFA`, `Impersonation`, `Audit`**: session
  lifetimes, login throttling, a second factor demanded by gate rather than of
  everyone, gated and time-boxed impersonation, and field-level audit diffs with
  a redaction list.
- **`Theme`** — Console, Paper, Grid and Native over one token set, emitted as
  CSS custom properties with light and dark defined so an explicit choice wins
  in both directions.
- **`When`**, a form condition serialised into props so a conditional field
  appears the instant another field changes, and re-checked on the server before
  a write.
- 818 tests, and no database connection in any of them.

- **The resolver.** `Resource(Post)` with no screens becomes a working list,
  form and detail page, derived from the model's own columns at mount. Widgets
  and formats are read off the schema — what the database says a column is — and
  never off an annotation.
- **Model checks**, raised at `Admin.bind()` with the line the declaration was
  written on: misspelled columns with a did-you-mean, a `Column.relation` over a
  plain column, a display that is not on the far side, `select_related` over
  something that is not a relation, a sum over a text column, a reverse relation
  on a form, and a readonly required column with no default — which renders,
  submits, and fails at the database naming a column the user was never shown.
  An inline panel over a child with two foreign keys back asks for `via=` rather
  than picking one.
- **`Schema`**, which reads a model in the admin's own terms and works before
  `Tortoise.init`: a relation still held as a string is reported as *unresolved*
  rather than missing, because "cannot check" is not "wrong".

- **`warder check`** and **`warder permissions`**, which take a
  `module:attribute` target and need no server, no port and no database
  connection. `check` exits non-zero on the first problem, so a misspelled
  column fails in CI rather than in production.

### Notes

- `Sort`, not `Order`: `Order` is one of the commonest model names there is, and
  an admin module importing both would carry a bug that reads as correct code.
- `Column.boolean`, `Format.boolean` and `Filter.boolean` rather than `bool`,
  because a method named `bool` shadows the type inside its own class body.
- `Field.readonly(name)` is the shorthand; the constructor keyword is
  `editable=False`, because a slot and a classmethod cannot share a name and the
  call site is what reads.

### Not yet built

- The routes, the Inertia interface and the bundled assets. `Admin.mount()`
  checks and binds, then raises `NotConfigured` at the route-building step.
- `warder permissions sync` and `warder eject`.
