# Warder

A declarative admin for [Sillo](https://sillo.build). A warder keeps the keys;
this one keeps your models — what is listed, what is editable, who may see it,
and which rows are theirs.

```bash
pip install warder
```

```python
from warder import (
    Access, Action, Admin, Column, Field, Filter, Form, List,
    Resource, Section, Sort, notice,
)

admin = Admin(title="Acme Ops", prefix="/admin")

admin.add(Resource(
    Post,
    group="Content", icon="file-text",

    list=List(
        Column("title", link=True),
        Column.relation("author", display="email"),
        Column.badge("status", colors={"live": "green", "draft": "zinc"}),
        Column.date("published_at", label="Published", style="relative"),
        Column.compute("Words", lambda row: len(row.body.split()), sort="word_count"),

        filters=[
            Filter.search("title", "body"),
            Filter.choice("status", ["draft", "live"]),
            Filter.date_range("published_at", presets=["7d", "30d", "quarter"]),
        ],
        actions=[Action("Publish", publish, confirm="Publish {count} posts?")],
        sort=Sort.desc("published_at"),
    ),

    form=Form(
        Section("Content", Field("title"), Field.markdown("body")),
        Section("Publishing", Field("status"), Field("published_at")),
        Section("Audit", Field.readonly("created_at"), collapsed=True),
    ),

    access=Access(view=True, add="post.add",
                  change=lambda ctx, row: row.author_id == ctx.user.id,
                  delete=False),
))

admin.mount(app)
```

## Why this exists

Three ideas hold the whole package up, and each one is a decision you can feel
by the second screen you write.

### A type annotation describes a type. It never selects behaviour.

Nothing here reads `__annotations__`, and nothing changes because a parameter is
spelled one way rather than another. Where something must be injected it arrives
as a value — a default, a keyword — because a value is visible and an annotation
is not. The types on this package's own declarations exist so your editor can
complete `column.sort_field`, and for nothing else.

The one place arity would ordinarily be sniffed is a rule callable, so it isn't:
a rule is **always** called as `(ctx, row)`, with `row` set to `None` when the
question is about the model rather than one row.

```python
Access(change=lambda ctx, row: row.team_id == ctx.user.team_id)
Gate.custom(lambda ctx: ctx.user.email.endswith("@acme.com"))   # gates see no row
```

### A declaration is a value

Nameable, storable, comparable, generatable in a loop, extendable with `.with_()`.
No metaclass, no class attributes with meanings you cannot derive, no
registration by import side effect.

```python
def reference_data(model, *fields):
    return Resource(
        model, group="Reference",
        list=List(*[Column(f) for f in fields], sort=Sort.asc(fields[0])),
        form=Form(Section("", *[Field(f) for f in fields])),
        access=Access.by_permission("reference", delete=False),
    )

for model in (Tag, Category, Region, Currency):
    admin.add(reference_data(model, "name", "slug"))
```

Extending appends parts and replaces keywords, returning a new declaration — so
a shared base cannot be edited by its fortieth user:

```python
BASE = List(Column("id"), Column("name"), per_page=50)

admin.add(Resource(Tag,  list=BASE.with_(Column("slug"))))
admin.add(Resource(Team, list=BASE.with_(Column.relation("owner"))))
```

Because a `List` is just a description of a table, it renders in your own route,
over your own queryset, inside your own layout:

```python
ORDERS = List(Column("id"), Column.money("total"), Column.badge("status"))

@app.get("/team/orders")
async def team_orders(ctx: HttpContext):
    return await admin.render(ctx, ORDERS, Order.filter(team_id=ctx.user.team_id))
```

### Mistakes fail at mount, not at request

Every reference is resolved once, at start-up, against the model — and the error
carries the file and line the declaration was written on, because "column 'titel'
is not a field of Post" is half an error message without it.

```
DeclarationError: Resource(Post).list column 'titel' is not a field of Post.
  Did you mean 'title'?
  Declared at app/admin.py:24
```

Values are checked even earlier, from the constructor, where the mistake was
typed:

```python
Column("total", align="middle")
# ValueError: align='middle' is not valid. Use one of: 'left', 'center', 'right'.
```

## The N+1 is derived away

Declaring a relation column is what removes it. `List.joins` collects the
relations its columns and filters traverse, so the join list cannot fall behind
the column list — it *is* the column list:

```python
>>> List(Column("author__email"), Column.relation("team"), Column("title")).joins
('author', 'team')
```

A `select_related=` attribute maintained beside the columns is a list that falls
out of step silently, and costs fifty queries a page when it does.

## Actions get a queryset

Not a list of ids. An action over forty thousand selected rows is one statement:

```python
async def publish(ctx, rows):
    count = await rows.filter(status="draft").update(status="live")
    return notice(f"Published {count} posts")
```

How the handler is called is decided by the declaration, visibly, and never by
inspecting its signature: with no `fields=` it is `(ctx, rows)`; with `fields=`
it is `(ctx, rows, values)`, where *values* is the little form the confirmation
dialog collected.

```python
Action("Assign", assign, fields=[Field.relation("assignee")])
```

Outcomes are free builders, the way `json()` and `text()` are elsewhere in
Sillo — `notice`, `warning`, `problem`, `go`, `download`, `modal`, `refresh`.
Returning `None` means "it worked, reload".

## Permissions: four questions, four layers

They really are different questions, and one answer does not cover the others.

| Question | Answered by |
| --- | --- |
| May you get in at all? | `Gate` |
| May you do this to this **model**? | `Access` |
| May you do it to **this row**? | `Access` callable, and `Scope` |
| May you see **this field**? | `Access` on a `Column` or `Field` |

```python
admin = Admin(
    title="Acme Ops",
    auth=Auth(
        users=User,                       # your model; omit for the bundled one
        gate=Gate.staff(),                # who may enter at all
        session=Session(idle="30m", absolute="12h", concurrent=1),
        login=Login(throttle="5/15m", remember=True),
        mfa=MFA.totp(required=Gate.role("owner")),
        impersonation=Impersonation(gate=Gate.permission("users.impersonate")),
        audit=Audit(retain="1y", redact=["password", "token", "secret"]),
    ),
)

admin.roles(
    Role("support", grants=["order.view", "customer.view"]),
    Role("editor", grants=Role.crud(Post, Tag), inherits=["support"]),
    Role("owner", grants="*"),
)
```

Nothing here is a second authorisation system: it compiles onto
`sillo.permissions`, which already ships `Permission`, `Group`, `UserPermission`
and `PermissionMixin`. Registering a `Resource` **declares** four permissions —
`post.view`, `post.add`, `post.change`, `post.delete` — and what a deployment can
grant follows what is registered rather than being typed twice.

`Access` and `Scope` are both needed and neither substitutes for the other:

```python
Resource(
    Order,
    access=Access(change=lambda ctx, row: row.team_id == ctx.user.team_id),
    scope=Scope.tenant("team_id"),
)
```

`Access` decides whether a button is shown and whether a write is allowed;
`Scope` decides what is in the queryset at all. Access without scope leaks the
existence of rows through pagination counts and search results; scope without
access leaves a writable object reachable by its id.

A field you may not view is **absent from the props**, not hidden with CSS — so
it never reaches the browser:

```python
Field("salary", access=Access(view="hr.salary.view", change="hr.salary.change"))
```

`Gate.staff()` is the default, and it matters more than it looks: when the admin
shares the application's user model — the ordinary arrangement — every registered
account holds a session, and admitting anyone with one hands over the database.

## Style

Four directions, one token set, all four light and dark. This is a choice about
defaults, not about architecture, so switching is a keyword.

| | |
| --- | --- |
| **Console** *(default)* | Dense, quiet, keyboard-first. 36px rows, hairline borders, tabular numerals, monospace ids. The one that does not fight a dense table |
| **Paper** | Light, generous, editorial. 48px rows, soft shadows. Shows about half as much per screen, and reads beautifully |
| **Grid** | Spreadsheet-first. 28px rows, ruled cells, no card chrome. For reconciliation, imports, moderation queues |
| **Native** | No opinion. Emits structure and no colour, so your design system's tokens win by not being overridden |

```python
Admin(theme=Theme.console(accent="#4f46e5", density="compact"))
Admin(theme=Theme.native())
```

Everything writes CSS custom properties into the shell. No rebuild, no Node —
which is what keeps theming a keyword rather than an ejection.

## Interface

Inertia, React and Tailwind. Python sends a *resolved declaration* as props and
the React side is a generic renderer for that shape — it does not know what a
`Post` is. That is the property that makes the whole thing work: adding
`Column.badge("status", colors=…)` changes a prop, not a template, so a new
resource never needs a UI rebuild.

**`pip install warder` does not require Node.** Built assets ship in the wheel
under `warder/static/`; the React sources live in `ui/` in the repository and are
excluded from it. No CDN and no external request, so the admin works air-gapped
and under a Content-Security-Policy that forbids third-party script.

Customising has three rungs, in increasing order of commitment: **theme tokens**
(no rebuild), **slots** — `admin.slot("list.toolbar", "acme/ExportButton")`,
mounted from your own build — and **`warder eject`**, which copies `ui/` into your
project and hands you the upgrades.

## `Resource(Post)` is already a screen

Everything is optional but the model. With no `list=`, `form=` or `detail=`, all
three are built at mount from the model's own columns — identity first, then
state, then time; a search box over the text columns, a chip per state, a date
range; every writable column on the form with the timestamps collapsed into an
Audit group; and a window onto each child table.

```python
admin.add(Resource(Post))          # a working list, form and detail page
admin.add(Resource(Post, sort="-published_at", search=["title", "body"]))
```

The inference reads the **schema** — what the database says a column is — and
never an annotation. A `TextField` gets a textarea because the column is long
text. Naming a widget is for when the default is wrong about the *meaning*
rather than the type: `body` and `internal_note` are both long text and only one
of them wants Markdown.

Every derived part is replaced by naming it, and nothing fights a declaration
that exists.

## Checking without starting the application

```console
$ warder check app.admin:admin
Acme Ops: 12 resources, 2 pages, 51 permissions. Every reference resolves.

$ warder permissions app.admin:admin
post.add
post.change
...
```

`warder check` resolves every declaration against its models exactly as
`mount()` does, and exits non-zero on the first problem — so a misspelled column
fails in CI rather than in production. It needs no server, no port and no
database connection, only the models importable.

`warder permissions` prints what the site declares, which is how you seed a
fixtures file or write a role against what actually exists.

## Status

Alpha, and honest about which parts exist.

| | |
| --- | --- |
| ✅ | The declaration layer — every value in the table below, frozen, comparable, extendable |
| ✅ | The site registry, navigation, declared permissions, and the checks that need no ORM |
| ✅ | The resolver: binding to models, deriving screens, checking every reference |
| 🚧 | The routes, the Inertia interface, and the bundled assets |
| ✅ | `warder check` and `warder permissions` |
| 🚧 | `warder permissions sync`, `warder eject` |

`Admin.check()` and `Admin.bind()` both work today. `Admin.mount()` runs both and
then raises `NotConfigured` at the route-building step until the routes land.

## The vocabulary

| | |
| --- | --- |
| `Admin` | The site. Resources, pages, auth, theme; `.mount(app)` |
| `Resource` | One model's surface: list, detail, form, access, scope |
| `List` `Form` `Detail` | The three screens |
| `Column` `Field` `Filter` | A list column, a form input, a list filter |
| `Action` | Something a person can do to rows |
| `Section` `Panel` | Grouping on a form, blocks on a detail page |
| `Access` `Gate` `Scope` `Role` | Who may do what, and to which rows |
| `Sort` `Format` `Widget` | Ordering, how a value is drawn, how it is edited |
| `When` | A form condition the browser and the server both evaluate |
| `Page` `Card` `Dashboard` | Screens that are not a model |
| `Theme` | Four directions over one token set |
| `Auth` `Session` `Login` `MFA` `Impersonation` `Audit` | Everything about who may be here |

`Sort`, not `Order`: `Order` is one of the most common model names there is, and
an admin module importing both would have a bug in it that reads as correct code.

## Requirements

Python 3.10 to 3.14, and `sillo-framework`. The declaration layer needs nothing
else — the whole test suite runs without a database, a connection, or a running
application.

## Licence

BSD-3-Clause.
