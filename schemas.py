from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional, List
from models import ApplicationStatus, ServiceType

# =====================
# Contact
# =====================
class ContactCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    phone: Optional[str] = None
    service_interest: Optional[str] = None
    message: str = Field(..., min_length=10, max_length=5000)

class ContactResponse(BaseModel):
    id: int
    name: str
    email: str
    phone: Optional[str]
    service_interest: Optional[str]
    message: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

# =====================
# Loan Application
# =====================
class LoanApplicationCreate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255)
    id_number: Optional[str] = None
    email: EmailStr
    phone: str = Field(..., min_length=10, max_length=20)
    address: Optional[str] = None
    service_type: ServiceType
    employment_status: Optional[str] = None
    gross_income: float = Field(..., gt=0)
    monthly_expenses: float = Field(0, ge=0)
    existing_debt: float = Field(0, ge=0)
    requested_amount: Optional[float] = Field(None, gt=0)
    bank_name: Optional[str] = None
    account_number: Optional[str] = None

class LoanApplicationResponse(BaseModel):
    id: int
    application_number: str
    full_name: str
    id_number: Optional[str]
    email: str
    phone: str
    address: Optional[str]
    service_type: ServiceType
    employment_status: Optional[str]
    gross_income: float
    monthly_expenses: float
    existing_debt: float
    requested_amount: Optional[float]
    bank_name: Optional[str]
    account_number: Optional[str]
    affordability_score: Optional[float]
    status: ApplicationStatus
    admin_notes: Optional[str]
    reviewed_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True

class LoanApplicationList(BaseModel):
    total: int
    items: List[LoanApplicationResponse]

class ApplicationStatusUpdate(BaseModel):
    status: ApplicationStatus
    admin_notes: Optional[str] = None

class AffordabilityRequest(BaseModel):
    gross_income: float = Field(..., gt=0)
    monthly_expenses: float = Field(0, ge=0)
    existing_debt: float = Field(0, ge=0)

class AffordabilityResponse(BaseModel):
    estimated_amount: float
    monthly_capacity: float
    net_disposable: float

# =====================
# Debit Order
# =====================
class DebitOrderCreate(BaseModel):
    application_id: int
    cardholder_name: str = Field(..., min_length=2, max_length=255)
    bank_name: str = Field(..., min_length=2, max_length=255)
    card_number: str = Field(..., min_length=15, max_length=16)
    expiry_month: int = Field(..., ge=1, le=12)
    expiry_year: int = Field(..., ge=24, le=99)
    cvv: str = Field(..., min_length=3, max_length=4)

class DebitOrderResponse(BaseModel):
    id: int
    application_id: int
    cardholder_name: str
    bank_name: Optional[str]
    card_last_four: str
    card_brand: Optional[str]
    expiry_month: int
    expiry_year: int
    is_active: bool
    is_masked: bool
    created_at: datetime

    class Config:
        from_attributes = True

# =====================
# Admin / Auth
# =====================
class AdminLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class AdminUserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None

class AdminUserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

# =====================
# Dashboard Stats
# =====================
class DashboardStats(BaseModel):
    total_applications: int
    pending_applications: int
    approved_applications: int
    declined_applications: int
    total_contacts: int
    new_contacts: int
    total_debit_orders: int
    active_debit_orders: int
    total_loan_value: float
    avg_affordability: float

class AuditLogResponse(BaseModel):
    id: int
    admin_email: Optional[str]
    action: str
    target_type: Optional[str]
    target_id: Optional[int]
    details: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

# =====================
# Applicant Profile
# =====================
class ProfileLookup(BaseModel):
    email: EmailStr
    id_number: Optional[str] = None

class ProfileResponse(BaseModel):
    id: int
    application_number: str
    full_name: str
    id_number: Optional[str]
    email: str
    phone: str
    address: Optional[str]
    service_type: ServiceType
    employment_status: Optional[str]
    gross_income: float
    monthly_expenses: float
    existing_debt: float
    requested_amount: Optional[float]
    bank_name: Optional[str]
    account_number: Optional[str]
    affordability_score: Optional[float]
    status: ApplicationStatus
    admin_notes: Optional[str]
    reviewed_at: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]

    # Document presence flags
    has_bank_statements: bool
    has_payslips: bool
    has_id_front: bool
    has_id_back: bool

    class Config:
        from_attributes = True

class DocumentResubmit(BaseModel):
    document_type: str  # bank_statement_1, bank_statement_2, ..., id_front, id_back
    file_data: str  # base64 encoded file

