import re
import httpx
import typer
import asyncio

from pathlib import Path
from typing import Optional, Annotated, TYPE_CHECKING

from league.ui import output
from league.replay import ReplayAPIClient

if TYPE_CHECKING:
    from league.replay import ReplayManager

from league.cli._shared import default_client_path

app = typer.Typer(name="replay", no_args_is_help=True, help="Replay download/launch and Replay API control commands")

MatchIDArg = Annotated[Optional[str], typer.Argument(help="Match ID (with or without platform prefix). Defaults to your last match.")]


TIME_UNITS_PATTERN = re.compile(r"^(?:(?P<h>\d+(?:\.\d+)?)h)?(?:(?P<m>\d+(?:\.\d+)?)m)?(?:(?P<s>\d+(?:\.\d+)?)s?)?$")


def _parse_time(value: str) -> float:
    """Accepts plain seconds (`90`), clock form (`1:30`, `1:02:03`) or units (`30s`, `2m`, `1m30s`)."""
    value = value.strip().lower().replace(" ", "")
    if ":" in value:
        seconds = 0.0
        for part in value.split(":"):
            seconds = seconds * 60 + float(part)
        return seconds

    match = TIME_UNITS_PATTERN.match(value)
    if not value or match is None:
        raise typer.BadParameter(f"Invalid time: {value!r}")

    h, m, s = (float(match.group(k) or 0) for k in ("h", "m", "s"))
    return h * 3600 + m * 60 + s


def _run_manager(client_install_path: Path, func):
    # imported here so Replay API-only commands skip the LCU/DataDragon import chain
    from league.replay import ReplayManager
    from league.lcu.exceptions import LCUMissingReplayMetadataException, LCUIncompatibleReplayException

    async def run():
        async with ReplayManager(client_install_path) as manager:
            try:
                return await func(manager)
            except LCUMissingReplayMetadataException as e:
                output.error(f"No replay metadata for match {e}")
                raise typer.Exit(1)
            except LCUIncompatibleReplayException as e:
                output.error(f"Replay for match {e} is incompatible or no longer available")
                raise typer.Exit(1)

    return asyncio.run(run())


def _run_api(func):
    async def run():
        api = ReplayAPIClient()
        try:
            return await func(api)
        except httpx.ConnectError:
            output.error("No replay running")
            raise typer.Exit(1)
        finally:
            await api.close()

    return asyncio.run(run())


@app.command(name="status", help="Show the LCU replay state for a match")
def replay_status(match_id: MatchIDArg = None, client_install_path: Optional[Path] = default_client_path):
    async def run(manager: ReplayManager):
        resolved = await manager.resolve_match_id(match_id)
        metadata = await manager.get_metadata(resolved)
        if metadata is None:
            output.warning(f"No replay metadata for match {resolved}")
            return

        output.print(f"Match [featherstorm]{resolved}[/]: {metadata.get('state')}")
        output.print(metadata)

    _run_manager(client_install_path, run)


@app.command(name="download", help="Download the replay (.rofl) for a match")
def replay_download(match_id: MatchIDArg = None, client_install_path: Optional[Path] = default_client_path):
    async def run(manager: ReplayManager):
        resolved = await manager.resolve_match_id(match_id)
        with output.status(f"[eminence]Downloading replay for match {resolved}...[/]"):
            status = await manager.download(resolved)
        output.print(f"Download status: {status.name}")

    _run_manager(client_install_path, run)


@app.command(name="open", help="Open the replay for a match (downloads it first if needed)")
def replay_open(
    match_id: MatchIDArg = None,
    wait: Annotated[bool, typer.Option("--wait/--no-wait", help="Wait until the Replay API is reachable")] = True,
    client_install_path: Optional[Path] = default_client_path,
):
    async def run(manager: ReplayManager):
        resolved = await manager.resolve_match_id(match_id)
        with output.status(f"[eminence]Opening replay for match {resolved}...[/]"):
            if wait:
                await manager.open_and_wait(resolved)
            else:
                await manager.open(resolved)
        output.success(f"Opened replay for match {resolved}")

    _run_manager(client_install_path, run)


@app.command(name="playback", help="Show the running replay's playback state")
def replay_playback():
    output.print(_run_api(lambda api: api.get_playback()))


@app.command(name="pause", help="Pause the running replay")
def replay_pause():
    _run_api(lambda api: api.pause())


@app.command(name="resume", help="Resume the running replay")
def replay_resume():
    _run_api(lambda api: api.resume())


@app.command(name="toggle", help="Pause the running replay if playing, resume it if paused")
def replay_toggle():
    paused = _run_api(lambda api: api.toggle_playback())
    output.success("Paused" if paused else "Resumed")


# ignore_unknown_options lets negative offsets like `-10` through as the argument instead of being parsed as options
@app.command(
    name="seek",
    help="Seek the running replay to a time (e.g. 90, 1:30, 1m30s), or by an offset with +/- (e.g. +30, -10, -1m)",
    context_settings={"ignore_unknown_options": True},
)
def replay_seek(time: str):
    sign = time.strip()[:1]
    offset = sign in ("+", "-")
    seconds = _parse_time(time.strip()[1:] if offset else time)
    if sign == "-":
        seconds = -seconds

    async def run(api: ReplayAPIClient):
        was_paused = (await api.get_playback()).get("paused")
        if offset:
            target = await api.seek_by(seconds)
            output.print(f"Seeking to {target:.0f}s")
        else:
            await api.seek_to(seconds)
        await api.wait_for_seek()
        if not was_paused:
            await api.resume()

    _run_api(run)


