# Tasks

Tasks are listed with unfinished tasks first, then by priority (high to low).
Use **Subtasks** on a task to add, complete, or remove its subtasks.
Completing or reopening a task updates all its subtasks. A task with subtasks
is completed when all its subtasks are complete; adding or reopening an
unfinished subtask reopens the task. Removing the last subtask leaves the
task's completion status unchanged.

# Calendar

The Calendar page displays tasks with due dates alongside independent events.
Switch between day, week, and month views, select a date to see its entries,
and choose an event to edit or delete it. Undated tasks do not appear.

Use **Calendars** to create, rename, recolor, and delete event calendars.
The Tasks calendar can be recolored but not renamed or deleted. At least one
event calendar must remain. Deleting a calendar deletes its events; an
individual occurrence moved into that calendar is removed without deleting
the rest of its series. A color picker and hex input allow custom colors.

Events support all-day or timed schedules, multiple days, and daily, weekly,
monthly, or yearly repeats with an optional inclusive end date. Monthly and
yearly events on dates missing from a month use its last day. Choose whether
to edit or delete one occurrence or the whole series. Changing a series'
start date, repeat frequency, or repeat end requires confirmation to discard
individual occurrence changes. Dates and times are local; timed end times are
exclusive, while an all-day event includes its end date. Times use 24-hour
`HH:MM` format.

Before starting the app with an existing Alembic-managed database, run
`uv run python -m alembic upgrade head`. Existing events move to the Personal
calendar, whose color replaces their old individual colors.