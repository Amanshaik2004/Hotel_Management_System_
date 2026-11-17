# Hospital Management System API

A comprehensive, clean, and modular RESTful API built with **FastAPI** and **Python** to manage core hospital operations across 6 unified modules:

1. **Patient Management** (Registration, CRUD, Demographics, Blood Group & Age Filters)
2. **Doctor Management** (Profiles, Specializations, Consultation Fees, Patient-Doctor Assignment)
3. **Appointment Booking** (Scheduling, Working Day & Conflict Validation, Rescheduling & Cancellation)
4. **Billing & Payment Processing** (Automatic Charges Calculation, Taxes, Discounts, Partial/Full Payments)
5. **Pharmacy & Medicine Inventory** (Stock Tracking, Expiry & Low-Stock Alerts, Patient Medicine Sales)
6. **Laboratory Test & Report Management** (Diagnostic Test Catalog, Test Orders, Status Workflow, Result Entry, Patient Lab History & Cost Summaries)

All data is maintained in-memory using standard Python data structures (lists/dicts), fulfilling all assignment specifications without premature database/ORM dependencies.

---

## Project Structure

```
Hospital_Management_System/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app initialization, routes registration, health check
│   ├── database.py          # In-memory database lists, ID sequences, and seed data
│   ├── schemas/             # Pydantic v2 validation models
│   │   ├── __init__.py
│   │   ├── patient.py       # Patient schemas (create, update, response, enums)
│   │   ├── doctor.py        # Doctor schemas (create, update, response, days validation)
│   │   ├── appointment.py   # Appointment schemas (create, update, response, status enum)
│   │   ├── billing.py       # Billing & Payment schemas (discount validator, enums)
│   │   ├── medicine.py      # Medicine & Sale schemas (stock adjustment, response)
│   │   └── lab.py           # Laboratory schemas (test, order, result, batch, summary)
│   └── routers/             # Modular FastAPI APIRouters
│       ├── __init__.py
│       ├── patients.py      # Patient endpoints & patient-doctor association
│       ├── doctors.py       # Doctor endpoints, search, filter, and sorting
│       ├── appointments.py  # Appointment booking, availability & conflict checks
│       ├── bills.py         # Billing calculations, invoicing, payment recording
│       ├── medicines.py     # Pharmacy inventory, stock updates, sales processing
│       └── lab.py           # Lab tests catalog, patient test orders, and diagnostic results
├── tests/                   # Pytest test suite (100% passing - 32 tests)
│   ├── __init__.py
│   ├── conftest.py          # TestClient fixture & clean database isolation
│   ├── test_patients.py     # Patient CRUD, validation & filter tests
│   ├── test_doctors.py      # Doctor CRUD, sorting, assignment tests
│   ├── test_appointments.py # Booking, conflicts, cancellation rules tests
│   ├── test_billing.py      # Invoicing, taxes, discount, partial payment tests
│   ├── test_medicines.py    # Inventory, expiry, low stock, sales tests
│   ├── test_lab.py          # Lab test CRUD, duplicate checks, orders, results, business rules
│   └── test_integration.py  # End-to-end hospital lifecycles & seed/reset tests
├── postman_collection.json  # Exported Postman Collection v2.1.0 with sample requests for all 6 modules
├── requirements.txt         # Project dependencies
├── README.md                # Documentation and execution guide
└── .gitignore               # Git ignore rules
```

---

## Requirements & Prerequisites

- **Python**: 3.10+ (Tested on Python 3.14)
- **FastAPI**: modern high-performance web framework
- **Uvicorn**: ASGI server
- **Pydantic**: v2 with email validation (`pydantic[email]`)
- **Pytest** & **HTTPX**: for automated testing

---

## Quick Start & Setup Instructions

### 1. Clone or Open Project Directory
```bash
cd /Users/aman/Desktop/Hospital_Management_System
```

