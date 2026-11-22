# Spec: Date Filter Profile

## Overview

This step adds date-range filtering to Spendly's profile page. Today
`GET /profile` (built in the profile-page step, extended with write routes in
the backend-routes step) renders the logged-in user's account details, but it
does not surface their spending at all — and there is nowhere in the app yet to
see a filtered view of one's own expenses by time period. This feature makes
the profile page also show the current user's expenses, and adds a small
date-range filter form (start date, end date) that narrows that list to a
chosen window. It is the first *querying* milestone in the roadmap: register
inserted a `users` row, login/logout manage the session, the backend-routes
step finally mutated the `users` row, and this step reads back over the
`expenses` table (seeded in Step 1) with a real `WHERE ... BETWEEN` predicate —
owned by the session's `user_id`, never any other user's data.

> **Roadmap note.** CLAUDE.md's placeholder roadmap originally labels Step 7 as
> `/expenses/add`. This feature instead delivers the date-filter profile as
> step 07; the `/expenses/add` placeholder in `app.py` is untouched and out of
> scope here. If the roadmap is later reconciled, the expense-CRUD steps simply
> follow this polished-then-filtered expense read path.

## Depends on

- **Step 1 — Database setup**: the `expenses` table must exist (created by
  `init_db()`) with `id`, `user_id` (FK), `amount`, `category`, `date`
  (ISO `TEXT`), and `description`, plus the seeded `demo@spendly.com` sample
  rows. This feature reads from that table and must NOT change its schema.
- **Step 3 — Profile page**: `GET /profile` and `templates/profile.html`
  establish the logged-in-only guard (`session["user_id"]`) and the profile
  shell this feature extends with the expense list + filter form.
- **Step 4 — Login**: the session contract (`session["user_id"]`,
  `session["user_name"]`) is the ownership boundary that scopes the expense
  query to the current user.
- **Step 6 — Backend routes for profile page**: `templates/profile.html`
  already re-renders on POST with retained input; this feature follows the same
  re-render/retain-and-error pattern for the filter form.

## Routes

- `GET /profile` — **modify existing**. Keep the current behavior (render
  account details, redirect to `/login` when logged out). Extend it to also
  fetch the current user's expenses between optional `start` and `end` query
  params (ISO dates, `YYYY-MM-DD`). Valid params narrow the list via
  `date >= start AND date <= end`; absent or blank params show all the user's
  expenses; invalid dates are ignored (treated as no filter) rather than
  erroring. Pass the filtered rows and the echoed filter values to the
  template. — logged-in

No new routes. The filter is expressed entirely through query parameters on the
existing `GET /profile` route.

## Database changes

No schema changes. The `expenses` table from Step 1 is used as-is. Queries are
read-only `SELECT`s against `expenses` filtered by the current `user_id` and
the optional date bounds.

## Templates

- **Modify:** `templates/profile.html` — add a date-range filter form (two
  `<input type="date">` fields, `name="start"` / `name="end"`, submitting via
  `GET` back to `url_for('profile')`) and an expense list section showing each
  filtered row (date, category, description, amount). Show a friendly
  empty state when the user has no expenses in the selected range. Echo the
  submitted `start`/`end` back into the inputs so the filter persists across
  page loads.

No new templates.

## Files to change

- `app.py` — extend the `GET /profile` handler to read `request.args` for
  `start`/`end`, validate them, query the user's expenses, and pass them (plus
  the echoed filter values) to `render_template`.
- `templates/profile.html` — add the filter form and expense list sections,
  styled with the existing design tokens.

## Files to create

- `.claude/specs/07-datr-filter-profile.md` — this spec.

No new Python modules or templates.

## New dependencies

No new dependencies. Reuses `sqlite3` and the existing Flask/jinja stack.

## Rules for implementation

- No SQLAlchemy or ORMs — raw `sqlite3` via `database/db.py`'s `get_db()` only.
- Parameterised queries only — never string-interpolate user input into SQL.
  Bind `user_id`, `start`, and `end` as `?` parameters.
- The expense query must be scoped by `WHERE user_id = ?` — one user must never
  see another user's rows.
- Date bounds use inclusive `BETWEEN` semantics (`date >= ? AND date <= ?`).
  Validate the ISO `YYYY-MM-DD` format with `datetime.strptime(..., "%Y-%m-%d")`
  in a `try/except` and drop invalid values silently.
- Passwords hashed with werkzeug — irrelevant to this read-only step, but do
  not regress the existing `generate_password_hash`/`check_password_hash`
  usage in the profile write routes.
- Use CSS variables — never hardcode hex values. Reuse the existing
  `--paper`/`--ink`/`--accent`/`--accent-2` tokens from `static/css/style.css`.
- All templates extend `base.html` — `profile.html` already does; keep it.
- Access the logged-in user's `id` from `session["user_id"]`, consistent with
  the existing profile routes.

## Definition of done

1. Start the dev server (`python app.py` on port 5001). Log in as the seeded
   `demo@spendly.com` / `demo123` user.
2. Visit `/profile`. The expense list shows the user's expenses (the 8 seeded
   sample rows) with no filter applied. The filter form shows empty date inputs.
3. Submit the filter with `start` and `end` spanning today only. The list
   narrows to expenses in that window, and the chosen dates appear back in the
   inputs after the page reloads.
4. Submit a range with no expenses (e.g. both dates far in the past). The list
   shows the friendly empty state, not a blank or erroring section.
5. Submit an invalid date (e.g. `start=not-a-date`). The page renders normally
   and shows all expenses (the invalid value is dropped, not a 500).
6. Log out and visit `/profile` directly. You are redirected to `/login`
   (existing behavior preserved; the new query code runs only behind the
   logged-in guard).
7. An authenticated second user (register a fresh account) sees only their own
   expenses — never `demo@spendly.com`'s rows.