from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.database import db
from app.schemas.doctor import DoctorResponse
from app.schemas.patient import PatientCreate, PatientResponse, PatientUpdate

router = APIRouter(prefix="/patients", tags=["Patients"])


@router.post("", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
def register_patient(patient_in: PatientCreate):
    """Register a new patient. Validates email uniqueness."""
    email_clean = patient_in.email.strip().lower()
    for p in db.patients:
        if p["email"].strip().lower() == email_clean:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Patient with email '{patient_in.email}' already exists.",
            )

    new_patient = patient_in.model_dump()
    new_patient["id"] = db.next_patient_id()
    new_patient["assigned_doctor_id"] = None
    db.patients.append(new_patient)
    return new_patient


@router.get("", response_model=List[PatientResponse])
def get_all_patients(
    gender: Optional[str] = Query(None, description="Filter by gender (Male, Female, Other)"),
    blood_group: Optional[str] = Query(None, description="Filter by blood group (e.g., A+, O-)"),
    min_age: Optional[int] = Query(None, ge=1, le=120, description="Filter by minimum age"),
    max_age: Optional[int] = Query(None, ge=1, le=120, description="Filter by maximum age"),
    search: Optional[str] = Query(None, description="Search by patient name (case-insensitive)"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
):
    """Retrieve all patients with optional search and filtering."""
    results = db.patients

    if gender is not None:
        results = [p for p in results if p["gender"].lower() == gender.strip().lower()]

    if blood_group is not None:
        results = [p for p in results if p["blood_group"].lower() == blood_group.strip().lower()]

    if min_age is not None:
        results = [p for p in results if p["age"] >= min_age]

    if max_age is not None:
        results = [p for p in results if p["age"] <= max_age]

    if search is not None:
        term = search.strip().lower()
        results = [p for p in results if term in p["full_name"].lower()]

    if is_active is not None:
        results = [p for p in results if p["is_active"] == is_active]

    return results


@router.get("/{patient_id}", response_model=PatientResponse)
def get_patient_by_id(patient_id: int):
    """Get patient details by patient ID."""
    patient = db.get_patient(patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with ID {patient_id} not found.",
        )
    return patient


@router.put("/{patient_id}", response_model=PatientResponse)
def update_patient(patient_id: int, patient_in: PatientUpdate):
    """Update patient details."""
    patient = db.get_patient(patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with ID {patient_id} not found.",
        )

    update_data = patient_in.model_dump(exclude_unset=True)

    # Check for unique email if email is being updated
    if "email" in update_data and update_data["email"]:
        new_email = update_data["email"].strip().lower()
        for p in db.patients:
            if p["id"] != patient_id and p["email"].strip().lower() == new_email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Patient with email '{update_data['email']}' already exists.",
                )

    patient.update(update_data)
    return patient


@router.delete("/{patient_id}")
def delete_patient(patient_id: int):
    """Delete a patient by ID."""
    patient = db.get_patient(patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with ID {patient_id} not found.",
        )
    db.patients.remove(patient)
    return {"message": f"Patient with ID {patient_id} deleted successfully", "id": patient_id}


# --- Day 2 Patient-Doctor Relationship Endpoints ---

@router.post("/{patient_id}/assign-doctor/{doctor_id}")
def assign_doctor_to_patient(patient_id: int, doctor_id: int):
    """Assign an existing doctor to an existing patient."""
    patient = db.get_patient(patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with ID {patient_id} not found.",
        )

    doctor = db.get_doctor(doctor_id)
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Doctor with ID {doctor_id} not found.",
        )

    patient["assigned_doctor_id"] = doctor_id
    return {
        "message": f"Doctor {doctor['full_name']} successfully assigned to patient {patient['full_name']}.",
        "patient_id": patient_id,
        "doctor_id": doctor_id,
    }


@router.get("/{patient_id}/doctor", response_model=DoctorResponse)
def get_assigned_doctor_for_patient(patient_id: int):
    """Retrieve the assigned doctor details for a patient."""
    patient = db.get_patient(patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with ID {patient_id} not found.",
        )

    doc_id = patient.get("assigned_doctor_id")
    if not doc_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No doctor is currently assigned to patient with ID {patient_id}.",
        )

    doctor = db.get_doctor(doc_id)
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assigned doctor with ID {doc_id} no longer exists.",
        )
    return doctor
