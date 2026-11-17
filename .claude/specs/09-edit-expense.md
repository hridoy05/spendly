# Spec: Edit Expense

## Overview

This step adds the *update* half of spend management: a form that lets a
logged-in user change an expense of their own. Today `/expenses/add` (built in
the add-expense step) lets a user create an expense, and `/profile` renders
their list — but a mistake (wrong amount, wrong category, typo in the date)
cannot be corrected; the only fix is to look at a wrong, permanently-stored
row. This feature turns the `/expenses/<int:id>/edit` placeholder into a real
logged-in-only route that pre-fills the add-expense form with the existing
row's values, validates the submitted amount/category/date/description exactly
as add does, and issues an `UPDATE` scoped to that expense *and* to the
session's `user_id`. It is the natural complement to the create path: add made
rows, edit corrects them. The critical new concern versus add is **ownership** —
because the URL carries a `user_id`-independent expense `id`, the route MUST
confirm the row belongs to the requester and scope every mutation to
`session["user_id"]`, so a user can never alter someone else's expense by
guessing an id.

## Depends on

- **Step 1 — Database setup**: the `expenses` table (id, `user_id` FK, amount,
  category, date, description) and the fixed `CATEGORIES` list. This feature
  `SELECT`s by id and `UPDATE`s it; it must NOT change the schema or category
  list.
- **Step 4 — Login** (and register): the session contract
  (`session["user_id"]`) is the ownership boundary. The route must be guarded
  like every other logged-in route, and `user_id` must come only from the
  session.
- **Step 7 — Date filter profile**: `templates/profile.html` renders the
  logged-in user's expense rows and is the natural home for an "Edit" link per
  row. The expense query there already selects `id`, so each row can point at
  its edit URL.
- **Step 8 — Add expense**: `templates/add_expense.html` and the
  `add_expense()` route establish the exact form structure, field names
  (`amount`, `category`, `date`, `description`), validation rules, error
  messages, and the `form`-dict retention pattern. The edit form reuses all of
  this — it is effectively add-expense pre-populated from a DB row, with an
  `UPDATE` in place of `INSERT` and the post-submit redirect back to the
  same place (`/profile`).

## Routes

- `GET /expenses/<int:id>/edit` — replace the placeholder. Guard for a logged-in
  user (redirect to `/login` when not authenticated). Look up the expense by
  `id` **and** `user_id`; if no such row belongs to this user, redirect (e.g.
  to `/profile`) rather than rendering a form for someone else's data. Render
  `templates/add_expense.html` (reused) pre-filled with the row's values. — logged-in
- `POST /expenses/<int:id>/edit` — validate the submitted `amount` (positive
  number), `category` (in `CATEGORIES`), `date` (valid `YYYY-MM-DD`), and
  optional `description` (same rules/messages as add-expense). On success,
  `UPDATE expenses SET amount = ?, category = ?, date = ?, description = ?
  WHERE id = ? AND user_id = ?` — scoping by **both** `id` and `user_id` — then
  redirect to `/profile`. On invalid input, re-render the form with the
  submitted values retained and an error. If the id matches no expense owned by
  this user (e.g. the row was deleted), redirect to `/profile`. — logged-in

No other new routes. The existing `/expenses/<int:id>/delete` placeholder stays
untouched (next step).

## Database changes

No schema changes. This step reads (`SELECT id, amount, category, date,
description ... WHERE id = ? AND user_id = ?`) and updates the existing
`expenses` table from Step 1.

## Templates

- **Create:** none. Reuse `templates/add_expense.html` — it must be made to
  work for both add (empty form, "Add expense" heading/submit) and edit
  (pre-filled, "Edit expense" heading/submit). The cleanest approach is to
  parametrise it minimally: when the route renders for an edit it passes the
  existing expense's values through the same `form` dict the add route uses, so
  the template logic (`{{ form['amount'] if form else ... }}`, the category
  `selected` check) already does the right thing; the only edit-specific bit is
  the form `action` (`url_for('edit_expense', id=...)` vs
  `url_for('add_expense')`) and the heading/submit label. Decide between a
  shared template with a small conditional on a passed `form_action`/`title`
  variable, or a thin `edit_expense.html` that includes/extends the add form —
  but prefer **reusing** `add_expense.html` with a couple of optional variables
  to avoid duplicating the form markup and validation wiring.
