"""Theme: four directions, one token set, no rebuild."""

from __future__ import annotations

import pytest

from warder.theme import STYLES, Theme


def test_the_default_is_console():
    assert Theme().style == "console"


def test_every_named_style_exists():
    for style in ("console", "paper", "grid", "native"):
        assert Theme(style).style == style


def test_an_unknown_style_is_refused():
    with pytest.raises(ValueError, match="not valid"):
        Theme("brutalist")


def test_the_shorthands_match_the_constructor():
    assert Theme.console().style == "console"
    assert Theme.paper().style == "paper"
    assert Theme.native().style == "native"


def test_grid_defaults_to_compact():
    assert Theme.grid().density == "compact"


def test_native_emits_structure_and_no_colour():
    # Whatever the host defines wins by not being overridden. A table still
    # needs a row height, and design systems rarely name one.
    variables = Theme.native().css_variables()
    assert "--wd-row" in variables
    assert not any(name.endswith(("-bg", "-ink", "-accent")) for name in variables)


def test_an_accent_overrides_the_style():
    assert Theme(accent="#059669").css_variables()["--wd-accent"] == "#059669"


def test_an_accent_can_differ_by_mode():
    theme = Theme(accent=("#111", "#eee"))
    assert theme.css_variables("light")["--wd-accent"] == "#111"
    assert theme.css_variables("dark")["--wd-accent"] == "#eee"


def test_density_scales_what_a_person_can_feel():
    # Row height, cell padding and page padding — not the font. A "compact"
    # setting that only shrinks the text is a smaller font, not a denser table.
    normal = Theme(density="normal").css_variables()
    compact = Theme(density="compact").css_variables()
    relaxed = Theme(density="relaxed").css_variables()
    for token in ("--wd-row", "--wd-cell-x", "--wd-pad"):
        assert _px(compact[token]) < _px(normal[token]) < _px(relaxed[token])
    assert compact["--wd-text"] == normal["--wd-text"]


def test_the_default_row_is_roomy_enough_to_scan():
    assert _px(Theme().css_variables()["--wd-row"]) >= 48


def _px(value: str) -> int:
    return int(value.removesuffix("px"))


def test_density_leaves_non_pixel_values_alone():
    theme = Theme(density="compact", tokens={"row": "2rem"})
    assert theme.css_variables()["--wd-row"] == "2rem"


def test_every_style_defines_the_spacing_tokens():
    # Row height, cell padding, page padding, sidebar and header width are all
    # tokens, which is what makes density a real setting.
    for tokens in STYLES.values():
        assert {"row", "cell-x", "pad", "sidebar", "header"} <= set(tokens)


def test_arbitrary_tokens_can_be_set():
    assert Theme(tokens={"ink": "#000"}).css_variables()["--wd-ink"] == "#000"


def test_fonts_can_be_replaced():
    theme = Theme(font="Inter, sans-serif", mono="Fira Code, monospace")
    assert theme.css_variables()["--wd-font"] == "Inter, sans-serif"
    assert theme.css_variables()["--wd-mono"] == "Fira Code, monospace"


def test_the_radius_can_be_replaced():
    assert Theme(radius="0px").css_variables()["--wd-radius"] == "0px"


def test_light_is_defined_on_bare_root():
    # A viewer with no preference must get a complete palette.
    assert Theme().stylesheet().startswith(":root {")


def test_dark_wins_in_both_directions():
    sheet = Theme().stylesheet()
    assert '[data-theme="dark"]' in sheet
    assert "prefers-color-scheme: dark" in sheet
    assert ':root:not([data-theme="light"])' in sheet


def test_a_light_only_theme_emits_one_block():
    sheet = Theme(dark=False).stylesheet()
    assert "prefers-color-scheme" not in sheet


def test_the_dark_setting_is_checked():
    with pytest.raises(ValueError, match="'light', 'dark', 'system'"):
        Theme(dark="maybe")


def test_density_is_checked():
    with pytest.raises(ValueError, match="not valid"):
        Theme(density="airy")


def test_every_style_defines_the_structural_tokens():
    for tokens in STYLES.values():
        assert {"radius", "row"} <= set(tokens)


def test_repr_names_what_was_chosen():
    assert repr(Theme()) == "Theme('console')"
    assert repr(Theme(density="compact")) == "Theme('console', density='compact')"
