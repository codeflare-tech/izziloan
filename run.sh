#!/bin/bash
cd "$(dirname "$0")"
export DATABASE_URL=sqlite:///./izziloan.db
export SECRET_KEY=izziloan-secret-key-change-in-production-2024
exec python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload --ssl-keyfile=10.247.5.158+3-key.pem --ssl-certfile=10.247.5.158+3.pem
