from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.database import db
from app.schemas.doctor import DoctorCreate, DoctorResponse, DoctorUpdate
from app.schemas.patient import PatientResponse

router = APIRouter(prefix="/doctors", tags=["Doctors"])


@router.post("", response_model=DoctorResponse, status_code=status.HTTP_201_CREATED)
def register_doctor(doctor_in: DoctorCreate):
    """Register a new doctor. Validates unique email, experience >= 0, and fee > 0."""
    email_clean = doctor_in.email.strip().lower()
    for d in db.doctors:
        if d["email"].strip().lower() == email_clean:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Doctor with email '{doctor_in.email}' already exists.",
            )

    new_doctor = doctor_in.model_dump()
    new_doctor["id"] = db.next_doctor_id()
    db.doctors.append(new_doctor)
    return new_doctor


@router.get("", response_model=List[DoctorResponse])
def get_all_doctors(
    search: Optional[str] = Query(None, description="Search doctor by name"),
    specialization: Optional[str] = Query(None, description="Filter by specialization"),
    min_experience: Optional[int] = Query(None, ge=0, description="Filter by minimum experience in years"),
    min_fee: Optional[float] = Query(None, ge=0.0, description="Minimum consultation fee"),
    max_fee: Optional[float] = Query(None, ge=0.0, description="Maximum consultation fee"),
    is_available: Optional[bool] = Query(None, description="Filter by availability status"),
    sort_by: Optional[str] = Query(None, description="Field to sort by: 'experience' or 'fee'"),
    sort_order: Optional[str] = Query("asc", description="Sort order: 'asc' or 'desc'"),
):
    """Retrieve all doctors with search, filtering, and sorting."""
    results = list(db.doctors)

    if search is not None:
        term = search.strip().lower()
        results = [d for d in results if term in d["full_name"].lower()]

    if specialization is not None:
        spec = specialization.strip().lower()
        results = [d for d in results if spec in d["specialization"].lower()]

    if min_experience is not None:
        results = [d for d in results if d["experience_years"] >= min_experience]

    if min_fee is not None:
        results = [d for d in results if d["consultation_fee"] >= min_fee]

    if max_fee is not None:
        results = [d for d in results if d["consultation_fee"] <= max_fee]

    if is_available is not None:
        results = [d for d in results if d["is_available"] == is_available]

    # Sorting
    if sort_by is not None:
        key_name = None
        s_by = sort_by.strip().lower()
        if s_by in ("experience", "experience_years"):
            key_name = "experience_years"
        elif s_by in ("fee", "consultation_fee"):
            key_name = "consultation_fee"

        if key_name:
            reverse = (sort_order or "").strip().lower() == "desc"
            results = sorted(results, key=lambda x: x[key_name], reverse=reverse)

    return results


@router.get("/{doctor_id}", response_model=DoctorResponse)
def get_doctor_by_id(doctor_id: int):
    """Get doctor details by ID."""
    doctor = db.get_doctor(doctor_id)
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Doctor with ID {doctor_id} not found.",
        )
    return doctor


@router.put("/{doctor_id}", response_model=DoctorResponse)
def update_doctor(doctor_id: int, doctor_in: DoctorUpdate):
    """Update doctor details."""
    doctor = db.get_doctor(doctor_id)
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Doctor with ID {doctor_id} not found.",
        )

    update_data = doctor_in.model_dump(exclude_unset=True)

    if "email" in update_data and update_data["email"]:
        new_email = update_data["email"].strip().lower()
        for d in db.doctors:
            if d["id"] != doctor_id and d["email"].strip().lower() == new_email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Doctor with email '{update_data['email']}' already exists.",
                )

    doctor.update(update_data)
    return doctor


@router.delete("/{doctor_id}")
def delete_doctor(doctor_id: int):
    """Delete a doctor by ID."""
    doctor = db.get_doctor(doctor_id)
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Doctor with ID {doctor_id} not found.",
        )
    db.doctors.remove(doctor)
    return {"message": f"Doctor with ID {doctor_id} deleted successfully", "id": doctor_id}


# --- Day 2 Patient-Doctor Relationship: Get patients assigned to a doctor ---

@router.get("/{doctor_id}/patients", response_model=List[PatientResponse])
def get_patients_for_doctor(doctor_id: int):
    """Retrieve all patients assigned to a particular doctor."""
    doctor = db.get_doctor(doctor_id)
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Doctor with ID {doctor_id} not found.",
        )

    assigned_patients = [p for p in db.patients if p.get("assigned_doctor_id") == doctor_id]
    return assigned_patients
