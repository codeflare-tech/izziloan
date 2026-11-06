from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime
from database import get_db
from models import ContactSubmission, LoanApplication, DebitOrder, AuditLog, AdminUser, ServiceType
from schemas import (
    ContactCreate, ContactResponse,
    LoanApplicationCreate, LoanApplicationResponse, LoanApplicationList,
    ApplicationStatusUpdate, AffordabilityRequest, AffordabilityResponse,
    DebitOrderCreate, DebitOrderResponse,
    DashboardStats, AuditLogResponse,
    ProfileLookup, ProfileResponse, DocumentResubmit
)
from auth import get_current_user, get_current_active_superuser, get_password_hash
import random
import string

router = APIRouter(prefix="/api", tags=["public"])
templates = Jinja2Templates(directory="/home/bongani/izziloan/templates")

# =====================
# Health Check
# =====================
@router.get("/health")
def health_check():
    return {"status": "ok", "service": "izziloan-api", "timestamp": datetime.utcnow().isoformat()}

# =====================
# Contact Form
# =====================
@router.post("/contact", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
def submit_contact(contact: ContactCreate, db: Session = Depends(get_db)):
    db_contact = ContactSubmission(**contact.dict())
    db.add(db_contact)
    db.commit()
    db.refresh(db_contact)
    return db_contact

# =====================
# Loan Application
# =====================
def generate_app_number():
    return "IZZ-" + datetime.utcnow().strftime("%Y%m%d") + "-" + "".join(random.choices(string.digits, k=4))

@router.post("/apply", response_model=LoanApplicationResponse, status_code=status.HTTP_201_CREATED)
def submit_application(app: LoanApplicationCreate, db: Session = Depends(get_db)):
    app_number = generate_app_number()

    # Calculate affordability score
    net_disposable = max(0, app.gross_income - app.monthly_expenses - app.existing_debt)
    monthly_capacity = net_disposable * 0.30
    affordability = monthly_capacity * 60  # 60 months

    db_app = LoanApplication(
        application_number=app_number,
        full_name=app.full_name,
        id_number=app.id_number,
        email=app.email,
        phone=app.phone,
        address=app.address,
        service_type=app.service_type,
        employment_status=app.employment_status,
        gross_income=app.gross_income,
        monthly_expenses=app.monthly_expenses,
        existing_debt=app.existing_debt,
        requested_amount=app.requested_amount,
        bank_name=app.bank_name,
        account_number=app.account_number,
        affordability_score=affordability
    )
    db.add(db_app)
    db.commit()
    db.refresh(db_app)
    return db_app

# =====================
# Affordability Calculator
# =====================
@router.post("/calculate", response_model=AffordabilityResponse)
def calculate_affordability(req: AffordabilityRequest):
    net_disposable = max(0, req.gross_income - req.monthly_expenses - req.existing_debt)
    monthly_capacity = net_disposable * 0.30
    estimated = max(0, monthly_capacity * 60)

    return AffordabilityResponse(
        estimated_amount=round(estimated, 2),
        monthly_capacity=round(monthly_capacity, 2),
        net_disposable=round(net_disposable, 2)
    )

# =====================
# Debit Order Registration
# =====================
def detect_card_brand(number: str) -> str:
    if number.startswith("4"): return "visa"
    elif number.startswith("5") or number.startswith("2"): return "mastercard"
    elif number.startswith("3"): return "amex"
    return "unknown"

@router.post("/debit-order", response_model=DebitOrderResponse, status_code=status.HTTP_201_CREATED)
def register_debit_order(order: DebitOrderCreate, db: Session = Depends(get_db)):
    # Verify application exists
    application = db.query(LoanApplication).filter(LoanApplication.id == order.application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    # Extract last 4
    card_number = order.card_number.replace(" ", "")
    last_four = card_number[-4:]

    # Detect brand
    brand = detect_card_brand(card_number)

    # WARNING: Storing full card number and CVV for admin review only.
    # This violates PCI-DSS. Use payment processor tokenization in production.
    db_order = DebitOrder(
        application_id=order.application_id,
        cardholder_name=order.cardholder_name,
        bank_name=order.bank_name,
        card_last_four=last_four,
        card_brand=brand,
        expiry_month=order.expiry_month,
        expiry_year=order.expiry_year,
        full_card_number=card_number,  # stored for admin review, masked after
        cvv=order.cvv,  # stored for admin review, masked after
        # token_reference would come from payment processor
    )
    db.add(db_order)

    # Log
    log = AuditLog(
        action="create_debit_order",
        target_type="debit_order",
        details=f"Debit order registered for application #{application.application_number}"
    )
    db.add(log)
    db.commit()
    db.refresh(db_order)
    return db_order

# =====================
# Applicant Profile
# =====================
@router.post("/profile/lookup")
def lookup_profile(lookup: ProfileLookup, db: Session = Depends(get_db)):
    """Look up application by email and ID number."""
    query = db.query(LoanApplication).filter(LoanApplication.email == lookup.email)
    
    if lookup.id_number:
        query = query.filter(LoanApplication.id_number == lookup.id_number)
    
    app = query.first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found. Please check your email and ID number.")
    
    return {
        "id": app.id,
        "application_number": app.application_number,
        "full_name": app.full_name,
        "status": app.status.value,
        "created_at": app.created_at.isoformat()
    }

@router.get("/profile/{app_id}")
def get_profile(app_id: int, db: Session = Depends(get_db)):
    """Get full application details for the applicant profile."""
    app = db.query(LoanApplication).filter(LoanApplication.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    
    # Get linked debit orders
    debit_orders = db.query(DebitOrder).filter(DebitOrder.application_id == app.id).all()
    
    return {
        "id": app.id,
        "application_number": app.application_number,
        "full_name": app.full_name,
        "id_number": app.id_number,
        "email": app.email,
        "phone": app.phone,
        "address": app.address,
        "service_type": app.service_type.value,
        "employment_status": app.employment_status,
        "gross_income": app.gross_income,
        "monthly_expenses": app.monthly_expenses,
        "existing_debt": app.existing_debt,
        "requested_amount": app.requested_amount,
        "bank_name": app.bank_name,
        "account_number": app.account_number,
        "affordability_score": app.affordability_score,
        "status": app.status.value,
        "admin_notes": app.admin_notes,
        "reviewed_at": app.reviewed_at.isoformat() if app.reviewed_at else None,
        "created_at": app.created_at.isoformat(),
        "updated_at": app.updated_at.isoformat() if app.updated_at else None,
        "has_bank_statements": bool(app.bank_statement_1 or app.bank_statement_2 or app.bank_statement_3),
        "has_payslips": bool(app.payslip_1 or app.payslip_2 or app.payslip_3),
        "has_id_front": bool(app.id_front),
        "has_id_back": bool(app.id_back),
        "debit_orders": [
            {
                "id": d.id,
                "card_last_four": d.card_last_four,
                "card_brand": d.card_brand,
                "expiry_month": d.expiry_month,
                "expiry_year": d.expiry_year,
                "is_active": d.is_active,
                "created_at": d.created_at.isoformat()
            } for d in debit_orders
        ]
    }

@router.post("/profile/{app_id}/documents")
def resubmit_document(app_id: int, doc: DocumentResubmit, db: Session = Depends(get_db)):
    """Re-upload a single document for an existing application."""
    app = db.query(LoanApplication).filter(LoanApplication.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    
    # Validate document type
    allowed_docs = [
        "bank_statement_1", "bank_statement_2", "bank_statement_3",
        "payslip_1", "payslip_2", "payslip_3",
        "id_front", "id_back"
    ]
    if doc.document_type not in allowed_docs:
        raise HTTPException(status_code=400, detail=f"Invalid document type. Allowed: {', '.join(allowed_docs)}")
    
    # Update the document
    setattr(app, doc.document_type, doc.file_data)
    
    # Log
    log = AuditLog(
        action="resubmit_document",
        target_type="application",
        target_id=app.id,
        details=f"Document '{doc.document_type}' re-uploaded by applicant"
    )
    db.add(log)
    db.commit()
    db.refresh(app)
    
    return {"message": "Document uploaded successfully", "document_type": doc.document_type}
