"""Gates, access rules, scopes and roles — the four questions."""

from __future__ import annotations

import pytest
from fakes import Ctx, Rows, User, model

from warder.access import ACTIONS, Access, Gate, Role, Scope, current_user

# ------------------------------------------------------------------- current_user


def test_current_user_returns_the_user():
    user = User()
    assert current_user(Ctx(user)) is user


def test_current_user_survives_a_context_without_authentication():
    # ctx.user raises rather than returning None when no middleware is
    # installed, and "may this person view" before login is an ordinary state.
    assert current_user(Ctx(None)) is None


# -------------------------------------------------------------------------- Gate


async def test_always_admits_anyone_signed_in():
    assert await Gate.always().allows(Ctx(User()))


async def test_always_still_refuses_nobody():
    assert not await Gate.always().allows(Ctx(None))


async def test_never_refuses_everyone():
    assert not await Gate.never().allows(Ctx(User(is_superuser=True)))


async def test_staff_admits_staff():
    assert await Gate.staff().allows(Ctx(User(is_staff=True)))


async def test_staff_admits_superusers():
    assert await Gate.staff().allows(Ctx(User(is_superuser=True)))


async def test_staff_refuses_an_ordinary_account():
    # The case that matters: when the admin shares the application's user
    # model, every registered account holds a session.
    assert not await Gate.staff().allows(Ctx(User()))


async def test_staff_refuses_a_deactivated_account():
    assert not await Gate.staff().allows(Ctx(User(is_staff=True, is_active=False)))


async def test_superuser_refuses_mere_staff():
    assert not await Gate.superuser().allows(Ctx(User(is_staff=True)))


async def test_permission_gate():
    ctx = Ctx(User(permissions=["admin.access"]))
    assert await Gate.permission("admin.access").allows(ctx)
    assert not await Gate.permission("admin.other").allows(ctx)


async def test_a_superuser_holds_every_permission():
    assert await Gate.permission("anything").allows(Ctx(User(is_superuser=True)))


async def test_permissions_are_loaded_once_per_user():
    user = User(permissions=["a", "b"])
    ctx = Ctx(user)
    await Gate.permission("a").allows(ctx)
    await Gate.permission("b").allows(ctx)
    assert user.loaded == 2  # once per check; the mixin caches on the instance


async def test_role_gate_uses_group_membership():
    assert await Gate.role("support").allows(Ctx(User(groups=["support"])))


async def test_role_gate_falls_back_to_a_role_attribute():
    role = model("Role")()
    role.slug = "support"
    assert await Gate.role("support").allows(Ctx(User(role=role)))


async def test_role_gate_matches_a_role_by_name():
    role = model("Role")()
    role.name = "support"
    assert await Gate.role("support").allows(Ctx(User(role=role)))


async def test_role_gate_refuses_a_user_with_no_roles_at_all():
    assert not await Gate.role("support").allows(Ctx(User()))


async def test_custom_gate():
    gate = Gate.custom(lambda ctx: ctx.user.id == 7)
    assert await gate.allows(Ctx(User(id=7)))
    assert not await gate.allows(Ctx(User(id=8)))


async def test_custom_gate_may_be_async():
    async def check(ctx):
        return True

    assert await Gate.custom(check).allows(Ctx(User()))


async def test_any_passes_when_one_does():
    gate = Gate.any(Gate.never(), Gate.staff())
    assert await gate.allows(Ctx(User(is_staff=True)))


async def test_any_of_nothing_admits_nobody():
    assert not await Gate.any().allows(Ctx(User(is_superuser=True)))


async def test_all_requires_every_gate():
    gate = Gate.all(Gate.staff(), Gate.permission("admin.access"))
    assert not await gate.allows(Ctx(User(is_staff=True)))
    assert await gate.allows(Ctx(User(is_staff=True, permissions=["admin.access"])))


async def test_all_of_nothing_admits_everyone():
    assert await Gate.all().allows(Ctx(User()))


