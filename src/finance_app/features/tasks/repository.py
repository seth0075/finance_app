
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from finance_app.core.database import SessionLocal
from finance_app.features.tasks.models import Task, Subtask


class TaskRepository:

    @staticmethod
    def _set_task_completed(task: Task, completed: bool) -> None:
        if task.completed != completed:
            task.completed = completed
            task.completed_at = (
                datetime.now(timezone.utc)
                if completed else None
            )

    @classmethod
    def _sync_task_from_subtasks(cls, task: Task) -> None:
        if task.subtasks:
            cls._set_task_completed(
                task, all(subtask.completed for subtask in task.subtasks)
            )

    def get_all(self) -> list[dict]:
        with SessionLocal() as session:
            statement = (
                select(Task)
                .options(selectinload(Task.subtasks))
                .order_by(
                    Task.completed.asc(),
                    Task.priority.desc(),
                    Task.created_at.asc()
                )
            )

            tasks = session.scalars(statement).all()

            return [
                {
                    "id": task.id,
                    "title": task.title,
                    "description": task.description or "",
                    "completed": task.completed,
                    "priority": task.priority,
                    "dueDate": (
                        task.due_date.isoformat()
                        if task.due_date else ""
                    ),
                    "subtasks": [
                        {
                            "id": subtask.id,
                            "title": subtask.title,
                            "completed": subtask.completed
                        }
                        for subtask in task.subtasks
                    ]
                }
                for task in tasks
            ]

    def add(
        self,
        title: str,
        description: str,
        due_date: date | None,
        priority: int
    ) -> None:
        with SessionLocal() as session:
            task = Task(
                title=title,
                description=description,
                due_date=due_date,
                priority=priority
            )

            session.add(task)
            session.commit()

    def update(
        self,
        task_id: str,
        title: str,
        description: str,
        due_date: date | None,
        priority: int
    ) -> None:
        with SessionLocal() as session:
            task = session.get(Task, task_id)

            if task is not None:
                task.title = title
                task.description = description
                task.due_date = due_date
                task.priority = priority

                session.commit()

    def set_completed(
        self,
        task_id: str,
        completed: bool
    ) -> None:
        with SessionLocal() as session:
            task = session.get(Task, task_id)

            if task is not None:
                self._set_task_completed(task, completed)
                for subtask in task.subtasks:
                    subtask.completed = completed
                session.commit()

    def delete(self, task_id: str) -> None:
        with SessionLocal() as session:
            task = session.get(Task, task_id)

            if task is not None:
                session.delete(task)
                session.commit()

    def add_subtask(
        self,
        task_id: str,
        title: str
    ) -> None:
        with SessionLocal() as session:
            task = session.get(Task, task_id)

            if task is not None:
                task.subtasks.append(
                    Subtask(title=title)
                )
                self._set_task_completed(task, False)
                session.commit()

    def set_subtask_completed(
        self,
        subtask_id: str,
        completed: bool
    ) -> None:
        with SessionLocal() as session:
            subtask = session.get(Subtask, subtask_id)

            if subtask is not None:
                subtask.completed = completed
                self._sync_task_from_subtasks(subtask.task)
                session.commit()

    def delete_subtask(self, subtask_id: str) -> None:
        with SessionLocal() as session:
            subtask = session.get(Subtask, subtask_id)

            if subtask is not None:
                task = subtask.task
                task.subtasks.remove(subtask)
                self._sync_task_from_subtasks(task)
                session.commit()
