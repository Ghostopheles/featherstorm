# Rendering Layer

`src/league/ui/` owns every byte written to the terminal. Four rules:

1. **Renderers are pure and sync** — domain/view model in, `RenderableType` out. No `await`, no console, no I/O. Anything a renderer needs (champion names, resolved item names) is fetched by the caller first.
2. **Only `ui/output.py` and `ui/console.py` touch the `Console`.** Commands call `output.print(...)`, never `console.print(...)`.
3. **Backend modules never import rich** and never import `league.ui`. They emit data (return values), diagnostics (`logging.getLogger(__name__)`), and progress (an injected `league.reporting.ProgressReporter`). The only ui-adjacent import they may take is `league.markup` — pure markup strings, zero rich.
4. **Markup is produced in the ui layer**, with one sanctioned exception: log and reporter messages may carry markup, since `RichHandler` is installed with `markup=True`.

Diagnostics: `setup_logging()` ([league/ui/logging.py](../src/league/ui/logging.py)) is called from the CLI callback and installs a `RichHandler` on the shared Console (httpx/websockets/asyncio pinned to WARNING). Bladecaller configures its own handlers — it imports nothing from `league.ui`.

Per-model rendering: `render()` ([league/ui/registry.py](../src/league/ui/registry.py)) is a `functools.singledispatch` — register a concrete model type in a renderer module to give it a default view; unregistered objects fall back to `rich.Pretty` (the old `print(model)` behaviour). Models themselves stay rich-free — no `__rich__` on anything in `models.py`.

Adding a renderer: write a pure function in `ui/renderers/`, export it from `ui/renderers/__init__.py`, and call it from the command as `output.print(my_renderer(data))`. Reuse `new_table()` ([league/ui/renderers/matches.py](../src/league/ui/renderers/matches.py)) for the project's table style and the `format_*` helpers in [league/markup.py](../src/league/markup.py) for KDA/result/duration/player cells.

Progress from backend code: take a `ProgressReporter` in the constructor, default to `NullReporter()`, and call `reporter.message()` / `reporter.step()` / `reporter.advance()` / `with reporter.task(desc, total=...)`. The CLI/composition root injects `RichProgressReporter()`. `HighlightManager` and `MatchWatcher` both work this way.