### 2. Create and Activate Virtual Environment
```bash
# Create virtual environment
python3 -m venv venv

# Activate on macOS / Linux
source venv/bin/activate

# On Windows (PowerShell)
# .\venv\Scripts\Activate.ps1
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Application with Uvicorn
```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Once running, access:
- **Root Health / Statistics**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Interactive Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc Documentation**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## Demo Data Seeding & Reset

To quickly test the entire system in Swagger UI without manually registering records first:

- **Seed Demo Data**: `POST http://127.0.0.1:8000/seed-data`
  - Populates realistic Doctors, Patients, Appointments, Invoices, Payments, Pharmacy stock, Laboratory Tests, Test Orders, and Results.
- **Reset In-Memory Data**: `POST http://127.0.0.1:8000/reset-data`
  - Resets all lists and sequence counters back to an empty state.

---

## Detailed API Endpoints Catalog

### 1. General Endpoints
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | API status, health overview, module catalog, and resource statistics |
| `POST` | `/seed-data` | Populates demo data across all modules |
| `POST` | `/reset-data` | Clears all data from in-memory storage |

---

### 2. Patient Management (`/patients`)
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/patients` | Register a new patient (Validates email uniqueness, age 1–120, blood group) |
| `GET` | `/patients` | List patients with query filters: `gender`, `blood_group`, `min_age`, `max_age`, `search` (by name), `is_active` |
| `GET` | `/patients/{patient_id}` | Retrieve patient details by ID |
| `PUT` | `/patients/{patient_id}` | Update patient details |
| `DELETE` | `/patients/{patient_id}` | Delete a patient |
| `POST` | `/patients/{patient_id}/assign-doctor/{doctor_id}` | Associate an existing patient with an existing doctor |
| `GET` | `/patients/{patient_id}/doctor` | Retrieve assigned doctor information for a patient |
| `GET` | `/patients/{patient_id}/appointments` | Retrieve all appointments for this patient |
| `GET` | `/patients/{patient_id}/bills` | Retrieve full billing history for this patient |
| `GET` | `/patients/{patient_id}/medicine-sales` | Retrieve medicine purchase history for this patient |
| `GET` | `/patients/{patient_id}/lab-orders` | Retrieve patient diagnostic lab history with `X-Total-Cost` header |
| `GET` | `/patients/{patient_id}/lab-orders/summary` | Retrieve summary of patient lab history and total ordered test costs |

#### Patient Registration Example (`POST /patients`):
```json
{
  "full_name": "John Doe",
  "age": 35,
  "gender": "Male",
  "email": "john.doe@example.com",
  "phone": "+1-555-0101",
  "blood_group": "O+",
  "address": "123 Elm Street, Cityville",
  "is_active": true
}
```

---

### 3. Doctor Management (`/doctors`)
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/doctors` | Register a new doctor (`consultation_fee > 0`, `experience_years >= 0`, unique email) |
| `GET` | `/doctors` | List doctors with filtering: `search`, `specialization`, `min_experience`, `min_fee`, `max_fee`, `is_available`, and sorting: `sort_by` (`fee`, `experience`), `sort_order` (`asc`, `desc`) |
| `GET` | `/doctors/{doctor_id}` | Retrieve doctor details by ID |
| `PUT` | `/doctors/{doctor_id}` | Update doctor details |
| `DELETE` | `/doctors/{doctor_id}` | Delete doctor |
| `GET` | `/doctors/{doctor_id}/patients` | Retrieve all patients currently assigned to this doctor |
| `GET` | `/doctors/{doctor_id}/appointments` | Retrieve all appointments scheduled for this doctor |

---

