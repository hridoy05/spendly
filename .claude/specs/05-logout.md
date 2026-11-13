# Spec: Logout

## Overview
This step implements Spendly's logout. Today `/logout` is a placeholder that
returns a plain string (`"Logout — coming in Step 3"`), while the navbar's
"Sign out" button (in `base.html`) already points at it via `url_for('logout')`.
This feature turns `/logout` into the real end of the auth lifecycle: it clears
the signed session cookie (dropping `session["user_id"]` and
`session["user_name"]`) and redirects the user to the landing page (or the
login page) as a signed-out visitor. It closes the register → login → logout
cycle: a user can sign in, use the app, then explicitly leave — after which
`/dashboard`, `/profile`, and the navbar all revert to their logged-out states
because they key off the same session. Logout is intentionally only
meaningful for a logged-in user; hitting it while already signed out is a
no-op that just redirects away.

## Depends on
- **Step 1 — Database setup**: none beyond the existing app; logout has no
  schema interaction.
- **Step 2 — Register** (and the login work): establishes the session contract
  that logout reverses — the same `session["user_id"]` / `session["user_name"]`
  keys that register sets and login re-sets, and that `base.html`,
  `dashboard.html`, and `profile.html` all read. Logout must clear exactly
  those so every downstream route returns to its signed-out default.
- The login step (implemented/merged) — logout is the counterpart that ends
  the session login begins, though it does not technically *require* login
  code to be present to work.

## Routes
- `GET /logout` — replace the placeholder: `session.clear()`, then redirect to
  `/` (landing). — logged-in (but harmless when already signed out)

No other new routes.

## Database changes
No database changes. Logout touches no tables, columns, or constraints; it only
clears the Flask signed session cookie. `database/db.py` is untouched.

## Templates
- **Create:** none.
- **Modify:** none required. `templates/base.html` already renders the "Sign
  out" link via `url_for('logout')` in the logged-in navbar branch, and the
  `{% if session.get("user_name") %}` guard automatically reverts to the
  "Sign in" / "Get started" pair once logout clears the session. No template or
  CSS changes are needed — the post-logout state is already the logged-out
  default.

## Files to change
- `app.py` — implement the `logout` route: replace the placeholder body with
  `session.clear()` and a `redirect(url_for("landing"))`.

## Files to create
None.

## New dependencies
No new pip packages. Use only Flask's built-in `session` (already configured
with `app.secret_key`) and `redirect` / `url_for` (already imported).

## Rules for implementation
- No SQLAlchemy or ORMs — logout performs no queries.
- No SQL at all here; when SQL is used elsewhere, parameterised queries only.
- Passwords hashed with `werkzeug.security` — logout never touches password
  material.
- Use CSS variables (`var(--...)`) from `style.css` — never hardcode hex
  values in new styles (none added here).
- All templates extend `base.html` — no new templates in this step.
- Keep the `logout` function name and `/logout` path — `base.html` uses
  `url_for('logout')`.
- Call `session.clear()` (mirroring the session-clear used on register/login
  success) so ALL session state is dropped, then redirect.
- Redirect target: `/` via `url_for('landing')` (the landing page is Spendly's
  public home and the natural place to return a signed-out visitor).
- Preserve mockup-driven styling; do not replace with a component framework.

## Definition of done
- [ ] `GET /logout` while logged in clears the session and returns a redirect
      (302) to `/` (the landing page) — not the placeholder string.
- [ ] After logout, `GET /dashboard` redirects to `/login` (no longer renders
      the private dashboard).
- [ ] After logout, `GET /profile` redirects to `/login` (no longer renders the
      private profile).
- [ ] After logout, the navbar reverts to the "Sign in" / "Get started" state
      (no user name, no "Sign out" link) on any page.
- [ ] `GET /logout` while already signed out is harmless — it still redirects
      to `/` without erroring.
- [ ] No session keys (`user_id`, `user_name`) survive `session.clear()` — the
      session cookie is effectively dropped.
- [ ] App starts without errors on port 5001 (`python app.py`) with the new
      route.
- [ ] No new templates, CSS, or dependencies were introduced.