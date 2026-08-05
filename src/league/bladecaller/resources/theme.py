"""Design tokens for the Bladecaller UI.

Mirrors the CSS custom properties from `ref/Featherstorm.html`. The oklch()
colors are pre-converted to sRGB because Qt stylesheets only understand
hex/rgb/rgba.
"""

# ── surfaces ──────────────────────────────────────────────────────────────────
BG0 = "#070510"
BG1 = "#0d0a1a"
BG2 = "#141028"
BG3 = "#1c1636"
BG4 = "#241e44"

SIDEBAR_TOP = "#0e0b1e"
SIDEBAR_BOTTOM = "#0a0816"

BORDER = "rgba(120, 90, 180, 18%)"
BORDER_SOFT = "rgba(120, 90, 180, 8%)"
BORDER_BRIGHT = "rgba(180, 100, 200, 35%)"
DIVIDER = "rgba(150, 115, 210, 40%)"

HOVER_WASH = "rgba(255, 255, 255, 3%)"

# ── brand ─────────────────────────────────────────────────────────────────────
ACCENT = "#da3aa4"
ACCENT_DIM = "#93126b"
ACCENT_GLOW = "rgba(218, 58, 164, 25%)"
ACCENT_WASH = "rgba(218, 58, 164, 12%)"
ACCENT_FAINT = "rgba(218, 58, 164, 6%)"

ACCENT2 = "#8267e2"
ACCENT2_DIM = "#50349c"
ACCENT2_WASH = "rgba(130, 103, 226, 12%)"

GOLD = "#f8ab4f"
GOLD_GLOW = "rgba(248, 171, 79, 30%)"
GOLD_WASH = "rgba(248, 171, 79, 15%)"

# ── text ──────────────────────────────────────────────────────────────────────
TEXT = "#f0eaf8"
TEXT2 = "#a899c0"
TEXT3 = "#5c5270"

# ── status ────────────────────────────────────────────────────────────────────
RED = "#ee343b"
GREEN = "#31aa40"
BLUE = "#0099f0"

# ── typography ────────────────────────────────────────────────────────────────
FONT_BODY = "Inter"
FONT_DISPLAY = "Barlow Semi Condensed"
FONT_SIZE = 13

# ── geometry ──────────────────────────────────────────────────────────────────
RADIUS = 8
RADIUS_SM = 4
SIDEBAR_WIDTH = 200

TOKENS: dict[str, str] = {name: str(value) for name, value in list(globals().items()) if name.isupper() and not name.startswith("_")}
