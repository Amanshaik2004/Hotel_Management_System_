from datetime import date, datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.database import db
from app.schemas.billing import (
    BillCreate,
    BillResponse,
    BillUpdate,
    PaymentCreate,
    PaymentMethod,
    PaymentResponse,
    PaymentStatus,
)

router = APIRouter(tags=["Billing & Payments"])


def calculate_bill_totals(
    consultation_fee: float,
    medicine_charges: float,
    lab_charges: float,
    other_charges: float,
    discount: float,
    tax_percentage: float,
    paid_amount: float = 0.0,
):
    """Calculates subtotal, discount, tax, total, and balance amounts."""
    subtotal = consultation_fee + medicine_charges + lab_charges + other_charges
    if discount > subtotal:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Discount ({discount}) cannot exceed total charges ({subtotal}).",
        )

    discounted_subtotal = subtotal - discount
    tax_amount = round(discounted_subtotal * (tax_percentage / 100.0), 2)
    total_amount = round(discounted_subtotal + tax_amount, 2)
    balance_amount = round(max(0.0, total_amount - paid_amount), 2)

    if paid_amount >= total_amount and total_amount > 0:
        p_status = PaymentStatus.PAID
    elif paid_amount > 0:
        p_status = PaymentStatus.PARTIALLY_PAID
    else:
        p_status = PaymentStatus.PENDING

    return total_amount, balance_amount, p_status


@router.post("/bills", response_model=BillResponse, status_code=status.HTTP_201_CREATED)
def generate_bill(bill_in: BillCreate):
    """Generate a new bill for an appointment."""
    patient = db.get_patient(bill_in.patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with ID {bill_in.patient_id} not found.",
        )

    appointment = db.get_appointment(bill_in.appointment_id)
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment with ID {bill_in.appointment_id} not found.",
        )

    # If consultation fee wasn't specified (>0), look up doctor consultation fee
    consultation_fee = bill_in.consultation_fee
    if consultation_fee == 0.0:
        doctor = db.get_doctor(appointment["doctor_id"])
        if doctor:
            consultation_fee = doctor.get("consultation_fee", 0.0)

    total_amount, balance_amount, payment_status = calculate_bill_totals(
        consultation_fee=consultation_fee,
        medicine_charges=bill_in.medicine_charges,
        lab_charges=bill_in.lab_charges,
        other_charges=bill_in.other_charges,
        discount=bill_in.discount,
        tax_percentage=bill_in.tax_percentage,
        paid_amount=0.0,
    )

    bill_id = db.next_bill_id()
    created_at = datetime.now()
    bill_number = f"BILL-{created_at.strftime('%Y%m%d')}-{bill_id:04d}"

    new_bill = {
        "id": bill_id,
        "bill_number": bill_number,
        "patient_id": bill_in.patient_id,
        "appointment_id": bill_in.appointment_id,
        "consultation_fee": consultation_fee,
        "medicine_charges": bill_in.medicine_charges,
        "lab_charges": bill_in.lab_charges,
        "other_charges": bill_in.other_charges,
        "discount": bill_in.discount,
        "tax_percentage": bill_in.tax_percentage,
        "total_amount": total_amount,
        "paid_amount": 0.0,
        "balance_amount": balance_amount,
        "payment_status": payment_status,
        "created_at": created_at,
    }

    db.bills.append(new_bill)
    return new_bill


@router.get("/bills", response_model=List[BillResponse])
def get_all_bills(
    patient_id: Optional[int] = Query(None, description="Filter by patient ID"),
    payment_status: Optional[PaymentStatus] = Query(None, description="Filter by payment status"),
    bill_number: Optional[str] = Query(None, description="Search by bill number"),
    start_date: Optional[date] = Query(None, description="Filter bills created on or after this date"),
    end_date: Optional[date] = Query(None, description="Filter bills created on or before this date"),
    sort_by: Optional[str] = Query(None, description="Sort by: 'date' or 'total_amount'"),
    sort_order: Optional[str] = Query("asc", description="Sort order: 'asc' or 'desc'"),
):
    """Retrieve all bills with filtering and sorting."""
    results = list(db.bills)

    if patient_id is not None:
        results = [b for b in results if b["patient_id"] == patient_id]

    if payment_status is not None:
        results = [b for b in results if b["payment_status"] == payment_status]

    if bill_number is not None:
        bn_term = bill_number.strip().lower()
        results = [b for b in results if bn_term in b["bill_number"].lower()]

    if start_date is not None:
        results = [b for b in results if b["created_at"].date() >= start_date]

    if end_date is not None:
        results = [b for b in results if b["created_at"].date() <= end_date]

    if sort_by is not None:
        reverse = (sort_order or "").strip().lower() == "desc"
        s_by = sort_by.strip().lower()
        if s_by in ("date", "created_at"):
            results = sorted(results, key=lambda x: x["created_at"], reverse=reverse)
        elif s_by in ("total_amount", "amount", "total"):
            results = sorted(results, key=lambda x: x["total_amount"], reverse=reverse)

    return results