### 4. Appointment Booking (`/appointments`)
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/appointments` | Book appointment (Validates doctor availability, day-of-week, past date, conflict check) |
| `GET` | `/appointments` | List appointments with filters: `patient_id`, `doctor_id`, `status`, `appointment_date`, `sort_by` (`date_time`, `date`, `time`), `sort_order` |
| `GET` | `/appointments/{appointment_id}` | Get appointment by ID |
| `PUT` | `/appointments/{appointment_id}` | Update or reschedule appointment |
| `PATCH` | `/appointments/{appointment_id}/cancel` | Cancel an appointment (Completed appointments cannot be cancelled) |
| `DELETE` | `/appointments/{appointment_id}` | Delete appointment |

---

### 5. Billing & Payments (`/bills`, `/payments`)
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/bills` | Generate a new bill for a patient appointment with automatic calculation of total, discount, and tax |
| `GET` | `/bills` | List bills with filters: `patient_id`, `payment_status`, `bill_number`, `start_date`, `end_date`, `sort_by` (`total_amount`, `date`), `sort_order` |
| `GET` | `/bills/{bill_id}` | Get bill details by ID |
| `PUT` | `/bills/{bill_id}` | Update bill charges and recompute totals and balances |
| `DELETE` | `/bills/{bill_id}` | Delete bill |
| `POST` | `/bills/{bill_id}/payments` | Record payment against a bill (Supports partial and full payments) |
| `GET` | `/bills/{bill_id}/payments` | Get payment transaction history for a bill |
| `GET` | `/payments/{payment_id}` | Get specific payment receipt details |
| `GET` | `/payments` | List all recorded payments with optional `payment_method` filter |

---

### 6. Pharmacy & Medicines (`/medicines`, `/medicine-sales`)
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/medicines` | Add medicine to inventory (`quantity >= 0`, `unit_price > 0`, valid expiry date) |
| `GET` | `/medicines` | List medicines with filters: `search`, `category`, `manufacturer`, `min_price`, `max_price`, `expiry_before`, `expiry_after`, `is_active`, and sorting |
| `GET` | `/medicines/low-stock` | Retrieve medicines whose quantity is $\le$ `minimum_stock` |
| `GET` | `/medicines/expiring` | Retrieve medicines expiring within the next 30 days |
| `GET` | `/medicines/{medicine_id}` | Get medicine details by ID |
| `PUT` | `/medicines/{medicine_id}` | Update medicine details |
| `DELETE` | `/medicines/{medicine_id}` | Delete medicine |
| `PATCH` | `/medicines/{medicine_id}/stock/add` | Add stock quantity |
| `PATCH` | `/medicines/{medicine_id}/stock/reduce` | Reduce stock (Cannot reduce beyond available quantity) |
| `POST` | `/medicine-sales` | Sell medicine to a patient: verifies stock, active status, non-expired status, computes total, and deducts inventory |
| `GET` | `/medicine-sales` | List all medicine sales transactions |
| `GET` | `/medicine-sales/{sale_id}` | Get sale details by ID |

---

### 7. Laboratory & Diagnostic Tests (`/lab-tests`, `/lab-orders`, `/lab-results`)

#### A. Laboratory Test Catalog
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/lab-tests` | Add a new diagnostic test (`price > 0`, non-blank fields, unique `test_code`) |
| `GET` | `/lab-tests` | Get all laboratory tests with search (`search` by name or code) and filter by `category`, `is_active` |
| `GET` | `/lab-tests/{test_id}` | Get laboratory test details by ID |
| `PUT` | `/lab-tests/{test_id}` | Update test details (Validates unique `test_code` if changed) |
| `DELETE` | `/lab-tests/{test_id}` | Delete test (Rejects deletion if orders reference it) |

#### B. Patient Lab Orders
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/lab-orders` | Create a lab test order for a patient (Initial status: `ORDERED`) |
| `POST` | `/lab-orders/batch` | Order multiple tests simultaneously for a patient and calculate total cost |
| `GET` | `/lab-orders` | Get all lab orders with filters: `patient_id`, `doctor_id`, `status`, `scheduled_date`, and sorting (`sort_by=order_date`) |
| `GET` | `/lab-orders/{order_id}` | Get lab order details by ID |
| `PATCH` | `/lab-orders/{order_id}/status` | Update order status (`ORDERED`, `SAMPLE_COLLECTED`, `PROCESSING`, `COMPLETED`, `CANCELLED`) |
| `GET` | `/patients/{patient_id}/lab-orders` | Get patient lab history with `X-Total-Cost` header |
| `GET` | `/patients/{patient_id}/lab-orders/summary` | Get patient lab summary including total orders and aggregated total cost |

#### C. Laboratory Result Management
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/lab-results` | Record test results (Auto-marks order `COMPLETED`, enforces order status rule, duplicate prevention) |
| `GET` | `/lab-results` | Get all recorded lab results |
| `GET` | `/lab-results/{result_id}` | Get result details by result ID |
| `GET` | `/lab-orders/{order_id}/result` | Get the diagnostic test result associated with a specific order |

