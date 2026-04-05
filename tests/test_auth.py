"""
Tests for authentication endpoints:
  POST /api/auth/register
  POST /api/auth/login
  GET  /api/auth/me
"""
from tests.conftest import get_token


class TestRegister:
    def test_register_success(self, client, db):
        res = client.post("/api/auth/register", json={
            "username": "newuser",
            "email": "newuser@test.com",
            "password": "password123",
        })
        assert res.status_code == 201
        data = res.get_json()
        assert "access_token" in data
        assert data["user"]["role"] == "viewer"  # always viewer on self-register

    def test_register_duplicate_username(self, client, viewer_user):
        res = client.post("/api/auth/register", json={
            "username": "testviewer",
            "email": "other@test.com",
            "password": "password123",
        })
        assert res.status_code == 409
        assert "Username already taken" in res.get_json()["error"]

    def test_register_missing_fields(self, client, db):
        res = client.post("/api/auth/register", json={"username": "x"})
        assert res.status_code == 422
        assert "details" in res.get_json()

    def test_register_short_password(self, client, db):
        res = client.post("/api/auth/register", json={
            "username": "shortpass",
            "email": "short@test.com",
            "password": "abc",
        })
        assert res.status_code == 422

    def test_register_invalid_email(self, client, db):
        res = client.post("/api/auth/register", json={
            "username": "bademail",
            "email": "not-an-email",
            "password": "password123",
        })
        assert res.status_code == 422


class TestLogin:
    def test_login_success(self, client, viewer_user):
        res = client.post("/api/auth/login", json={
            "username": "testviewer",
            "password": "password123",
        })
        assert res.status_code == 200
        assert "access_token" in res.get_json()

    def test_login_wrong_password(self, client, viewer_user):
        res = client.post("/api/auth/login", json={
            "username": "testviewer",
            "password": "wrongpassword",
        })
        assert res.status_code == 401

    def test_login_nonexistent_user(self, client, db):
        res = client.post("/api/auth/login", json={
            "username": "nobody",
            "password": "password123",
        })
        assert res.status_code == 401

    def test_login_inactive_user(self, client, db):
        from app.models.user import User, Role
        from app import db as _db
        user = User(username="inactive", email="inactive@test.com", role=Role.VIEWER, is_active=False)
        user.set_password("password123")
        _db.session.add(user)
        _db.session.commit()

        res = client.post("/api/auth/login", json={
            "username": "inactive",
            "password": "password123",
        })
        assert res.status_code == 403

    def test_login_missing_fields(self, client, db):
        res = client.post("/api/auth/login", json={"username": "someone"})
        assert res.status_code == 422


class TestMe:
    def test_me_returns_current_user(self, client, admin_user, admin_token):
        res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {admin_token}"})
        assert res.status_code == 200
        assert res.get_json()["user"]["username"] == "testadmin"

    def test_me_requires_auth(self, client, db):
        res = client.get("/api/auth/me")
        assert res.status_code == 401
