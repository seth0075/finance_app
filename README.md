# Project layout

- `src/finance_app/features/`: local tasks, calendar, and finance logic.
- `src/finance_app/integrations/`: Google Calendar and Plaid clients, models,
  and view models.
- `src/finance_app/ui/components/`: shared controls plus feature-specific
  component folders; pages compose these components.
- `tests/unit/`, `tests/integration/`, and `tests/acceptance/`: focused logic,
  database/integration, and offscreen UI tests, respectively.

Run the test suite with `uv run python -m pytest`.

# Tasks

Tasks are listed with unfinished tasks first, then by priority (high to low).
Use **Subtasks** on a task to add, complete, or remove its subtasks.
Completing or reopening a task updates all its subtasks. A task with subtasks
is completed when all its subtasks are complete; adding or reopening an
unfinished subtask reopens the task. Removing the last subtask leaves the
task's completion status unchanged.

# Finances

The Finances page uses manually entered USD amounts. Add bank/cash and credit
card accounts with an opening date and balance; a credit card's opening balance
is the amount owed, and its available credit is its limit minus that balance.
The opening balance is the balance at the start of the opening date. Earlier
transactions are allowed and reconstruct balances backwards from that snapshot;
transactions on and after the opening date are applied forwards. Balances
before the first recorded transaction or opening date are shown as not open.
Changing an opening date or balance recalculates history.

Record income, expenses, and transfers, choosing an account for each transaction.
Transfers, including credit-card
payments, change account balances but do not count as income or expenses.
Choose a category or create one while recording an income or expense.
Select an account or transaction to edit it; accounts with transactions cannot
be deleted until those transactions are removed.

Switch between Day, Month, and Year to browse recorded transactions and
income/expense totals. Net balance and available credit are as of the selected
period's end; net balance is bank/cash balances minus credit-card debt. Charts
show expense categories, income versus expenses, and cumulative income and
expenses alongside net balance. The Day chart covers the selected day and six
preceding days; Month and Year charts use daily and monthly buckets.
For a wholly future Day, Month, or Year, expense charts include both recorded
future expenses and active subscription estimates. The Day chart includes
estimates for future dates in its preceding seven-day window as well. These
amounts can overlap, because estimates are not reconciled against recorded
transactions. Once the selected period begins, its charts show recorded
transactions only. Income and the net-balance line always use recorded data.

Use **Assign categories** in Transactions to select income and expense entries
in the displayed period and assign them together. Transfers are excluded.
Choose an existing category or create one, and use **Choose color** to pick its
chart color. Save a new category or changed color before assigning it; category
colors apply across periods in the expense chart. Saving a category or color
takes effect immediately, even if the dialog is cancelled.

Run `uv run python -m alembic upgrade head` before starting an existing
Alembic-managed database.

Mark an expense as a monthly or yearly subscription. Active subscriptions show
estimated future charges in the selected period, using the last day of shorter
months where necessary. Estimates are separate from recorded transactions and
do not affect recorded summary totals or balances; they are not automatically
reconciled with manually entered charges. Select a subscription to edit it or mark it inactive.
Deleting its source transaction also deletes the subscription.

Use **Delete all transactions** in the Transactions section to permanently
remove transactions from every account and period, including transfers and
subscriptions. Accounts, opening balances, categories, and Plaid connections
are kept. The action also clears Plaid import history, allowing transactions
to be reviewed and imported again; it does not automatically re-import them.

## Import transactions from CSV

Create the destination account first, then choose **Import CSV** on Finances.
Select a local file, its delimiter, and the account; check the suggested column
mapping, date format, and direction before previewing. Files must be UTF-8
(with or without a BOM), have a header, and contain at most 10,000 rows and
5 MB. Comma, semicolon, and tab delimiters are supported. Dates can be
`YYYY-MM-DD`, `MM/DD/YYYY`, `MM/DD/YY`, or `DD/MM/YYYY`; select the format
explicitly when dates are ambiguous.

Use signed amounts, a type column with configurable debit and credit values,
or separate debit and credit amount columns. Amount signs are ignored when
using a type column or separate amount columns. Imported debits are expenses
and credits are income; transfers are not inferred. Optionally map a category
column; otherwise rows use Uncategorized. New categories are created as needed.
Account number and balance columns are not imported, and a recognized Account
Number column containing multiple accounts is rejected. Opening dates and
balances remain unchanged. Transactions before the opening date reconstruct
earlier balances; transactions on or after it change later balances.

Review the preview before choosing **Import selected**. Invalid rows cannot be
selected. Possible duplicates, matched by account, date, description, direction,
and amount against existing transactions or earlier rows in the file, are
unchecked by default. This is a heuristic: identical legitimate transactions
can occur, so inspect warnings and explicitly select any you want to import.
**Select all valid** includes possible duplicates, but not invalid rows.
The selected rows are saved together, and no data is imported until confirmed.

## Connect bank accounts with Plaid

