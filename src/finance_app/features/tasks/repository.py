from sqlalchemy import select

from finance_app.core.database import SessionLocal
from finance_app.features.tasks.models import Task


class TaskRepository:

    def get_all(self) -> list[dict]:
        with SessionLocal() as session:
            statement = select(Task).order_by(Task.created_at)

            tasks = session.scalars(statement).all()

            return [
                {
                    "id": task.id,
                    "title": task.title,
                    "completed": task.completed
                }
                for task in tasks
            ]

    def add(self, title: str) -> None:
        with SessionLocal() as session:
            task = Task(title=title)

            session.add(task)
            session.commit()

    def set_completed(
        self,
        task_id: str,
        completed: bool
    ) -> None:
        with SessionLocal() as session:
            task = session.get(Task, task_id)

            if task is not None:
                task.completed = completed
                session.commit()

    def delete(self, task_id: str) -> None:
        with SessionLocal() as session:
            task = session.get(Task, task_id)

            if task is not None:
                session.delete(task)
                session.commit()
