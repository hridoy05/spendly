# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

**Spendly** — a Flask expense-tracking web app ("Track every poisa. Own your finances."). It is a staged teaching/assignment project: core features (auth, expense CRUD) exist as placeholder routes with comments like "coming in Step N", and students implement them against a spec. The landing page and static marketing pages (terms, privacy) are the most complete parts.

## Commands

All under the repo's `venv/` virtualenv. Activate it before working (`source venv/bin/activate`) or prefix commands with `venv/bin/`.

- **Run the dev server**: `python app.py` — runs on port **5001** with Flask debug mode.
- **Run tests**: `pytest` (uses `pytest-flask`; no `tests/` directory exists yet — it will be added as the project develops).

Dependencies are pinned in `requirements.txt` and should be installed into `venv/`.

## Architecture

A single-module Flask app. There is no application factory, blueprint, or models layer yet — planning for one is a likely direction as the steps progress.

### Routing — `app.py`
The single source of app logic. Every route is a `@app.route` handler. Named routes matter: templates reference them via `url_for(...)`, so route/function names are load-bearing (e.g. `landing`, `login`, `register`, `terms`, `privacy`).

- Complete routes: `/` (landing), `/register`, `/login`, `/terms`, `/privacy` — all `render_template(...)`.
- Placeholder routes (return plain strings, not yet implemented): `/logout` (Step 3), `/profile` (Step 4), `/expenses/add` (Step 7), `/expenses/<id>/edit` (Step 8), `/expenses/<id>/delete` (Step 9).

### Database — `database/`
`database/db.py` is an empty stub to be written by students in Step 1. Its documented contract:
- `get_db()` — return a SQLite connection with `row_factory` and foreign keys enabled.
- `init_db()` — create all tables using `CREATE TABLE IF NOT EXISTS`.
- `seed_db()` — insert sample development data.

The DB file `expense_tracker.db` is gitignored. `database/__init__.py` is currently empty.

### Templates — `templates/`
Jinja2. `base.html` defines the shared shell: a `<nav>` with brand + Sign in / **Get started** links, a `<main>` content block, and a footer with terms/privacy links. All nav and footer links use `url_for(...)` against named routes above. The base loads Google Fonts (DM Serif Display + DM Sans), `css/style.css`, and `js/main.js`; pages add CSS via a `head` block.

### Static assets — `static/`
- `css/style.css` — global design tokens (`:root` CSS variables: ink/paper neutrals, an `--accent` dark green, `--accent-2` gold) and base component styles shared across pages.
- `css/landing.css` — landing-page-specific overrides, linked only from `landing.html` (not `base.html`). Declares its own hero palette (`--hero-*`, chart dot/bar colors) and overrides `body` with the Inter font.
- `js/main.js` — shared front-end script loaded by `base.html`.

## Conventions worth preserving

- **Design is mockup-driven.** The live git history shows UI work done "to match mockup": hero sections and landing styling are hand-written CSS overrides. Preserve that base style (cream `#f7f6f3` paper, dark green `#1a472a`, serif display font) rather than replacing it with a component framework.
- **Comments with "Step N"** mark deliberately unfinished scaffolding for students — don't treat them as TODOs to implement spontaneously; the assignments are done in order.
- The app name in the UI is **Spendly**; the gitignore comment shows a working DB named `expense_tracker.db`.
- Port **5001** is intentional (not the Flask default 5000) — keep the hardcoded `port=5001` in `app.py`.

## Notes

- No README, no `tests/` directory, and no `.cursorrules`/Copilot instructions exist yet.
- All dependencies are vendored in the local `venv/`; `requirements.txt` lists `flask`, `werkzeug`, `pytest`, and `pytest-flask`.
