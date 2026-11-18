import importlib.util
import os
from pathlib import Path

import pytest

DRAFT = Path(__file__).resolve().parent.parent / "original" / "lancer_obd_draft.py"


@pytest.fixture(scope="session")
def draft():
    """Оригінальний чернетковий скрипт — для перевірки, що логіку перенесено без змін."""
    spec = importlib.util.spec_from_file_location("lancer_obd_draft", DRAFT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def qapp():
    """Один QApplication на всі тести інтерфейсу (QCoreApplication не підходить для віджетів)."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    widgets = pytest.importorskip("PySide6.QtWidgets")
    return widgets.QApplication.instance() or widgets.QApplication([])
