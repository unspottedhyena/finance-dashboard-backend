# Finance Dashboard — Backend

A backend API for a role-based finance dashboard. Built with Flask, PostgreSQL, and JWT auth.

---

## Stack

- **Python / Flask** — lightweight, easy to reason about for a project this size
- **PostgreSQL** — relational DB via SQLAlchemy ORM
- **Flask-JWT-Extended** — token-based auth
- **Flask-Migrate** — database migrations via Alembic
- **pytest** — unit and integration tests using SQLite in-memory

---

## Project Layout

```
app/
  __init__.py           # app factory
  models/
    user.py             # User model, Role constants, permission map
    financial_record.py # FinancialRecord model
  routes/
    auth.py             # register, login, /me
    users.py            # user management (admin only)
    records.py          # financial record CRUD
    dashboard.py        # summary and analytics endpoints
  middleware/
    auth.py             # JWT decorator + RBAC decorators
  utils/
    validators.py       # input validation
tests/
  conftest.py           # fixtures (uses SQLite in-memory)
  test_auth.py
  test_records.py
  test_dashboard.py
run.py                  # entry point + seed command
```

---

## Getting Started

### 1. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set up environment variables

Copy `.env.example` to `.env` and fill in your values:

```
DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/finance_dashboard
JWT_SECRET_KEY=anylongstringatleast32charslong1234
SECRET_KEY=anotherlongstringatleast32chars1234
FLASK_ENV=development
FLASK_DEBUG=True
```

The app loads `.env` automatically using an absolute path, so it works regardless of which directory you run Flask from. Make sure the `.env` file sits in the project root alongside `run.py`.

### 4. Create the database

```sql
CREATE DATABASE finance_dashboard;
```

### 5. Run migrations

```bash
set FLASK_APP=run.py       # Windows
export FLASK_APP=run.py    # Mac/Linux

flask db init
flask db migrate -m "initial schema"
flask db upgrade
```

### 6. Seed sample data

```bash
flask seed
```

Creates three users and 30 sample records:

| Username | Password | Role |
|---|---|---|
| admin | admin123 | admin |
| analyst | analyst123 | analyst |
| viewer | viewer123 | viewer |

### 7. Run the server

```bash
python run.py
```

API is available at `http://localhost:5000`

### 8. Run tests

Tests use an in-memory SQLite database — no PostgreSQL needed.

```bash
pytest
```

---

## Roles and Access

I went with three roles. The permission map is defined once in `user.py` so there's a single place to update if roles ever change.

| Role | What they can do |
|---|---|
| viewer | Read records, view dashboard summary |
| analyst | Everything viewer can + trends and insights |
| admin | Full access — manage records and users |

Access is enforced at the route level with two decorators: `@jwt_required_with_active_check` (validates token and checks if the account is still active) and `@require_permission("some_permission")` (checks role). They stack on any route.

---

## API Overview

All protected routes need this header:
```
Authorization: Bearer <token>
```

### Auth

| Method | Endpoint | Access | Description |
|---|---|---|---|
| POST | `/api/auth/register` | Public | Register (always creates a viewer) |
| POST | `/api/auth/login` | Public | Login, returns JWT token |
| GET | `/api/auth/me` | Any logged-in user | Current user profile |

### Users

| Method | Endpoint | Access | Description |
|---|---|---|---|
| GET | `/api/users/` | Admin | List users — filter by `?role=` or `?is_active=` |
| GET | `/api/users/<id>` | Admin | Get one user |
| POST | `/api/users/` | Admin | Create user with any role |
| PATCH | `/api/users/<id>` | Admin | Update role, email, or status |
| DELETE | `/api/users/<id>` | Admin | Delete user |

### Records

| Method | Endpoint | Access | Description |
|---|---|---|---|
| GET | `/api/records/` | All roles | List records — filter by `?type=`, `?category=`, `?date_from=`, `?date_to=`, `?search=` |
| GET | `/api/records/<id>` | All roles | Get one record |
| POST | `/api/records/` | Admin | Create record |
| PATCH | `/api/records/<id>` | Admin | Update record (partial) |
| DELETE | `/api/records/<id>` | Admin | Soft delete |

### Dashboard

| Method | Endpoint | Access | Description |
|---|---|---|---|
| GET | `/api/dashboard/summary` | All roles | Total income, expenses, net balance |
| GET | `/api/dashboard/category-breakdown` | All roles | Totals grouped by category |
| GET | `/api/dashboard/recent` | All roles | Recent records — optional `?limit=` |
| GET | `/api/dashboard/monthly-trends` | Analyst, Admin | Income vs expense per month — optional `?year=` |
| GET | `/api/dashboard/weekly-trends` | Analyst, Admin | Daily totals for past N days — optional `?days=` |

### Error format

Every error comes back in the same shape:

```json
{
  "error": "what went wrong",
  "details": ["field-level specifics if relevant"]
}
```

Status codes: `200` success, `201` created, `400` bad JSON, `401` no/expired token, `403` wrong role, `404` not found, `409` conflict (duplicate username or email), `422` validation failed.

---

## A few decisions worth noting

**Soft deletes on records** — financial data shouldn't just disappear. Records get an `is_deleted` flag so they're excluded from queries but still in the database if you ever need them. Users are hard-deleted since there was no requirement to preserve user history.

**Self-registration always creates a viewer** — the public `/register` endpoint intentionally locks the role to viewer. Only an admin can create accounts with elevated roles via `/api/users/`. This prevents someone from signing up as an admin.

**Validation without a schema library** — I kept validation as plain functions that return a list of error strings. It's straightforward to follow without needing to know marshmallow or pydantic, and for a project this size it doesn't add meaningful overhead.

**Permission map in one place** — `Role.PERMISSIONS` in `user.py` is the single source of truth for what each role can do. Adding a new permission means updating that dict, nothing else.

**Amounts are always positive** — the `type` field (income/expense) handles direction. Storing negative amounts would make aggregation queries messier.

**JWT identity as string** — Flask-JWT-Extended 4.x requires the JWT identity to be a string. Tokens are created with `str(user.id)` and converted back to `int` when querying the database. This is handled in `app/routes/auth.py` and `app/middleware/auth.py`.

---

## Assumptions

- Date fields store only the date (no time), which is enough for financial entries.
- JWT tokens expire after 15 minutes by default with Flask-JWT-Extended 4.x. For a longer session, set `JWT_ACCESS_TOKEN_EXPIRES` in `.env`.
- There is no refresh token flow, though Flask-JWT-Extended supports it and it would be straightforward to add.
- The `.env` file is not committed to version control. Copy `.env.example` to `.env` and fill in your own values before running the project.
