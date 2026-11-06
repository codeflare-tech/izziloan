from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timedelta
from database import get_db
from models import (
    AdminUser, LoanApplication, ContactSubmission,
    DebitOrder, AuditLog, ApplicationStatus, ServiceType
)
from schemas import (
    LoanApplicationList, LoanApplicationResponse, DashboardStats,
    ApplicationStatusUpdate, AuditLogResponse, ContactResponse,
    DebitOrderResponse
)
from auth import get_current_user, get_current_active_superuser
from typing import Optional

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="/home/bongani/izziloan/admin/templates")

# =====================
# Admin Login Page
# =====================
@router.get("/login", response_class=HTMLResponse)
async def admin_login(request: Request):
    return templates.TemplateResponse(request, "login.html", {"request": request})

@router.post("/logout")
async def admin_logout(response: Response):
    response.delete_cookie("admin_access_token")
    return {"detail": "Logged out"}

# =====================
# Admin Dashboard Page
# =====================
@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(request: Request, db: Session = Depends(get_db), current_user: AdminUser = Depends(get_current_active_superuser)):
    total_apps = db.query(LoanApplication).count()
    pending_apps = db.query(LoanApplication).filter(LoanApplication.status == ApplicationStatus.pending).count()
    total_contacts = db.query(ContactSubmission).count()
    new_contacts = db.query(ContactSubmission).filter(ContactSubmission.status == "new").count()
    total_debit_orders = db.query(DebitOrder).count()
    active_debit_orders = db.query(DebitOrder).filter(DebitOrder.is_active == True).count()

    recent_apps = db.query(LoanApplication).order_by(desc(LoanApplication.created_at)).limit(10).all()
    recent_contacts = db.query(ContactSubmission).order_by(desc(ContactSubmission.created_at)).limit(10).all()
    recent_debit_orders = db.query(DebitOrder).order_by(desc(DebitOrder.created_at)).limit(10).all()

    return templates.TemplateResponse(request, "dashboard.html", {
        "request": request,
        "total_apps": total_apps,
        "pending_apps": pending_apps,
        "total_contacts": total_contacts,
        "new_contacts": new_contacts,
        "total_debit_orders": total_debit_orders,
        "active_debit_orders": active_debit_orders,
        "recent_apps": recent_apps,
        "recent_contacts": recent_contacts,
        "recent_debit_orders": recent_debit_orders,
        "user": None
    })

# =====================
# Applications Page
# =====================
@router.get("/applications", response_class=HTMLResponse)
async def admin_applications(request: Request, db: Session = Depends(get_db), current_user: AdminUser = Depends(get_current_active_superuser)):
    page = int(request.query_params.get("page", 1))
    per_page = 20
    skip = (page - 1) * per_page

    total = db.query(LoanApplication).count()
    apps = db.query(LoanApplication).order_by(desc(LoanApplication.created_at)).offset(skip).limit(per_page).all()
    total_pages = (total + per_page - 1) // per_page

    return templates.TemplateResponse(request, "applications.html", {
        "request": request,
        "apps": apps,
        "page": page,
        "total_pages": total_pages,
        "total": total,
        "new_contacts": db.query(ContactSubmission).filter(ContactSubmission.status == "new").count()
    })

# =====================
# Contacts Page
# =====================
@router.get("/contacts", response_class=HTMLResponse)
async def admin_contacts(request: Request, db: Session = Depends(get_db), current_user: AdminUser = Depends(get_current_active_superuser)):
    contacts = db.query(ContactSubmission).order_by(desc(ContactSubmission.created_at)).limit(100).all()
    return templates.TemplateResponse(request, "contacts.html", {
        "request": request,
        "contacts": contacts,
        "new_contacts": db.query(ContactSubmission).filter(ContactSubmission.status == "new").count()
    })

# =====================
# Debit Orders Page
# =====================
@router.get("/debit-orders", response_class=HTMLResponse)
async def admin_debit_orders(request: Request, db: Session = Depends(get_db), current_user: AdminUser = Depends(get_current_active_superuser)):
    orders = db.query(DebitOrder).order_by(desc(DebitOrder.created_at)).limit(100).all()
    return templates.TemplateResponse(request, "debit-orders.html", {
        "request": request,
        "orders": orders,
        "new_contacts": db.query(ContactSubmission).filter(ContactSubmission.status == "new").count()
    })

# =====================
# Audit Logs Page
# =====================
@router.get("/audit", response_class=HTMLResponse)
async def admin_audit(request: Request, db: Session = Depends(get_db), current_user: AdminUser = Depends(get_current_active_superuser)):
    logs = db.query(AuditLog).order_by(desc(AuditLog.created_at)).limit(200).all()
    return templates.TemplateResponse(request, "audit.html", {
        "request": request,
        "logs": logs,
        "new_contacts": db.query(ContactSubmission).filter(ContactSubmission.status == "new").count()
    })

