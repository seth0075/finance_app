import os
import subprocess
import sys


def test_fresh_database_registers_google_cache_models(tmp_path):
    env = os.environ.copy()
    env["LOCALAPPDATA"] = str(tmp_path)
    script = """
from sqlalchemy import inspect
from finance_app.core.database import engine, initialize_database

initialize_database()
tables = set(inspect(engine).get_table_names())
assert {"google_calendars", "google_events", "google_cache"} <= tables
"""
    subprocess.run(
        [sys.executable, "-c", script],
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
