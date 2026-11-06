#!/usr/bin/env python3
"""Initialize database with tables and default admin user."""
import sys
sys.path.insert(0, ".")

from database import engine, SessionLocal
from models import Base, AdminUser
from auth import get_password_hash

def init_db():
    # Create tables
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created")

    # Create default admin user
    db = SessionLocal()
    try:
        existing = db.query(AdminUser).filter(AdminUser.email == "admin@izziloan.co.za").first()
        if existing:
            print("ℹ️  Admin user already exists: admin@izziloan.co.za")
            return

        admin = AdminUser(
            email="admin@izziloan.co.za",
            hashed_password=get_password_hash("admin123"),
            full_name="Admin User",
            is_active=True,
            is_superuser=True
        )
        db.add(admin)
        db.commit()
        print("✅ Admin user created: admin@izziloan.co.za / admin123")
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
