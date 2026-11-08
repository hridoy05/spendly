# Plan: Step 1 — Database Setup

**Branch:** `feature/database-setup` (already created)
**Spec:** `.claude/specs/01-database-setup`
**Files to change:** `database/db.py`, `app.py`, `.gitignore` (swap `expense_tracker.db` → `spendly.db`), `CLAUDE.md` (update `expense_tracker.db` reference to `spendly.db`)
**Files to create:** none

---

## 1. Implement `database/db.py`

Replace the stub (currently 5 comment lines) with a full SQLite data layer. No new packages — `sqlite3` (stdlib) + `werkzeug.security` (already in venv).

### 1a. Imports and module constants
- `import sqlite3`
- `from werkzeug.security import generate_password_hash`
- `import datetime` (or `datetime.date.today()`) to compute the current month for seeding.
- Define a DB path constant, e.g. `DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'spendly.db')` (resolved to the project root, next to `app.py`). Use `pathlib` or `os.path.abspath` so it works regardless of the working directory.
- Define a `CATEGORIES` constant = the fixed list from spec §10:
  `["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]`.

### 1b. `get_db()`
- Open a connection to `DB_PATH` with `sqlite3.connect(DB_PATH)`.
- Set `conn.row_factory = sqlite3.Row` (dictionary-like access).
- Run `conn.execute("PRAGMA foreign_keys = ON")` **on every connection**.
- `return conn`.

### 1c. `init_db()`
- Use `sqlite3.connect(DB_PATH)` (respecting `get_db()` pattern) inside a `with` block on connection + context manager.
- Execute `CREATE TABLE IF NOT EXISTS` for both tables — safe to call repeatedly.
- **users**:
  - `id INTEGER PRIMARY KEY AUTOINCREMENT`
  - `name TEXT NOT NULL`
  - `email TEXT UNIQUE NOT NULL`
  - `password_hash TEXT NOT NULL`
  - `created_at TEXT DEFAULT (datetime('now'))`
- **expenses**:
  - `id INTEGER PRIMARY KEY AUTOINCREMENT`
  - `user_id INTEGER NOT NULL REFERENCES users(id)`
  - `amount REAL NOT NULL`
  - `category TEXT NOT NULL`
  - `date TEXT NOT NULL`  (YYYY-MM-DD)
  - `description TEXT`    (nullable)
  - `created_at TEXT DEFAULT (datetime('now'))`

### 1d. `seed_db()`
- **Idempotency guard first:** `SELECT COUNT(*) FROM users` — if `> 0`, `return` immediately (no duplicates on reruns).
- Insert **one demo user**:
  - name `Demo User`, email `demo@spendly.com`
  - password `demo123` → `generate_password_hash` before insert (never store plaintext). Capture the new user's rowid.
- Insert **8 sample expenses** sharing that `user_id`, each covering at least one of the fixed categories:
  - Mix of categories across `Food, Transport, Bills, Health, Entertainment, Shopping, Other`.
  - `date` values spread across the **current month** in `YYYY-MM-DD` format (build via `datetime.date.today()` and `.strftime`/`.isoformat()`).
  - `amount` as REAL; include one with a `NULL`/absent description and at least one with a description.
- Commit at the end (single transaction so a failure rolls back cleanly).

---

## 2. Wire up `app.py`

- Add imports from the db layer: `from database.db import get_db, init_db, seed_db`.
- At startup (guarded by the `if __name__ == "__main__":` block, before `app.run`), initialize inside an app context:
  ```python
  with app.app_context():
      init_db()
      seed_db()
  app.run(debug=True, port=5001)
  ```
- Leave all routes untouched (spec §3 — no new routes, placeholders unchanged).
- Keep `port=5001` (per CLAUDE.md convention).

---

## 3. Create supporting files

- `.claude/specs/01-database-setup` already exists (the spec). No new files required by the spec.
- The SQLite file (`spendly.db` / `expense_tracker.db`) is already gitignored, so it won't be committed. Note: `.gitignore` currently lists `expense_tracker.db` but the spec mentions `spendly.db` — **confirm the chosen filename and add it to `.gitignore` if it differs.**

---

## 4. Verification

Since `app.py` starting will `init_db()` + `seed_db()` on every run, verification is a manual/scripted smoke test:

1. Delete any existing `*.db` in the project root.
2. Run `venv/bin/python -c "from database.db import init_db, seed_db; from app import app; app.app_context().push(); init_db(); seed_db()"`.
   - Or simply start the server once: `venv/bin/python app.py` then stop it.
3. Confirm `spendly.db` exists in the project root.
4. Inspect schema via `sqlite3 spendly.db ".schema"` → both tables present with correct columns/constraints.
5. `SELECT * FROM users;` → exactly one `Demo User`, plaintext `demo` nowhere.
6. `SELECT COUNT(*) FROM expenses;` → `8`, all with that `user_id`, `date` strings in `YYYY-MM-DD`.
7. **Idempotency:** run init+seed a second time → counts stay `1` and `8`.
8. **Constraint checks:**
   - Inserting a duplicate email raises `sqlite3.IntegrityError`.
   - Inserting an expense with a nonexistent `user_id` raises `sqlite3.IntegrityError` (proves `PRAGMA foreign_keys` is working).

---

## 5. Definition of Done (from spec §14)

- [x/ ] Database file created on startup
- [x/ ] Both tables with correct schema + constraints
- [x/ ] Demo user with hashed password
- [x/ ] 8 sample expenses across categories
- [x/ ] No duplicate seed data on reruns
- [x/ ] App starts without errors
- [x/ ] Foreign key enforcement works
- [x/ ] All queries parameterized (no string-format SQL)

---

## 6. Open questions / risks

- **DB filename — DECIDED: use `spendly.db`** (chosen by user). This requires a `.gitignore` change: remove `expense_tracker.db`, add `spendly.db` (line 2). CLAUDE.md notes `expense_tracker.db` as the working name — update that reference to `spendly.db` during implementation.
- **Seed categories:** spec requires "at least one expense per category" — with 8 expenses and 7 categories, each will appear exactly once, except one category appears twice. Distribution is an implementation detail.
- Hashing in `seed_db()` means a fresh hash each run — harmless since we guard on the `users` count before inserting.