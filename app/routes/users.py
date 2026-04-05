from flask import Blueprint, request, jsonify
from app import db
from app.models.user import User, Role
from app.middleware.auth import (
    jwt_required_with_active_check,
    require_permission,
    get_current_user,
)
from app.utils.validators import validate_user_create, validate_user_update

users_bp = Blueprint("users", __name__)


@users_bp.route("/", methods=["GET"])
@jwt_required_with_active_check
@require_permission("manage_users")
def list_users():

    """List all users. Admin only."""

    role_filter = request.args.get("role")
    active_filter = request.args.get("is_active")

    query = User.query

    if role_filter:
        if role_filter not in Role.ALL:
            return jsonify({"error": f"Invalid role filter. Must be one of: {', '.join(Role.ALL)}"}), 422
        query = query.filter_by(role=role_filter)

    if active_filter is not None:
        is_active = active_filter.lower() == "true"
        query = query.filter_by(is_active=is_active)

    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    paginated = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        "users": [u.to_dict() for u in paginated.items],
        "pagination": {
            "page": paginated.page,
            "per_page": per_page,
            "total": paginated.total,
            "pages": paginated.pages,
        }
    }), 200


@users_bp.route("/<int:user_id>", methods=["GET"])
@jwt_required_with_active_check
@require_permission("manage_users")
def get_user(user_id):

    """Get user by ID. Admin only."""

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify({"user": user.to_dict()}), 200


@users_bp.route("/", methods=["POST"])
@jwt_required_with_active_check
@require_permission("manage_users")
def create_user():
    """create user. Admin only"""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    errors = validate_user_create(data)
    if errors:
        return jsonify({"error": "Validation failed", "details": errors}), 422

    if User.query.filter_by(username=data["username"].strip()).first():
        return jsonify({"error": "Username already taken"}), 409

    if User.query.filter_by(email=data["email"].strip().lower()).first():
        return jsonify({"error": "Email already registered"}), 409

    user = User(
        username=data["username"].strip(),
        email=data["email"].strip().lower(),
        role=data.get("role", Role.VIEWER),
    )
    user.set_password(data["password"])
    db.session.add(user)
    db.session.commit()

    return jsonify({"message": "User created", "user": user.to_dict()}), 201


@users_bp.route("/<int:user_id>", methods=["PATCH"])
@jwt_required_with_active_check
@require_permission("manage_users")
def update_user(user_id):
    """Update user. Admin only."""
    current_user = get_current_user()

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    if current_user.id == user_id and data.get("is_active") is False:
        return jsonify({"error": "You cannot deactivate your own account"}), 400

    errors = validate_user_update(data)
    if errors:
        return jsonify({"error": "Validation failed", "details": errors}), 422

    if "role" in data:
        user.role = data["role"]
    if "is_active" in data:
        user.is_active = data["is_active"]
    if "email" in data:
        existing = User.query.filter_by(email=data["email"].strip().lower()).first()
        if existing and existing.id != user_id:
            return jsonify({"error": "Email already in use"}), 409
        user.email = data["email"].strip().lower()

    db.session.commit()
    return jsonify({"message": "User updated", "user": user.to_dict()}), 200


@users_bp.route("/<int:user_id>", methods=["DELETE"])
@jwt_required_with_active_check
@require_permission("manage_users")
def delete_user(user_id):
    """Permanently delete user. Admin only."""
    current_user = get_current_user()
    if current_user.id == user_id:
        return jsonify({"error": "You cannot delete your own account"}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    db.session.delete(user)
    db.session.commit()
    return jsonify({"message": f"User '{user.username}' deleted"}), 200
