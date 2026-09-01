"""``Theme`` — four directions, one token set.

All four ship light and dark, all four are the same custom properties with
different values, and all four are Tailwind underneath. So this is a choice
about defaults, not about architecture, and switching is one keyword rather
than a fork.

**Console** *(the default)* — dense, quiet, keyboard-first. Near-black and
near-white rather than pure, one restrained accent used only for focus and
primary actions, hairline borders instead of shadows, tabular numerals
everywhere, monospace for ids and timestamps, 36px rows. Right because an
admin is a tool for people who are in it all day: it reads as infrastructure,
gets out of the way, and is the one direction that does not fight a dense
table.

**Paper** — light, generous, editorial. Serif headings, 15px body, 48px rows,
cards with soft shadows. Right when the admin is a content tool used
occasionally by people who do not think of themselves as operators. Shows
about half as much per screen, which is the trade.

**Grid** — spreadsheet-first. Ruled cells, frozen header, 28px rows, no card
chrome at all. Right for bulk data work — reconciliation, imports, moderation
queues — and wrong for anything with long-form fields.

**Native** — no opinion. Inherits the host application's custom properties, so
the admin looks like the product it is a tab inside.
"""

from __future__ import annotations

import typing

from warder._check import one_of
from warder.base import Declaration

__all__ = ["STYLES", "Theme"]

#: The four token sets. Each maps a custom-property suffix to its light and
#: dark values; ``Theme.css_variables`` flattens one into ``--wd-*`` names.
STYLES: dict[str, dict[str, tuple[str, str]]] = {
    "console": {
        "bg": ("#fbfbfa", "#101114"),
        "surface": ("#ffffff", "#17181d"),
        "raised": ("#f4f4f3", "#1e2026"),
        "ink": ("#16181d", "#e8e8ea"),
        "dim": ("#6b7280", "#9095a1"),
        "line": ("#e4e4e7", "#26282e"),
        "accent": ("#4f46e5", "#818cf8"),
        "radius": ("6px", "6px"),
        "row": ("36px", "36px"),
        "text": ("13px", "13px"),
        "heading": ("13px", "13px"),
        "shadow": ("none", "none"),
        "font": ("ui-sans-serif, system-ui, sans-serif",) * 2,
        "mono": ("ui-monospace, SFMono-Regular, Menlo, monospace",) * 2,
    },
    "paper": {
        "bg": ("#fdfcfa", "#14130f"),
        "surface": ("#ffffff", "#1c1b17"),
        "raised": ("#f7f5f0", "#232219"),
        "ink": ("#1c1a17", "#eceae4"),
        "dim": ("#78716c", "#a8a29e"),
        "line": ("#e7e2d9", "#2c2a24"),
        "accent": ("#9a3412", "#fb923c"),
        "radius": ("10px", "10px"),
        "row": ("48px", "48px"),
        "text": ("15px", "15px"),
        "heading": ("18px", "18px"),
        "shadow": ("0 1px 3px rgb(0 0 0 / 0.07)", "0 1px 3px rgb(0 0 0 / 0.4)"),
        "font": ("ui-sans-serif, system-ui, sans-serif",) * 2,
        "mono": ("ui-monospace, Menlo, monospace",) * 2,
    },
    "grid": {
        "bg": ("#ffffff", "#0b0d10"),
        "surface": ("#ffffff", "#111418"),
        "raised": ("#f8fafc", "#161a1f"),
        "ink": ("#0f172a", "#e2e8f0"),
        "dim": ("#64748b", "#94a3b8"),
        "line": ("#cbd5e1", "#1f262e"),
        "accent": ("#0284c7", "#38bdf8"),
        "radius": ("2px", "2px"),
        "row": ("28px", "28px"),
        "text": ("12px", "12px"),
        "heading": ("12px", "12px"),
        "shadow": ("none", "none"),
        "font": ("ui-sans-serif, system-ui, sans-serif",) * 2,
        "mono": ("ui-monospace, SFMono-Regular, monospace",) * 2,
    },
}

#: Native emits structure and no colour, so whatever the host application
#: defines wins by simply not being overridden. A table still needs a row
#: height, and design systems rarely name one.
STYLES["native"] = {
    "radius": ("8px", "8px"),
    "row": ("40px", "40px"),
    "text": ("14px", "14px"),
    "heading": ("14px", "14px"),
    "shadow": ("none", "none"),
}

#: Extra spacing per density, as a multiplier on the row height.
DENSITIES = {"compact": 0.86, "normal": 1.0, "relaxed": 1.2}


