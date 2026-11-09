# Spec: Profile Page

## Overview
This step implements Spendly's account profile page. Today `/profile` is a
placeholder that returns a plain string (`"Profile page — coming in Step 4"`).
This feature turns it into a real, logged-in-only route that looks up the
current user's row and renders their account details (name, email, and account
creation date) in a `templates/profile.html` page that extends the shared
`base.html` shell. It is the third milestone in the staged roadmap: it consumes
the `users` schema built in Step 1 and the session cookie machinery introduced
in Step 2, giving a signed-in user a private place to see the account they
registered. It is read-only — no editing, password change, or deletion yet;
those can come in later steps.

## Depends on
- **Step 1 — Database setup**: the `users` table must exist (created by
  `init_db()`) with `id`, `name`, `email`, `password_hash`, and `created_at`.
  This feature reads from that table and must NOT change its schema.
- **Step 2 — Register**: the signed session cookie (`session["user_id"]` and
  `session["user_name"]`) must exist so the profile can identify and greet the
  current user. Registering initiates that session and `base.html` already
  renders the logged-in navbar state that the profile page sits behind.

## Routes
- `GET /profile` — replace the placeholder. Look up the logged-in user's row,
  guard the route (redirect to `/login` if no `session["user_id"]`), and render
  `profile.html` with the user's details. — logged-in

No other new routes.

## Database changes
No schema changes. The `users` table already exists from Step 1.

Behavior relied on (already in `database/db.py`):
- `get_db()` returns a connection with `row_factory = sqlite3.Row`, so a user
  row can be fetched and read with `row["name"]`, `row["email"]`,
  `row["created_at"]`.
- The `users` table stores `email` and a `created_at` default of
  `datetime('now')`, both of which the profile page displays.
- No new columns (e.g. no avatar, bio, or address) are added in this step —
  keep the scope read-only against the existing schema.

## Templates
- **Create:** `templates/profile.html` — a dedicated profile page that extends
  `base.html`. It renders the user's `name`, `email`, and `created_at` in a
  profile card, styled with the existing `style.css` design tokens (shared
  `.auth-card`/container styles or a small profile-specific section). It
  should feel consistent with `dashboard.html` — same paper background, serif
  display heading, and neutral ink/body type.
- **Modify:** none required. `base.html` already renders the logged-in navbar
  with the user's name and a Sign out link (from Step 2), so the profile needs
  no shell changes. If a "Profile" link is desired, it can be added to the
  logged-in navbar branch in `base.html` via `url_for('profile')`.

## Files to change
- `app.py` — replace the placeholder `profile` route body: guard on
  `session["user_id"]`, `SELECT` the user row, and `render_template`.

## Files to create
- `templates/profile.html` — the profile display page.

## New dependencies
No new pip packages. Use:
- `sqlite3` (standard library) via `get_db()`.
- Flask's built-in `session` (signed cookie) — already configured with
  `app.secret_key` from Step 2.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` via `get_db()`.
- Parameterised queries only (`?` placeholders); never string-format or
  f-string values into SQL. The lookup is by the logged-in user's id.
- Passwords hashed with `werkzeug.security` — the profile never displays,
  logs, or returns the `password_hash` value.
- Use CSS variables (`var(--...)`) from `style.css` — never hardcode hex
  values in new styles.
- All templates extend `base.html`.
- Keep the `profile` function name and route path — templates/later steps use
  `url_for('profile')`.
- Handle "user not found" gracefully: if the session id no longer matches a
  `users` row, clear the session and redirect to `/login` (or render a clear
  message) rather than erroring.
- Preserve mockup-driven styling; do not replace with a component framework.
- Close every `get_db()` connection (`conn.close()` or a `with` block) after
  use.

## Definition of done
- [ ] `GET /profile` while logged out redirects to `/login` (never renders
      profile content or returns the placeholder string).
- [ ] `GET /profile` while logged in renders `profile.html` showing the current
      user's `name`, `email`, and `created_at`.
- [ ] The visible name/email match the `users` row for the logged-in id (not
      hardcoded).
- [ ] `password_hash` is never displayed or leaked on the profile page.
- [ ] The `created_at` timestamp is formatted readably (not a raw SQL default
      string on its own) if the display requires it.
- [ ] A session pointing at a deleted/nonexistent user redirects to login
      with a clean state instead of crashing.
- [ ] All new SQL uses `?` placeholders; no f-string/`.format()` SQL.
- [ ] No CSS hex values hardcoded in any new styles — only `var(--...)`.
- [ ] The profile page extends `base.html` and looks consistent with
      `dashboard.html` (paper background, serif heading, neutral type).
- [ ] App starts without errors on port 5001 (`python app.py`) with the new
      route.