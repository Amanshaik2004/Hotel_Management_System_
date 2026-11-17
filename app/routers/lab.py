from datetime import date, datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Response, status

from app.database import db
from app.schemas.lab import (
    LabBatchOrderResponse,
    LabOrderBatchCreate,
    LabOrderCreate,
    LabOrderResponse,
    LabOrderStatus,
    LabOrderStatusUpdate,
    LabResultCreate,
    LabResultResponse,
    LabTestCreate,
    LabTestResponse,
    LabTestUpdate,
    PatientLabHistorySummary,
)

router = APIRouter(tags=["Laboratory & Diagnostic Tests"])


def format_order_response(order: dict) -> dict:
    """Enrich lab order record with test name, code, and price."""
    res = dict(order)
    test = db.get_lab_test(order["test_id"])
    if test:
        res["test_name"] = test.get("test_name")
        res["test_code"] = test.get("test_code")
        res["test_price"] = test.get("price")
    return res


# ============================================================================
# 1. Laboratory Test CRUD Endpoints
# ============================================================================

@router.post("/lab-tests", response_model=LabTestResponse, status_code=status.HTTP_201_CREATED)
def create_lab_test(test_in: LabTestCreate):
    """Add a new laboratory test. Validates test_code uniqueness."""
    code_normalized = test_in.test_code.strip().upper()
    for existing in db.lab_tests:
        if existing["test_code"].strip().upper() == code_normalized:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Laboratory test with code '{test_in.test_code}' already exists.",
            )

    test_data = test_in.model_dump()
    test_data["id"] = db.next_lab_test_id()
    test_data["test_code"] = code_normalized
    db.lab_tests.append(test_data)
    return test_data


@router.get("/lab-tests", response_model=List[LabTestResponse])
def get_all_lab_tests(
    search: Optional[str] = Query(None, description="Search tests by name or code (case-insensitive)"),
    category: Optional[str] = Query(None, description="Filter tests by category (case-insensitive)"),
    is_active: Optional[bool] = Query(None, description="Filter tests by active status"),
):
    """Retrieve all laboratory tests with optional search and category filters."""
    results = list(db.lab_tests)

    if search is not None:
        term = search.strip().lower()
        results = [
            t for t in results
            if term in t["test_name"].lower() or term in t["test_code"].lower()
        ]

    if category is not None:
        cat_term = category.strip().lower()
        results = [t for t in results if cat_term in t["category"].lower()]

    if is_active is not None:
        results = [t for t in results if t["is_active"] == is_active]

    return results


@router.get("/lab-tests/{test_id}", response_model=LabTestResponse)
def get_lab_test_by_id(test_id: int):
    """Get laboratory test details by ID."""
    test = db.get_lab_test(test_id)
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Laboratory test with ID {test_id} not found.",
        )
    return test


@router.put("/lab-tests/{test_id}", response_model=LabTestResponse)
def update_lab_test(test_id: int, test_in: LabTestUpdate):
    """Update laboratory test details. Validates uniqueness if test_code is changed."""
    test = db.get_lab_test(test_id)
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Laboratory test with ID {test_id} not found.",
        )

    update_dict = test_in.model_dump(exclude_unset=True)

    # Check test_code uniqueness if updated
    if "test_code" in update_dict and update_dict["test_code"]:
        code_normalized = update_dict["test_code"].strip().upper()
        for existing in db.lab_tests:
            if existing["id"] != test_id and existing["test_code"].strip().upper() == code_normalized:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Laboratory test with code '{update_dict['test_code']}' already exists.",
                )
        update_dict["test_code"] = code_normalized

    test.update(update_dict)
    return test


@router.delete("/lab-tests/{test_id}")
def delete_lab_test(test_id: int):
    """Delete a laboratory test. Prevents deletion if associated lab orders exist."""
    test = db.get_lab_test(test_id)
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Laboratory test with ID {test_id} not found.",
        )

    has_orders = any(o["test_id"] == test_id for o in db.lab_orders)
    if has_orders:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete laboratory test '{test['test_name']}' because existing orders reference it. Deactivate it instead.",
        )

    db.lab_tests.remove(test)
    return {
        "message": f"Laboratory test '{test['test_name']}' (ID: {test_id}) deleted successfully.",
        "test_id": test_id,
    }


# ============================================================================
# 2. Patient Lab Test Orders
# ============================================================================

