"""
Tests for RBAC access control and dashboard summary endpoints.
Verifies that each role can only access what it should.
"""


class TestRBACAccessControl:
    """Explicitly test that role boundaries are enforced."""

    def test_viewer_can_access_summary(self, client, viewer_token):
        res = client.get("/api/dashboard/summary",
                         headers={"Authorization": f"Bearer {viewer_token}"})
        assert res.status_code == 200

    def test_viewer_can_access_recent(self, client, viewer_token):
        res = client.get("/api/dashboard/recent",
                         headers={"Authorization": f"Bearer {viewer_token}"})
        assert res.status_code == 200

    def test_viewer_cannot_access_monthly_trends(self, client, viewer_token):
        """Monthly trends require analyst or admin."""
        res = client.get("/api/dashboard/monthly-trends",
                         headers={"Authorization": f"Bearer {viewer_token}"})
        assert res.status_code == 403

    def test_viewer_cannot_access_weekly_trends(self, client, viewer_token):
        res = client.get("/api/dashboard/weekly-trends",
                         headers={"Authorization": f"Bearer {viewer_token}"})
        assert res.status_code == 403

    def test_analyst_can_access_monthly_trends(self, client, analyst_token):
        res = client.get("/api/dashboard/monthly-trends",
                         headers={"Authorization": f"Bearer {analyst_token}"})
        assert res.status_code == 200

    def test_analyst_can_access_weekly_trends(self, client, analyst_token):
        res = client.get("/api/dashboard/weekly-trends",
                         headers={"Authorization": f"Bearer {analyst_token}"})
        assert res.status_code == 200

    def test_analyst_cannot_manage_users(self, client, analyst_token):
        res = client.get("/api/users/",
                         headers={"Authorization": f"Bearer {analyst_token}"})
        assert res.status_code == 403

    def test_admin_can_manage_users(self, client, admin_token):
        res = client.get("/api/users/",
                         headers={"Authorization": f"Bearer {admin_token}"})
        assert res.status_code == 200

    def test_unauthenticated_cannot_access_dashboard(self, client, db):
        res = client.get("/api/dashboard/summary")
        assert res.status_code == 401

    def test_unauthenticated_cannot_access_records(self, client, db):
        res = client.get("/api/records/")
        assert res.status_code == 401


class TestDashboardSummary:
    def test_summary_returns_correct_keys(self, client, admin_token):
        res = client.get("/api/dashboard/summary",
                         headers={"Authorization": f"Bearer {admin_token}"})
        assert res.status_code == 200
        data = res.get_json()
        assert "total_income" in data
        assert "total_expenses" in data
        assert "net_balance" in data

    def test_summary_net_balance_is_correct(self, client, admin_token, db, admin_user):
        """Create known records and verify the net balance calculation."""
        from app.models.financial_record import FinancialRecord
        from datetime import date

        r1 = FinancialRecord(amount=1000, type="income",  category="Salary",   date=date(2024,1,1), created_by=admin_user.id)
        r2 = FinancialRecord(amount=400,  type="expense", category="Rent",     date=date(2024,1,2), created_by=admin_user.id)
        r3 = FinancialRecord(amount=100,  type="expense", category="Groceries",date=date(2024,1,3), created_by=admin_user.id)
        db.session.add_all([r1, r2, r3])
        db.session.commit()

        res = client.get("/api/dashboard/summary",
                         headers={"Authorization": f"Bearer {admin_token}"})
        data = res.get_json()
        assert data["total_income"] == 1000.0
        assert data["total_expenses"] == 500.0
        assert data["net_balance"] == 500.0

    def test_category_breakdown_returns_list(self, client, analyst_token, sample_record):
        res = client.get("/api/dashboard/category-breakdown",
                         headers={"Authorization": f"Bearer {analyst_token}"})
        assert res.status_code == 200
        assert "breakdown" in res.get_json()

    def test_recent_activity_respects_limit(self, client, admin_token, db, admin_user):
        from app.models.financial_record import FinancialRecord
        from datetime import date
        for i in range(15):
            db.session.add(FinancialRecord(
                amount=100, type="income", category="Test",
                date=date(2024, 1, i + 1), created_by=admin_user.id
            ))
        db.session.commit()

        res = client.get("/api/dashboard/recent?limit=5",
                         headers={"Authorization": f"Bearer {admin_token}"})
        assert res.status_code == 200
        assert len(res.get_json()["recent"]) <= 5

    def test_monthly_trends_returns_12_months(self, client, analyst_token):
        res = client.get("/api/dashboard/monthly-trends?year=2024",
                         headers={"Authorization": f"Bearer {analyst_token}"})
        assert res.status_code == 200
        data = res.get_json()
        assert data["year"] == 2024
        assert len(data["monthly_trends"]) == 12

    def test_monthly_trends_invalid_year(self, client, analyst_token):
        res = client.get("/api/dashboard/monthly-trends?year=1800",
                         headers={"Authorization": f"Bearer {analyst_token}"})
        assert res.status_code == 422

    def test_weekly_trends_returns_correct_days(self, client, analyst_token):
        res = client.get("/api/dashboard/weekly-trends?days=14",
                         headers={"Authorization": f"Bearer {analyst_token}"})
        assert res.status_code == 200
        assert len(res.get_json()["trend"]) == 14