---

## Laboratory Module Request & Response Examples

### 1. Adding a Laboratory Test (`POST /lab-tests`)
**Request Body:**
```json
{
  "test_name": "Complete Blood Count",
  "test_code": "CBC-001",
  "category": "Hematology",
  "description": "Evaluates overall health and detects anemia and infections.",
  "price": 35.0,
  "sample_type": "Whole Blood",
  "preparation_instructions": "No special fasting required.",
  "is_active": true
}
```
**Response (201 Created):**
```json
{
  "id": 1,
  "test_name": "Complete Blood Count",
  "test_code": "CBC-001",
  "category": "Hematology",
  "description": "Evaluates overall health and detects anemia and infections.",
  "price": 35.0,
  "sample_type": "Whole Blood",
  "preparation_instructions": "No special fasting required.",
  "is_active": true
}
```

### 2. Creating a Patient Lab Order (`POST /lab-orders`)
**Request Body:**
```json
{
  "patient_id": 1,
  "doctor_id": 1,
  "test_id": 1,
  "scheduled_date": "2026-11-20",
  "notes": "Patient presenting with fatigue and pallor"
}
```
**Response (201 Created):**
```json
{
  "id": 1,
  "patient_id": 1,
  "doctor_id": 1,
  "test_id": 1,
  "order_date": "2026-11-17T22:00:00",
  "scheduled_date": "2026-11-20",
  "status": "ORDERED",
  "notes": "Patient presenting with fatigue and pallor",
  "test_name": "Complete Blood Count",
  "test_code": "CBC-001",
  "test_price": 35.0
}
```

### 3. Ordering Multiple Tests & Total Cost Calculation (`POST /lab-orders/batch`)
**Request Body:**
```json
{
  "patient_id": 1,
  "doctor_id": 1,
  "test_ids": [1, 2],
  "scheduled_date": "2026-11-20",
  "notes": "Comprehensive routine health checkup"
}
```
**Response (201 Created):**
```json
{
  "patient_id": 1,
  "doctor_id": 1,
  "total_orders": 2,
  "total_cost": 55.0,
  "orders": [
    {
      "id": 2,
      "patient_id": 1,
      "doctor_id": 1,
      "test_id": 1,
      "order_date": "2026-11-17T22:00:00",
      "scheduled_date": "2026-11-20",
      "status": "ORDERED",
      "notes": "Comprehensive routine health checkup",
      "test_name": "Complete Blood Count",
      "test_code": "CBC-001",
      "test_price": 35.0
    },
    {
      "id": 3,
      "patient_id": 1,
      "doctor_id": 1,
      "test_id": 2,
      "order_date": "2026-11-17T22:00:00",
      "scheduled_date": "2026-11-20",
      "status": "ORDERED",
      "notes": "Comprehensive routine health checkup",
      "test_name": "Fasting Blood Sugar",
      "test_code": "FBS-002",
      "test_price": 20.0
    }
  ]
}
```

### 4. Updating Order Status (`PATCH /lab-orders/{order_id}/status`)
**Request Body:**
```json
{
  "status": "SAMPLE_COLLECTED"
}
```

