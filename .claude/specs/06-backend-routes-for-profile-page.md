# Spec: Backend Routes for Profile Page

## Overview

This step adds the write path for Spendly's profile page. The profile already
exists as a **read-only** display: `GET /profile` looks up the logged-in user's
row and `templates/profile.html` renders their `name`, `email`, and `created_at`
(delivered in the profile-page step). But there is no way for a user to *change*
any of that — the page shows hardcoded, non-editable values, and there is no
password change at all. This feature turns the profile page into an editable
account settings screen by adding the backend routes that handle its forms:
`POST /profile` to update the account details (name and email), and a password
change route (`POST /profile/password`) that validates the current password
before setting a new one. It is the first update-write in the roadmap: register
inserted a `users` row, login/logout manage the session, and this step finally
lets an authenticated user mutate their own `users` row — while never touching
any other user's data and never leaking the stored `password_hash`.

## Depends on

- **Step 1 — Database setup**: the `users` table with `id`, `name`, `email`
  (`UNIQUE`), `password_hash`, `created_at`. This step issues `UPDATE` /
  `DELETE`-style writes against it and must NOT change its schema.
- **Step 4 — Login** (and register): establishes `session["user_id"]` /
  `session["user_name"]` so the routes can identify *which* user is making a
  change, and provides `check_password_hash` usage to authorize a password
  change. The session is the ownership boundary.
- **Profile page** (read-only GET, already shipped): `GET /profile` and
  `templates/profile.html`. This step keeps that route, may re-render it on a
  validation error so the form retains the user's input + an error message, and
  converts its static value rows into editable inputs.

## Routes

- `GET /profile` — **existing**; keep at `url_for('profile')`. May now render
  the page with a `form` (the editable mode) and, on a failed POST, re-render
  with the submitted values and an `error`. — logged-in
- `POST /profile` — handle the account-details form: validate the submitted
  `name` and `email`, `UPDATE` the current user's `users` row, refresh
  `session["user_name"]` if the name changed, and redirect to a clean
  `GET /profile`. — logged-in
- `POST /profile/password` — handle the change-password form: require the
  current password (authorize via `check_password_hash` against
  `session["user_id"]`'s row), validate the new password (min. 8 chars), hash it
  with `generate_password_hash`, `UPDATE password_hash`, then redirect. — logged-in

No other new routes.

## Database changes

No schema changes. The `users` table already exists from Step 1
(`id`, `name`, `email UNIQUE`, `password_hash`, `created_at`).

Behavior relied on (already in `database/db.py`):
- `get_db()` returns a connection with `row_factory = sqlite3.Row` and
  `PRAGMA foreign_keys = ON`.
- `email` is `UNIQUE` — updating a user to an email already held by *another*
  row must raise `sqlite3.IntegrityError`, which the route must catch and
  surface as a friendly "email already in use" error.
- `check_password_hash` and `generate_password_hash` (both already used by
  `seed_db()` / register) are the only way this step touches password material.

## Templates

- **Modify:** `templates/profile.html` — turn the three read-only
  `.profile-value` rows into an editable account-details `<form method="post"
  action="{{ url_for('profile') }}">` (pre-filled `name` and `email` inputs,
  labelled "Full name" / "Email address"), plus a second
  `<form method="post" action="{{ url_for('change_password') }}">` under a
  "Change password" heading with current/new-password fields. Render an optional
  `{{ error }}` (and, if used, a flash success message) and keep the card styling
  consistent with the current page and `dashboard.html`.
- **Modify:** `templates/base.html` — none required unless a "Profile" nav entry
  is desired (already present as the user-name link). Do not change the logout
  link.

## Files to change

- `app.py` — add the two POST handlers. The existing `profile` function already
  guards on `session["user_id"]`, fetches the user, and renders `profile.html`;
  extend it (or factor a helper) so the same guard applies to the POST routes,
  parameterise every query by the logged-in id, and catch
  `sqlite3.IntegrityError` for the unique-email case.
- `templates/profile.html` — add the two forms (see Templates).

## Files to create

None.

## New dependencies

No new pip packages. Use:
- `sqlite3` (standard library) via `get_db()`.
- `werkzeug.security` (already vendored): `generate_password_hash`,
  `check_password_hash`.
- Flask's built-in `session`, `request`, `redirect`, `url_for` (already
  imported in `app.py`).

## Rules for implementation

- No SQLAlchemy or ORMs — raw `sqlite3` via `get_db()`.
- Parameterised queries only (`?` placeholders); never string-format or
  f-string values into SQL.
- Scope every write to the logged-in user: the `WHERE` clause must always bind
  `session["user_id"]` — never derive the target from a hidden field or URL.
- Passwords hashed with `werkzeug.security`:
  - `generate_password_hash` for the new password (same scheme as register/seed).
  - `check_password_hash` against the stored hash before any password change —
    a wrong current password must not proceed.
  - Never store, log, render, or return plaintext or the stored `password_hash`.
- Email uniqueness: catch `sqlite3.IntegrityError` on the email column and
  re-render the form with a friendly "that email is already in use" error rather
  than crashing. A user is allowed to keep their own unchanged email.
- Validate `name` (non-empty) and `email` (contains `@`), and reject new
  passwords shorter than 8 characters — same rules as register.
- Use CSS variables (`var(--...)`) from `style.css` — never hardcode hex values
  in new styles.
- All templates extend `base.html` (the profile page already does).
- Keep route/function names stable and reference them with `url_for`: use
  `url_for('profile')` for the update form action and add a `change_password`
  function for the password action.
- Preserve mockup-driven styling; do not replace with a component framework.
- Close every `get_db()` connection (`conn.close()` or a `with` block) after use.
- On success, refresh `session["user_name"]` when the name changed, and redirect
  (POST-redirect-GET) rather than rendering the page on the POST.

## Definition of done

- [ ] `POST /profile` while logged out redirects to `/login` (no DB write).
- [ ] Submitting a valid new `name`/`email` as the logged-in user `UPDATE`s
      **only that user's** `users` row, then redirects to `GET /profile`, which
      reflects the new values.
- [ ] Re-submitting an email already used by a *different* account shows an
      "email already in use" error and does not overwrite the other user's row.
- [ ] A user saving their own unchanged email does not error.
- [ ] `POST /profile/password` with the wrong current password is rejected with
      an error; the stored `password_hash` is unchanged.
- [ ] `POST /profile/password` with a correct current password and a new
      password of ≥ 8 chars updates `password_hash`, and the new password
      verifies with `check_password_hash`.
- [ ] A new password shorter than 8 characters is rejected and no write occurs.
- [ ] `profile.html` renders two working forms (account details + change
      password) with pre-filled current values and an `{{ error }}` slot, and
      still extends `base.html`.
- [ ] `password_hash` / plaintext password is never displayed on the page or
      returned by any route.
- [ ] All new SQL uses `?` placeholders bound to `session["user_id"]`; no
      f-string/`.format()` SQL; no writes keyed off client-supplied id fields.
- [ ] No CSS hex values hardcoded in any new styles — only `var(--...)`.
- [ ] App starts without errors on port 5001 (`python app.py`); all profile
      routes respond without crashing.