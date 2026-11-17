from datetime import date, datetime, time
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.database import db
from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentResponse,
    AppointmentStatus,
    AppointmentUpdate,
)

router = APIRouter(tags=["Appointments"])


def check_past_datetime(appt_date: date, appt_time: time):
    """Ensure appointment is not in the past."""
    now = datetime.now()
    today = now.date()
    current_time = now.time()

    if appt_date < today:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot book or reschedule an appointment in the past.",
        )
    if appt_date == today and appt_time < current_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot book or reschedule an appointment for a past time today.",
        )


def check_doctor_availability(doctor: dict, appt_date: date):
    """Check doctor availability status and working days."""
    if not doctor.get("is_available", True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Doctor '{doctor['full_name']}' is currently marked as unavailable.",
        )

    weekday_name = appt_date.strftime("%A")
    available_days = [d.capitalize() for d in doctor.get("available_days", [])]
    if available_days and weekday_name not in available_days:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Doctor '{doctor['full_name']}' is not available on {weekday_name}s. "
                f"Available days: {', '.join(available_days)}."
            ),
        )


def check_double_booking(doctor_id: int, appt_date: date, appt_time: time, exclude_appt_id: Optional[int] = None):
    """Prevent overlapping appointments for the same doctor at identical date and time."""
    for appt in db.appointments:
        if exclude_appt_id and appt["id"] == exclude_appt_id:
            continue
        if (
            appt["doctor_id"] == doctor_id
            and appt["appointment_date"] == appt_date
            and appt["appointment_time"] == appt_time
            and appt["status"] != AppointmentStatus.CANCELLED
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Doctor already has an active appointment on {appt_date} at {appt_time}.",
            )


@router.post("/appointments", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
def book_appointment(appointment_in: AppointmentCreate):
    """Book a new appointment with availability validation and conflict prevention."""
    # 1. Verify patient exists
    patient = db.get_patient(appointment_in.patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with ID {appointment_in.patient_id} not found.",
        )

    # 2. Verify doctor exists
    doctor = db.get_doctor(appointment_in.doctor_id)
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Doctor with ID {appointment_in.doctor_id} not found.",
        )

    # 3. Check not in past
    check_past_datetime(appointment_in.appointment_date, appointment_in.appointment_time)

    # 4. Check doctor availability & available days
    check_doctor_availability(doctor, appointment_in.appointment_date)

    # 5. Check double booking
    check_double_booking(appointment_in.doctor_id, appointment_in.appointment_date, appointment_in.appointment_time)

    new_appointment = appointment_in.model_dump()
    new_appointment["id"] = db.next_appointment_id()
    new_appointment["status"] = AppointmentStatus.SCHEDULED
    new_appointment["created_at"] = datetime.now()

    db.appointments.append(new_appointment)
    return new_appointment


@router.get("/appointments", response_model=List[AppointmentResponse])
def get_all_appointments(
    patient_id: Optional[int] = Query(None, description="Filter by patient ID"),
    doctor_id: Optional[int] = Query(None, description="Filter by doctor ID"),
    status_filter: Optional[AppointmentStatus] = Query(None, alias="status", description="Filter by appointment status"),
    appointment_date: Optional[date] = Query(None, description="Filter by appointment date (YYYY-MM-DD)"),
    sort_by: Optional[str] = Query("date_time", description="Sort by: 'date', 'time', or 'date_time'"),
    sort_order: Optional[str] = Query("asc", description="Sort order: 'asc' or 'desc'"),
):
    """Retrieve all appointments with filters and sorting."""
    results = list(db.appointments)

    if patient_id is not None:
        results = [a for a in results if a["patient_id"] == patient_id]

    if doctor_id is not None:
        results = [a for a in results if a["doctor_id"] == doctor_id]

    if status_filter is not None:
        results = [a for a in results if a["status"] == status_filter]

    if appointment_date is not None:
        results = [a for a in results if a["appointment_date"] == appointment_date]

    reverse = (sort_order or "").strip().lower() == "desc"
    s_by = (sort_by or "date_time").strip().lower()

    if s_by in ("date_time", "datetime"):
        results = sorted(
            results,
            key=lambda x: datetime.combine(x["appointment_date"], x["appointment_time"]),
            reverse=reverse,
        )
    elif s_by == "date":
        results = sorted(results, key=lambda x: x["appointment_date"], reverse=reverse)
    elif s_by == "time":
        results = sorted(results, key=lambda x: x["appointment_time"], reverse=reverse)

    return results