@app.command(name="speed", help="Set the running replay's playback speed")
def replay_speed(speed: float):
    _run_api(lambda api: api.set_speed(speed))


@app.command(name="hide-ui", help="Hide most of the replay UI (same layout highlights use)")
def replay_hide_ui():
    _run_api(lambda api: api.hide_ui())


@app.command(name="follow", help="Attach the camera to a player by Riot ID game name")
def replay_follow(name: str):
    _run_api(lambda api: api.follow_player(name))


@app.command(name="render", help="Show the running replay's render settings")
def replay_render():
    output.print(_run_api(lambda api: api.get_render()))


record_app = typer.Typer(name="record", no_args_is_help=True, help="Record the running replay to a video file")
app.add_typer(record_app)


@record_app.command(name="start", help="Start recording the running replay (defaults: from the current time to the end of the game)")
def record_start(
    out: Annotated[Optional[Path], typer.Argument(help="Output video file path. Defaults to the game client's replay directory.")] = None,
    start: Annotated[Optional[str], typer.Option(help="Start time (e.g. 90, 1:30, 1m30s). Defaults to the current replay time.")] = None,
    end: Annotated[Optional[str], typer.Option(help="End time (e.g. 90, 1:30, 1m30s). Defaults to the end of the game.")] = None,
    duration: Annotated[
        Optional[str], typer.Option("--duration", "-d", help="Record this long from the start time (e.g. 30, 30s, 1:00). Can't be combined with --end.")
    ] = None,
    width: int = 2560,
    height: int = 1440,
    fps: int = 60,
    codec: str = "webm",
    lossless: Annotated[bool, typer.Option("--lossless/--lossy", help="Lossless recordings are huge")] = False,
    wait: Annotated[bool, typer.Option("--wait/--no-wait", help="Block until the recording finishes")] = False,
):
    if end is not None and duration is not None:
        raise typer.BadParameter("Use either --end or --duration, not both")

    if out is not None:
        out = out.resolve()
        out.parent.mkdir(parents=True, exist_ok=True)

    async def run(api: ReplayAPIClient):
        playback = await api.get_playback()
        length = playback.get("length")
        start_time = _parse_time(start) if start is not None else playback.get("time", 0)
        if duration is not None:
            end_time = start_time + _parse_time(duration)
            if length is not None:
                end_time = min(end_time, length)
        elif end is not None:
            end_time = _parse_time(end)
        else:
            end_time = length

        if start is not None:
            await api.seek_to(start_time)
            await api.wait_for_seek()

        # the Replay API only captures frames while the replay is playing
        await api.resume()
        recording = await api.start_recording(
            out.as_posix() if out is not None else None, start_time, end_time, width=width, height=height, fps=fps, lossless=lossless, codec=codec
        )
        destination = (recording or {}).get("path") or out or "the default replay directory"
        output.success(f"Recording {start_time:.0f}s → {end_time:.0f}s to {destination}")

        if wait:
            try:
                with output.status("[eminence]Recording...[/] (Ctrl+C to stop)"):
                    await api.wait_for_recording(timeout=None)
            except KeyboardInterrupt, asyncio.CancelledError:
                await api.stop_recording()
                output.warning("Recording stopped early")
                return
            output.success("Recording finished")

    _run_api(run)


@record_app.command(name="stop", help="Stop the current recording")
def record_stop():
    async def run(api: ReplayAPIClient):
        recording = await api.get_recording()
        if not recording.get("recording"):
            output.warning("Not recording")
            return

        await api.stop_recording()
        output.success(f"Stopped recording to {recording.get('path')}")

    _run_api(run)


@record_app.command(name="toggle", help="Stop the current recording, or start one from the current time to the end of the game")
def record_toggle(
    out: Annotated[Optional[Path], typer.Argument(help="Output video file path when starting. Defaults to the game client's replay directory.")] = None,
    width: int = 2560,
    height: int = 1440,
    fps: int = 60,
    codec: str = "webm",
    lossless: Annotated[bool, typer.Option("--lossless/--lossy", help="Lossless recordings are huge")] = False,
):
    if out is not None:
        out = out.resolve()
        out.parent.mkdir(parents=True, exist_ok=True)

    async def run(api: ReplayAPIClient):
        started, recording = await api.toggle_recording(
            out.as_posix() if out is not None else None, width=width, height=height, fps=fps, lossless=lossless, codec=codec
        )
        if started:
            destination = recording.get("path") or out or "the default replay directory"
            output.success(f"Recording to {destination}")
        else:
            output.success(f"Stopped recording to {recording.get('path')}")

    _run_api(run)


@record_app.command(name="status", help="Show the current recording state")
def record_status():
    output.print(_run_api(lambda api: api.get_recording()))
