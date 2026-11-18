"""Запуск графічного інтерфейсу."""

import sys

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from .. import APP_NAME
from ..config import load_all
from ..i18n import set_language, system_language
from .main_window import MainWindow, app_icon, app_stylesheet
from .theme import Theme


def main():
    if sys.platform == "win32":
        try:      # власна іконка на панелі завдань, а не значок Python
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("obdstudio.app")
        except Exception:
            pass
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setWindowIcon(app_icon())
    app.setFont(QFont("Segoe UI", 10))
    timing, settings = load_all()
    Theme.set(settings.theme)
    set_language(settings.language or system_language())   # порожньо — за мовою Windows
    app.setStyleSheet(app_stylesheet())
    win = MainWindow(timing, settings)
    win.show()
    if "--self-test" in sys.argv:    # перевірка зібраного .exe: вікно будується й одразу закривається
        for key in win.pages:
            win.navigate(key)
            app.processEvents()
        ok = not win.grab().isNull() and not app_icon().isNull()
        win.close()
        return 0 if ok else 1
    return app.exec()
