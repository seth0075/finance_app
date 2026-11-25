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

    @Slot(str)
    def addTask(self, title):
        title = title.strip()

        if not title or len(title) > 500:
            return

        self._repository.add(title)
        self._refresh_tasks()

    @Slot(str, bool)
    def setCompleted(self, task_id, completed):
        self._repository.set_completed(task_id, completed)
        self._refresh_tasks()

    @Slot(str)
    def deleteTask(self, task_id):
        self._repository.delete(task_id)
        self._refresh_tasks()
