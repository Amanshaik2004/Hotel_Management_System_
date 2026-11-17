from datetime import date, datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.database import db
from app.schemas.medicine import (
    MedicineCreate,
    MedicineResponse,
    MedicineSaleCreate,
    MedicineSaleResponse,
    MedicineUpdate,
    StockAdjustment,
)

router = APIRouter(tags=["Medicines & Pharmacy"])


def format_medicine_response(med: dict) -> dict:
    """Helper to populate computed field is_low_stock."""
    res = dict(med)
    res["is_low_stock"] = res["quantity"] <= res["minimum_stock"]
    return res


# Note: Specific routes like /medicines/low-stock and /medicines/expiring
# must appear BEFORE /medicines/{medicine_id} in path resolution.

@router.post("/medicines", response_model=MedicineResponse, status_code=status.HTTP_201_CREATED)
def add_medicine(med_in: MedicineCreate):
    """Add a new medicine to inventory."""
    med_data = med_in.model_dump()
    med_data["id"] = db.next_medicine_id()
    db.medicines.append(med_data)
    return format_medicine_response(med_data)


@router.get("/medicines/low-stock", response_model=List[MedicineResponse])
def get_low_stock_medicines():
    """Retrieve medicines where current quantity is less than or equal to minimum stock."""
    low_stock = [format_medicine_response(m) for m in db.medicines if m["quantity"] <= m["minimum_stock"]]
    return low_stock


@router.get("/medicines/expiring", response_model=List[MedicineResponse])
def get_expiring_medicines(
    days: int = Query(30, ge=1, description="Number of days to look ahead for expiry"),
):
    """Identify medicines expiring within the specified days (default: next 30 days)."""
    today = date.today()
    target_cutoff = today + timedelta(days=days)

    expiring = [
        format_medicine_response(m)
        for m in db.medicines
        if today <= m["expiry_date"] <= target_cutoff
    ]
    return expiring


@router.get("/medicines", response_model=List[MedicineResponse])
def get_all_medicines(
    search: Optional[str] = Query(None, description="Search by medicine name (case-insensitive)"),
    category: Optional[str] = Query(None, description="Filter by category"),
    manufacturer: Optional[str] = Query(None, description="Filter by manufacturer"),
    min_price: Optional[float] = Query(None, ge=0.0, description="Minimum unit price"),
    max_price: Optional[float] = Query(None, ge=0.0, description="Maximum unit price"),
    expiry_before: Optional[date] = Query(None, description="Filter medicines expiring on or before this date"),
    expiry_after: Optional[date] = Query(None, description="Filter medicines expiring on or after this date"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    sort_by: Optional[str] = Query(None, description="Sort by: 'price', 'quantity', or 'expiry_date'"),
    sort_order: Optional[str] = Query("asc", description="Sort order: 'asc' or 'desc'"),
):
    """Retrieve all medicines with search, filtering, and sorting."""
    results = list(db.medicines)

    if search is not None:
        term = search.strip().lower()
        results = [m for m in results if term in m["medicine_name"].lower()]

    if category is not None:
        cat = category.strip().lower()
        results = [m for m in results if cat in m["category"].lower()]

    if manufacturer is not None:
        man = manufacturer.strip().lower()
        results = [m for m in results if man in m["manufacturer"].lower()]

    if min_price is not None:
        results = [m for m in results if m["unit_price"] >= min_price]

    if max_price is not None:
        results = [m for m in results if m["unit_price"] <= max_price]

    if expiry_before is not None:
        results = [m for m in results if m["expiry_date"] <= expiry_before]

    if expiry_after is not None:
        results = [m for m in results if m["expiry_date"] >= expiry_after]

    if is_active is not None:
        results = [m for m in results if m["is_active"] == is_active]

    if sort_by is not None:
        reverse = (sort_order or "").strip().lower() == "desc"
        s_by = sort_by.strip().lower()
        if s_by in ("price", "unit_price"):
            results = sorted(results, key=lambda x: x["unit_price"], reverse=reverse)
        elif s_by == "quantity":
            results = sorted(results, key=lambda x: x["quantity"], reverse=reverse)
        elif s_by in ("expiry", "expiry_date"):
            results = sorted(results, key=lambda x: x["expiry_date"], reverse=reverse)

    return [format_medicine_response(m) for m in results]


@router.get("/medicines/{medicine_id}", response_model=MedicineResponse)
def get_medicine_by_id(medicine_id: int):
    """Get medicine details by ID."""
    med = db.get_medicine(medicine_id)
    if not med:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Medicine with ID {medicine_id} not found.",
        )
    return format_medicine_response(med)