### 5. Recording Test Result (`POST /lab-results`)
**Request Body:**
```json
{
  "order_id": 1,
  "result_value": "Hemoglobin: 14.2 g/dL, WBC: 6,800 /mcL, Platelets: 250,000 /mcL",
  "normal_range": "Hb: 13.5-17.5 g/dL, WBC: 4,500-11,000 /mcL, Platelets: 150,000-450,000 /mcL",
  "remarks": "All parameters are within normal reference limits.",
  "tested_by": "Alex Morgan, MLS"
}
```
**Response (201 Created):**
```json
{
  "id": 1,
  "order_id": 1,
  "result_value": "Hemoglobin: 14.2 g/dL, WBC: 6,800 /mcL, Platelets: 250,000 /mcL",
  "normal_range": "Hb: 13.5-17.5 g/dL, WBC: 4,500-11,000 /mcL, Platelets: 150,000-450,000 /mcL",
  "remarks": "All parameters are within normal reference limits.",
  "tested_by": "Alex Morgan, MLS",
  "result_date": "2026-11-17T22:05:00"
}
```
*(Notice: The corresponding order is automatically updated to `status: "COMPLETED"`).*

---

## Business Logic & Validation Summary

1. **Patient Validation**:
   - Unique email validation (returns `400 Bad Request` if duplicate).
   - Age constrained to $1 \le \text{age} \le 120$.
   - Blood groups validated against standard ABO/Rh types (`A+`, `A-`, `B+`, `B-`, `AB+`, `AB-`, `O+`, `O-`).
   - Rejects blank/whitespace-only strings on all required fields.

2. **Doctor Validation**:
   - Unique doctor email validation.
   - Non-negative experience (`experience_years >= 0`).
   - Positive consultation fee (`consultation_fee > 0`).
   - Normalized weekday availability validation.

3. **Appointment Scheduling Rules**:
   - Both patient and doctor must exist in memory (`404 Not Found` if missing).
   - Doctor must be marked active (`is_available == True`).
   - Appointment date day-of-week must match doctor's working schedule.
   - Appointment date and time cannot be in the past (`400 Bad Request`).
   - Double-booking prevention: rejects duplicate active bookings for the same doctor at identical date and time.
   - Rescheduling a `CANCELLED` appointment requires explicit reconfirmation (`SCHEDULED` or `CONFIRMED`).
   - `COMPLETED` appointments cannot be cancelled.

4. **Billing & Financial Rules**:
   - Validates existence of both patient and appointment.
   - Subtotal calculated from consultation fee, medicines, lab, and other charges.
   - Discount cannot exceed total charges.
   - Tax percentage (0–100%) applied to discounted subtotal.
   - Automatic payment status transitions: `PENDING` $\rightarrow$ `PARTIALLY_PAID` $\rightarrow$ `PAID`.
   - Rejects payments exceeding outstanding balance (`400 Bad Request`).
   - Rejects payments against `CANCELLED` bills.

5. **Pharmacy & Stock Rules**:
   - Stock reduction cannot exceed available stock.
   - Flags low-stock medicines automatically (`quantity <= minimum_stock`).
   - Detects upcoming expirations within 30 days.
   - Rejects sales of expired medicines.
   - Rejects sales of inactive medicines.
   - Rejects sales when requested quantity exceeds inventory.

6. **Laboratory Management Rules**:
   - **Entity Existence Check**: Verifies patient, doctor, and test all exist prior to creating an order (`404 Not Found` if any is missing).
   - **Active Status Check**: Prevents ordering inactive laboratory tests (`400 Bad Request`).
   - **Unique Test Codes**: Enforces unique, normalized uppercase `test_code` across the laboratory catalog.
   - **Sample Collection / Processing Requirement**: Results can **only** be recorded after sample collection or during processing (`status` must be `SAMPLE_COLLECTED` or `PROCESSING`).
   - **Cancelled Order Protection**: Strictly forbids recording results for `CANCELLED` orders (`400 Bad Request`).
   - **Duplicate Result Prevention**: Prevents duplicate results from being submitted for the same order (`400 Bad Request`).
   - **Automatic Status Advancement**: Automatically transitions the order status to `COMPLETED` once the result is recorded.
   - **Cost Calculation**: Computes total test cost when multiple tests are ordered (`POST /lab-orders/batch`), exposes `X-Total-Cost` header on patient lab history, and provides a dedicated patient summary endpoint (`/patients/{patient_id}/lab-orders/summary`).
   - **Referential Integrity**: Prevents deleting diagnostic tests that are referenced by active laboratory orders.

