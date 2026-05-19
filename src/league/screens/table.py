from pynput import keyboard

from rich.align import Align
from rich.table import Table
from rich.layout import Layout

from league.console import print, console

OPTIONS = {
    "uwu",
    "owo"
}

g_selected = 0

def on_press(key):
    global g_selected
    if key == keyboard.Key.up:
        g_selected = (g_selected - 1) % len(OPTIONS)
    elif key == keyboard.Key.down:
        g_selected = (g_selected + 1) % len(OPTIONS)
    elif key == keyboard.Key.enter:
        console.clear()
        print(f"You selected: {OPTIONS[g_selected]}")
        return False  # Stop listener


with console.screen() as screen:
    with keyboard.Listener(on_press=on_press) as listener:
        while listener.running:
            table = Table.grid(expand=True)
            table.add_column("Text")

            for i, option in enumerate(OPTIONS):
                if i == g_selected:
                    table.add_row(f"> {option}")
                else:
                    table.add_row(f"  {option}")

            screen.update(table)
