from functools import singledispatch

from rich.pretty import Pretty
from rich.console import RenderableType, ConsoleRenderable, RichCast


@singledispatch
def render(obj) -> RenderableType:
    """Default view for an object. Renderers register concrete types onto this."""
    if isinstance(obj, (ConsoleRenderable, RichCast)):
        return obj
    return Pretty(obj)


@render.register
def _render_str(obj: str) -> RenderableType:
    return obj
