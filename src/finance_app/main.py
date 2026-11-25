import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from finance_app.core.database import initialize_database
from finance_app.features.calendar.viewmodel import CalendarViewModel
from finance_app.features.tasks.viewmodel import TaskViewModel


def main():
    app = QGuiApplication(sys.argv)

    initialize_database()

    engine = QQmlApplicationEngine()

    task_viewmodel = TaskViewModel()
    calendar_viewmodel = CalendarViewModel()

    engine.setInitialProperties({
        "taskViewModel": task_viewmodel,
        "calendarViewModel": calendar_viewmodel,
    })

    qml_file = Path(__file__).parent / "ui" / "Main.qml"

    engine.load(QUrl.fromLocalFile(str(qml_file)))

    if not engine.rootObjects():
        sys.exit(1)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
