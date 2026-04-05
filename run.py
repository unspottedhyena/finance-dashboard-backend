from app import create_app, db
from app.models.user import User, Role
from app.models.financial_record import FinancialRecord

app = create_app()


@app.cli.command("seed")
def seed_db():
    """
    Seed the database with an initial admin user and sample records.
    Run with: flask seed
    """
    from datetime import date
    import random

    print("Seeding database...")

    # Create admin user
    if not User.query.filter_by(username="admin").first():
        admin = User(username="admin", email="admin@example.com", role=Role.ADMIN)
        admin.set_password("admin123")
        db.session.add(admin)
        print("  Created admin user (username: admin, password: admin123)")

    # Create analyst user
    if not User.query.filter_by(username="analyst").first():
        analyst = User(username="analyst", email="analyst@example.com", role=Role.ANALYST)
        analyst.set_password("analyst123")
        db.session.add(analyst)
        print("  Created analyst user (username: analyst, password: analyst123)")

    # Create viewer user
    if not User.query.filter_by(username="viewer").first():
        viewer = User(username="viewer", email="viewer@example.com", role=Role.VIEWER)
        viewer.set_password("viewer123")
        db.session.add(viewer)
        print("  Created viewer user (username: viewer, password: viewer123)")

    db.session.commit()

    admin = User.query.filter_by(username="admin").first()

    # Sample financial records
    categories = {
        "income": ["Salary", "Freelance", "Investment", "Bonus", "Rental"],
        "expense": ["Rent", "Groceries", "Utilities", "Transport", "Entertainment", "Healthcare"],
    }

    if FinancialRecord.query.count() == 0:
        import datetime
        today = date.today()
        for i in range(30):
            rec_date = today - datetime.timedelta(days=random.randint(0, 180))
            rec_type = random.choice(["income", "expense"])
            record = FinancialRecord(
                amount=round(random.uniform(50, 5000), 2),
                type=rec_type,
                category=random.choice(categories[rec_type]),
                date=rec_date,
                notes=f"Sample {rec_type} record #{i+1}",
                created_by=admin.id,
            )
            db.session.add(record)
        db.session.commit()
        print("  Created 30 sample financial records")

    print("Seeding complete.")


if __name__ == "__main__":
    app.run(debug=True)
