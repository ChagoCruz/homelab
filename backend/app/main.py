import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import journal, tarot, bills, car_mileage, expenses, income  # later: expenses, bills, etc.

app = FastAPI(title="Homelab API")

# --- CORS ---
raw_origins = os.environ.get("CORS_ALLOWED_ORIGINS", "")
allow_origins = [o.strip() for o in raw_origins.split(",") if o.strip()] or [
    "http://localhost:3000",
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routers ---
app.include_router(journal.router)  # becomes /journal/...
app.include_router(tarot.router)  # becomes /tarot/...
app.include_router(bills.router) 
app.include_router(car_mileage.router) 
app.include_router(expenses.router) 
app.include_router(income.router) 

@app.get("/")
def root():
    return {"name": "homelab-api", "status": "ok"}

@app.get("/health")
def health():
    return {"ok": True}