@router.post("/lab-orders", response_model=LabOrderResponse, status_code=status.HTTP_201_CREATED)
def create_lab_order(order_in: LabOrderCreate):
    """
    Create a new lab test order.
    Business Rules:
    - Patient, doctor, and test must exist (404 otherwise).
    - Inactive laboratory tests cannot be ordered (400).
    - Initial order status is ORDERED.
    """
    patient = db.get_patient(order_in.patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with ID {order_in.patient_id} not found.",
        )

    doctor = db.get_doctor(order_in.doctor_id)
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Doctor with ID {order_in.doctor_id} not found.",
        )

    test = db.get_lab_test(order_in.test_id)
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Laboratory test with ID {order_in.test_id} not found.",
        )

    if not test["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Laboratory test '{test['test_name']}' is currently inactive and cannot be ordered.",
        )

    order_record = {
        "id": db.next_lab_order_id(),
        "patient_id": order_in.patient_id,
        "doctor_id": order_in.doctor_id,
        "test_id": order_in.test_id,
        "order_date": datetime.now(),
        "scheduled_date": order_in.scheduled_date or date.today(),
        "status": LabOrderStatus.ORDERED.value,
        "notes": order_in.notes or "",
    }
    db.lab_orders.append(order_record)
    return format_order_response(order_record)


@router.post("/lab-orders/batch", response_model=LabBatchOrderResponse, status_code=status.HTTP_201_CREATED)
def create_batch_lab_orders(batch_in: LabOrderBatchCreate):
    """
    Create orders for multiple tests for a patient and calculate the total cost.
    Validates patient, doctor, and all tests.
    """
    patient = db.get_patient(batch_in.patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with ID {batch_in.patient_id} not found.",
        )

    doctor = db.get_doctor(batch_in.doctor_id)
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Doctor with ID {batch_in.doctor_id} not found.",
        )

    # Validate all tests first
    tests_to_order = []
    for tid in batch_in.test_ids:
        test = db.get_lab_test(tid)
        if not test:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Laboratory test with ID {tid} not found.",
            )
        if not test["is_active"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Laboratory test '{test['test_name']}' (ID: {tid}) is inactive and cannot be ordered.",
            )
        tests_to_order.append(test)

    created_orders = []
    total_cost = 0.0
    now = datetime.now()
    sched = batch_in.scheduled_date or date.today()

    for test in tests_to_order:
        ord_rec = {
            "id": db.next_lab_order_id(),
            "patient_id": batch_in.patient_id,
            "doctor_id": batch_in.doctor_id,
            "test_id": test["id"],
            "order_date": now,
            "scheduled_date": sched,
            "status": LabOrderStatus.ORDERED.value,
            "notes": batch_in.notes or "",
        }
        db.lab_orders.append(ord_rec)
        created_orders.append(format_order_response(ord_rec))
        total_cost += test["price"]

    return {
        "patient_id": batch_in.patient_id,
        "doctor_id": batch_in.doctor_id,
        "total_orders": len(created_orders),
        "total_cost": round(total_cost, 2),
        "orders": created_orders,
    }


@router.get("/lab-orders", response_model=List[LabOrderResponse])
def get_all_lab_orders(
    patient_id: Optional[int] = Query(None, description="Filter orders by patient ID"),
    doctor_id: Optional[int] = Query(None, description="Filter orders by doctor ID"),
    status: Optional[str] = Query(None, description="Filter orders by status (e.g., ORDERED, COMPLETED)"),
    scheduled_date: Optional[date] = Query(None, description="Filter orders by scheduled date"),
    sort_by: Optional[str] = Query("order_date", description="Sort by 'order_date' or 'scheduled_date'"),
    sort_order: Optional[str] = Query("desc", description="Sort order: 'asc' or 'desc'"),
):
    """Retrieve all lab orders with filtering by patient, doctor, status, date, and sorting."""
    results = list(db.lab_orders)

    if patient_id is not None:
        results = [o for o in results if o["patient_id"] == patient_id]

    if doctor_id is not None:
        results = [o for o in results if o["doctor_id"] == doctor_id]

    if status is not None:
        status_clean = status.strip().upper()
        results = [o for o in results if o["status"].upper() == status_clean]

    if scheduled_date is not None:
        results = [o for o in results if o["scheduled_date"] == scheduled_date]

    # Sort
    reverse = (sort_order.lower() == "desc") if sort_order else True
    if sort_by == "scheduled_date":
        results.sort(key=lambda x: x["scheduled_date"], reverse=reverse)
    else:
        results.sort(key=lambda x: x["order_date"], reverse=reverse)

    return [format_order_response(o) for o in results]


@router.get("/lab-orders/{order_id}", response_model=LabOrderResponse)
def get_lab_order_by_id(order_id: int):
    """Get laboratory order details by ID."""
    order = db.get_lab_order(order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Laboratory order with ID {order_id} not found.",
        )
    return format_order_response(order)


@router.patch("/lab-orders/{order_id}/status", response_model=LabOrderResponse)
def update_lab_order_status(order_id: int, status_in: LabOrderStatusUpdate):
    """
    Update the status of a laboratory order.
    Validates status values (ORDERED, SAMPLE_COLLECTED, PROCESSING, COMPLETED, CANCELLED).
    """
    order = db.get_lab_order(order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Laboratory order with ID {order_id} not found.",
        )

    new_status = status_in.status.value

    # If already COMPLETED and trying to change to ORDERED/PROCESSING
    if order["status"] == LabOrderStatus.COMPLETED.value and new_status != LabOrderStatus.COMPLETED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot alter the status of an already COMPLETED order.",
        )

    order["status"] = new_status
    return format_order_response(order)


