"""
In-memory database storing hospital data in Python lists.
No external database or SQLAlchemy is used, adhering to assignment requirements.
"""

from datetime import date, datetime, time, timedelta
from typing import Any, Dict, List, Optional


class InMemoryDatabase:
    def __init__(self):
        self.reset()

    def reset(self):
        """Reset all in-memory lists and sequence counters."""
        self.patients: List[Dict[str, Any]] = []
        self.doctors: List[Dict[str, Any]] = []
        self.appointments: List[Dict[str, Any]] = []
        self.bills: List[Dict[str, Any]] = []
        self.payments: List[Dict[str, Any]] = []
        self.medicines: List[Dict[str, Any]] = []
        self.medicine_sales: List[Dict[str, Any]] = []
        self.lab_tests: List[Dict[str, Any]] = []
        self.lab_orders: List[Dict[str, Any]] = []
        self.lab_results: List[Dict[str, Any]] = []

        self._patient_id_counter = 1
        self._doctor_id_counter = 1
        self._appointment_id_counter = 1
        self._bill_id_counter = 1
        self._payment_id_counter = 1
        self._medicine_id_counter = 1
        self._sale_id_counter = 1
        self._lab_test_id_counter = 1
        self._lab_order_id_counter = 1
        self._lab_result_id_counter = 1

    # --- ID Generators ---
    def next_patient_id(self) -> int:
        nid = self._patient_id_counter
        self._patient_id_counter += 1
        return nid

    def next_doctor_id(self) -> int:
        nid = self._doctor_id_counter
        self._doctor_id_counter += 1
        return nid

    def next_appointment_id(self) -> int:
        nid = self._appointment_id_counter
        self._appointment_id_counter += 1
        return nid

    def next_bill_id(self) -> int:
        nid = self._bill_id_counter
        self._bill_id_counter += 1
        return nid

    def next_payment_id(self) -> int:
        nid = self._payment_id_counter
        self._payment_id_counter += 1
        return nid

    def next_medicine_id(self) -> int:
        nid = self._medicine_id_counter
        self._medicine_id_counter += 1
        return nid

    def next_sale_id(self) -> int:
        nid = self._sale_id_counter
        self._sale_id_counter += 1
        return nid

    def next_lab_test_id(self) -> int:
        nid = self._lab_test_id_counter
        self._lab_test_id_counter += 1
        return nid

    def next_lab_order_id(self) -> int:
        nid = self._lab_order_id_counter
        self._lab_order_id_counter += 1
        return nid

    def next_lab_result_id(self) -> int:
        nid = self._lab_result_id_counter
        self._lab_result_id_counter += 1
        return nid

    # --- Lookup Helpers ---
    def get_patient(self, patient_id: int) -> Optional[Dict[str, Any]]:
        return next((p for p in self.patients if p["id"] == patient_id), None)

    def get_doctor(self, doctor_id: int) -> Optional[Dict[str, Any]]:
        return next((d for d in self.doctors if d["id"] == doctor_id), None)

    def get_appointment(self, appointment_id: int) -> Optional[Dict[str, Any]]:
        return next((a for a in self.appointments if a["id"] == appointment_id), None)

    def get_bill(self, bill_id: int) -> Optional[Dict[str, Any]]:
        return next((b for b in self.bills if b["id"] == bill_id), None)

    def get_payment(self, payment_id: int) -> Optional[Dict[str, Any]]:
        return next((p for p in self.payments if p["id"] == payment_id), None)

    def get_medicine(self, medicine_id: int) -> Optional[Dict[str, Any]]:
        return next((m for m in self.medicines if m["id"] == medicine_id), None)

    def get_sale(self, sale_id: int) -> Optional[Dict[str, Any]]:
        return next((s for s in self.medicine_sales if s["id"] == sale_id), None)

    def get_lab_test(self, test_id: int) -> Optional[Dict[str, Any]]:
        return next((t for t in self.lab_tests if t["id"] == test_id), None)

    def get_lab_order(self, order_id: int) -> Optional[Dict[str, Any]]:
        return next((o for o in self.lab_orders if o["id"] == order_id), None)

    def get_lab_result(self, result_id: int) -> Optional[Dict[str, Any]]:
        return next((r for r in self.lab_results if r["id"] == result_id), None)

    def get_lab_result_by_order(self, order_id: int) -> Optional[Dict[str, Any]]:
        return next((r for r in self.lab_results if r["order_id"] == order_id), None)

    def seed_sample_data(self):
        """Populate initial realistic sample data for testing and Swagger UI demonstration."""
        self.reset()
        today = date.today()

        # Seed Doctors
        d1 = {
            "id": self.next_doctor_id(),
            "full_name": "Dr. Sarah Connor",
            "specialization": "Cardiology",
            "email": "sarah.connor@hospital.com",
            "phone": "+1-555-0101",
            "experience_years": 12,
            "consultation_fee": 150.0,
            "available_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
            "is_available": True,
        }
        d2 = {
            "id": self.next_doctor_id(),
            "full_name": "Dr. Gregory House",
            "specialization": "Neurology",
            "email": "gregory.house@hospital.com",
            "phone": "+1-555-0102",
            "experience_years": 18,
            "consultation_fee": 250.0,
            "available_days": ["Monday", "Wednesday", "Friday"],
            "is_available": True,
        }
        self.doctors.extend([d1, d2])

        # Seed Patients
        p1 = {
            "id": self.next_patient_id(),
            "full_name": "John Doe",
            "age": 35,
            "gender": "Male",
            "email": "john.doe@example.com",
            "phone": "+1-555-0201",
            "blood_group": "O+",
            "address": "123 Elm Street, Cityville",
            "is_active": True,
            "assigned_doctor_id": d1["id"],
        }
        p2 = {
            "id": self.next_patient_id(),
            "full_name": "Jane Smith",
            "age": 28,
            "gender": "Female",
            "email": "jane.smith@example.com",
            "phone": "+1-555-0202",
            "blood_group": "A+",
            "address": "456 Oak Avenue, Metropolis",
            "is_active": True,
            "assigned_doctor_id": d2["id"],
        }
        self.patients.extend([p1, p2])

        # Seed Appointments
        # Pick next available weekday
        days_ahead = 2
        appt_date = today + timedelta(days=days_ahead)
        while appt_date.strftime("%A") not in d1["available_days"]:
            appt_date += timedelta(days=1)

        a1 = {
            "id": self.next_appointment_id(),
            "patient_id": p1["id"],
            "doctor_id": d1["id"],
            "appointment_date": appt_date,
            "appointment_time": time(10, 30),
            "reason": "Regular cardiac checkup",
            "status": "CONFIRMED",
            "created_at": datetime.now(),
        }
        self.appointments.append(a1)

        # Seed Bill
        subtotal = 150.0 + 40.0 + 50.0  # consultation + medicine + lab
        discount = 20.0
        tax = (subtotal - discount) * 0.10
        total = round((subtotal - discount) + tax, 2)
        paid = 100.0
        balance = round(total - paid, 2)

        b1 = {
            "id": self.next_bill_id(),
            "bill_number": f"BILL-{today.strftime('%Y%m%d')}-0001",
            "patient_id": p1["id"],
            "appointment_id": a1["id"],
            "consultation_fee": 150.0,
            "medicine_charges": 40.0,
            "lab_charges": 50.0,
            "other_charges": 0.0,
            "discount": discount,
            "tax_percentage": 10.0,
            "total_amount": total,
            "paid_amount": paid,
            "balance_amount": balance,
            "payment_status": "PARTIALLY_PAID",
            "created_at": datetime.now(),
        }
        self.bills.append(b1)

        # Seed Payment
        pay1 = {
            "id": self.next_payment_id(),
            "bill_id": b1["id"],
            "amount": paid,
            "payment_method": "CARD",
            "transaction_reference": "TXN-INIT-9001",
            "payment_date": datetime.now(),
            "status": "SUCCESS",
        }
        self.payments.append(pay1)

        # Seed Medicines
        m1 = {
            "id": self.next_medicine_id(),
            "medicine_name": "Amoxicillin 500mg",
            "generic_name": "Amoxicillin",
            "manufacturer": "PharmaCorp",
            "category": "Antibiotic",
            "batch_number": "AMX-2026-A1",
            "quantity": 100,
            "unit_price": 12.50,
            "expiry_date": today + timedelta(days=180),
            "minimum_stock": 20,
            "is_active": True,
        }
        m2 = {
            "id": self.next_medicine_id(),
            "medicine_name": "Paracetamol 650mg",
            "generic_name": "Acetaminophen",
            "manufacturer": "HealthCare Ltd",
            "category": "Analgesic",
            "batch_number": "PCM-2026-B4",
            "quantity": 15,  # Low stock test
            "unit_price": 2.00,
            "expiry_date": today + timedelta(days=20),  # Expiring soon test
            "minimum_stock": 25,
            "is_active": True,
        }
        self.medicines.extend([m1, m2])

        # Seed Lab Tests
        t1 = {
            "id": self.next_lab_test_id(),
            "test_name": "Complete Blood Count",
            "test_code": "CBC-001",
            "category": "Hematology",
            "description": "Evaluates overall health and detects anemia and infections.",
            "price": 35.0,
            "sample_type": "Whole Blood",
            "preparation_instructions": "No special fasting required.",
            "is_active": True,
        }
        t2 = {
            "id": self.next_lab_test_id(),
            "test_name": "Fasting Blood Sugar",
            "test_code": "FBS-002",
            "category": "Biochemistry",
            "description": "Measures blood glucose level to screen for diabetes.",
            "price": 20.0,
            "sample_type": "Serum",
            "preparation_instructions": "Fasting for 8-12 hours prior to test.",
            "is_active": True,
        }
        t3 = {
            "id": self.next_lab_test_id(),
            "test_name": "Lipid Profile Panel",
            "test_code": "LPD-003",
            "category": "Biochemistry",
            "description": "Comprehensive cholesterol and triglycerides screening.",
            "price": 65.0,
            "sample_type": "Serum",
            "preparation_instructions": "Fasting for 12 hours required.",
            "is_active": True,
        }
        t4 = {
            "id": self.next_lab_test_id(),
            "test_name": "Archived Liver Screen",
            "test_code": "LFT-ARCHIVED",
            "category": "Hepatology",
            "description": "Legacy liver screen replaced by updated panel.",
            "price": 40.0,
            "sample_type": "Serum",
            "preparation_instructions": "Fasting for 8 hours.",
            "is_active": False,
        }
        self.lab_tests.extend([t1, t2, t3, t4])

        # Seed Lab Orders
        ord1 = {
            "id": self.next_lab_order_id(),
            "patient_id": p1["id"],
            "doctor_id": d1["id"],
            "test_id": t1["id"],
            "order_date": datetime.now() - timedelta(hours=5),
            "scheduled_date": today,
            "status": "COMPLETED",
            "notes": "Routine checkup screening",
        }
        ord2 = {
            "id": self.next_lab_order_id(),
            "patient_id": p1["id"],
            "doctor_id": d1["id"],
            "test_id": t2["id"],
            "order_date": datetime.now() - timedelta(hours=1),
            "scheduled_date": today,
            "status": "SAMPLE_COLLECTED",
            "notes": "Fasting blood sugar follow-up",
        }
        self.lab_orders.extend([ord1, ord2])

        # Seed Lab Result for Completed Order 1
        res1 = {
            "id": self.next_lab_result_id(),
            "order_id": ord1["id"],
            "result_value": "Hemoglobin: 14.2 g/dL, WBC: 6,800 /mcL, Platelets: 250,000 /mcL",
            "normal_range": "Hb: 13.5-17.5 g/dL, WBC: 4,500-11,000 /mcL, Platelets: 150,000-450,000 /mcL",
            "remarks": "All parameters are within normal reference ranges.",
            "tested_by": "Alex Morgan, MLS",
            "result_date": datetime.now() - timedelta(hours=2),
        }
        self.lab_results.append(res1)


# Global database instance
db = InMemoryDatabase()
