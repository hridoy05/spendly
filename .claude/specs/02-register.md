# Spec: Register

## Overview
This step wires up Spendly's user registration. Today `/register` only
`render_template("register.html")` on GET; the submitted form drops the user's
input and creates no account. This feature makes `/register` handle POST — it
validates the submitted `name`, `email`, and `password`, hashes the password,
and inserts a new row into the `users` table (built in Step 1). On success the
new user is automatically logged in via a signed session cookie and redirected
to the dashboard, so a fresh account leads straight into the app. It is the
second milestone in Spendly's staged roadmap: the data layer (Step 1) now pays
off with its first real write path, and it sets up the session machinery that
Step 3 (login/logout) will depend on.

## Depends on
- **Step 1 — Database setup**: the `users` table must exist (created by
  `init_db()`) with `id`, `name`, `email` (UNIQUE), `password_hash`, and
  `created_at`. This feature inserts into that table and must NOT change its
  schema.

## Routes
- `POST /register` — handle the sign-up form: validate input, hash the
  password, insert the user, open a session, and redirect to the dashboard
  (or `/` if no dashboard route exists yet). — public
- `GET /register` — already exists (`render_template("register.html")`); keep
  it, but add a check: if a user is already logged in, redirect them away
  (e.g. to the dashboard) instead of showing the form. — public

No other new routes. `/login` (Step 3) is out of scope.

## Database changes
No schema changes. The `users` table already exists from Step 1
(`CREATE TABLE IF NOT EXISTS users (...)`).

Behavior relied on (already in `database/db.py`):
- `get_db()` returns a connection with `row_factory = sqlite3.Row` and
  `PRAGMA foreign_keys = ON`.
- `email` is `UNIQUE NOT NULL` — a duplicate-email INSERT must raise
  `sqlite3.IntegrityError`, which the route must catch and surface as a
  friendly "email already registered" error.
- Password storage uses `generate_password_hash` (already used by
  `seed_db()`), so new registrations must use the same hashing scheme for
  consistency with `seed_db()`'s `demo@spendly.com` user.

## Templates
- **Create:** `templates/dashboard.html` — a minimal logged-in landing page
  (private shell) that the register route can redirect to after a successful
  sign-up. It extends `base.html`, greets the user by name, and is the target
  that Step 3+ will grow into a real dashboard. If the project prefers
  redirecting to `/` for now, this template is a placeholder target so the
  redirect is meaningful.
- **Modify:** `templates/register.html` — the form already posts to
  `/register` with `name`, `email`, `password` and renders an optional
  `{{ error }}`. Keep its structure and field names verbatim (they match the
  route contract). Changes are limited to ensuring it renders correctly after
  the route is implemented and any flash/error display is wired; do not rename
  fields or the route action.
- **Modify:** `templates/base.html` — swap the navbar's "Sign in" / "Get
  started" pair for a logged-in state once a session exists (e.g. show the
  user's name and a Sign out link). This is the placeholder route's first
  consumer of session state. If kept minimal for this step, note it for Step 3.

## Files to change
- `app.py` — implement the `register` route: handle POST, validate, hash,
  insert, start a session, and define the redirect target. Add imports
  (`request`, `redirect`, `url_for`, `session`, `flash`,
  `sqlite3`/`werkzeug` hash as needed) and a `app.secret_key` so signed
  session cookies work.

## Files to create
- `templates/dashboard.html` — minimal logged-in landing target (see above).

## New dependencies
No new pip packages. Use:
- `sqlite3` (standard library)
- `werkzeug.security` (already vendored; `generate_password_hash`,
  `check_password_hash`)
- Flask's built-in `session` (signed cookie) — requires setting
  `app.secret_key`.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` via `get_db()`.
- Parameterised queries only (`?` placeholders); never string-format or
  f-string values into SQL.
- Passwords hashed with `werkzeug.security.generate_password_hash`; never
  store plaintext. Use the same hashing scheme as `seed_db()`.
- Set a `app.secret_key` (e.g. via `os.environ.get("SECRET_KEY", ...)` with a
  dev fallback) for the signed session cookie.
- Use CSS variables (`var(--...)`) from `style.css` — never hardcode hex
  values in new styles.
- All templates extend `base.html`.
- Catch `sqlite3.IntegrityError` on duplicate email and re-render the register
  form with a friendly `{{ error }}` message; check password length (min. 8 —
  matches the form's placeholder) server-side.
- Keep the `register` function name — templates use `url_for('register')`.
- Preserve mockup-driven styling; do not replace with a component framework.

## Definition of done
- [ ] `GET /register` still renders the sign-up form without error.
- [ ] Submitting a valid `name`/`email`/`password` (min. 8 chars) creates a row
      in `users` with a `password_hash` (not plaintext).
- [ ] After a successful sign-up the app sets a session cookie and redirects,
      and the dashboard shows the new user's name.
- [ ] Re-submitting the same email shows a friendly "already registered" error
      and does NOT create a second user (UNIQUE constraint respected).
- [ ] A password shorter than 8 characters is rejected with an error and no row
      is inserted.
- [ ] The new user's password verifies against its stored hash with
      `check_password_hash`.
- [ ] An empty/`None` password_hash has never been stored; plaintext is never
      logged or returned.
- [ ] App starts without errors on port 5001 (`python app.py`) with the new route.
- [ ] Navbar reflects the logged-in state (shows the user / sign-out instead of
      the Sign in CTA).
- [ ] All new SQL uses `?` placeholders; no f-string/`.format()` SQL.
- [ ] No CSS hex values hardcoded in any new styles — only `var(--...)`.