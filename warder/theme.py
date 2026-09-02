"""``Theme`` — four directions, one token set.

All four ship light and dark, all four are the same custom properties with
different values, and all four are Tailwind underneath. So this is a choice
about defaults, not about architecture, and switching is one keyword rather
than a fork.

**Console** *(the default)* — quiet, roomy, keyboard-first. Near-black and
near-white rather than pure, one accent used for focus and primary actions,
hairline borders, tabular numerals everywhere, monospace for ids and
timestamps. 52px rows and 20px cells, because a table you read all day is not
a spreadsheet and the row you are looking at should be obvious without
squinting. Right because an admin is a tool for people who are in it all day:
it reads as infrastructure and gets out of the way.

Every measurement here is a token, including the ones people usually hard-code
— row height, cell padding, page padding, sidebar width. That is what makes
``density="compact"`` a real setting rather than a smaller font.

**Paper** — light, generous, editorial. 15px body, 64px rows, warm neutrals and
soft shadows. Right when the admin is a content tool used occasionally by
people who do not think of themselves as operators. Shows about half as much
per screen, which is the trade.

**Grid** — spreadsheet-first. Ruled cells, 38px rows, 4px radius, almost no
chrome. Right for bulk data work — reconciliation, imports, moderation queues —
and wrong for anything with long-form fields.

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
        "bg": ("#ffffff", "#050505"),
        "surface": ("#fafafa", "#0a0a0a"),
        "raised": ("#f4f4f5", "#121212"),
        "sunken": ("#ffffff", "#080808"),
        "ink": ("#0a0a0a", "#fafafa"),
        "dim": ("#666666", "#8a8a8a"),
        "faint": ("#999999", "#5a5a5a"),
        "line": ("#eaeaea", "#1c1c1c"),
        "edge": ("#e0e0e0", "#262626"),
        "accent": ("#fc0345", "#fc0345"),
        "on-accent": ("#ffffff", "#ffffff"),
        "radius": ("10px", "10px"),
        "radius-sm": ("7px", "7px"),
        "row": ("52px", "52px"),
        "cell-x": ("20px", "20px"),
        "pad": ("32px", "32px"),
        "sidebar": ("248px", "248px"),
        "header": ("58px", "58px"),
        "text": ("14px", "14px"),
        "small": ("12.5px", "12.5px"),
        "heading": ("22px", "22px"),
        "shadow": ("0 1px 2px rgb(0 0 0 / 0.05)", "0 1px 2px rgb(0 0 0 / 0.4)"),
        "font": ("Inter, ui-sans-serif, system-ui, -apple-system, sans-serif",) * 2,
        "mono": ("ui-monospace, SFMono-Regular, Menlo, monospace",) * 2,
    },
    "paper": {
        "bg": ("#fdfcfa", "#14130f"),
        "surface": ("#ffffff", "#1c1b17"),
        "raised": ("#f7f5f0", "#232219"),
        "sunken": ("#ffffff", "#191814"),
        "ink": ("#1c1a17", "#eceae4"),
        "dim": ("#78716c", "#a8a29e"),
        "faint": ("#a8a29e", "#6b665f"),
        "line": ("#e7e2d9", "#2c2a24"),
        "edge": ("#ddd6ca", "#37342c"),
        "accent": ("#9a3412", "#fb923c"),
        "on-accent": ("#ffffff", "#1c1b17"),
        "radius": ("14px", "14px"),
        "radius-sm": ("9px", "9px"),
        "row": ("64px", "64px"),
        "cell-x": ("24px", "24px"),
        "pad": ("44px", "44px"),
        "sidebar": ("264px", "264px"),
        "header": ("64px", "64px"),
        "text": ("15px", "15px"),
        "small": ("13px", "13px"),
        "heading": ("26px", "26px"),
        "shadow": ("0 1px 3px rgb(0 0 0 / 0.07)", "0 1px 3px rgb(0 0 0 / 0.4)"),
        "font": ("Inter, ui-sans-serif, system-ui, sans-serif",) * 2,
        "mono": ("ui-monospace, Menlo, monospace",) * 2,
    },
    "grid": {
        "bg": ("#ffffff", "#0b0d10"),
        "surface": ("#ffffff", "#111418"),
        "raised": ("#f8fafc", "#161a1f"),
        "sunken": ("#ffffff", "#0e1114"),
        "ink": ("#0f172a", "#e2e8f0"),
        "dim": ("#64748b", "#94a3b8"),
        "faint": ("#94a3b8", "#5b6774"),
        "line": ("#e2e8f0", "#1f262e"),
        "edge": ("#cbd5e1", "#2b333c"),
        "accent": ("#0284c7", "#38bdf8"),
        "on-accent": ("#ffffff", "#0b0d10"),
        "radius": ("4px", "4px"),
        "radius-sm": ("3px", "3px"),
        "row": ("38px", "38px"),
        "cell-x": ("12px", "12px"),
        "pad": ("20px", "20px"),
        "sidebar": ("224px", "224px"),
        "header": ("48px", "48px"),
        "text": ("13px", "13px"),
        "small": ("12px", "12px"),
        "heading": ("18px", "18px"),
        "shadow": ("none", "none"),
        "font": ("Inter, ui-sans-serif, system-ui, sans-serif",) * 2,
        "mono": ("ui-monospace, SFMono-Regular, monospace",) * 2,
    },
}

#: Native emits structure and no colour, so whatever the host application
#: defines wins by simply not being overridden. A table still needs a row
#: height, and design systems rarely name one.
STYLES["native"] = {
    "radius": ("8px", "8px"),
    "radius-sm": ("6px", "6px"),
    "row": ("52px", "52px"),
    "cell-x": ("20px", "20px"),
    "pad": ("32px", "32px"),
    "sidebar": ("248px", "248px"),
    "header": ("58px", "58px"),
    "text": ("14px", "14px"),
    "small": ("12.5px", "12.5px"),
    "heading": ("22px", "22px"),
    "shadow": ("none", "none"),
}

#: How much room a density gives back, applied to the measurements a person can
#: actually feel: row height, cell padding, page padding. Never the font — a
#: "compact" setting that only shrinks the text is a smaller font, not a denser
#: table.
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
        factor = DENSITIES[self.density]
        for name in ("row", "cell-x", "pad"):
            if name in base:
                base[name] = tuple(  # type: ignore[assignment]
                    _scale(length, factor) for length in base[name]
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