@router.get("/patients/{patient_id}/lab-orders", response_model=List[LabOrderResponse])
def get_patient_lab_orders(patient_id: int, response: Response):
    """
    Get patient lab history.
    Calculates total cost of all ordered tests and sets 'X-Total-Cost' in the response headers.
    """
    patient = db.get_patient(patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with ID {patient_id} not found.",
        )

    orders = [o for o in db.lab_orders if o["patient_id"] == patient_id]

    total_cost = 0.0
    formatted_orders = []
    for o in orders:
        fmt = format_order_response(o)
        formatted_orders.append(fmt)
        if fmt.get("test_price"):
            total_cost += fmt["test_price"]

    # Expose total cost in headers for convenience
    response.headers["X-Total-Cost"] = str(round(total_cost, 2))
    response.headers["X-Total-Orders"] = str(len(orders))
    return formatted_orders


@router.get("/patients/{patient_id}/lab-orders/summary", response_model=PatientLabHistorySummary)
def get_patient_lab_summary(patient_id: int):
    """
    Get patient lab history summary including total tests ordered and calculated total cost.
    """
    patient = db.get_patient(patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with ID {patient_id} not found.",
        )

    orders = [o for o in db.lab_orders if o["patient_id"] == patient_id]
    formatted_orders = [format_order_response(o) for o in orders]
    total_cost = sum(o.get("test_price", 0.0) or 0.0 for o in formatted_orders)

    return {
        "patient_id": patient["id"],
        "patient_name": patient["full_name"],
        "total_orders": len(formatted_orders),
        "total_cost": round(total_cost, 2),
        "orders": formatted_orders,
    }


# ============================================================================
# 3. Laboratory Result Management
# ============================================================================

@router.post("/lab-results", response_model=LabResultResponse, status_code=status.HTTP_201_CREATED)
def record_lab_result(result_in: LabResultCreate):
    """
    Record laboratory test results for an order.
    Business Rules:
    - Order must exist (404).
    - Cannot record results for a CANCELLED order (400).
    - Results can only be recorded after sample collection or processing (SAMPLE_COLLECTED or PROCESSING) (400).
    - Prevent duplicate results for the same order (400).
    - Automatically marks the order as COMPLETED after the result is recorded.
    """
    order = db.get_lab_order(result_in.order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Laboratory order with ID {result_in.order_id} not found.",
        )

    # 1. Prevent duplicate results for the same order
    existing_result = db.get_lab_result_by_order(result_in.order_id)
    if existing_result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A laboratory result has already been recorded for order ID {result_in.order_id}.",
        )

    # 2. Do not allow cancelled orders to receive results
    if order["status"] == LabOrderStatus.CANCELLED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot record results for a CANCELLED laboratory order.",
        )

    # 3. Allow results to be recorded only after sample collection or processing
    if order["status"] not in [LabOrderStatus.SAMPLE_COLLECTED.value, LabOrderStatus.PROCESSING.value]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot record result for order with status '{order['status']}'. "
                "Results can only be recorded after sample collection or during processing "
                "(status must be SAMPLE_COLLECTED or PROCESSING)."
            ),
        )

    # 4. Automatically mark order as COMPLETED
    order["status"] = LabOrderStatus.COMPLETED.value

    # 5. Store the result
    result_record = {
        "id": db.next_lab_result_id(),
        "order_id": result_in.order_id,
        "result_value": result_in.result_value,
        "normal_range": result_in.normal_range,
        "remarks": result_in.remarks or "",
        "tested_by": result_in.tested_by,
        "result_date": result_in.result_date or datetime.now(),
    }
    db.lab_results.append(result_record)
    return result_record


@router.get("/lab-results", response_model=List[LabResultResponse])
def get_all_lab_results():
    """Retrieve all recorded laboratory test results."""
    return db.lab_results


@router.get("/lab-results/{result_id}", response_model=LabResultResponse)
def get_lab_result_by_id(result_id: int):
    """Get laboratory test result details by result ID."""
    result = db.get_lab_result(result_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Laboratory result with ID {result_id} not found.",
        )
    return result


@router.get("/lab-orders/{order_id}/result", response_model=LabResultResponse)
def get_result_for_order(order_id: int):
    """Get the laboratory test result associated with a specific order."""
    order = db.get_lab_order(order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Laboratory order with ID {order_id} not found.",
        )

    result = db.get_lab_result_by_order(order_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No laboratory result found for order ID {order_id}.",
        )
    return result
