from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class PaymentStatus(str, Enum):
    PENDING = "PENDING"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    PAID = "PAID"
    CANCELLED = "CANCELLED"


class PaymentMethod(str, Enum):
    CASH = "CASH"
    UPI = "UPI"
    CARD = "CARD"
    BANK_TRANSFER = "BANK_TRANSFER"


class BillCreate(BaseModel):
    patient_id: int = Field(..., gt=0, description="Patient ID")
    appointment_id: int = Field(..., gt=0, description="Appointment ID")
    consultation_fee: float = Field(default=0.0, ge=0.0, description="Consultation fee")
    medicine_charges: float = Field(default=0.0, ge=0.0, description="Medicine charges")
    lab_charges: float = Field(default=0.0, ge=0.0, description="Laboratory test charges")
    other_charges: float = Field(default=0.0, ge=0.0, description="Other miscellaneous charges")
    discount: float = Field(default=0.0, ge=0.0, description="Discount amount")
    tax_percentage: float = Field(default=0.0, ge=0.0, le=100.0, description="Tax percentage (0-100)")

    @model_validator(mode="after")
    def validate_discount(self):
        subtotal = self.consultation_fee + self.medicine_charges + self.lab_charges + self.other_charges
        if self.discount > subtotal:
            raise ValueError(f"Discount ({self.discount}) cannot exceed the subtotal charges ({subtotal})")
        return self


class BillUpdate(BaseModel):
    consultation_fee: Optional[float] = Field(None, ge=0.0)
    medicine_charges: Optional[float] = Field(None, ge=0.0)
    lab_charges: Optional[float] = Field(None, ge=0.0)
    other_charges: Optional[float] = Field(None, ge=0.0)
    discount: Optional[float] = Field(None, ge=0.0)
    tax_percentage: Optional[float] = Field(None, ge=0.0, le=100.0)
    payment_status: Optional[PaymentStatus] = None


class BillResponse(BaseModel):
    id: int
    bill_number: str
    patient_id: int
    appointment_id: int
    consultation_fee: float
    medicine_charges: float
    lab_charges: float
    other_charges: float
    discount: float
    tax_percentage: float
    total_amount: float
    paid_amount: float
    balance_amount: float
    payment_status: PaymentStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaymentCreate(BaseModel):
    amount: float = Field(..., gt=0.0, description="Payment amount must be greater than zero")
    payment_method: PaymentMethod = Field(..., description="Payment method (CASH, UPI, CARD, BANK_TRANSFER)")
    transaction_reference: Optional[str] = Field(None, description="Optional transaction reference or receipt ID")


class PaymentResponse(BaseModel):
    id: int
    bill_id: int
    amount: float
    payment_method: PaymentMethod
    transaction_reference: str
    payment_date: datetime
    status: str

    model_config = ConfigDict(from_attributes=True)