@router.get("/bills/{bill_id}", response_model=BillResponse)
def get_bill_by_id(bill_id: int):
    """Get bill details by ID."""
    bill = db.get_bill(bill_id)
    if not bill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bill with ID {bill_id} not found.",
        )
    return bill


@router.put("/bills/{bill_id}", response_model=BillResponse)
def update_bill(bill_id: int, update_in: BillUpdate):
    """Update bill charges, recompute total & balance."""
    bill = db.get_bill(bill_id)
    if not bill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bill with ID {bill_id} not found.",
        )

    update_dict = update_in.model_dump(exclude_unset=True)

    consultation_fee = update_dict.get("consultation_fee", bill["consultation_fee"])
    medicine_charges = update_dict.get("medicine_charges", bill["medicine_charges"])
    lab_charges = update_dict.get("lab_charges", bill["lab_charges"])
    other_charges = update_dict.get("other_charges", bill["other_charges"])
    discount = update_dict.get("discount", bill["discount"])
    tax_percentage = update_dict.get("tax_percentage", bill["tax_percentage"])

    total_amount, balance_amount, computed_status = calculate_bill_totals(
        consultation_fee=consultation_fee,
        medicine_charges=medicine_charges,
        lab_charges=lab_charges,
        other_charges=other_charges,
        discount=discount,
        tax_percentage=tax_percentage,
        paid_amount=bill["paid_amount"],
    )

    bill.update({
        "consultation_fee": consultation_fee,
        "medicine_charges": medicine_charges,
        "lab_charges": lab_charges,
        "other_charges": other_charges,
        "discount": discount,
        "tax_percentage": tax_percentage,
        "total_amount": total_amount,
        "balance_amount": balance_amount,
        "payment_status": update_dict.get("payment_status", computed_status),
    })

    return bill


@router.delete("/bills/{bill_id}")
def delete_bill(bill_id: int):
    """Delete a bill."""
    bill = db.get_bill(bill_id)
    if not bill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bill with ID {bill_id} not found.",
        )
    db.bills.remove(bill)
    return {"message": f"Bill with ID {bill_id} deleted successfully", "id": bill_id}


@router.get("/patients/{patient_id}/bills", response_model=List[BillResponse])
def get_patient_bills(patient_id: int):
    """Get all bills for a particular patient."""
    patient = db.get_patient(patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with ID {patient_id} not found.",
        )
    return [b for b in db.bills if b["patient_id"] == patient_id]


# --- Payment Management ---

@router.post("/bills/{bill_id}/payments", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
def record_payment(bill_id: int, payment_in: PaymentCreate):
    """Record a payment towards a bill. Supports partial payment and updates bill balance."""
    bill = db.get_bill(bill_id)
    if not bill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bill with ID {bill_id} not found.",
        )

    if bill["payment_status"] == PaymentStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot record payment against a CANCELLED bill.",
        )

    if bill["balance_amount"] <= 0.0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bill is already fully paid.",
        )

    if payment_in.amount > bill["balance_amount"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Payment amount ({payment_in.amount}) exceeds outstanding "
                f"balance ({bill['balance_amount']})."
            ),
        )

    payment_id = db.next_payment_id()
    txn_ref = payment_in.transaction_reference or f"TXN-{datetime.now().strftime('%Y%m%d%H%M%S')}-{payment_id}"

    payment = {
        "id": payment_id,
        "bill_id": bill_id,
        "amount": payment_in.amount,
        "payment_method": payment_in.payment_method,
        "transaction_reference": txn_ref,
        "payment_date": datetime.now(),
        "status": "SUCCESS",
    }
    db.payments.append(payment)

    # Update bill totals
    bill["paid_amount"] = round(bill["paid_amount"] + payment_in.amount, 2)
    bill["balance_amount"] = round(max(0.0, bill["total_amount"] - bill["paid_amount"]), 2)

    if bill["balance_amount"] <= 0.0:
        bill["payment_status"] = PaymentStatus.PAID
    else:
        bill["payment_status"] = PaymentStatus.PARTIALLY_PAID

    return payment


@router.get("/bills/{bill_id}/payments", response_model=List[PaymentResponse])
def get_bill_payment_history(bill_id: int):
    """Retrieve payment history for a specific bill."""
    bill = db.get_bill(bill_id)
    if not bill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bill with ID {bill_id} not found.",
        )
    return [p for p in db.payments if p["bill_id"] == bill_id]


@router.get("/payments", response_model=List[PaymentResponse])
def get_all_payments(
    payment_method: Optional[PaymentMethod] = Query(None, description="Filter payments by payment method"),
):
    """Get all recorded payments with optional method filter."""
    results = list(db.payments)
    if payment_method is not None:
        results = [p for p in results if p["payment_method"] == payment_method]
    return results


@router.get("/payments/{payment_id}", response_model=PaymentResponse)
def get_payment_details(payment_id: int):
    """Retrieve details of a single payment by payment ID."""
    payment = db.get_payment(payment_id)
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment with ID {payment_id} not found.",
        )
    return payment