- **Modify:** `templates/profile.html` — add an "Edit" link per expense row
  pointing at `url_for('edit_expense', id=e['id'])` so the route is reachable;
  and `templates/add_expense.html` — make its form `action` and heading/label
  correct for edit as well as add (via small controllable variables OR a
  separate edit wrapper).

## Files to change

- `app.py` — replace the `edit_expense(id)` placeholder with `GET`/`POST`
  handling: logged-in guard, ownership-scoped `SELECT`, pre-filling, the same
  validation as add, the ownership-scoped `UPDATE`, re-render on error, and
  redirect to `/profile` on success / missing row.
- `templates/add_expense.html` — parametrise so it serves both add and edit
  (form `action`, heading, submit label), or otherwise provide for edit pre-fill.
- `templates/profile.html` — add an "Edit" link to each expense row.

## Files to create

- `.claude/specs/09-edit-expense.md` — this spec.

No new templates (reuse the add form) and no new Python modules.

## New dependencies

No new dependencies. Reuses `sqlite3` and the existing Flask/jinja stack.

## Rules for implementation

- No SQLAlchemy or ORMs — raw `sqlite3` via `database/db.py`'s `get_db()` only.
- Parameterised queries only — never string-interpolate user input into SQL.
  Bind `id`, `user_id`, `amount`, `category`, `date`, and `description` as `?`
  parameters.
- **Ownership is mandatory.** Every `SELECT` and `UPDATE` against expenses must
  be scoped by `WHERE ... AND user_id = ?` using `session["user_id"]`. A user
  must never be able to read or modify another user's expense by guessing an
  `id`; a request for a non-owned or nonexistent id must not render an edit
  form and must not change any row.
- `user_id` must always come from `session["user_id"]` — never from user input.
- Validate `amount` (positive number), `category` (in `CATEGORIES`), and `date`
  (`YYYY-MM-DD` via `datetime.strptime` in `try/except`) with the exact rules
  and messages established in add-expense (Step 8), so the two routes behave
  identically.
- Passwords hashed with werkzeug — no password change here, but do not regress
  existing `generate_password_hash`/`check_password_hash` usage.
- Use CSS variables — never hardcode hex values. Reuse the existing tokens and
  `form-input` / `btn-submit` classes.
- All templates extend `base.html`.

## Definition of done

1. Start the dev server (`python app.py` on port 5001). Log in as the seeded
   `demo@spendly.com` / `demo123` user.
2. On `/profile`, each expense row shows an "Edit" link. Clicking it (or
   visiting `/expenses/<id>/edit` for a demo expense id) opens the form
   pre-filled with that row's `amount`, `category` (the matching option
   selected), `date`, and `description`.
3. Change the amount (e.g. to a new value) and submit. You are redirected to
   `/profile`, and the row now shows the updated amount in the list.
4. Submit an invalid amount (e.g. `-5` or `abc`) on the edit form. The form
   re-renders with a validation error, the other fields retain their
   (submitted) values, and the database is unchanged.
5. Submit an invalid category or an invalid date (e.g. `2026-02-30`). The form
   re-renders with a validation error; the row is unchanged.
6. Log out and visit `/expenses/<id>/edit` directly. You are redirected to
   `/login`.
7. Authenticate as a second user (register a fresh account) and visit
   `/expenses/<id>/edit` for an id that belongs to `demo@spendly.com`. You are
   redirected away (to `/profile`) and the demo expense's row is **not** shown
   or modified. The demo user can still see and edit their own expense
   unchanged.
8. Confirm `/expenses/<id>/delete` still returns its plain placeholder
   ("Delete expense — coming in Step 9" / "coming in Step \*"), untouched.