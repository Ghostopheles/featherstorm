from rich.theme import Theme

DARK_XAYAH = "#840e3e"
XAYAH = "#b01d5d"

DARK_RAKAN = "magenta"
RAKAN = "#cba6f7"

GOLD = "#c3a17c"

LIGHT_GRAY = "#7f7d8e"

THEME = Theme(
    {
        "log.time": f"bold {GOLD}",
        "xayah": XAYAH,
        "dark_xayah": DARK_XAYAH,
        "rakan": RAKAN,
        "dark_rakan": DARK_RAKAN,
        "gold": GOLD,
        "featherstorm": f"bold {XAYAH}",
        "featherstorm_bg": f"on {XAYAH}",
        "featherstorm_dim": f"dim {XAYAH}",
        "heading": f"bold {RAKAN}",
        "highlights": f"bold {RAKAN}",
        "highlights_match_id": "bold blue",
        "eminence": f"bold {GOLD}",
        "eminence_dim": f"dim {GOLD}",
        "file": f"bold underline {GOLD}",
        "url": f"bold underline {RAKAN}",
        "external_api": "bold blue",
        "warning": "bold underline red",
        "error": "bold red",
        "light_gray": LIGHT_GRAY,
        "less_dim": LIGHT_GRAY,
        "success": "bold green",
    }
)
