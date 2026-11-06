from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
from database import engine, Base
from routers import public, admin, auth
import os

templates = Jinja2Templates(directory="/home/bongani/izziloan/templates")

# Create tables
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 izziloan API starting up...")
    yield
    print("👋 izziloan API shutting down...")

app = FastAPI(
    title="izziloan API",
    description="Full-stack loan management platform",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/admin/static", StaticFiles(directory="admin/static"), name="admin-static")

# Include routers
app.include_router(public.router)
app.include_router(admin.router)
app.include_router(auth.router)

# Serve the main landing page
@app.get("/", response_class=FileResponse)
async def serve_landing():
    return FileResponse("templates/index.html")

# Applicant Profile Pages
@app.get("/profile", response_class=HTMLResponse)
async def profile_lookup(request: Request):
    return templates.TemplateResponse(request, "profile-lookup.html", {"request": request})

@app.get("/profile/{app_id}", response_class=HTMLResponse)
async def profile_detail(request: Request, app_id: int):
    return templates.TemplateResponse(request, "profile.html", {"request": request, "app_id": app_id})

# Phone Access Helper
@app.get("/phone-access", response_class=HTMLResponse)
async def phone_access(request: Request):
    return templates.TemplateResponse(request, "phone-access.html", {"request": request})

# Health
@app.get("/health")
async def health():
    return {"status": "ok"}
