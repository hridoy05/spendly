# Spec: Login

## Overview
This step implements Spendly's user login. Today `/login` only
`render_template("login.html")` on GET — the submitted form's POST is never
handled, so a user with an existing account cannot sign in (Step 2 only covers
registering a new account, which auto-logs-in). This feature makes `/login`
handle POST: it looks up the submitted `email` in the `users` table, verifies
the password against the stored hash with `check_password_hash`, and on success
starts the signed session cookie (`session["user_id"]`, `session["user_name"]`)
and redirects to the dashboard. On failure it re-renders the same form with a
friendly error and a 401-appropriate message, never revealing which field was
wrong. It also redirects already-logged-in visitors away from the login page.
This is the logical completion of the auth pair (register + login), closing the
loop so users can sign back into the account they created in Step 2.

## Depends on
- **Step 1 — Database setup**: the `users` table must exist (created by
  `init_db()`) with `id`, `name`, `email` (UNIQUE), and `password_hash`.
- **Step 2 — Register**: establishes the session pattern
  (`session["user_id"]` + `session["user_name"]`, `session.clear()` on success,
  `app.secret_key`) and the hashing scheme (`generate_password_hash`). Login
  reuses both — it must use `check_password_hash` against the same hashes that
  registration (and `seed_db()`'s `demo@spendly.com` user) create, and set the
  same session keys so `base.html`/`dashboard.html`/`profile.html` render the
  same signed-in state.

## Routes
- `POST /login` — handle the sign-in form: look up `email`, verify the password
  with `check_password_hash`, open a session, and redirect to the dashboard. On
  mismatch: re-render `login.html` with a generic error. — public
- `GET /login` — already exists (`render_template("login.html")`); keep it, but
  add a check: if a user is already logged in, redirect them to the dashboard
  instead of showing the sign-in form. — public

No other new routes. `/logout` (Step 3) is out of scope — it remains the
placeholder that `base.html`'s "Sign out" link points at.

## Database changes
No schema changes. The `users` table already exists from Step 1
(`CREATE TABLE IF NOT EXISTS users (...)`).

Behavior relied on (already in `database/db.py`):
- `get_db()` returns a connection with `row_factory = sqlite3.Row` and
  `PRAGMA foreign_keys = ON`.
- `email` is `NOT NULL` and `UNIQUE` — lookups by email return at most one row.
- Password storage uses `generate_password_hash` (in `seed_db()` and the
  register route), so login must match against those hashes with
  `check_password_hash`.

## Templates
- **Modify:** `templates/login.html` — keep its structure and field names
  verbatim (the form already posts to `/login` with `name="email"` and
  `name="password"` and renders an optional `{{ error }}`). No field renames or
  action changes. The template is already correct; minimal/no changes expected
  beyond the route returning the `error` context it already reads.
- **Create:** none.

## Files to change
- `app.py` — implement the `login` route: add the GET redirect-guard, handle
  POST (query the user by email, verify with `check_password_hash`, set the
  session, redirect to dashboard or re-render with an error). Add
  `check_password_hash` to the existing `from werkzeug.security import
  generate_password_hash` import (and `sqlite3` for any row handling, already
  imported).

## Files to create
None.

## New dependencies
No new pip packages. Use:
- `werkzeug.security.check_password_hash` (already vendored; `generate_password_hash`
  is already imported).
- `sqlite3` (standard library) via `get_db()`.
- Flask's built-in `session` (signed cookie) — already configured with
  `app.secret_key` from Step 2.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` via `get_db()`.
- Parameterised queries only (`?` placeholders); never string-format or
  f-string values into SQL. The WHERE clause matches on the submitted `email`.
- Passwords hashed with `werkzeug.security` — login verifies with
  `check_password_hash`; never store, compare, or return plaintext.
- On a failed login (wrong email OR wrong password) show ONE generic error
  (e.g. "Invalid email or password.") so the app doesn't leak which credential
  was incorrect.
- Use CSS variables (`var(--...)`) from `style.css` — never hardcode hex
  values in new styles.
- All templates extend `base.html`.
- Keep the `login` function name and `/login` path — templates and the
  redirect-guards use `url_for('login')`.
- If already logged in, redirect away from `/login` (the dashboard).
- Close every `get_db()` connection (`conn.close()` or a `with` block) after use.
- Preserve mockup-driven styling; do not replace with a component framework.

## Definition of done
- [ ] `GET /login` while logged out renders the sign-in form without error.
- [ ] `GET /login` while already logged in redirects to the dashboard (never
      shows the form).
- [ ] Submitting a valid `email`/`password` for an existing user sets the
      session and redirects to the dashboard, which greets the user by name.
- [ ] The seeded `demo@spendly.com` user can sign in with its known password.
- [ ] Submitting a wrong password for an existing email shows the generic
      error and does NOT log the user in or redirect.
- [ ] Submitting an unknown email shows the same generic error (no account
      enumeration).
- [ ] No plaintext password is ever stored, logged, or returned; the password
      verifies only via `check_password_hash`.
- [ ] All new SQL uses `?` placeholders; no f-string/`.format()` SQL.
- [ ] No CSS hex values hardcoded in any new styles — only `var(--...)`.
- [ ] App starts without errors on port 5001 (`python app.py`) with the new
      route.