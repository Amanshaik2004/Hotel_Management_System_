from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class WeekDayEnum(str, Enum):
    MONDAY = "Monday"
    TUESDAY = "Tuesday"
    WEDNESDAY = "Wednesday"
    THURSDAY = "Thursday"
    FRIDAY = "Friday"
    SATURDAY = "Saturday"
    SUNDAY = "Sunday"


def validate_not_blank(v: Optional[str], field_name: str) -> Optional[str]:
    if v is not None:
        v_stripped = v.strip()
        if not v_stripped:
            raise ValueError(f"{field_name} cannot be empty or blank")
        return v_stripped
    return v


class DoctorBase(BaseModel):
    full_name: str = Field(..., description="Full name of the doctor", min_length=1)
    specialization: str = Field(..., description="Medical specialization (e.g., Cardiology)", min_length=1)
    email: EmailStr = Field(..., description="Unique email address")
    phone: str = Field(..., min_length=1, description="Contact phone number")
    experience_years: int = Field(..., ge=0, description="Years of experience (>= 0)")
    consultation_fee: float = Field(..., gt=0.0, description="Consultation fee (> 0)")
    available_days: List[str] = Field(
        default=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
        description="List of available weekdays (e.g., ['Monday', 'Wednesday'])"
    )
    is_available: bool = Field(default=True, description="Availability flag")

    @field_validator("full_name")
    @classmethod
    def check_name_not_blank(cls, v: str) -> str:
        return validate_not_blank(v, "full_name")  # type: ignore

    @field_validator("specialization")
    @classmethod
    def check_spec_not_blank(cls, v: str) -> str:
        return validate_not_blank(v, "specialization")  # type: ignore

    @field_validator("phone")
    @classmethod
    def check_phone_not_blank(cls, v: str) -> str:
        return validate_not_blank(v, "phone")  # type: ignore

    @field_validator("available_days")
    @classmethod
    def check_available_days(cls, days: List[str]) -> List[str]:
        valid_days = {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"}
        normalized = []
        for d in days:
            day_title = d.strip().capitalize()
            if day_title not in valid_days:
                raise ValueError(f"Invalid day '{d}'. Must be one of {sorted(valid_days)}")
            normalized.append(day_title)
        return normalized


class DoctorCreate(DoctorBase):
    pass


class DoctorUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1)
    specialization: Optional[str] = Field(None, min_length=1)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, min_length=1)
    experience_years: Optional[int] = Field(None, ge=0)
    consultation_fee: Optional[float] = Field(None, gt=0.0)
    available_days: Optional[List[str]] = None
    is_available: Optional[bool] = None

    @field_validator("full_name")
    @classmethod
    def check_name_not_blank(cls, v: Optional[str]) -> Optional[str]:
        return validate_not_blank(v, "full_name")

    @field_validator("specialization")
    @classmethod
    def check_spec_not_blank(cls, v: Optional[str]) -> Optional[str]:
        return validate_not_blank(v, "specialization")

    @field_validator("phone")
    @classmethod
    def check_phone_not_blank(cls, v: Optional[str]) -> Optional[str]:
        return validate_not_blank(v, "phone")

    @field_validator("available_days")
    @classmethod
    def check_available_days(cls, days: Optional[List[str]]) -> Optional[List[str]]:
        if days is None:
            return None
        valid_days = {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"}
        normalized = []
        for d in days:
            day_title = d.strip().capitalize()
            if day_title not in valid_days:
                raise ValueError(f"Invalid day '{d}'. Must be one of {sorted(valid_days)}")
            normalized.append(day_title)
        return normalized


class DoctorResponse(DoctorBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
