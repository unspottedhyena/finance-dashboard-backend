"""
Tests for financial record endpoints:
  GET    /api/records/
  GET    /api/records/<id>
  POST   /api/records/
  PATCH  /api/records/<id>
  DELETE /api/records/<id>

Also covers search and filter query params.
"""


class TestListRecords:
    def test_viewer_can_list_records(self, client, viewer_token, sample_record):
        res = client.get("/api/records/", headers={"Authorization": f"Bearer {viewer_token}"})
        assert res.status_code == 200
        data = res.get_json()
        assert "records" in data
        assert "pagination" in data

    def test_list_requires_auth(self, client, db):
        res = client.get("/api/records/")
        assert res.status_code == 401

    def test_filter_by_type(self, client, viewer_token, sample_record):
        res = client.get("/api/records/?type=income", headers={"Authorization": f"Bearer {viewer_token}"})
        assert res.status_code == 200
        for record in res.get_json()["records"]:
            assert record["type"] == "income"

    def test_filter_invalid_type(self, client, viewer_token, db):
        res = client.get("/api/records/?type=invalid", headers={"Authorization": f"Bearer {viewer_token}"})
        assert res.status_code == 422

    def test_search_by_keyword(self, client, viewer_token, sample_record):
        res = client.get("/api/records/?search=Salary", headers={"Authorization": f"Bearer {viewer_token}"})
        assert res.status_code == 200
        records = res.get_json()["records"]
        assert len(records) >= 1
        assert any("Salary" in r["category"] for r in records)

    def test_search_no_match_returns_empty(self, client, viewer_token, sample_record):
        res = client.get("/api/records/?search=XYZNOTEXIST", headers={"Authorization": f"Bearer {viewer_token}"})
        assert res.status_code == 200
        assert res.get_json()["records"] == []

    def test_pagination_fields_present(self, client, viewer_token, sample_record):
        res = client.get("/api/records/?page=1&per_page=5", headers={"Authorization": f"Bearer {viewer_token}"})
        pagination = res.get_json()["pagination"]
        assert "page" in pagination
        assert "total" in pagination
        assert "pages" in pagination


class TestGetRecord:
    def test_get_existing_record(self, client, viewer_token, sample_record):
        res = client.get(f"/api/records/{sample_record.id}", headers={"Authorization": f"Bearer {viewer_token}"})
        assert res.status_code == 200
        assert res.get_json()["record"]["id"] == sample_record.id

    def test_get_nonexistent_record(self, client, viewer_token, db):
        res = client.get("/api/records/99999", headers={"Authorization": f"Bearer {viewer_token}"})
        assert res.status_code == 404


class TestCreateRecord:
    def test_admin_can_create_record(self, client, admin_token):
        res = client.post("/api/records/", json={
            "amount": 2500.00,
            "type": "income",
            "category": "Freelance",
            "date": "2024-07-01",
            "notes": "Project payment",
        }, headers={"Authorization": f"Bearer {admin_token}"})
        assert res.status_code == 201
        assert res.get_json()["record"]["category"] == "Freelance"

    def test_viewer_cannot_create_record(self, client, viewer_token):
        res = client.post("/api/records/", json={
            "amount": 100,
            "type": "expense",
            "category": "Food",
            "date": "2024-07-01",
        }, headers={"Authorization": f"Bearer {viewer_token}"})
        assert res.status_code == 403

    def test_analyst_cannot_create_record(self, client, analyst_token):
        res = client.post("/api/records/", json={
            "amount": 100,
            "type": "expense",
            "category": "Food",
            "date": "2024-07-01",
        }, headers={"Authorization": f"Bearer {analyst_token}"})
        assert res.status_code == 403

    def test_create_record_missing_amount(self, client, admin_token):
        res = client.post("/api/records/", json={
            "type": "income",
            "category": "Salary",
            "date": "2024-07-01",
        }, headers={"Authorization": f"Bearer {admin_token}"})
        assert res.status_code == 422

    def test_create_record_invalid_type(self, client, admin_token):
        res = client.post("/api/records/", json={
            "amount": 500,
            "type": "transfer",
            "category": "Bank",
            "date": "2024-07-01",
        }, headers={"Authorization": f"Bearer {admin_token}"})
        assert res.status_code == 422

    def test_create_record_invalid_date(self, client, admin_token):
        res = client.post("/api/records/", json={
            "amount": 500,
            "type": "income",
            "category": "Salary",
            "date": "not-a-date",
        }, headers={"Authorization": f"Bearer {admin_token}"})
        assert res.status_code == 422

    def test_create_record_negative_amount(self, client, admin_token):
        res = client.post("/api/records/", json={
            "amount": -100,
            "type": "expense",
            "category": "Food",
            "date": "2024-07-01",
        }, headers={"Authorization": f"Bearer {admin_token}"})
        assert res.status_code == 422


class TestUpdateRecord:
    def test_admin_can_update_record(self, client, admin_token, sample_record):
        res = client.patch(f"/api/records/{sample_record.id}", json={
            "category": "Bonus",
        }, headers={"Authorization": f"Bearer {admin_token}"})
        assert res.status_code == 200
        assert res.get_json()["record"]["category"] == "Bonus"

    def test_viewer_cannot_update_record(self, client, viewer_token, sample_record):
        res = client.patch(f"/api/records/{sample_record.id}", json={"category": "Hack"},
                           headers={"Authorization": f"Bearer {viewer_token}"})
        assert res.status_code == 403

    def test_update_nonexistent_record(self, client, admin_token):
        res = client.patch("/api/records/99999", json={"category": "X"},
                           headers={"Authorization": f"Bearer {admin_token}"})
        assert res.status_code == 404


class TestDeleteRecord:
    def test_admin_can_soft_delete_record(self, client, admin_token, sample_record):
        res = client.delete(f"/api/records/{sample_record.id}",
                            headers={"Authorization": f"Bearer {admin_token}"})
        assert res.status_code == 200

        # Record should no longer be retrievable
        res2 = client.get(f"/api/records/{sample_record.id}",
                          headers={"Authorization": f"Bearer {admin_token}"})
        assert res2.status_code == 404

    def test_viewer_cannot_delete_record(self, client, viewer_token, sample_record):
        res = client.delete(f"/api/records/{sample_record.id}",
                            headers={"Authorization": f"Bearer {viewer_token}"})
        assert res.status_code == 403