@router.get("/appointments/{appointment_id}", response_model=AppointmentResponse)
def get_appointment_by_id(appointment_id: int):
    """Get appointment by ID."""
    appt = db.get_appointment(appointment_id)
    if not appt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment with ID {appointment_id} not found.",
        )
    return appt


@router.put("/appointments/{appointment_id}", response_model=AppointmentResponse)
def update_appointment(appointment_id: int, update_in: AppointmentUpdate):
    """Update or reschedule appointment."""
    appt = db.get_appointment(appointment_id)
    if not appt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment with ID {appointment_id} not found.",
        )

    # Business Rule: Prevent cancelled appointments from being rescheduled without confirmation
    if appt["status"] == AppointmentStatus.CANCELLED:
        if not update_in.status or update_in.status == AppointmentStatus.CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cancelled appointment cannot be rescheduled without confirming new status (CONFIRMED or SCHEDULED).",
            )

    update_data = update_in.model_dump(exclude_unset=True)

    # Determine prospective target doctor, date, and time
    target_doc_id = update_data.get("doctor_id", appt["doctor_id"])
    target_date = update_data.get("appointment_date", appt["appointment_date"])
    target_time = update_data.get("appointment_time", appt["appointment_time"])

    doctor = db.get_doctor(target_doc_id)
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Doctor with ID {target_doc_id} not found.",
        )

    if "patient_id" in update_data:
        patient = db.get_patient(update_data["patient_id"])
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patient with ID {update_data['patient_id']} not found.",
            )

    # If rescheduling date or time, validate availability and conflicts
    date_or_time_changed = (target_date != appt["appointment_date"]) or (target_time != appt["appointment_time"])
    if date_or_time_changed:
        check_past_datetime(target_date, target_time)
        check_doctor_availability(doctor, target_date)
        check_double_booking(target_doc_id, target_date, target_time, exclude_appt_id=appointment_id)

    appt.update(update_data)
    return appt


@router.patch("/appointments/{appointment_id}/cancel", response_model=AppointmentResponse)
def cancel_appointment(appointment_id: int):
    """Cancel an appointment. Completed appointments cannot be cancelled."""
    appt = db.get_appointment(appointment_id)
    if not appt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment with ID {appointment_id} not found.",
        )

    if appt["status"] == AppointmentStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel an appointment that has already been completed.",
        )

    appt["status"] = AppointmentStatus.CANCELLED
    return appt


@router.delete("/appointments/{appointment_id}")
def delete_appointment(appointment_id: int):
    """Delete an appointment."""
    appt = db.get_appointment(appointment_id)
    if not appt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment with ID {appointment_id} not found.",
        )
    db.appointments.remove(appt)
    return {"message": f"Appointment with ID {appointment_id} deleted successfully", "id": appointment_id}


# Specific resource relationship helpers
@router.get("/patients/{patient_id}/appointments", response_model=List[AppointmentResponse])
def get_patient_appointments(patient_id: int):
    """Retrieve all appointments for a particular patient."""
    patient = db.get_patient(patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with ID {patient_id} not found.",
        )
    return [a for a in db.appointments if a["patient_id"] == patient_id]


@router.get("/doctors/{doctor_id}/appointments", response_model=List[AppointmentResponse])
def get_doctor_appointments(doctor_id: int):
    """Retrieve all appointments for a particular doctor."""
    doctor = db.get_doctor(doctor_id)
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Doctor with ID {doctor_id} not found.",
        )
    return [a for a in db.appointments if a["doctor_id"] == doctor_id]
