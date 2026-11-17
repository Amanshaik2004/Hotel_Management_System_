from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class GenderEnum(str, Enum):
    MALE = "Male"
    FEMALE = "Female"
    OTHER = "Other"


class BloodGroupEnum(str, Enum):
    A_POS = "A+"
    A_NEG = "A-"
    B_POS = "B+"
    B_NEG = "B-"
    AB_POS = "AB+"
    AB_NEG = "AB-"
    O_POS = "O+"
    O_NEG = "O-"


def validate_not_blank(v: Optional[str], field_name: str) -> Optional[str]:
    if v is not None:
        v_stripped = v.strip()
        if not v_stripped:
            raise ValueError(f"{field_name} cannot be empty or blank")
        return v_stripped
    return v


class PatientBase(BaseModel):
    full_name: str = Field(..., description="Full name of the patient", min_length=1)
    age: int = Field(..., gt=0, le=120, description="Patient age between 1 and 120")
    gender: GenderEnum = Field(..., description="Gender (Male, Female, Other)")
    email: EmailStr = Field(..., description="Valid unique email address")
    phone: str = Field(..., min_length=1, description="Contact phone number")
    blood_group: BloodGroupEnum = Field(..., description="Blood group (e.g., A+, O-, etc.)")
    address: str = Field(..., min_length=1, description="Residential address")
    is_active: bool = Field(default=True, description="Active status")

    @field_validator("full_name")
    @classmethod
    def check_name_not_blank(cls, v: str) -> str:
        return validate_not_blank(v, "full_name")  # type: ignore

    @field_validator("phone")
    @classmethod
    def check_phone_not_blank(cls, v: str) -> str:
        return validate_not_blank(v, "phone")  # type: ignore

    @field_validator("address")
    @classmethod
    def check_address_not_blank(cls, v: str) -> str:
        return validate_not_blank(v, "address")  # type: ignore


class PatientCreate(PatientBase):
    pass


class PatientUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1)
    age: Optional[int] = Field(None, gt=0, le=120)
    gender: Optional[GenderEnum] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, min_length=1)
    blood_group: Optional[BloodGroupEnum] = None
    address: Optional[str] = Field(None, min_length=1)
    is_active: Optional[bool] = None

    @field_validator("full_name")
    @classmethod
    def check_name_not_blank(cls, v: Optional[str]) -> Optional[str]:
        return validate_not_blank(v, "full_name")

    @field_validator("phone")
    @classmethod
    def check_phone_not_blank(cls, v: Optional[str]) -> Optional[str]:
        return validate_not_blank(v, "phone")

    @field_validator("address")
    @classmethod
    def check_address_not_blank(cls, v: Optional[str]) -> Optional[str]:
        return validate_not_blank(v, "address")


class PatientResponse(PatientBase):
    id: int
    assigned_doctor_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)