class Theme(Declaration):
    """The admin's appearance, as custom properties.

    ::

        Theme(style="console", accent="#4f46e5", density="compact")
        Theme.native()                       # inherit the host's tokens
        Theme(tokens={"accent": ("#059669", "#34d399")})

    Everything here writes CSS custom properties into the shell. No rebuild,
    no Node, no second stylesheet — which is what keeps theming a keyword
    rather than an ejection.
    """

    __slots__ = (
        "style",
        "accent",
        "radius",
        "density",
        "font",
        "mono",
        "logo",
        "favicon",
        "dark",
        "tokens",
        "wide",
    )
    _fields = __slots__

    style: str
    accent: str | tuple[str, str] | None
    radius: str | None
    density: str
    font: str | None
    mono: str | None
    logo: str | None
    favicon: str | None
    dark: bool | str
    tokens: typing.Mapping[str, str | tuple[str, str]]
    wide: bool

    def __init__(
        self,
        style: str = "console",
        *,
        accent: str | tuple[str, str] | None = None,
        radius: str | None = None,
        density: str = "normal",
        font: str | None = None,
        mono: str | None = None,
        logo: str | None = None,
        favicon: str | None = None,
        dark: bool | str = True,
        tokens: typing.Mapping[str, str | tuple[str, str]] | None = None,
        wide: bool = False,
    ) -> None:
        self._init(
            style=one_of("style", style, tuple(STYLES)),
            accent=accent,
            radius=radius,
            density=one_of("density", density, tuple(DENSITIES)),
            font=font,
            mono=mono,
            logo=logo,
            favicon=favicon,
            dark=dark
            if isinstance(dark, bool)
            else one_of("dark", dark, ("light", "dark", "system")),
            tokens=dict(tokens or {}),
            wide=wide,
        )

    @classmethod
    def console(cls, **options: typing.Any) -> Theme:
        return cls("console", **options)

    @classmethod
    def paper(cls, **options: typing.Any) -> Theme:
        return cls("paper", **options)

    @classmethod
    def grid(cls, **options: typing.Any) -> Theme:
        return cls("grid", density=options.pop("density", "compact"), **options)

    @classmethod
    def native(cls, **options: typing.Any) -> Theme:
        """Inherit the host application's tokens.

        Emits no colours at all, so anything the host defines wins by simply
        not being overridden. The structural tokens — radius, row height —
        still come from here, because a table needs a row height and a design
        system rarely names one.
        """
        return cls("native", **options)

    # ------------------------------------------------------------------ output

    def palette(self) -> dict[str, tuple[str, str]]:
        """Every token, light and dark, after the overrides."""
        base = dict(STYLES.get(self.style, {}))
        if self.accent is not None:
            base["accent"] = _pair(self.accent)
        if self.radius is not None:
            base["radius"] = (self.radius, self.radius)
        if self.font is not None:
            base["font"] = (self.font, self.font)
        if self.mono is not None:
            base["mono"] = (self.mono, self.mono)
        for name, value in self.tokens.items():
            base[name] = _pair(value)
        if "row" in base:
            base["row"] = tuple(  # type: ignore[assignment]
                _scale(height, DENSITIES[self.density]) for height in base["row"]
            )
        return base

    def css_variables(self, mode: str = "light") -> dict[str, str]:
        """The custom properties for one mode, ready to write into a style tag."""
        index = 0 if mode == "light" else 1
        return {
            f"--wd-{name}": values[index] for name, values in self.palette().items()
        }

    def stylesheet(self) -> str:
        """``:root`` and its dark counterpart, as one small block of CSS.

        Light on bare ``:root`` so a viewer with no preference gets a complete
        palette; dark redefined under both the media query and an explicit
        attribute, so the toggle wins in either direction.
        """
        light = _block(":root", self.css_variables("light"))
        if self.dark is False:
            return light
        dark = self.css_variables("dark")
        chosen = _block('[data-theme="dark"]', dark)
        preferred = _block(':root:not([data-theme="light"])', dark)
        media = "@media (prefers-color-scheme: dark) {\n" + preferred + "\n}"
        return "\n".join([light, chosen, media])

    def __repr__(self) -> str:
        extras = [f"density={self.density!r}"] if self.density != "normal" else []
        if self.accent:
            extras.append(f"accent={self.accent!r}")
        return f"Theme({', '.join([repr(self.style), *extras])})"


def _pair(value: str | tuple[str, str]) -> tuple[str, str]:
    """One value for both modes, or an explicit light/dark pair."""
    if isinstance(value, tuple):
        return value
    return (value, value)


def _scale(length: str, factor: float) -> str:
    """``"36px"`` at 0.86 → ``"31px"``. Non-pixel values pass through."""
    if not length.endswith("px"):
        return length
    try:
        return f"{round(float(length[:-2]) * factor)}px"
    except ValueError:  # pragma: no cover - malformed override
        return length


def _block(selector: str, variables: typing.Mapping[str, str]) -> str:
    body = "\n".join(f"  {name}: {value};" for name, value in variables.items())
    return f"{selector} {{\n{body}\n}}"
