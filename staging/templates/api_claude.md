The backend service for the storefront. FastAPI, Postgres 16, SQLAlchemy 2.

Run it with `uvicorn app.main:app --reload --port 8000`.

Migrations are Alembic; never edit a migration that has already been applied.
Tests use a throwaway database created per session, so they are safe to run anywhere.
