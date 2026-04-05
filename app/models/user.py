from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from app import db


class Role:
    VIEWER = "viewer"
    ANALYST = "analyst"
    ADMIN = "admin"

    ALL = [VIEWER, ANALYST, ADMIN]

    #Permissions
    PERMISSIONS = {
        VIEWER: ["read_records", "read_dashboard"],
        ANALYST: ["read_records", "read_dashboard", "read_insights"],
        ADMIN: ["read_records", "read_dashboard", "read_insights",
                "create_records", "update_records", "delete_records",
                "manage_users"],
    }

    @classmethod
    def has_permission(cls, role: str, permission: str) -> bool:
        return permission in cls.PERMISSIONS.get(role, [])


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=Role.VIEWER)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    #Relationship to financial records
    records = db.relationship("FinancialRecord", backref="created_by_user", lazy=True)

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def has_permission(self, permission: str) -> bool:
        return Role.has_permission(self.role, permission)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"
