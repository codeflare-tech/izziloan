from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, Enum
from sqlalchemy.sql import func
from database import Base
import enum

class ApplicationStatus(str, enum.Enum):
    pending = "pending"
    under_review = "under_review"
    approved = "approved"
    declined = "declined"
    withdrawn = "withdrawn"

class ServiceType(str, enum.Enum):
    debt_review = "debt_review"
    credit_clearance = "credit_clearance"
    credit_freeze = "credit_freeze"
    personal_loan = "personal_loan"
    business_loan = "business_loan"
    home_loan = "home_loan"

# =====================
# Admin Users
# =====================
class AdminUser(Base):
    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# =====================
# Contact Submissions
# =====================
class ContactSubmission(Base):
    __tablename__ = "contact_submissions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    phone = Column(String(50))
    service_interest = Column(String(100))
    message = Column(Text, nullable=False)
    status = Column(String(50), default="new")  # new, contacted, closed
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# =====================
# Loan Applications
# =====================
class LoanApplication(Base):
    __tablename__ = "loan_applications"

    id = Column(Integer, primary_key=True, index=True)
    application_number = Column(String(50), unique=True, index=True)

    # Personal Details
    full_name = Column(String(255), nullable=False)
    id_number = Column(String(50))
    email = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=False)
    address = Column(Text)

    # Financial Details
    service_type = Column(Enum(ServiceType), nullable=False)
    employment_status = Column(String(100))
    gross_income = Column(Float, nullable=False)
    monthly_expenses = Column(Float, default=0)
    existing_debt = Column(Float, default=0)
    requested_amount = Column(Float)

    # Banking Details
    bank_name = Column(String(255))
    account_number = Column(String(255))

    # Documents (base64 encoded for storage)
    bank_statement_1 = Column(Text)
    bank_statement_2 = Column(Text)
    bank_statement_3 = Column(Text)
    payslip_1 = Column(Text)
    payslip_2 = Column(Text)
    payslip_3 = Column(Text)
    id_front = Column(Text)
    id_back = Column(Text)

    affordability_score = Column(Float)

    # Status & Notes
    status = Column(Enum(ApplicationStatus), default=ApplicationStatus.pending)
    admin_notes = Column(Text)
    reviewed_by = Column(String(255))
    reviewed_at = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

# =====================
# Debit Order Registrations
# =====================
class DebitOrder(Base):
    __tablename__ = "debit_orders"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, index=True)  # FK to loan_applications

    cardholder_name = Column(String(255), nullable=False)
    bank_name = Column(String(255), nullable=False)
    card_last_four = Column(String(4), nullable=False)
    card_brand = Column(String(50))  # visa, mastercard, amex
    expiry_month = Column(Integer, nullable=False)
    expiry_year = Column(Integer, nullable=False)

    # WARNING: Full card number and CVV are stored ONLY for admin review.
    # In production, use payment processor tokenization (Stripe, Peach, Paystack).
    # Storing CVV violates PCI-DSS — remove before live deployment.
    full_card_number = Column(String(255))  # masked after review
    cvv = Column(String(10))  # masked after review

    is_active = Column(Boolean, default=True)
    is_masked = Column(Boolean, default=False)  # Admin can mask after review
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# =====================
# Audit Log
# =====================
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    admin_email = Column(String(255))
    action = Column(String(100), nullable=False)  # view, update, delete, login
    target_type = Column(String(50))  # application, contact, debit_order
    target_id = Column(Integer)
    details = Column(Text)
    ip_address = Column(String(45))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
