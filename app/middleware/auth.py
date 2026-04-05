from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from app.models.user import User


def get_current_user() -> User | None:
    
    user_id = get_jwt_identity()
    return User.query.get(int(user_id))


def jwt_required_with_active_check(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        user = get_current_user()
        if not user:
            return jsonify({"error": "User not found"}), 404
        if not user.is_active:
            return jsonify({"error": "Account is inactive"}), 403
        return fn(*args, **kwargs)
    return wrapper


def require_permission(permission: str):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = get_current_user()
            if not user or not user.has_permission(permission):
                return jsonify({
                    "error": "Access denied",
                    "detail": f"Your role does not have the '{permission}' permission"
                }), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def require_role(*roles: str):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = get_current_user()
            if not user or user.role not in roles:
                return jsonify({
                    "error": "Access denied",
                    "detail": f"This action requires one of these roles: {', '.join(roles)}"
                }), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator
