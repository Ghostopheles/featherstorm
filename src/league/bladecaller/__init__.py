def launch_ui():
    try:
        from league.bladecaller.ui.app import run
    except ImportError:
        raise SystemExit("Failed to import the UI module. Please ensure that the optional `ui` dependencies are installed.")
    return run()
