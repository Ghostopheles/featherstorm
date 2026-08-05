from typing import Literal
from dataclasses import dataclass

Kind = Literal["auto", "dir", "file", "choice", "secret"]


@dataclass(frozen=True)
class SettingField:
    label: str | None = None
    kind: Kind = "auto"
    tooltip: str = ""
    minimum: float | None = None
    maximum: float | None = None
    step: float | None = None
    decimals: int | None = None
    choices: tuple[str, ...] = ()
    suffix: str = ""
    as_str: bool = False


SCHEMA: dict[str, SettingField] = {
    "lcu.client_install_path": SettingField(
        "League install path",
        kind="dir",
        tooltip="Root folder containing LeagueClient.exe",
    ),
    "meta.cache_dir": SettingField("Cache directory", kind="dir"),
    "highlights.export_path": SettingField("Export directory", kind="dir"),
    "govee.default_brightness": SettingField(minimum=1, maximum=100, suffix="%"),
    "govee.request_timeout": SettingField(minimum=0.05, maximum=10.0, step=0.05, decimals=2, suffix=" s"),
    "chroma.teammate_dim_factor": SettingField(minimum=0.0, maximum=1.0, step=0.05, decimals=2),
    "companion.wait_interval": SettingField(minimum=0.1, maximum=60.0, step=0.5, decimals=2, suffix=" s"),
    "companion.poll_interval": SettingField(minimum=0.05, maximum=5.0, step=0.05, decimals=2, suffix=" s"),
    "companion.session_timeout": SettingField(minimum=1.0, maximum=600.0, step=5.0, decimals=1, suffix=" s"),
    "companion.max_reconnect_attempts": SettingField(minimum=0, maximum=100),
    # these are strings that are really numbers — keep the type, fix the widget
    "highlights.export_constant_quality": SettingField(
        "Constant quality (CQ)", minimum=0, maximum=51, as_str=True, tooltip="Lower is better quality. NVENC CQ scale."
    ),
    "highlights.export_fps": SettingField("FPS", minimum=1, maximum=480, as_str=True),
    "highlights.export_preset": SettingField("NVENC preset", minimum=1, maximum=7, as_str=True),
    "highlights.export_multipass": SettingField(kind="choice", choices=("disabled", "qres", "fullres")),
    "discord.app_id": SettingField("Application ID"),
    "bladecaller.status_poll_interval": SettingField(
        "Status poll interval", minimum=0.5, maximum=60.0, step=0.5, decimals=1, suffix=" s", tooltip="How often the sidebar indicator checks the League client"
    ),
}

SECTION_LABELS = {
    "lcu": "League Client",
    "govee": "Govee",
    "chroma": "Chroma",
    "companion": "Companion",
    "meta": "General",
    "highlights": "Highlights",
    "discord": "Discord",
    "bladecaller": "Interface",
}
