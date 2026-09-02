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
- 962 tests. The declaration layer opens no database at all; the interface,
  the routes and the CLI are tested end to end against a real one.

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

- **The interface** — list, form, detail, dashboard, login and a command
  palette, in Inertia, React and Tailwind. Python sends a resolved declaration
  and the renderer is generic over it: Python extracts what this person may see,
  the browser formats it in their locale.
- **The routes**: nine per resource, plus pages, a relation-picker endpoint,
  login and the asset mount. Scope is applied before any row is read, so a row
  outside your scope is a 404 rather than a 403 — telling you it exists is
  itself a disclosure.
- **The Inertia protocol**, implemented here rather than depended on, since
  `sillo-inertia` is on the 0.x API. A redirect after a mutation is 303, a stale
  asset version is a 409 with a location, and a partial reload sends only what
  it asked for.
- **A bundled wheel**: one JavaScript file and one stylesheet under
  `warder/static/`, no CDN, no Node at install time. `build_ui.py` fails the
  build rather than shipping a wheel whose interface did not compile.

- **Signing in.** `Admin()` with no `auth=` gets the bundled `AdminUser`, a
  session backend, `Gate.staff()` and session middleware installed on mount.
  Throttling counts per identity *and* per address. The session carries an id
  and two timestamps and never a user, so deactivating somebody takes effect on
  their next click rather than their next sign-in.
- **`warder create-admin`** and **`warder users`**. `create-admin` writes the
  column the sign-in form asks for, sets only the flags the model has, and
  refuses up front — naming what to do — when the model is unregistered, its
  table is missing, it cannot hash a password, or it needs a column Warder
  cannot know about.
- **Export**: CSV and JSON of the filtered set, capped, with a guard on cells a
  spreadsheet would run as a formula.
- **Column visibility** and a **light/dark toggle**, both remembered per browser.

### Notes

- `Sort`, not `Order`: `Order` is one of the commonest model names there is, and
  an admin module importing both would carry a bug that reads as correct code.
- `Column.boolean`, `Format.boolean` and `Filter.boolean` rather than `bool`,
  because a method named `bool` shadows the type inside its own class body.
- `Field.readonly(name)` is the shorthand; the constructor keyword is
  `editable=False`, because a slot and a classmethod cannot share a name and the
  call site is what reads.

### Not yet built

- Inline editing inside child panels; MFA and impersonation are declarable but
  not yet enforced.
- `warder permissions sync` and `warder eject`.
