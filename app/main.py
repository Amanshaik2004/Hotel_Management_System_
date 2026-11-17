from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import db
from app.routers import appointments, bills, doctors, lab, medicines, patients

app = FastAPI(
    title="Hospital Management System API",
    description="""
A comprehensive REST API built with FastAPI managing:
- **Day 1: Patients** (Registration, CRUD, Age/Blood Group/Gender filters)
- **Day 2: Doctors** (Profile, CRUD, Specialization/Fee filters, Doctor-Patient assignment)
- **Day 3: Appointments** (Booking, Availability check, Double-booking prevention, Cancellation)
- **Day 4: Billing & Payments** (Automatic calculations, Taxes, Discounts, Partial payments)
- **Day 5: Medicines & Pharmacy** (Inventory stock management, Expiry & Low-stock alerts, Dispensing/Sales)
- **Day 6: Laboratory & Diagnostic Tests** (Test catalog, Lab test orders, Result recording, Patient lab history)

All data is managed in-memory using Python lists per project requirements.
    """,
    version="1.0.0",
)

# Enable CORS for frontend integration / Swagger UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all module routers
app.include_router(patients.router)
app.include_router(doctors.router)
app.include_router(appointments.router)
app.include_router(bills.router)
app.include_router(medicines.router)
app.include_router(lab.router)


@app.get("/", tags=["General"])
def root():
    """Root health check and documentation pointers."""
    return {
        "message": "Welcome to the Hospital Management System API",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "modules": [
            "Patients (/patients)",
            "Doctors (/doctors)",
            "Appointments (/appointments)",
            "Billing & Payments (/bills, /payments)",
            "Medicines & Pharmacy (/medicines, /medicine-sales)",
            "Laboratory Tests & Orders (/lab-tests, /lab-orders, /lab-results)",
        ],
        "statistics": {
            "total_patients": len(db.patients),
            "total_doctors": len(db.doctors),
            "total_appointments": len(db.appointments),
            "total_bills": len(db.bills),
            "total_medicines": len(db.medicines),
            "total_lab_tests": len(db.lab_tests),
            "total_lab_orders": len(db.lab_orders),
            "total_lab_results": len(db.lab_results),
        },
    }


@app.post("/seed-data", tags=["General"])
def populate_demo_data():
    """Helper endpoint to populate sample hospital data for demonstration in Swagger UI."""
    db.seed_sample_data()
    return {
        "message": "Sample hospital data successfully seeded.",
        "counts": {
            "patients": len(db.patients),
            "doctors": len(db.doctors),
            "appointments": len(db.appointments),
            "bills": len(db.bills),
            "medicines": len(db.medicines),
            "lab_tests": len(db.lab_tests),
            "lab_orders": len(db.lab_orders),
            "lab_results": len(db.lab_results),
        },
    }


@app.post("/reset-data", tags=["General"])
def reset_database():
    """Helper endpoint to completely clear all in-memory lists."""
    db.reset()
    return {"message": "In-memory database has been cleared."}