@router.put("/medicines/{medicine_id}", response_model=MedicineResponse)
def update_medicine(medicine_id: int, med_in: MedicineUpdate):
    """Update medicine details."""
    med = db.get_medicine(medicine_id)
    if not med:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Medicine with ID {medicine_id} not found.",
        )

    update_data = med_in.model_dump(exclude_unset=True)
    med.update(update_data)
    return format_medicine_response(med)


@router.delete("/medicines/{medicine_id}")
def delete_medicine(medicine_id: int):
    """Delete a medicine from inventory."""
    med = db.get_medicine(medicine_id)
    if not med:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Medicine with ID {medicine_id} not found.",
        )
    db.medicines.remove(med)
    return {"message": f"Medicine with ID {medicine_id} deleted successfully", "id": medicine_id}


# --- Stock Management ---

@router.patch("/medicines/{medicine_id}/stock/add", response_model=MedicineResponse)
def add_stock(medicine_id: int, adj: StockAdjustment):
    """Add stock to a medicine."""
    med = db.get_medicine(medicine_id)
    if not med:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Medicine with ID {medicine_id} not found.",
        )

    med["quantity"] += adj.quantity
    return format_medicine_response(med)


@router.patch("/medicines/{medicine_id}/stock/reduce", response_model=MedicineResponse)
def reduce_stock(medicine_id: int, adj: StockAdjustment):
    """Reduce medicine stock. Prevents reduction beyond available quantity."""
    med = db.get_medicine(medicine_id)
    if not med:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Medicine with ID {medicine_id} not found.",
        )

    if adj.quantity > med["quantity"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot reduce {adj.quantity} units. Available stock is only {med['quantity']} units."
            ),
        )

    med["quantity"] -= adj.quantity
    return format_medicine_response(med)


# --- Medicine Sales Management ---

@router.post("/medicine-sales", response_model=MedicineSaleResponse, status_code=status.HTTP_201_CREATED)
def sell_medicine(sale_in: MedicineSaleCreate):
    """Process a medicine sale to a patient, update inventory, and log transaction."""
    med = db.get_medicine(sale_in.medicine_id)
    if not med:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Medicine with ID {sale_in.medicine_id} not found.",
        )

    patient = db.get_patient(sale_in.patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with ID {sale_in.patient_id} not found.",
        )

    if not med.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Medicine '{med['medicine_name']}' is currently marked as inactive and cannot be sold.",
        )

    if med["expiry_date"] < date.today():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot sell expired medicine '{med['medicine_name']}'. "
                f"Expired on {med['expiry_date']}."
            ),
        )

    if sale_in.quantity_sold > med["quantity"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Insufficient stock for '{med['medicine_name']}'. "
                f"Requested: {sale_in.quantity_sold}, Available: {med['quantity']}."
            ),
        )

    # Deduct stock
    med["quantity"] -= sale_in.quantity_sold

    total_amount = round(sale_in.quantity_sold * med["unit_price"], 2)
    sale_id = db.next_sale_id()

    sale_record = {
        "id": sale_id,
        "medicine_id": sale_in.medicine_id,
        "patient_id": sale_in.patient_id,
        "quantity_sold": sale_in.quantity_sold,
        "unit_price": med["unit_price"],
        "total_amount": total_amount,
        "sale_date": datetime.now(),
    }
    db.medicine_sales.append(sale_record)

    return sale_record


@router.get("/medicine-sales", response_model=List[MedicineSaleResponse])
def get_all_sales():
    """Retrieve all medicine sales records."""
    return db.medicine_sales


@router.get("/medicine-sales/{sale_id}", response_model=MedicineSaleResponse)
def get_sale_by_id(sale_id: int):
    """Get sale details by ID."""
    sale = db.get_sale(sale_id)
    if not sale:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Medicine sale with ID {sale_id} not found.",
        )
    return sale


@router.get("/patients/{patient_id}/medicine-sales", response_model=List[MedicineSaleResponse])
def get_patient_medicine_sales(patient_id: int):
    """Retrieve all medicine purchase history for a patient."""
    patient = db.get_patient(patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with ID {patient_id} not found.",
        )
    return [s for s in db.medicine_sales if s["patient_id"] == patient_id]
