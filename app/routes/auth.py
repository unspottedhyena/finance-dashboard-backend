from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token
from app import db
from app.models.user import User, Role
from app.middleware.auth import jwt_required_with_active_check, get_current_user
from app.utils.validators import validate_user_create

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["POST"])
def register():
    """ Register new user. Default "viewer". "Non Viewer" AdminOnly"""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    data["role"] = Role.VIEWER
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
        role=Role.VIEWER,
    )
    user.set_password(data["password"])
    db.session.add(user)
    db.session.commit()

    # identity must be a string for Flask-JWT-Extended 4.x
    token = create_access_token(identity=str(user.id))
    return jsonify({
        "message": "Registration successful",
        "user": user.to_dict(),
        "access_token": token,
    }), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    """Authenticate user/return JWT access token."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return jsonify({"error": "username and password are required"}), 422

    user = User.query.filter_by(username=username).first()

    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid username or password"}), 401

    if not user.is_active:
        return jsonify({"error": "Account is inactive. Contact an administrator."}), 403

    token = create_access_token(identity=str(user.id))
    return jsonify({
        "message": "Login successful",
        "user": user.to_dict(),
        "access_token": token,
    }), 200


@auth_bp.route("/me", methods=["GET"])
@jwt_required_with_active_check
def me():
    user = get_current_user()
    return jsonify({"user": user.to_dict()}), 200