---

## Running Automated Tests

A comprehensive suite of **32 automated unit and integration tests** is included using `pytest` and `httpx.TestClient`.

Run the full test suite:
```bash
pytest -v
```

Expected output:
```
============================= test session starts ==============================
collected 32 items

tests/test_appointments.py::test_book_appointment_success_and_rules PASSED [  3%]
tests/test_appointments.py::test_appointment_cancellation_and_rescheduling PASSED [  6%]
tests/test_appointments.py::test_appointment_filters_and_queries PASSED  [  9%]
tests/test_billing.py::test_bill_generation_and_calculations PASSED      [ 12%]
tests/test_billing.py::test_discount_cannot_exceed_subtotal PASSED       [ 15%]
tests/test_billing.py::test_partial_and_full_payments PASSED             [ 18%]
tests/test_billing.py::test_payment_against_cancelled_bill_rejected PASSED [ 21%]
tests/test_billing.py::test_patient_billing_history PASSED               [ 25%]
tests/test_doctors.py::test_register_doctor_success PASSED               [ 28%]
tests/test_doctors.py::test_doctor_validation_errors PASSED              [ 31%]
tests/test_doctors.py::test_doctor_search_filter_sort PASSED             [ 34%]
tests/test_doctors.py::test_doctor_patient_assignment_and_retrieval PASSED [ 37%]
tests/test_integration.py::test_seed_and_reset_endpoints PASSED          [ 40%]
tests/test_integration.py::test_full_patient_to_billing_and_pharmacy_lifecycle PASSED [ 43%]
tests/test_integration.py::test_full_patient_laboratory_lifecycle PASSED [ 46%]
tests/test_lab.py::test_create_lab_test_success_and_validation PASSED    [ 50%]
tests/test_lab.py::test_duplicate_test_code_prevention PASSED            [ 53%]
tests/test_lab.py::test_get_lab_tests_search_and_filter PASSED           [ 56%]
tests/test_lab.py::test_update_and_delete_lab_test PASSED                [ 59%]
tests/test_lab.py::test_create_lab_order_and_entity_validations PASSED   [ 62%]
tests/test_lab.py::test_batch_ordering_and_total_cost_calculation PASSED [ 65%]
tests/test_lab.py::test_lab_order_search_filtering_and_sorting PASSED    [ 68%]
tests/test_lab.py::test_lab_result_lifecycle_and_business_rules PASSED   [ 71%]
tests/test_medicines.py::test_medicine_crud_and_validation PASSED        [ 75%]
tests/test_medicines.py::test_stock_management_and_alerts PASSED         [ 78%]
tests/test_medicines.py::test_medicine_sales_and_business_rules PASSED   [ 81%]
tests/test_patients.py::test_register_patient_success PASSED             [ 84%]
tests/test_patients.py::test_duplicate_email_validation PASSED           [ 87%]
tests/test_patients.py::test_invalid_age_and_email_format PASSED         [ 90%]
tests/test_patients.py::test_blank_required_fields PASSED                [ 93%]
tests/test_patients.py::test_patient_crud_and_not_found PASSED           [ 96%]
tests/test_patients.py::test_patient_search_and_filters PASSED           [100%]

============================== 32 passed in 0.18s ==============================
```

---

## Postman Collection

The file `postman_collection.json` is ready to import into Postman:

1. Open Postman.
2. Click **Import** in the top left.
3. Select or drag-and-drop `postman_collection.json`.
4. The collection will import with all requests organized into folders:
   - `General & Utility`
   - `1. Patient Management`
   - `2. Doctor Management`
   - `3. Appointment Booking`
   - `4. Billing & Payments`
   - `5. Medicines & Pharmacy`
   - `6. Laboratory Test Management`
5. The `baseUrl` collection variable defaults to `http://127.0.0.1:8000`.
