set windows-shell := ["powershell.exe", "-NoLogo", "-Command"]

run:
    uv run main.py

lcu:
    uv run lcu_main.py

riot:
    uv run riot_main.py
