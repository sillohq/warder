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
- 641 tests, no database required.

### Notes

- `Sort`, not `Order`: `Order` is one of the commonest model names there is, and
  an admin module importing both would carry a bug that reads as correct code.
- `Column.boolean`, `Format.boolean` and `Filter.boolean` rather than `bool`,
  because a method named `bool` shadows the type inside its own class body.
- `Field.readonly(name)` is the shorthand; the constructor keyword is
  `editable=False`, because a slot and a classmethod cannot share a name and the
  call site is what reads.

### Not yet built

- The resolver that binds declarations to models and derives the screens a bare
  `Resource(Post)` implies.
- The routes, the Inertia interface and the bundled assets. `Admin.mount()`
  runs every check it can and raises `NotConfigured` at the route-building step.
- `warder permissions sync` and `warder eject`.
