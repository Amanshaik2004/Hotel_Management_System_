from datetime import date, datetime, time
from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class AppointmentStatus(str, Enum):
    SCHEDULED = "SCHEDULED"
    CONFIRMED = "CONFIRMED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


def validate_not_blank(v: Optional[str], field_name: str) -> Optional[str]:
    if v is not None:
        v_stripped = v.strip()
        if not v_stripped:
            raise ValueError(f"{field_name} cannot be empty or blank")
        return v_stripped
    return v


class AppointmentBase(BaseModel):
    patient_id: int = Field(..., gt=0, description="Positive ID of the patient")
    doctor_id: int = Field(..., gt=0, description="Positive ID of the doctor")
    appointment_date: date = Field(..., description="Date of the appointment (YYYY-MM-DD)")
    appointment_time: time = Field(..., description="Time of the appointment (HH:MM:SS)")
    reason: str = Field(..., min_length=1, description="Reason for the appointment")

    @field_validator("reason")
    @classmethod
    def check_reason_not_blank(cls, v: str) -> str:
        return validate_not_blank(v, "reason")  # type: ignore


class AppointmentCreate(AppointmentBase):
    pass


class AppointmentUpdate(BaseModel):
    patient_id: Optional[int] = Field(None, gt=0)
    doctor_id: Optional[int] = Field(None, gt=0)
    appointment_date: Optional[date] = None
    appointment_time: Optional[time] = None
    reason: Optional[str] = Field(None, min_length=1)
    status: Optional[AppointmentStatus] = None

    @field_validator("reason")
    @classmethod
    def check_reason_not_blank(cls, v: Optional[str]) -> Optional[str]:
        return validate_not_blank(v, "reason")


class AppointmentResponse(AppointmentBase):
    id: int
    status: AppointmentStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