async def test_gates_compose_with_operators():
    assert await (Gate.never() | Gate.always()).allows(Ctx(User()))
    assert not await (Gate.never() & Gate.always()).allows(Ctx(User()))
    assert await (~Gate.never()).allows(Ctx(User()))


def test_an_unknown_gate_kind_is_refused():
    with pytest.raises(ValueError, match="not one of"):
        Gate("sometimes")


def test_gate_custom_needs_a_callable():
    with pytest.raises(TypeError, match="must be callable"):
        Gate.custom("nope")


# ------------------------------------------------------------------------ Access


async def test_an_unset_rule_defers_to_the_layer_above():
    assert await Access().allows(Ctx(User()), "view")


async def test_a_fixed_rule():
    assert await Access(view=True).allows(Ctx(User()), "view")
    assert not await Access(view=False).allows(Ctx(User()), "view")


async def test_a_permission_rule():
    ctx = Ctx(User(permissions=["post.add"]))
    assert await Access(add="post.add").allows(ctx, "add")
    assert not await Access(add="post.change").allows(ctx, "add")


async def test_a_callable_rule_is_given_the_row():
    access = Access(change=lambda ctx, row: row.author_id == ctx.user.id)
    row = model("Row")()
    row.author_id = 1
    assert await access.allows(Ctx(User(id=1)), "change", row)
    assert not await access.allows(Ctx(User(id=2)), "change", row)


async def test_a_callable_rule_gets_none_when_there_is_no_row():
    # No arity sniffing: the callable is always (ctx, row).
    seen = []

    def rule(ctx, row):
        seen.append(row)
        return True

    await Access(add=rule).allows(Ctx(User()), "add")
    assert seen == [None]


async def test_a_callable_rule_may_be_async():
    async def rule(ctx, row):
        return True

    assert await Access(view=rule).allows(Ctx(User()), "view")


def test_an_unknown_action_is_refused():
    with pytest.raises(ValueError, match="not one of"):
        Access().rule("publish")


def test_open_allows_everything():
    assert all(Access.open().rule(action) is True for action in ACTIONS)


def test_readonly_allows_only_view():
    readonly = Access.readonly()
    assert readonly.rule("view") is True
    assert readonly.rule("change") is False


def test_none_allows_nothing():
    assert all(Access.none().rule(action) is False for action in ACTIONS)


def test_by_permission_names_the_four():
    access = Access.by_permission("post")
    assert access.rule("view") == "post.view"
    assert access.rule("delete") == "post.delete"


def test_by_permission_takes_a_delete_override():
    assert Access.by_permission("post", delete=False).rule("delete") is False


def test_merging_narrows_and_never_widens():
    parent = Access.by_permission("post")
    merged = Access(view=True).merged_under(parent)
    assert merged.rule("view") is True
    assert merged.rule("change") == "post.change"


def test_merging_under_nothing_is_the_original():
    access = Access(view=True)
    assert access.merged_under(None) is access


def test_access_is_falsy_when_it_decides_nothing():
    assert not Access()
    assert Access(view=True)


# ------------------------------------------------------------------------- Scope


async def test_all_leaves_the_queryset_alone(rows, anyone):
    assert await Scope.all().apply(anyone, rows) is rows


async def test_none_matches_nothing(rows, anyone):
    assert (await Scope.none().apply(anyone, rows)).filters == [{"pk__in": []}]


async def test_by_filters(rows):
    scope = Scope.by(lambda ctx: {"team_id": ctx.user.team_id})
    narrowed = await scope.apply(Ctx(User(team_id=4)), rows)
    assert narrowed.filters == [{"team_id": 4}]


async def test_by_may_be_async(rows, anyone):
    async def build(ctx):
        return {"a": 1}

    assert (await Scope.by(build).apply(anyone, rows)).filters == [{"a": 1}]


async def test_empty_filters_leave_the_queryset_alone(rows, anyone):
    assert await Scope.by(lambda ctx: {}).apply(anyone, rows) is rows


