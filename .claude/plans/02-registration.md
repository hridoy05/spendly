# Plan: Register (Step 2)

Implements the spec at `.claude/specs/02-register.md`. Branch: `feature/register`.

## Context

`/register` currently only `render_template("register.html")` (a GET). The
form already posts `name`, `email`, `password` to `/register` and renders an
optional `{{ error }}`. The `users` table exists from Step 1 with `email
UNIQUE NOT NULL` and `password_hash NOT NULL`. The DB helper `get_db()`
returns `sqlite3.Row` connections with foreign keys on.

## Design decisions

1. **Redirect target after sign-up.** A dashboard route does not exist yet.
   Create a minimal `templates/dashboard.html` and a `GET /dashboard` route so
   a successful registration has a real private landing to redirect to. This
   is deliberately minimal now; Step 3 (login) and Step 4 (profile) grow it.
2. **Session.** Use Flask's signed-cookie `session`. Must set `app.secret_key`
   before the route reads/writes the session. Use an env var with a dev
   fallback. Store `user_id` and `user_name` so templates can show the
   logged-in user.
3. **Auth guard for the register page.** If the user is already logged in,
   `GET /register` redirects to `/dashboard` instead of showing the form.
4. **Message display.** Keep the template's existing `{{ error }}` block rather
   than introducing flash for the register page — fewer moving parts, matches
   the existing design. (Flash is reserved for Step 3 where it's more natural.)

## Steps

### 1. `app.py` — imports and secret key

- Extend the Flask import line to pull in the helpers needed:
  `from flask import Flask, render_template, request, redirect, url_for, session`
- Add `import os` and a secret key near app creation:

```python
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")
```

- Add `from werkzeug.security import generate_password_hash` (hours won't use
  the runtime import from Step 1's seed; keep `generate_password_hash` here).
- Add `import sqlite3` (for `sqlite3.IntegrityError`) and
  `from database.db import get_db`.

### 2. `app.py` — implement the `register` route

Replace the current `register()` function (both GET and POST in one handler):

```python
@app.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        error = None
        if not name or not email or not password:
            error = "All fields are required."
        elif len(password) < 8:
            error = "Password must be at least 8 characters."
        elif "@" not in email:
            error = "Enter a valid email address."

        if not error:
            try:
                conn = get_db()
                cur = conn.execute(
                    "INSERT INTO users (name, email, password_hash)"
                    " VALUES (?, ?, ?)",
                    (name, email, generate_password_hash(password)),
                )
                conn.commit()
                conn.close()
                session.clear()
                session["user_id"] = cur.lastrowid
                session["user_name"] = name
                return redirect(url_for("dashboard"))
            except sqlite3.IntegrityError:
                error = "An account with that email already exists."
            finally:
                # close conn if still open (handles the error path)
                if "conn" in locals() and conn:
                    conn.close()
                # conn was closed on success; guard against double-close is moot
                # because the success path already returned.

        return render_template("register.html", error=error)

    return render_template("register.html")
```

> **Note to implementer:** the try/finally above has a subtlety — on success the
> `conn.commit()`/`conn.close()` happen and then `return` runs inside the `try`.
> The `finally` block's `conn.close()` then runs again. To keep it clean,
> restructure so the success path closes the connection once and skips the
> `finally` on success, or only commit/close in `finally`. Suggested clean shape:

```python
    if not error:
        conn = get_db()
        try:
            cur = conn.execute("INSERT ...", (...))
            conn.commit()
            user_id = cur.lastrowid
        except sqlite3.IntegrityError:
            user_id = None
        finally:
            conn.close()
        if user_id is not None:
            session.clear()
            session["user_id"] = user_id
            session["user_name"] = name
            return redirect(url_for("dashboard"))
        error = "An account with that email already exists."
```

### 3. `app.py` — add the `dashboard` route

```python
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("dashboard.html", user_name=session.get("user_name"))
```

Placed in the routes section. It will reference `url_for('login')`, which is a
complete route — fine.

### 4. `templates/dashboard.html` — create

Minimal private landing extending `base.html`:

- `{% extends "base.html" %}` and a `title` block ("Dashboard — Spendly").
- Greets the user: "Welcome back, <name>!" using the `user_name` passed in.
- Explains the dashboard is a placeholder that Step 3+ will fill out.

### 5. `templates/base.html` — logged-in navbar

Conditionally swap the right-side nav links based on session:

- When `session` has a `user_name`: show the user's name and a "Sign out"
  link (the `/logout` route exists as a placeholder string; keep linking to it
  via `url_for('logout')`). Hide the "Sign in" / "Get started" pair.
- When not logged in: keep the current "Sign in" / "Get started" pair.

Changes within the existing `nav-links` div — use Jinja conditionals, but do
not introduce new hex values.

### 6. Verify

Run the app and exercise the Definition-of-done checklist from the spec.

## Files to change
- `app.py` — imports, secret key, `register` route (GET+POST), new `dashboard`
  route.
- `templates/base.html` — session-aware navbar.

## Files to create
- `templates/dashboard.html`.

## Out of scope
- `/login` and `/logout` logic (Step 3) — `/logout` remains a placeholder.
- Profile page (Step 4).
- Expense routes (Steps 7–9).
- No schema changes, dependencies, or tests directory.

## Definition of done
Verified by the spec's checklist: GET renders form; valid POST creates a hashed
user + session + redirect to dashboard showing the name; duplicate email shows a
friendly error and inserts no second row; short password rejected; stored hash
verifies with `check_password_hash`; app boots on 5001; navbar reflects
logged-in state; all SQL is parameterised; no hardcoded hex in new styles.