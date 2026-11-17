from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


def validate_not_blank(v: Optional[str], field_name: str) -> Optional[str]:
    if v is not None:
        v_stripped = v.strip()
        if not v_stripped:
            raise ValueError(f"{field_name} cannot be empty or blank")
        return v_stripped
    return v


class MedicineBase(BaseModel):
    medicine_name: str = Field(..., min_length=1, description="Brand name of the medicine")
    generic_name: str = Field(..., min_length=1, description="Generic chemical name")
    manufacturer: str = Field(..., min_length=1, description="Manufacturing company")
    category: str = Field(..., min_length=1, description="Therapeutic category (e.g. Antibiotic)")
    batch_number: str = Field(..., min_length=1, description="Manufacturing batch number")
    quantity: int = Field(default=0, ge=0, description="Available stock quantity (>= 0)")
    unit_price: float = Field(..., gt=0.0, description="Price per unit (> 0)")
    expiry_date: date = Field(..., description="Expiration date (YYYY-MM-DD)")
    minimum_stock: int = Field(default=10, ge=0, description="Threshold for low-stock warning (>= 0)")
    is_active: bool = Field(default=True, description="Active status")

    @field_validator("medicine_name")
    @classmethod
    def check_name_not_blank(cls, v: str) -> str:
        return validate_not_blank(v, "medicine_name")  # type: ignore

    @field_validator("generic_name")
    @classmethod
    def check_gen_not_blank(cls, v: str) -> str:
        return validate_not_blank(v, "generic_name")  # type: ignore

    @field_validator("manufacturer")
    @classmethod
    def check_man_not_blank(cls, v: str) -> str:
        return validate_not_blank(v, "manufacturer")  # type: ignore


class MedicineCreate(MedicineBase):
    pass


class MedicineUpdate(BaseModel):
    medicine_name: Optional[str] = Field(None, min_length=1)
    generic_name: Optional[str] = Field(None, min_length=1)
    manufacturer: Optional[str] = Field(None, min_length=1)
    category: Optional[str] = Field(None, min_length=1)
    batch_number: Optional[str] = Field(None, min_length=1)
    quantity: Optional[int] = Field(None, ge=0)
    unit_price: Optional[float] = Field(None, gt=0.0)
    expiry_date: Optional[date] = None
    minimum_stock: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None

    @field_validator("medicine_name")
    @classmethod
    def check_name_not_blank(cls, v: Optional[str]) -> Optional[str]:
        return validate_not_blank(v, "medicine_name")

    @field_validator("generic_name")
    @classmethod
    def check_gen_not_blank(cls, v: Optional[str]) -> Optional[str]:
        return validate_not_blank(v, "generic_name")

    @field_validator("manufacturer")
    @classmethod
    def check_man_not_blank(cls, v: Optional[str]) -> Optional[str]:
        return validate_not_blank(v, "manufacturer")


class MedicineResponse(MedicineBase):
    id: int
    is_low_stock: bool = False

    model_config = ConfigDict(from_attributes=True)


class StockAdjustment(BaseModel):
    quantity: int = Field(..., gt=0, description="Quantity to add or reduce (must be > 0)")


class MedicineSaleCreate(BaseModel):
    medicine_id: int = Field(..., gt=0, description="ID of medicine to sell")
    patient_id: int = Field(..., gt=0, description="ID of patient purchasing")
    quantity_sold: int = Field(..., gt=0, description="Number of units to purchase")


class MedicineSaleResponse(BaseModel):
    id: int
    medicine_id: int
    patient_id: int
    quantity_sold: int
    unit_price: float
    total_amount: float
    sale_date: datetime

    model_config = ConfigDict(from_attributes=True)