async def test_owner(rows):
    narrowed = await Scope.owner("author_id").apply(Ctx(User(id=9)), rows)
    assert narrowed.filters == [{"author_id": 9}]


async def test_tenant_reads_the_matching_attribute(rows):
    narrowed = await Scope.tenant("team_id").apply(Ctx(User(team_id=3)), rows)
    assert narrowed.filters == [{"team_id": 3}]


async def test_tenant_can_read_a_differently_named_attribute(rows):
    scope = Scope.tenant("organisation_id", source="org_id")
    narrowed = await scope.apply(Ctx(User(org_id=5)), rows)
    assert narrowed.filters == [{"organisation_id": 5}]


async def test_query_gets_the_queryset(rows, anyone):
    scope = Scope.query(lambda ctx, base: base.exclude(archived=True))
    narrowed = await scope.apply(anyone, rows)
    assert narrowed.calls == (("exclude", (), {"archived": True}),)


async def test_query_may_be_async(rows, anyone):
    async def narrow(ctx, base):
        return base.filter(a=1)

    assert (await Scope.query(narrow).apply(anyone, rows)).filters == [{"a": 1}]


def test_scope_is_falsy_only_when_it_narrows_nothing():
    assert not Scope.all()
    assert Scope.none()
    assert Scope.owner()


def test_an_unknown_scope_kind_is_refused():
    with pytest.raises(ValueError, match="not one of"):
        Scope("mostly")


# -------------------------------------------------------------------------- Role


def test_a_role_labels_itself():
    assert Role("support_lead").label == "Support lead"


def test_grants_star_is_recognised():
    assert Role("owner", grants="*").unrestricted
    assert not Role("editor", grants=["post.add"]).unrestricted


def test_crud_names_the_four_permissions_per_model():
    assert Role.crud(model("Post")) == (
        "post.view",
        "post.add",
        "post.change",
        "post.delete",
    )


def test_crud_takes_a_narrower_set_of_actions():
    assert Role.crud(model("Tag"), actions=["view"]) == ("tag.view",)


def test_expand_follows_inheritance():
    roles = {
        r.name: r
        for r in [
            Role("support", grants=["order.view"]),
            Role("editor", grants=["post.add"], inherits=["support"]),
        ]
    }
    assert roles["editor"].expand(roles) == frozenset({"post.add", "order.view"})


def test_expand_survives_a_cycle():
    roles = {
        r.name: r
        for r in [
            Role("a", grants=["x"], inherits=["b"]),
            Role("b", grants=["y"], inherits=["a"]),
        ]
    }
    assert roles["a"].expand(roles) == frozenset({"x", "y"})


def test_expand_ignores_an_unknown_parent():
    role = Role("a", grants=["x"], inherits=["ghost"])
    assert role.expand({"a": role}) == frozenset({"x"})


async def test_a_query_scope_that_returns_a_queryset_is_not_executed(rows, anyone):
    # A queryset is *awaitable*: `await Post.filter(...)` runs the query and
    # returns a list. Awaiting one here would turn the narrowed queryset into
    # rows, and the next .filter() would fail somewhere else entirely.
    narrowed = await Scope.query(lambda ctx, base: base.filter(a=1)).apply(anyone, rows)
    assert isinstance(narrowed, Rows)
    assert narrowed.filters == [{"a": 1}]


async def test_a_resource_queryset_that_returns_a_queryset_is_not_executed(
    rows, anyone
):
    from warder.resource import Resource

    resource = Resource(model("Post"), queryset=lambda ctx, base: base.filter(a=1))
    narrowed = await resource.rows(anyone, rows)
    assert isinstance(narrowed, Rows)


async def test_a_gate_may_answer_with_an_awaitable(anyone):
    # A gate returns an answer, not a query, so anything awaitable is awaited.
    class Answer:
        def __await__(self):
            async def yes():
                return True

            return yes().__await__()

    assert await Gate.custom(lambda ctx: Answer()).allows(anyone)
