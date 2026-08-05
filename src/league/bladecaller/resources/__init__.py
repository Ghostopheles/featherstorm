from importlib.resources import files

def load_stylesheet() -> str:
    return files("league.bladecaller.resources").joinpath("app.qss").read_text(encoding="utf-8")
