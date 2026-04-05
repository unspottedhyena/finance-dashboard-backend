from datetime import date
from flask import Blueprint, request, jsonify
from app import db
from app.models.financial_record import FinancialRecord, RecordType
from app.middleware.auth import (
    jwt_required_with_active_check,
    require_permission,
    get_current_user,
)
from app.utils.validators import validate_record_create, validate_record_update

records_bp = Blueprint("records", __name__)


@records_bp.route("/", methods=["GET"])
@jwt_required_with_active_check
@require_permission("read_records")
def list_records():

    """ List financial records """

    query = FinancialRecord.query.filter_by(is_deleted=False)
    search = request.args.get("search", "").strip()
    if search:
        query = query.filter(
            db.or_(
                FinancialRecord.category.ilike(f"%{search}%"),
                FinancialRecord.notes.ilike(f"%{search}%"),
            )
        )

    type_filter = request.args.get("type")
    if type_filter:
        if type_filter not in RecordType.ALL:
            return jsonify({"error": f"type must be one of: {', '.join(RecordType.ALL)}"}), 422
        query = query.filter_by(type=type_filter)

    category_filter = request.args.get("category")
    if category_filter:
        query = query.filter(FinancialRecord.category.ilike(f"%{category_filter}%"))

    date_from = request.args.get("date_from")
    if date_from:
        try:
            query = query.filter(FinancialRecord.date >= date.fromisoformat(date_from))
        except ValueError:
            return jsonify({"error": "date_from must be in YYYY-MM-DD format"}), 422

    date_to = request.args.get("date_to")
    if date_to:
        try:
            query = query.filter(FinancialRecord.date <= date.fromisoformat(date_to))
        except ValueError:
            return jsonify({"error": "date_to must be in YYYY-MM-DD format"}), 422

    query = query.order_by(FinancialRecord.date.desc(), FinancialRecord.created_at.desc())

    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    paginated = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        "records": [r.to_dict() for r in paginated.items],
        "pagination": {
            "page": paginated.page,
            "per_page": per_page,
            "total": paginated.total,
            "pages": paginated.pages,
        }
    }), 200


@records_bp.route("/<int:record_id>", methods=["GET"])
@jwt_required_with_active_check
@require_permission("read_records")
def get_record(record_id):

    """financial record by ID"""

    record = FinancialRecord.query.filter_by(id=record_id, is_deleted=False).first()
    if not record:
        return jsonify({"error": "Record not found"}), 404
    return jsonify({"record": record.to_dict()}), 200


@records_bp.route("/", methods=["POST"])
@jwt_required_with_active_check
@require_permission("create_records")
def create_record():

    """new financial record. Admin only."""

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    errors = validate_record_create(data)
    if errors:
        return jsonify({"error": "Validation failed", "details": errors}), 422

    current_user = get_current_user()
    record = FinancialRecord(
        amount=float(data["amount"]),
        type=data["type"].strip(),
        category=data["category"].strip(),
        date=date.fromisoformat(str(data["date"])),
        notes=data.get("notes", "").strip() or None,
        created_by=current_user.id,
    )
    db.session.add(record)
    db.session.commit()

    return jsonify({"message": "Record created", "record": record.to_dict()}), 201


@records_bp.route("/<int:record_id>", methods=["PATCH"])
@jwt_required_with_active_check
@require_permission("update_records")
def update_record(record_id):

    """update financial record. Admin only."""

    record = FinancialRecord.query.filter_by(id=record_id, is_deleted=False).first()
    if not record:
        return jsonify({"error": "Record not found"}), 404

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    errors = validate_record_update(data)
    if errors:
        return jsonify({"error": "Validation failed", "details": errors}), 422

    if "amount" in data:
        record.amount = float(data["amount"])
    if "type" in data:
        record.type = data["type"].strip()
    if "category" in data:
        record.category = data["category"].strip()
    if "date" in data:
        record.date = date.fromisoformat(str(data["date"]))
    if "notes" in data:
        record.notes = data["notes"].strip() or None

    db.session.commit()
    return jsonify({"message": "Record updated", "record": record.to_dict()}), 200


@records_bp.route("/<int:record_id>", methods=["DELETE"])
@jwt_required_with_active_check
@require_permission("delete_records")
def delete_record(record_id):

    """soft delete financial record. Admin only."""

    record = FinancialRecord.query.filter_by(id=record_id, is_deleted=False).first()
    if not record:
        return jsonify({"error": "Record not found"}), 404

    record.is_deleted = True
    db.session.commit()
    return jsonify({"message": f"Record {record_id} deleted"}), 200