Plaid is a third-party service. When you link a bank, Plaid receives the
financial data you authorize. Production access requires Plaid approval and
may incur charges; review [Plaid pricing](https://plaid.com/pricing/) and its
[OAuth requirements](https://plaid.com/docs/link/oauth/). Sandbox uses
simulated institutions and data, not your actual Capital One accounts.

1. In the [Plaid dashboard](https://dashboard.plaid.com/), obtain your client
   ID and the secret for the environment you want to use. Enable the
   Transactions product; for real accounts, complete Plaid's Production and
   institution/OAuth requirements. Do not put secrets in source code or share
   them in chat.
2. In the app, open **Settings → Connect Plaid**. Select **Sandbox** first and
   enter the client ID and Sandbox secret. Choose **Open Plaid Link** and
   complete the simulated sign-in in your browser. Return to the app and
   choose **Finish linking**, then **Refresh**.
3. After testing, choose **Disconnect** in Settings to remove the Sandbox
   item. Connect again using **Production** and the Production secret. Select
   Capital One in Plaid Link, sign in on the bank's site, authorize the
   accounts, and return to the app to choose **Finish linking** and **Refresh**.
   The bank may require separate links for accounts it does not offer together;
   this app supports one linked Plaid item at a time.
4. On **Finances**, linked accounts and their Plaid-reported balances appear
   separately from local account balances. Plaid's balances can be cached and
   may not be current. Choose **Import transactions**, select a linked account,
   then select a matching local account or use **+ New local account** to create
   one. The new account is saved immediately, even if you cancel the import.
   Its Plaid current balance is shown for reference, and its credit limit is
   prefilled when available. Enter an opening date and start-of-day balance, or
   choose to use Plaid's current balance as tomorrow's opening snapshot.
   This is approximate: the balance may be cached or include pending activity.
   Transactions dated before tomorrow reconstruct history; later transactions
   change the balance. Without earlier transactions, the account appears not open
   until tomorrow. Review each row and choose **Import selected**. No bank
   transactions are imported until you confirm. Use the
   Day/Month/Year controls to navigate to the dates of older imported transactions.

Plaid is asked for up to 730 days of history; actual availability varies and
history may take time to load; the refresh status indicates whether initial or
historical data is ready. Refresh again later if it is incomplete. Pending
and non-USD transactions cannot be imported. Already-imported Plaid transaction
IDs are excluded, and possible matches with local transactions are unchecked
for review. Matching is heuristic and can miss duplicates or flag legitimate
identical transactions. Transfers are not inferred. Imported records are local
snapshots; later changes or removals at the bank do not automatically update
them. Review and edit them manually if needed.

Importing does not change local opening balances. Since transactions on or
after a local account's opening date affect its calculated balance, review that
snapshot to avoid double counting. Plaid balances are not added to local totals.
The client ID, environment secret, and access token are stored in the system
credential store; imported transactions and source IDs are stored unencrypted
in the local database. Disconnecting removes the Plaid item and its access
token but retains imported transactions and the Plaid client credentials.
If linking is cancelled after completing Plaid Link, or credential storage
fails, check the Plaid dashboard for an unwanted item and remove it to avoid
possible ongoing charges. If Plaid reports that the bank login is required
again, disconnect the item in Settings and link it again; review duplicates
because Plaid's transaction IDs may change.

# Calendar

The Calendar page displays tasks with due dates alongside independent events.
Switch between day, week, and month views, select a date to see its entries,
and choose an event to edit or delete it. Undated tasks do not appear.

Use **Calendars** to create, rename, recolor, and delete event calendars.
The Tasks calendar can be recolored but not renamed or deleted. At least one
event calendar must remain. Deleting a calendar deletes its events; an
individual occurrence moved into that calendar is removed without deleting
the rest of its series. Use the circles beside calendars to show or hide them;
the choice is saved, including for Tasks and Google calendars. Hidden items
remain intact and can be shown again. A color picker and hex input allow custom colors.

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

# Google Calendar

The Settings page can connect one Google account. Google calendars and events
are read-only; edit them in Google Calendar. A successful refresh replaces the
local cache covering events from 365 days before through 365 days after the refresh.
Recurring Google events are expanded within that window, including exceptions.
The app refreshes on startup and provides a **Refresh** button in Settings.
If a refresh fails, the last successful cache remains available offline. The
Calendar page shows the cache coverage, so dates outside it may be incomplete.

To connect:

1. In [Google Cloud Console](https://console.cloud.google.com/), create or
   select a project and enable the Google Calendar API.
2. Configure the OAuth consent screen (Google Auth Platform). For an external
   app in testing, add your Google account as a test user. Google may show an
   unverified-app warning for a personal testing project.
3. Under **Clients**, create an OAuth client of type **Desktop app** and
   download its JSON file. Keep this file private and do not commit it.
4. Open **Settings**, choose **Connect Google Calendar**, select that JSON
   file, and complete the browser sign-in and read-only consent. The browser
   redirects to a temporary loopback address on your computer.

OAuth credentials are stored in the system credential store (Windows
Credential Manager), not in the application database. Cached event titles and
times are stored in the local database and are not encrypted by the app.
An external testing OAuth app may issue refresh tokens that expire after seven
days; reconnect if Google requires authorization again. Disconnecting removes
the local credentials and cached Google data, but does not revoke the Google
grant. To revoke access, also remove the app in your Google Account's
third-party connections.