from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from finance_app.core.database import Base
from finance_app.features.tasks import repository
from finance_app.features.tasks.models import Task


def make_repository(monkeypatch):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    monkeypatch.setattr(repository, "SessionLocal", sessions)
    return repository.TaskRepository(), sessions


def test_subtasks_and_parent_completion_stay_in_sync(monkeypatch):
    repo, sessions = make_repository(monkeypatch)
    repo.add("Task", "", None, 2)
    task_id = repo.get_all()[0]["id"]
    repo.add_subtask(task_id, "First")
    repo.add_subtask(task_id, "Second")
    first, second = repo.get_all()[0]["subtasks"]

    repo.set_subtask_completed(first["id"], True)
    assert repo.get_all()[0]["completed"] is False
    repo.set_subtask_completed(second["id"], True)
    assert repo.get_all()[0]["completed"] is True
    with sessions() as session:
        assert session.get(Task, task_id).completed_at is not None

    repo.set_subtask_completed(first["id"], False)
    assert repo.get_all()[0]["completed"] is False
    with sessions() as session:
        assert session.get(Task, task_id).completed_at is None

    repo.set_completed(task_id, True)
    assert all(subtask["completed"] for subtask in repo.get_all()[0]["subtasks"])
    repo.set_completed(task_id, False)
    assert not any(subtask["completed"] for subtask in repo.get_all()[0]["subtasks"])

    repo.set_completed(task_id, True)
    repo.add_subtask(task_id, "Third")
    assert repo.get_all()[0]["completed"] is False


def test_deletion_and_priority_order(monkeypatch):
    repo, _ = make_repository(monkeypatch)
    repo.add("Low", "", None, 1)
    repo.add("High", "", None, 3)
    repo.add("Medium", "", None, 2)
    tasks = repo.get_all()
    assert [task["title"] for task in tasks] == ["High", "Medium", "Low"]

    high_id = tasks[0]["id"]
    repo.add_subtask(high_id, "Done")
    repo.add_subtask(high_id, "Unfinished")
    done, unfinished = repo.get_all()[0]["subtasks"]
    repo.set_subtask_completed(done["id"], True)
    repo.delete_subtask(unfinished["id"])
    tasks = repo.get_all()
    assert [task["title"] for task in tasks] == ["Medium", "Low", "High"]
    assert tasks[-1]["completed"] is True

    repo.delete_subtask(done["id"])
    assert repo.get_all()[-1]["completed"] is True
    repo.set_completed(high_id, False)
    assert repo.get_all()[0]["title"] == "High"
