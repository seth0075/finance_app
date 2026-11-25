from pathlib import Path

from PySide6.QtCore import QObject, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine


def test_main_qml_loads(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    _app = QGuiApplication.instance() or QGuiApplication([])
    engine = QQmlApplicationEngine()
    warnings = []
    engine.warnings.connect(
        lambda errors: warnings.extend(error.toString() for error in errors)
    )
    task_viewmodel = QObject()
    calendar_viewmodel = QObject()
    engine.setInitialProperties({
        "taskViewModel": task_viewmodel,
        "calendarViewModel": calendar_viewmodel,
    })
    qml_file = Path(__file__).parents[2] / "src" / "finance_app" / "ui" / "Main.qml"

    engine.load(QUrl.fromLocalFile(str(qml_file)))

    assert engine.rootObjects(), "\n".join(warnings)
