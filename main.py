import os
import sys


def main():
    # allow launching a simple Tk GUI for editing config or running monitor: `python main.py gui`
    # default: launch GUI when no arguments are provided
    if len(sys.argv) == 1 or (len(sys.argv) > 1 and sys.argv[1].lower() in ("gui", "config", "setup")):
        try:
            from gui import run_gui
            run_gui()
            return
        except Exception as e:
            print('Failed to launch GUI:', e)
            # fall through to normal run

    # default: run monitor directly (console mode)
    try:
        import threading
        import monitor
        # when frozen by PyInstaller, use _MEIPASS; otherwise use project dir
        if getattr(sys, 'frozen', False):
            path = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
        else:
            path = os.path.dirname(os.path.realpath(__file__))
        stop_event = threading.Event()
        monitor.run_monitor(path, stop_event)
    except Exception as e:
        print('Failed to start monitor:', e)


if __name__ == "__main__":
    main()






