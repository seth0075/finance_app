
from datetime import date, timedelta

from PySide6.QtCore import QObject, Signal, Slot, Property

from finance_app.features.tasks.repository import TaskRepository


class TaskViewModel(QObject):

    tasksChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self._repository = TaskRepository()
        self._tasks = []

        self._refresh_tasks()

    def _refresh_tasks(self):
        self._tasks = self._repository.get_all()
        self.tasksChanged.emit()

    @Property("QVariantList", notify=tasksChanged)
    def tasks(self):
        return self._tasks

    @Slot(result=str)
    def today(self):
        return date.today().isoformat()

    @Slot(str, result="QVariantMap")
    def dateRange(self, period):
        today = date.today()

        if period == "Week":
            start = today - timedelta(days=today.weekday())
            end = start + timedelta(days=6)

        elif period == "Month":
            start = today.replace(day=1)

            next_month = (
                start + timedelta(days=32)
            ).replace(day=1)

            end = next_month - timedelta(days=1)

        else:
            start = today
            end = today

        return {
            "start": start.isoformat(),
            "end": end.isoformat()
        }

    @Slot(str, str, str, int, result=bool)
    def addTask(
        self,
        title,
        description,
        due_date,
        priority
    ):
        title = title.strip()

        if not title or len(title) > 500:
            return False

        if priority not in (1, 2, 3):
            return False

        try:
            parsed_date = (
                date.fromisoformat(due_date)
                if due_date else None
            )
        except ValueError:
            return False

        self._repository.add(
            title,
            description,
            parsed_date,
            priority
        )

        self._refresh_tasks()
        return True

    @Slot(str, str, str, str, int, result=bool)
    def updateTask(
        self,
        task_id,
        title,
        description,
        due_date,
        priority
    ):
        title = title.strip()

        if not title or len(title) > 500:
            return False

        if priority not in (1, 2, 3):
            return False

        try:
            parsed_date = (
                date.fromisoformat(due_date)
                if due_date else None
            )
        except ValueError:
            return False

        self._repository.update(
            task_id,
            title,
            description,
            parsed_date,
            priority
        )

        self._refresh_tasks()
        return True

    @Slot(str, bool)
    def setCompleted(self, task_id, completed):
        self._repository.set_completed(
            task_id,
            completed
        )

        self._refresh_tasks()

    @Slot(str)
    def deleteTask(self, task_id):
        self._repository.delete(task_id)
        self._refresh_tasks()

    @Slot(str, str)
    def addSubtask(self, task_id, title):
        title = title.strip()

        if not title or len(title) > 500:
            return

        self._repository.add_subtask(task_id, title)
        self._refresh_tasks()

    @Slot(str, bool)
    def setSubtaskCompleted(self, subtask_id, completed):
        self._repository.set_subtask_completed(
            subtask_id,
            completed
        )

        self._refresh_tasks()

    @Slot(str)
    def deleteSubtask(self, subtask_id):
        self._repository.delete_subtask(subtask_id)
        self._refresh_tasks()