# =====================
# Application Detail API
# =====================
@router.get("/api/applications", response_model=LoanApplicationList)
async def list_applications(
    page: int = 1,
    per_page: int = 20,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(LoanApplication)
    if status:
        query = query.filter(LoanApplication.status == status)

    total = query.count()
    apps = query.order_by(desc(LoanApplication.created_at)).offset((page - 1) * per_page).limit(per_page).all()
    return LoanApplicationList(total=total, items=apps)

@router.get("/api/applications/{app_id}", response_model=LoanApplicationResponse)
async def get_application(app_id: int, db: Session = Depends(get_db)):
    app = db.query(LoanApplication).filter(LoanApplication.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    return app

@router.patch("/api/applications/{app_id}", response_model=LoanApplicationResponse)
async def update_application_status(
    app_id: int,
    update: ApplicationStatusUpdate,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_active_superuser)
):
    app = db.query(LoanApplication).filter(LoanApplication.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    app.status = update.status
    app.admin_notes = update.admin_notes
    app.reviewed_by = current_user.email
    app.reviewed_at = datetime.utcnow()

    # Audit log
    log = AuditLog(
        admin_email=current_user.email,
        action="update_application",
        target_type="application",
        target_id=app.id,
        details=f"Status changed to {update.status.value}"
    )
    db.add(log)
    db.commit()
    db.refresh(app)
    return app

# =====================
# Dashboard Stats API
# =====================
@router.get("/api/stats", response_model=DashboardStats)
async def get_dashboard_stats(db: Session = Depends(get_db)):
    total_apps = db.query(LoanApplication).count()
    pending = db.query(LoanApplication).filter(LoanApplication.status == ApplicationStatus.pending).count()
    approved = db.query(LoanApplication).filter(LoanApplication.status == ApplicationStatus.approved).count()
    declined = db.query(LoanApplication).filter(LoanApplication.status == ApplicationStatus.declined).count()
    total_contacts = db.query(ContactSubmission).count()
    new_contacts = db.query(ContactSubmission).filter(ContactSubmission.status == "new").count()
    total_orders = db.query(DebitOrder).count()
    active_orders = db.query(DebitOrder).filter(DebitOrder.is_active == True).count()

    # Total loan value (approved only)
    loan_value = db.query(func.sum(LoanApplication.requested_amount)).filter(
        LoanApplication.status == ApplicationStatus.approved
    ).scalar() or 0

    # Avg affordability
    avg_afford = db.query(func.avg(LoanApplication.affordability_score)).scalar() or 0

    return DashboardStats(
        total_applications=total_apps,
        pending_applications=pending,
        approved_applications=approved,
        declined_applications=declined,
        total_contacts=total_contacts,
        new_contacts=new_contacts,
        total_debit_orders=total_orders,
        active_debit_orders=active_orders,
        total_loan_value=round(loan_value, 2),
        avg_affordability=round(avg_afford, 2)
    )

# =====================
# Contacts API
# =====================
@router.get("/api/contacts", response_model=list[ContactResponse])
async def list_contacts(db: Session = Depends(get_db)):
    return db.query(ContactSubmission).order_by(desc(ContactSubmission.created_at)).limit(100).all()

@router.patch("/api/contacts/{contact_id}", response_model=ContactResponse)
async def update_contact_status(
    contact_id: int,
    status: str,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_active_superuser)
):
    contact = db.query(ContactSubmission).filter(ContactSubmission.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    contact.status = status
    db.commit()
    db.refresh(contact)
    return contact

# =====================
# Debit Orders API
# =====================
@router.get("/api/debit-orders", response_model=list[DebitOrderResponse])
async def list_debit_orders(db: Session = Depends(get_db)):
    return db.query(DebitOrder).order_by(desc(DebitOrder.created_at)).limit(100).all()

@router.get("/api/debit-orders/{order_id}", response_model=DebitOrderResponse)
async def get_debit_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(DebitOrder).filter(DebitOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Debit order not found")
    return order

from fastapi import Body

@router.patch("/api/debit-orders/{order_id}", response_model=DebitOrderResponse)
async def update_debit_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_active_superuser),
    is_active: bool = Body(None),
    is_masked: bool = Body(None),
    admin_notes: str = Body(None)
):
    order = db.query(DebitOrder).filter(DebitOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Debit order not found")

    if is_active is not None:
        order.is_active = is_active

    if is_masked is not None:
        setattr(order, 'is_masked', is_masked)
        if is_masked:
            # Permanently clear sensitive fields on mask
            setattr(order, 'full_card_number', None)
            setattr(order, 'cvv', None)

    # Log action
    log = AuditLog(
        admin_email=current_user.email,
        action="update_debit_order",
        target_type="debit_order",
        target_id=order.id,
        details=f"Updated debit order #{order.id}"
    )
    db.add(log)
    db.commit()
    db.refresh(order)
    return order

# =====================
# Application Review Page
# =====================
@router.get("/applications/{app_id}", response_class=HTMLResponse)
async def admin_application_detail(request: Request, app_id: int, db: Session = Depends(get_db), current_user: AdminUser = Depends(get_current_active_superuser)):
    app = db.query(LoanApplication).filter(LoanApplication.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    # Get associated debit orders
    debit_orders = db.query(DebitOrder).filter(DebitOrder.application_id == app.id).all()

    return templates.TemplateResponse(request, "application-detail.html", {
        "request": request,
        "app": app,
        "debit_orders": debit_orders,
        "new_contacts": db.query(ContactSubmission).filter(ContactSubmission.status == "new").count()
    })

# =====================
# Debit Order Review Page
# =====================
@router.get("/debit-orders/{order_id}", response_class=HTMLResponse)
async def admin_debit_order_detail(request: Request, order_id: int, db: Session = Depends(get_db), current_user: AdminUser = Depends(get_current_active_superuser)):
    order = db.query(DebitOrder).filter(DebitOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Debit order not found")

    # Get associated application
    application = db.query(LoanApplication).filter(LoanApplication.id == order.application_id).first()

    return templates.TemplateResponse(request, "debit-order-detail.html", {
        "request": request,
        "order": order,
        "application": application,
        "new_contacts": db.query(ContactSubmission).filter(ContactSubmission.status == "new").count()
    })

# =====================
# Audit Log API
# =====================
@router.get("/api/audit", response_model=list[AuditLogResponse])
async def list_audit_logs(db: Session = Depends(get_db)):
    return db.query(AuditLog).order_by(desc(AuditLog.created_at)).limit(200).all()
