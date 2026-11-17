from datetime import date, datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


def validate_not_blank(v: Optional[str], field_name: str) -> Optional[str]:
    """Helper to validate that a string field is not empty or pure whitespace."""
    if v is not None:
        v_stripped = v.strip()
        if not v_stripped:
            raise ValueError(f"{field_name} cannot be empty or blank")
        return v_stripped
    return v


class LabOrderStatus(str, Enum):
    ORDERED = "ORDERED"
    SAMPLE_COLLECTED = "SAMPLE_COLLECTED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


# ==========================================
# Lab Test Schemas
# ==========================================

class LabTestBase(BaseModel):
    test_name: str = Field(..., min_length=1, description="Official name of the laboratory diagnostic test")
    test_code: str = Field(..., min_length=1, description="Unique alphanumeric identifier (e.g., CBC-001)")
    category: str = Field(..., min_length=1, description="Laboratory category (e.g., Hematology, Biochemistry)")
    description: Optional[str] = Field(default="", description="Detailed description of the diagnostic test")
    price: float = Field(..., gt=0.0, description="Test fee in USD (must be strictly greater than 0)")
    sample_type: str = Field(..., min_length=1, description="Type of specimen required (e.g., Blood, Urine, Serum)")
    preparation_instructions: Optional[str] = Field(default="", description="Instructions for patient before test")
    is_active: bool = Field(default=True, description="Availability status for ordering")

    @field_validator("test_name")
    @classmethod
    def check_name_not_blank(cls, v: str) -> str:
        return validate_not_blank(v, "test_name")  # type: ignore

    @field_validator("test_code")
    @classmethod
    def check_code_not_blank(cls, v: str) -> str:
        res = validate_not_blank(v, "test_code")
        return res.upper() if res else res  # type: ignore

    @field_validator("category")
    @classmethod
    def check_category_not_blank(cls, v: str) -> str:
        return validate_not_blank(v, "category")  # type: ignore

    @field_validator("sample_type")
    @classmethod
    def check_sample_not_blank(cls, v: str) -> str:
        return validate_not_blank(v, "sample_type")  # type: ignore


class LabTestCreate(LabTestBase):
    pass


class LabTestUpdate(BaseModel):
    test_name: Optional[str] = Field(None, min_length=1)
    test_code: Optional[str] = Field(None, min_length=1)
    category: Optional[str] = Field(None, min_length=1)
    description: Optional[str] = None
    price: Optional[float] = Field(None, gt=0.0)
    sample_type: Optional[str] = Field(None, min_length=1)
    preparation_instructions: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator("test_name")
    @classmethod
    def check_name_not_blank(cls, v: Optional[str]) -> Optional[str]:
        return validate_not_blank(v, "test_name")

    @field_validator("test_code")
    @classmethod
    def check_code_not_blank(cls, v: Optional[str]) -> Optional[str]:
        res = validate_not_blank(v, "test_code")
        return res.upper() if res else res

    @field_validator("category")
    @classmethod
    def check_category_not_blank(cls, v: Optional[str]) -> Optional[str]:
        return validate_not_blank(v, "category")

    @field_validator("sample_type")
    @classmethod
    def check_sample_not_blank(cls, v: Optional[str]) -> Optional[str]:
        return validate_not_blank(v, "sample_type")


class LabTestResponse(LabTestBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# Lab Order Schemas
# ==========================================

class LabOrderCreate(BaseModel):
    patient_id: int = Field(..., gt=0, description="ID of patient requiring the diagnostic test")
    doctor_id: int = Field(..., gt=0, description="ID of doctor prescribing the test")
    test_id: int = Field(..., gt=0, description="ID of laboratory test being ordered")
    scheduled_date: Optional[date] = Field(None, description="Date for sample collection (defaults to today)")
    notes: Optional[str] = Field(default="", description="Clinical indications, symptoms, or special instructions")


class LabOrderBatchCreate(BaseModel):
    patient_id: int = Field(..., gt=0, description="ID of patient")
    doctor_id: int = Field(..., gt=0, description="ID of doctor prescribing tests")
    test_ids: List[int] = Field(..., min_length=1, description="List of test IDs ordered together")
    scheduled_date: Optional[date] = Field(None, description="Scheduled date for sample collection")
    notes: Optional[str] = Field(default="", description="General order notes")


class LabOrderStatusUpdate(BaseModel):
    status: LabOrderStatus = Field(..., description="Target status: ORDERED, SAMPLE_COLLECTED, PROCESSING, COMPLETED, CANCELLED")


class LabOrderResponse(BaseModel):
    id: int
    patient_id: int
    doctor_id: int
    test_id: int
    order_date: datetime
    scheduled_date: date
    status: str
    notes: Optional[str] = ""
    # Enriched test details for convenience & total cost visibility
    test_name: Optional[str] = None
    test_code: Optional[str] = None
    test_price: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class LabBatchOrderResponse(BaseModel):
    patient_id: int
    doctor_id: int
    total_orders: int
    total_cost: float
    orders: List[LabOrderResponse]


class PatientLabHistorySummary(BaseModel):
    patient_id: int
    patient_name: str
    total_orders: int
    total_cost: float
    orders: List[LabOrderResponse]


# ==========================================
# Lab Result Schemas
# ==========================================

class LabResultCreate(BaseModel):
    order_id: int = Field(..., gt=0, description="ID of laboratory test order")
    result_value: str = Field(..., min_length=1, description="Quantitative or qualitative diagnostic finding")
    normal_range: str = Field(..., min_length=1, description="Standard medical reference range")
    remarks: Optional[str] = Field(default="", description="Pathologist/technician remarks or clinical interpretation")
    tested_by: str = Field(..., min_length=1, description="Name or credential of the laboratory professional")
    result_date: Optional[datetime] = Field(None, description="Timestamp when result was finalized (defaults to now)")

    @field_validator("result_value")
    @classmethod
    def check_result_not_blank(cls, v: str) -> str:
        return validate_not_blank(v, "result_value")  # type: ignore

    @field_validator("normal_range")
    @classmethod
    def check_range_not_blank(cls, v: str) -> str:
        return validate_not_blank(v, "normal_range")  # type: ignore

    @field_validator("tested_by")
    @classmethod
    def check_tested_not_blank(cls, v: str) -> str:
        return validate_not_blank(v, "tested_by")  # type: ignore


class LabResultResponse(BaseModel):
    id: int
    order_id: int
    result_value: str
    normal_range: str
    remarks: Optional[str] = ""
    tested_by: str
    result_date: datetime

    model_config = ConfigDict(from_attributes=True)
