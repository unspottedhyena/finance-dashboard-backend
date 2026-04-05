from datetime import date, timedelta
from flask import Blueprint, request, jsonify
from sqlalchemy import func, extract
from app import db
from app.models.financial_record import FinancialRecord, RecordType
from app.middleware.auth import jwt_required_with_active_check, require_permission

dashboard_bp = Blueprint("dashboard", __name__)


def _base_query():
    """non-deleted records."""
    return FinancialRecord.query.filter_by(is_deleted=False)


@dashboard_bp.route("/summary", methods=["GET"])
@jwt_required_with_active_check
@require_permission("read_dashboard")
def summary():
    """
    financial summary:
    - Total income
    - Total expenses
    - Net balance
    """
    total_income = db.session.query(
        func.coalesce(func.sum(FinancialRecord.amount), 0)
    ).filter(
        FinancialRecord.is_deleted == False,
        FinancialRecord.type == RecordType.INCOME,
    ).scalar()

    total_expenses = db.session.query(
        func.coalesce(func.sum(FinancialRecord.amount), 0)
    ).filter(
        FinancialRecord.is_deleted == False,
        FinancialRecord.type == RecordType.EXPENSE,
    ).scalar()

    net_balance = float(total_income) - float(total_expenses)

    return jsonify({
        "total_income": float(total_income),
        "total_expenses": float(total_expenses),
        "net_balance": net_balance,
    }), 200


@dashboard_bp.route("/category-breakdown", methods=["GET"])
@jwt_required_with_active_check
@require_permission("read_dashboard")
def category_breakdown():
    """category wise"""
    query = db.session.query(
        FinancialRecord.category,
        FinancialRecord.type,
        func.sum(FinancialRecord.amount).label("total"),
        func.count(FinancialRecord.id).label("count"),
    ).filter(FinancialRecord.is_deleted == False)

    type_filter = request.args.get("type")
    if type_filter:
        if type_filter not in RecordType.ALL:
            return jsonify({"error": f"type must be one of: {', '.join(RecordType.ALL)}"}), 422
        query = query.filter(FinancialRecord.type == type_filter)

    results = query.group_by(
        FinancialRecord.category, FinancialRecord.type
    ).order_by(func.sum(FinancialRecord.amount).desc()).all()

    return jsonify({
        "breakdown": [
            {
                "category": row.category,
                "type": row.type,
                "total": float(row.total),
                "count": row.count,
            }
            for row in results
        ]
    }), 200


@dashboard_bp.route("/recent", methods=["GET"])
@jwt_required_with_active_check
@require_permission("read_dashboard")
def recent_activity():

    """ most recent financial records"""

    limit = min(request.args.get("limit", 10, type=int), 50)
    records = (
        _base_query()
        .order_by(FinancialRecord.date.desc(), FinancialRecord.created_at.desc())
        .limit(limit)
        .all()
    )
    return jsonify({"recent": [r.to_dict() for r in records]}), 200


@dashboard_bp.route("/monthly-trends", methods=["GET"])
@jwt_required_with_active_check
@require_permission("read_insights")
def monthly_trends():

    """monthly income vs expense totals. Analyst and Admin only."""

    year = request.args.get("year", date.today().year, type=int)
    if year < 2000 or year > 2100:
        return jsonify({"error": "year must be between 2000 and 2100"}), 422

    results = db.session.query(
        extract("month", FinancialRecord.date).label("month"),
        FinancialRecord.type,
        func.sum(FinancialRecord.amount).label("total"),
    ).filter(
        FinancialRecord.is_deleted == False,
        extract("year", FinancialRecord.date) == year,
    ).group_by(
        extract("month", FinancialRecord.date),
        FinancialRecord.type,
    ).order_by("month").all()

    months = {m: {"income": 0.0, "expense": 0.0} for m in range(1, 13)}
    for row in results:
        months[int(row.month)][row.type] = float(row.total)

    MONTH_NAMES = [
        "", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
    ]

    return jsonify({
        "year": year,
        "monthly_trends": [
            {
                "month": m,
                "month_name": MONTH_NAMES[m],
                "income": months[m]["income"],
                "expense": months[m]["expense"],
                "net": months[m]["income"] - months[m]["expense"],
            }
            for m in range(1, 13)
        ]
    }), 200


@dashboard_bp.route("/weekly-trends", methods=["GET"])
@jwt_required_with_active_check
@require_permission("read_insights")
def weekly_trends():

    """daily totals for the past N days. Analyst and Admin only."""

    days = min(request.args.get("days", 7, type=int), 90)
    if days < 1:
        return jsonify({"error": "days must be at least 1"}), 422

    start_date = date.today() - timedelta(days=days - 1)

    results = db.session.query(
        FinancialRecord.date,
        FinancialRecord.type,
        func.sum(FinancialRecord.amount).label("total"),
    ).filter(
        FinancialRecord.is_deleted == False,
        FinancialRecord.date >= start_date,
    ).group_by(
        FinancialRecord.date,
        FinancialRecord.type,
    ).order_by(FinancialRecord.date).all()

    data: dict = {}
    for row in results:
        d = row.date.isoformat()
        if d not in data:
            data[d] = {"income": 0.0, "expense": 0.0}
        data[d][row.type] = float(row.total)

    trend = []
    for i in range(days):
        d = (start_date + timedelta(days=i)).isoformat()
        income = data.get(d, {}).get("income", 0.0)
        expense = data.get(d, {}).get("expense", 0.0)
        trend.append({
            "date": d,
            "income": income,
            "expense": expense,
            "net": income - expense,
        })

    return jsonify({"days": days, "trend": trend}), 200
