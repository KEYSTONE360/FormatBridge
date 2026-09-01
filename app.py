import ctypes
import os

from formatbridge.gui import run

if __name__ == "__main__":
    if os.name == "nt":
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("FormatBridge.Local.1")
        except Exception:
            pass
    run()
