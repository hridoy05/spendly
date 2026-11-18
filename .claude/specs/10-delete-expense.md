# Spec: Delete Expense

## Overview

This step completes the expense CRUD lifecycle and removes an expense a user no
longer wants. Steps 7–9 added the full create → read → update path: users can
record an expense (`/expenses/add`), see it filtered on `/profile`, and correct
it (`/expenses/<id>/edit`). But there is no way to *remove* a row — an
accidentally created or now-meaningless expense stays in the list forever.
This feature turns the `/expenses/<int:id>/delete` placeholder into a real
logged-in-only route that deletes exactly one expense — and only if it belongs
to the requester. It uses **POST** (never GET) because deletion is destructive
and must not be triggered by a crawler, link preview, or prefetch, and every
`DELETE` is scoped by both the expense `id` and the session's `user_id`, the
same ownership discipline established in the edit step, so a user can never
delete someone else's expense by guessing an id. After deleting, the user is
redirected back to `/profile` where the row disappears from their list. It is
the final member of the add → edit → delete trio and reads for nothing but the
existing `expenses` table from Step 1.

## Depends on

- **Step 1 — Database setup**: the `expenses` table (id, `user_id` FK, amount,
  category, date, description). This feature `DELETE`s from it and must NOT
  change its schema.
- **Step 4 — Login** (and register): the session contract
  (`session["user_id"]`) is the ownership boundary; `user_id` comes only from
  the session, never from a form field or URL.
- **Step 7 — Date filter profile**: `templates/profile.html` renders the
  logged-in user's expense rows and is the natural home for the "Delete"
  control per row (the expense query there already selects `id`).
- **Step 9 — Edit expense**: established the ownership pattern this step
  extends — every mutation on an id-bearing route is scoped by
  `WHERE ... AND user_id = ?`, and a non-owned/nonexistent id redirects safely.
  The per-row actions slot in `profile.html` already has an "Edit" link; delete
  joins it there. (Step 9 also left `/expenses/<id>/delete` as a placeholder
  explicitly "for the next step", which this is.)

## Routes

- `POST /expenses/<int:id>/delete` — replace the placeholder. Guard for a
  logged-in user (redirect to `/login` when not authenticated). Validate
  ownership implicitly by issuing `DELETE FROM expenses WHERE id = ? AND
  user_id = ?`. A non-owned or nonexistent id simply deletes no rows — no error
  surfaced, just a redirect to `/profile` (deleting someone else's row must
  never succeed, and deleting a nonexistent row should be a harmless no-op).
  On any valid (owned) row, redirect to `/profile`. — logged-in

No new routes; no `GET` delete route (deletion must not be reachable by a plain
link/prefetch). The existing edit/add routes are untouched.

## Database changes

No schema changes. This step issues `DELETE FROM expenses WHERE id = ? AND
user_id = ?` against the existing `expenses` table (the `user_id` FK ensures
the row belongs to a user; the scoping ensures it belongs to *this* user).

## Templates

- **Modify:** `templates/profile.html` — in each expense row's existing
  `.expense-actions` slot, alongside the "Edit" link, add a small **POST form**
  to `url_for('delete_expense', id=e['id'])` with a "Delete" submit button
  styled as a text link (so it matches the Edit link in appearance but is a
  real form submission). Add a lightweight confirm — e.g. `onsubmit="return
  confirm('Delete this expense?')"` (inline, since the app has no JS framework;
  the shared `js/main.js` could hold a delegated handler instead, but a tiny
  inline `onsubmit` is the minimal, dependency-free approach consistent with
  the project). Keep it visually muted/danger-ish using existing tokens
  (`--danger`, `--danger-light`).
- **Create:** none — no separate confirmation page; the tiny inline/browser
  confirm is sufficient for this teaching project, and POST semantics protect
  against accidental/GET-triggered deletion.

## Files to change

- `app.py` — replace the `delete_expense(id)` placeholder with a logged-in-only
  `POST` handler that `DELETE`s an owned row and redirects to `/profile`.
- `templates/profile.html` — add the per-row delete form/button next to the
  Edit link.
- `static/css/style.css` — a small `.expense-delete` style (danger-tinted text
  link using `--danger`/tokens) sharing the row-actions layout, with no
  hardcoded hex.

## Files to create

- `.claude/specs/10-delete-expense.md` — this spec.

No new templates or Python modules.

## New dependencies

No new dependencies. Reuses `sqlite3` and the existing Flask/jinja stack.

## Rules for implementation

- No SQLAlchemy or ORMs — raw `sqlite3` via `database/db.py`'s `get_db()` only.
- Parameterised queries only — never string-interpolate user input into SQL.
  Bind `id` and `user_id` as `?` parameters.
- **Ownership is mandatory.** The `DELETE` must be scoped by
  `WHERE id = ? AND user_id = ?` using `session["user_id"]`; a user must never
  be able to delete another user's expense by guessing an `id`. A non-owned or
  nonexistent id must delete no rows.
- `user_id` must always come from `session["user_id"]` — never from a form
  field or URL parameter.
- **POST only.** The route must handle `request.method == "POST"`; a `GET`
  request to the same URL should be redirected away (e.g. to `/profile`), never
  delete. Destructive actions must not be reachable via a plain link/prefetch.
- Passwords hashed with werkzeug — no password involvement here, but do not
  regress existing `generate_password_hash`/`check_password_hash` usage.
- Use CSS variables — never hardcode hex values. Reuse existing tokens
  (`--danger`, `--accent`) and the established expense-row styles; no new
  hardcoded colors.
- All templates extend `base.html`.

## Definition of done

1. Start the dev server (`python app.py` on port 5001). Log in as the seeded
   `demo@spendly.com` / `demo123` user.
2. On `/profile`, each expense row shows a "Delete" control next to "Edit"
   (8 seeded rows → 8 "Delete" controls). Clicking it shows a confirm prompt;
   confirming submits the POST.
3. Confirm delete on one expense. You are redirected to `/profile`, and that
   row is gone (the list now has 7 rows, and the deleted one's description is
   no longer present).
4. The deleted row is actually removed from the database — `SELECT COUNT(*)`
   on that user's `expenses` is 7, and the specific `id` no longer exists.
5. Delete the remaining rows one at a time; they each disappear from the list
   without error, until the list is empty (the friendly empty state still
   shows, no crash).
6. Log out and `POST` to `/expenses/<id>/delete` (e.g. via the test client).
   You are redirected to `/login`, and no row is deleted while logged out.
7. A `GET` request to `/expenses/<id>/delete` (not POST) does **not** delete
   the row — it redirects away instead.
8. Authenticate as a second user (register a fresh account) and `POST` to
   `/expenses/<id>/delete` for an id owned by `demo@spendly.com`. The demo
   row is **not** deleted (still present when demo logs back in), and the
   second user is simply redirected to `/profile`.
9. Confirm `/expenses/add` and `/expenses/<id>/edit` still work as before
   (unaffected by this step).