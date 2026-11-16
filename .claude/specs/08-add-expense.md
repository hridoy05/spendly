# Spec: Add Expense

## Overview

This step wires up the first *write* to the `expenses` table: a form that lets
a logged-in user record a new expense of their own. Today `/expenses/add` is a
placeholder that returns a plain string (`"Add expense — coming in Step 7"`),
and the only expenses that exist are the demo rows seeded in Step 1 (which the
date-filter step just displayed, read-only). This feature turns `/expenses/add`
into a real logged-in-only route that handles a POST form — validating the
`amount`, `category`, `date`, and optional `description`, then inserting a row
scoped to the session's `user_id` and redirecting back to the profile (or
wherever the user's expense list lives). It is the natural counterpart to the
date-filter profile: that step lets a user *see* their spending, and this step
lets them *grow* it. It uses the same `expenses` schema from Step 1 unchanged
and the same session ownership boundary from Steps 2–6.

## Depends on

- **Step 1 — Database setup**: the `expenses` table must exist (created by
  `init_db()`) with `id`, `user_id` (FK), `amount`, `category`, `date`
  (ISO `TEXT`), `description`, and `created_at`, plus the `CATEGORIES` list
  (Food, Transport, Bills, Health, Entertainment, Shopping, Other). This
  feature inserts into that table and must NOT change its schema or the
  category list.
- **Step 4 — Login** (and register): the session contract
  (`session["user_id"]` / `session["user_name"]`) is the ownership boundary;
  the new expense row's `user_id` must come from `session["user_id"]`, never a
  form field. `/expenses/add` must be guarded (redirect to `/login` when
  logged out), matching the profile routes.
- **Step 7 — Date filter profile**: `templates/profile.html` and the
  `GET /profile` handler already render a logged-in user's expense list
  (`category`, `date`, `description`, amount). This feature complements it by
  providing the write path — the same category set, the same ISO `YYYY-MM-DD` date format,
  the same user-scoping — and the post-add redirect can land on that list.

## Routes

- `GET /expenses/add` — replace the placeholder with a logged-in-only guard
  (redirect to `/login` when not authenticated) that renders an empty
  "add expense" form (`templates/add_expense.html`). — logged-in
- `POST /expenses/add` — validate the submitted `amount` (a positive number),
  `category` (one of the fixed `CATEGORIES`), `date` (a valid `YYYY-MM-DD`
  date), and optional `description`; on success `INSERT` a new row owned by
  `session["user_id"]` and redirect (e.g. to `/profile` so the new expense is
  visible in the date-filter list). On error, re-render the form with the
  user's input retained and an error message. — logged-in

No other new routes.

## Database changes

No schema changes. This step inserts into the existing `expenses` table from
Step 1 (`INSERT INTO expenses (user_id, amount, category, date, description)
VALUES (?, ?, ?, ?, ?)`).

## Templates

- **Create:** `templates/add_expense.html` — a form extending `base.html`
  (consistent with `login.html`/`register.html`/`profile.html`) with inputs
  for `amount` (number), `category` (a `<select>` populated from the fixed
  categories — not hardcoded in the template, passed from the view), `date`
  (`<input type="date">`, defaulting to today), and `description` (optional),
  plus a submit button.
- **Modify:** none strictly required. (Optionally a small "Add expense" link
  into `/expenses/add` from `templates/profile.html`'s expense list so the new
  route is reachable; this is a nice-to-have, not a requirement.)

## Files to change

- `app.py` — replace the `add_expense()` placeholder (currently returning a
  plain string) with `GET`/`POST` handling: the logged-in guard, form
  validation, the `INSERT` into `expenses`, and re-render on error.
- `templates/profile.html` — *optional*: add an "Add expense" link to the
  expense card so the new route is discoverable.

## Files to create

- `templates/add_expense.html` — the new add-expense form.
- `.claude/specs/08-add-expense.md` — this spec.

## New dependencies

No new dependencies. Reuses `sqlite3` and the existing Flask/jinja stack.

## Rules for implementation

- No SQLAlchemy or ORMs — raw `sqlite3` via `database/db.py`'s `get_db()` only.
- Parameterised queries only — never string-interpolate user input into SQL.
  Bind `user_id`, `amount`, `category`, `date`, and `description` as `?`
  parameters.
- `user_id` must always come from `session["user_id"]` — never from user input.
  One user must never be able to create a row owned by someone else.
- Validate `amount` as a positive number (reject non-numeric, negative, and
  zero), `category` against the fixed `database/db.py` `CATEGORIES` list
  (reject anything not in it), and `date` as a valid `YYYY-MM-DD` via
  `datetime.strptime(..., "%Y-%m-%d")` in a `try/except`, matching the date
  validation added in Step 7.
- Passwords hashed with werkzeug — no password change here, but do not regress
  existing `generate_password_hash`/`check_password_hash` usage in the auth and
  profile routes.
- Use CSS variables — never hardcode hex values. Reuse the existing
  `--paper`/`--ink`/`--accent`/`--accent-2` tokens and `form-input` /
  `btn-submit` classes from `static/css/style.css`.
- All templates extend `base.html`.
- Access the logged-in user's `id` from `session["user_id"]`, consistent with
  the existing profile routes.

## Definition of done

1. Start the dev server (`python app.py` on port 5001). Log in as the seeded
   `demo@spendly.com` / `demo123` user.
2. Visit `/expenses/add`. The add-expense form renders (amount, category
   dropdown populated with the fixed categories, date defaulting to today,
   optional description). No error is shown.
3. Submit a valid expense (e.g. amount `12.50`, category `Food`, today's date).
   You are redirected to `/profile`, and the new expense appears in the expense
   list (the demo list had 8 rows; it now has 9, and the new one is present).
4. Submit an invalid amount (e.g. `-5` or `abc`). The form re-renders with a
   validation error and the other fields' input is retained; nothing is
   inserted into the database.
5. Submit an invalid category (not in the fixed list). The form re-renders with
   an error; no row is created.
6. Submit an invalid date (e.g. `2026-02-30` or a malformed value). The form
   re-renders with a validation error; no row is created.
7. Log out and visit `/expenses/add` directly. You are redirected to `/login`;
   you cannot add an expense while signed out.
8. An authenticated second user (register a fresh account) can add their own
   expense, and it does not appear in `demo@spendly.com`'s list.