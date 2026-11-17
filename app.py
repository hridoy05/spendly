import os
import sqlite3
from datetime import datetime, date

from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash

from database.db import get_db, init_db, seed_db, CATEGORIES

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


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
            conn = get_db()
            try:
                cur = conn.execute(
                    "INSERT INTO users (name, email, password_hash)"
                    " VALUES (?, ?, ?)",
                    (name, email, generate_password_hash(password)),
                )
                conn.commit()
                user_id = cur.lastrowid
            except sqlite3.IntegrityError:
                user_id = None
                error = "An account with that email already exists."
            finally:
                conn.close()

            if user_id is not None:
                session.clear()
                session["user_id"] = user_id
                session["user_name"] = name
                return redirect(url_for("dashboard"))

        return render_template("register.html", error=error)

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        conn = get_db()
        user = conn.execute(
            "SELECT id, name, password_hash FROM users WHERE email = ?",
            (email,),
        ).fetchone()
        conn.close()

        if user is not None and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            return redirect(url_for("dashboard"))

        error = "Invalid email or password."
        return render_template("login.html", error=error)

    return render_template("login.html")


@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("dashboard.html", user_name=session.get("user_name"))


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/profile", methods=["GET", "POST"])
def profile():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    user = conn.execute(
        "SELECT id, name, email, created_at FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
    if user is None:
        conn.close()
        session.clear()
        return redirect(url_for("login"))

    # Optional date-range filter, expressed as GET query params (?start=&end=).
    filter_start = request.args.get("start", "").strip()
    filter_end = request.args.get("end", "").strip()

    def _valid_date(value):
        try:
            datetime.strptime(value, "%Y-%m-%d")
            return True
        except (ValueError, TypeError):
            return False

    if filter_start and not _valid_date(filter_start):
        filter_start = ""
    if filter_end and not _valid_date(filter_end):
        filter_end = ""

    query = (
        "SELECT id, amount, category, date, description"
        " FROM expenses WHERE user_id = ?"
    )
    params = [session["user_id"]]
    if filter_start:
        query += " AND date >= ?"
        params.append(filter_start)
    if filter_end:
        query += " AND date <= ?"
        params.append(filter_end)
    query += " ORDER BY date DESC"
    expenses = conn.execute(query, params).fetchall()
    conn.close()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()

        error = None
        if not name or not email:
            error = "Name and email are required."
        elif "@" not in email:
            error = "Enter a valid email address."

        if not error:
            conn = get_db()
            try:
                conn.execute(
                    "UPDATE users SET name = ?, email = ? WHERE id = ?",
                    (name, email, session["user_id"]),
                )
                conn.commit()
            except sqlite3.IntegrityError:
                error = "That email is already in use by another account."
            finally:
                conn.close()

            if error is None:
                session["user_name"] = name
                return redirect(url_for("profile"))

        return render_template(
            "profile.html",
            user=user,
            error=error,
            password_error=None,
            expenses=expenses,
            filter_start=filter_start,
            filter_end=filter_end,
        )

    return render_template(
        "profile.html",
        user=user,
        expenses=expenses,
        filter_start=filter_start,
        filter_end=filter_end,
    )


@app.route("/profile/password", methods=["POST"])
def change_password():
    if "user_id" not in session:
        return redirect(url_for("login"))

    current_password = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")

    conn = get_db()
    user = conn.execute(
        "SELECT id, name, email, created_at, password_hash FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
    if user is None:
        conn.close()
        session.clear()
        return redirect(url_for("login"))

    error = None
    if not check_password_hash(user["password_hash"], current_password):
        error = "Current password is incorrect."
    elif len(new_password) < 8:
        error = "New password must be at least 8 characters."

    if error is None:
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (generate_password_hash(new_password), session["user_id"]),
        )
        conn.commit()

    conn.close()
    if error is None:
        return redirect(url_for("profile"))

    return render_template(
        "profile.html",
        user=user,
        error=None,
        password_error=error,
        expenses=[],
        filter_start="",
        filter_end="",
    )


@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
    if "user_id" not in session:
        return redirect(url_for("login"))

    today = date.today().isoformat()

    if request.method == "POST":
        form = {
            "amount": request.form.get("amount", "").strip(),
            "category": request.form.get("category", "").strip(),
            "date": request.form.get("date", "").strip(),
            "description": request.form.get("description", "").strip(),
        }

        error = None
        try:
            amount = float(form["amount"])
        except (ValueError, TypeError):
            amount = None
        if form["amount"] and (amount is None or amount <= 0):
            error = "Amount must be a positive number."
        elif form["category"] not in CATEGORIES:
            error = "Choose a valid category."
        else:
            try:
                datetime.strptime(form["date"], "%Y-%m-%d")
            except (ValueError, TypeError):
                error = "Enter a valid date."

        if not error:
            conn = get_db()
            conn.execute(
                "INSERT INTO expenses (user_id, amount, category, date, description)"
                " VALUES (?, ?, ?, ?, ?)",
                (
                    session["user_id"],
                    amount,
                    form["category"],
                    form["date"],
                    form["description"] or None,
                ),
            )
            conn.commit()
            conn.close()
            return redirect(url_for("profile"))

        return render_template(
            "add_expense.html",
            categories=CATEGORIES,
            form=form,
            error=error,
            today=today,
            form_action=url_for("add_expense"),
            form_title="Add an expense",
            form_subtitle="Record what you spent today",
            form_submit="Add expense",
        )

    return render_template(
        "add_expense.html",
        categories=CATEGORIES,
        form={},
        error=None,
        today=today,
        form_action=url_for("add_expense"),
        form_title="Add an expense",
        form_subtitle="Record what you spent today",
        form_submit="Add expense",
    )


@app.route("/expenses/<int:id>/edit", methods=["GET", "POST"])
def edit_expense(id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    expense = conn.execute(
        "SELECT id, amount, category, date, description"
        " FROM expenses WHERE id = ? AND user_id = ?",
        (id, session["user_id"]),
    ).fetchone()
    if expense is None:
        conn.close()
        return redirect(url_for("profile"))

    error = None
    if request.method == "POST":
        form = {
            "amount": request.form.get("amount", "").strip(),
            "category": request.form.get("category", "").strip(),
            "date": request.form.get("date", "").strip(),
            "description": request.form.get("description", "").strip(),
        }

        try:
            amount = float(form["amount"])
        except (ValueError, TypeError):
            amount = None
        if form["amount"] and (amount is None or amount <= 0):
            error = "Amount must be a positive number."
        elif form["category"] not in CATEGORIES:
            error = "Choose a valid category."
        else:
            try:
                datetime.strptime(form["date"], "%Y-%m-%d")
            except (ValueError, TypeError):
                error = "Enter a valid date."

        if not error:
            conn.execute(
                "UPDATE expenses SET amount = ?, category = ?, date = ?,"
                " description = ? WHERE id = ? AND user_id = ?",
                (
                    amount,
                    form["category"],
                    form["date"],
                    form["description"] or None,
                    id,
                    session["user_id"],
                ),
            )
            conn.commit()
            conn.close()
            return redirect(url_for("profile"))
    else:
        form = {
            "amount": str(expense["amount"]),
            "category": expense["category"],
            "date": expense["date"],
            "description": expense["description"] or "",
        }

    conn.close()
    return render_template(
        "add_expense.html",
        categories=CATEGORIES,
        form=form,
        error=error,
        today=date.today().isoformat(),
        form_action=url_for("edit_expense", id=id),
        form_title="Edit expense",
        form_subtitle="Update the details below",
        form_submit="Save changes",
    )


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    # Ensure the schema and seed data exist before serving any routes.
    with app.app_context():
        init_db()
        seed_db()
    app.run(debug=True, port=5001)
