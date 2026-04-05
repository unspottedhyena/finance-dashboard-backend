"""
Shared pytest fixtures for all tests.
Uses an in-memory SQLite database so no PostgreSQL connection is needed to run tests.
"""
import pytest
from app import create_app, db as _db
from app.models.user import User, Role
from app.models.financial_record import FinancialRecord
from datetime import date


@pytest.fixture(scope="session")
def app():
    """Create a test Flask application using an in-memory SQLite database."""
    test_app = create_app()
    test_app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "JWT_SECRET_KEY": "test-secret-key",
        "WTF_CSRF_ENABLED": False,
    })
    with test_app.app_context():
        _db.create_all()
        yield test_app
        _db.drop_all()


@pytest.fixture(scope="function")
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture(scope="function")
def db(app):
    """Provide a clean database for each test by rolling back after each test."""
    with app.app_context():
        yield _db
        _db.session.rollback()
        # Clean all tables after each test
        for table in reversed(_db.metadata.sorted_tables):
            _db.session.execute(table.delete())
        _db.session.commit()


@pytest.fixture
def admin_user(db):
    user = User(username="testadmin", email="admin@test.com", role=Role.ADMIN)
    user.set_password("password123")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def analyst_user(db):
    user = User(username="testanalyst", email="analyst@test.com", role=Role.ANALYST)
    user.set_password("password123")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def viewer_user(db):
    user = User(username="testviewer", email="viewer@test.com", role=Role.VIEWER)
    user.set_password("password123")
    db.session.add(user)
    db.session.commit()
    return user


def get_token(client, username, password="password123"):
    """Helper to log in and return a JWT token."""
    response = client.post("/api/auth/login", json={
        "username": username,
        "password": password,
    })
    return response.get_json()["access_token"]


@pytest.fixture
def admin_token(client, admin_user):
    return get_token(client, "testadmin")


@pytest.fixture
def analyst_token(client, analyst_user):
    return get_token(client, "testanalyst")


@pytest.fixture
def viewer_token(client, viewer_user):
    return get_token(client, "testviewer")


@pytest.fixture
def sample_record(db, admin_user):
    """A single financial record created by the admin user."""
    record = FinancialRecord(
        amount=1500.00,
        type="income",
        category="Salary",
        date=date(2024, 6, 1),
        notes="June salary payment",
        created_by=admin_user.id,
    )
    db.session.add(record)
    db.session.commit()
    return record
