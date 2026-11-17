from datetime import date, timedelta
import pytest


@pytest.fixture
def lab_setup(client):
    """Sets up a sample doctor, patient, and lab tests for tests."""
    doc = client.post("/doctors", json={
        "full_name": "Dr. Gregory House",
        "specialization": "Diagnostics",
        "email": "house@princeton.edu",
        "phone": "+1-555-0199",
        "experience_years": 20,
        "consultation_fee": 300.0,
        "available_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
    }).json()

    pat = client.post("/patients", json={
        "full_name": "James Wilson",
        "age": 42,
        "gender": "Male",
        "email": "wilson@princeton.edu",
        "phone": "+1-555-0299",
        "blood_group": "AB+",
        "address": "100 Mercer St, Princeton, NJ",
    }).json()

    # Active Test 1
    t1 = client.post("/lab-tests", json={
        "test_name": "Complete Blood Count",
        "test_code": "CBC-001",
        "category": "Hematology",
        "description": "Measures RBC, WBC, platelets, and hemoglobin",
        "price": 30.0,
        "sample_type": "Whole Blood",
        "preparation_instructions": "No fasting needed",
        "is_active": True,
    }).json()

    # Active Test 2
    t2 = client.post("/lab-tests", json={
        "test_name": "Comprehensive Metabolic Panel",
        "test_code": "CMP-002",
        "category": "Biochemistry",
        "description": "Evaluates organ function and electrolytes",
        "price": 50.0,
        "sample_type": "Serum",
        "preparation_instructions": "12-hour fasting required",
        "is_active": True,
    }).json()

    # Inactive Test 3
    t_inactive = client.post("/lab-tests", json={
        "test_name": "Legacy Urinalysis Panel",
        "test_code": "URN-OLD",
        "category": "Urinalysis",
        "description": "Discontinued panel",
        "price": 25.0,
        "sample_type": "Urine",
        "preparation_instructions": "None",
        "is_active": False,
    }).json()

    return {
        "doctor": doc,
        "patient": pat,
        "test_cbc": t1,
        "test_cmp": t2,
        "test_inactive": t_inactive,
    }


# ============================================================================
# 1. Laboratory Test CRUD Operations & Validation Tests
# ============================================================================

def test_create_lab_test_success_and_validation(client):
    # Validation: price <= 0 should fail with 422
    res_bad_price = client.post("/lab-tests", json={
        "test_name": "Thyroid Stimulating Hormone",
        "test_code": "TSH-001",
        "category": "Endocrinology",
        "price": 0.0,
        "sample_type": "Serum",
    })
    assert res_bad_price.status_code == 422

    res_negative_price = client.post("/lab-tests", json={
        "test_name": "Thyroid Stimulating Hormone",
        "test_code": "TSH-001",
        "category": "Endocrinology",
        "price": -15.0,
        "sample_type": "Serum",
    })
    assert res_negative_price.status_code == 422

    # Validation: empty / blank name or code should fail with 422
    res_blank_name = client.post("/lab-tests", json={
        "test_name": "   ",
        "test_code": "TSH-001",
        "category": "Endocrinology",
        "price": 40.0,
        "sample_type": "Serum",
    })
    assert res_blank_name.status_code == 422

    res_blank_code = client.post("/lab-tests", json={
        "test_name": "Thyroid Stimulating Hormone",
        "test_code": "   ",
        "category": "Endocrinology",
        "price": 40.0,
        "sample_type": "Serum",
    })
    assert res_blank_code.status_code == 422

    # Successful creation
    res_valid = client.post("/lab-tests", json={
        "test_name": "Thyroid Stimulating Hormone",
        "test_code": "tsh-001",  # should be normalized to uppercase
        "category": "Endocrinology",
        "description": "Evaluates thyroid gland activity",
        "price": 45.0,
        "sample_type": "Serum",
        "preparation_instructions": "Fasting not required",
        "is_active": True,
    })
    assert res_valid.status_code == 201
    data = res_valid.json()
    assert data["id"] == 1
    assert data["test_name"] == "Thyroid Stimulating Hormone"
    assert data["test_code"] == "TSH-001"
    assert data["price"] == 45.0
    assert data["is_active"] is True


def test_duplicate_test_code_prevention(client, lab_setup):
    # Attempt to create duplicate test code (case-insensitive)
    res_dup = client.post("/lab-tests", json={
        "test_name": "Another CBC",
        "test_code": "cbc-001",  # already exists as CBC-001
        "category": "Hematology",
        "price": 32.0,
        "sample_type": "Whole Blood",
    })
    assert res_dup.status_code == 400
    assert "already exists" in res_dup.json()["detail"]


def test_get_lab_tests_search_and_filter(client, lab_setup):
    # Get all tests
    res_all = client.get("/lab-tests")
    assert res_all.status_code == 200
    assert len(res_all.json()) == 3

    # Search by test name (case-insensitive)
    res_search_name = client.get("/lab-tests?search=metabolic")
    assert res_search_name.status_code == 200
    assert len(res_search_name.json()) == 1
    assert res_search_name.json()[0]["test_code"] == "CMP-002"

    # Search by test code
    res_search_code = client.get("/lab-tests?search=cbc")
    assert res_search_code.status_code == 200
    assert len(res_search_code.json()) == 1
    assert res_search_code.json()[0]["test_name"] == "Complete Blood Count"

    # Filter by category
    res_cat = client.get("/lab-tests?category=Biochemistry")
    assert res_cat.status_code == 200
    assert len(res_cat.json()) == 1
    assert res_cat.json()[0]["test_code"] == "CMP-002"

    # Filter by is_active
    res_active = client.get("/lab-tests?is_active=true")
    assert res_active.status_code == 200
    assert len(res_active.json()) == 2

    res_inactive = client.get("/lab-tests?is_active=false")
    assert res_inactive.status_code == 200
    assert len(res_inactive.json()) == 1
    assert res_inactive.json()[0]["test_code"] == "URN-OLD"


def test_update_and_delete_lab_test(client, lab_setup):
    t = lab_setup["test_cbc"]

    # Get by ID
    get_res = client.get(f"/lab-tests/{t['id']}")
    assert get_res.status_code == 200
    assert get_res.json()["test_code"] == "CBC-001"

    # Update test details
    up_res = client.put(f"/lab-tests/{t['id']}", json={
        "price": 38.0,
        "description": "Updated CBC description",
    })
    assert up_res.status_code == 200
    assert up_res.json()["price"] == 38.0
    assert up_res.json()["description"] == "Updated CBC description"

    # Attempt to update to an existing code of another test
    up_dup = client.put(f"/lab-tests/{t['id']}", json={"test_code": "CMP-002"})
    assert up_dup.status_code == 400
    assert "already exists" in up_dup.json()["detail"]

    # Delete unused test
    del_res = client.delete(f"/lab-tests/{lab_setup['test_inactive']['id']}")
    assert del_res.status_code == 200
    assert "deleted successfully" in del_res.json()["message"]

    # Verify 404 after deletion
    assert client.get(f"/lab-tests/{lab_setup['test_inactive']['id']}").status_code == 404


# ============================================================================
# 2. Patient Lab Test Orders & Business Logic Tests
# ============================================================================

def test_create_lab_order_and_entity_validations(client, lab_setup):
    pat = lab_setup["patient"]
    doc = lab_setup["doctor"]
    t_cbc = lab_setup["test_cbc"]
    t_inact = lab_setup["test_inactive"]

    # 1. Invalid Patient ID -> 404
    res_inv_pat = client.post("/lab-orders", json={
        "patient_id": 9999,
        "doctor_id": doc["id"],
        "test_id": t_cbc["id"],
    })
    assert res_inv_pat.status_code == 404
    assert "Patient" in res_inv_pat.json()["detail"]

    # 2. Invalid Doctor ID -> 404
    res_inv_doc = client.post("/lab-orders", json={
        "patient_id": pat["id"],
        "doctor_id": 9999,
        "test_id": t_cbc["id"],
    })
    assert res_inv_doc.status_code == 404
    assert "Doctor" in res_inv_doc.json()["detail"]

    # 3. Invalid Test ID -> 404
    res_inv_test = client.post("/lab-orders", json={
        "patient_id": pat["id"],
        "doctor_id": doc["id"],
        "test_id": 9999,
    })
    assert res_inv_test.status_code == 404
    assert "Laboratory test" in res_inv_test.json()["detail"]

    # 4. Inactive test ordering prevention -> 400
    res_inact_order = client.post("/lab-orders", json={
        "patient_id": pat["id"],
        "doctor_id": doc["id"],
        "test_id": t_inact["id"],
    })
    assert res_inact_order.status_code == 400
    assert "inactive" in res_inact_order.json()["detail"]

    # 5. Successful Order creation
    today = date.today()
    res_ok = client.post("/lab-orders", json={
        "patient_id": pat["id"],
        "doctor_id": doc["id"],
        "test_id": t_cbc["id"],
        "scheduled_date": today.isoformat(),
        "notes": "Patient reports severe fatigue",
    })
    assert res_ok.status_code == 201
    ord_data = res_ok.json()
    assert ord_data["id"] == 1
    assert ord_data["status"] == "ORDERED"
    assert ord_data["patient_id"] == pat["id"]
    assert ord_data["doctor_id"] == doc["id"]
    assert ord_data["test_id"] == t_cbc["id"]
    assert ord_data["test_name"] == "Complete Blood Count"
    assert ord_data["test_price"] == 30.0

    # Cannot delete test now that it has an order
    del_block = client.delete(f"/lab-tests/{t_cbc['id']}")
    assert del_block.status_code == 400
    assert "existing orders reference it" in del_block.json()["detail"]


def test_batch_ordering_and_total_cost_calculation(client, lab_setup):
    pat = lab_setup["patient"]
    doc = lab_setup["doctor"]
    t1 = lab_setup["test_cbc"]  # 30.0
    t2 = lab_setup["test_cmp"]  # 50.0

    # Batch order both tests for one patient
    res = client.post("/lab-orders/batch", json={
        "patient_id": pat["id"],
        "doctor_id": doc["id"],
        "test_ids": [t1["id"], t2["id"]],
        "notes": "Annual executive health screening",
    })
    assert res.status_code == 201
    data = res.json()
    assert data["total_orders"] == 2
    assert data["total_cost"] == 80.0  # 30.0 + 50.0
    assert len(data["orders"]) == 2
    assert data["orders"][0]["status"] == "ORDERED"
    assert data["orders"][1]["status"] == "ORDERED"

    # Patient Lab History endpoint
    history = client.get(f"/patients/{pat['id']}/lab-orders")
    assert history.status_code == 200
    assert len(history.json()) == 2
    assert history.headers["X-Total-Cost"] == "80.0"

    # Patient Lab Summary endpoint
    summary = client.get(f"/patients/{pat['id']}/lab-orders/summary")
    assert summary.status_code == 200
    sum_data = summary.json()
    assert sum_data["patient_id"] == pat["id"]
    assert sum_data["total_orders"] == 2
    assert sum_data["total_cost"] == 80.0


def test_lab_order_search_filtering_and_sorting(client, lab_setup):
    pat = lab_setup["patient"]
    doc = lab_setup["doctor"]
    t1 = lab_setup["test_cbc"]
    t2 = lab_setup["test_cmp"]

    today = date.today()
    tomorrow = today + timedelta(days=1)

    # Order 1: today
    ord1 = client.post("/lab-orders", json={
        "patient_id": pat["id"],
        "doctor_id": doc["id"],
        "test_id": t1["id"],
        "scheduled_date": today.isoformat(),
    }).json()

    # Order 2: tomorrow
    ord2 = client.post("/lab-orders", json={
        "patient_id": pat["id"],
        "doctor_id": doc["id"],
        "test_id": t2["id"],
        "scheduled_date": tomorrow.isoformat(),
    }).json()

    # Update ord2 status to SAMPLE_COLLECTED
    client.patch(f"/lab-orders/{ord2['id']}/status", json={"status": "SAMPLE_COLLECTED"})

    # Filter by patient_id
    res_pat = client.get(f"/lab-orders?patient_id={pat['id']}")
    assert res_pat.status_code == 200
    assert len(res_pat.json()) == 2

    # Filter by status
    res_status = client.get("/lab-orders?status=SAMPLE_COLLECTED")
    assert res_status.status_code == 200
    assert len(res_status.json()) == 1
    assert res_status.json()[0]["id"] == ord2["id"]

    # Filter by scheduled_date
    res_date = client.get(f"/lab-orders?scheduled_date={tomorrow.isoformat()}")
    assert res_date.status_code == 200
    assert len(res_date.json()) == 1
    assert res_date.json()[0]["id"] == ord2["id"]

    # Sort orders by creation date
    res_sort_asc = client.get("/lab-orders?sort_by=order_date&sort_order=asc")
    assert res_sort_asc.status_code == 200
    assert res_sort_asc.json()[0]["id"] == ord1["id"]

    res_sort_desc = client.get("/lab-orders?sort_by=order_date&sort_order=desc")
    assert res_sort_desc.status_code == 200
    assert res_sort_desc.json()[0]["id"] == ord2["id"]


# ============================================================================
# 3. Laboratory Result Management & Business Logic Rules Tests
# ============================================================================

def test_lab_result_lifecycle_and_business_rules(client, lab_setup):
    pat = lab_setup["patient"]
    doc = lab_setup["doctor"]
    t_cbc = lab_setup["test_cbc"]

    # Create Order (initial status: ORDERED)
    order = client.post("/lab-orders", json={
        "patient_id": pat["id"],
        "doctor_id": doc["id"],
        "test_id": t_cbc["id"],
    }).json()
    order_id = order["id"]

    # 1. Rule Check: Cannot record result while order is still ORDERED
    res_fail_ordered = client.post("/lab-results", json={
        "order_id": order_id,
        "result_value": "Hemoglobin 14.5 g/dL",
        "normal_range": "13.5-17.5 g/dL",
        "tested_by": "Dr. House",
    })
    assert res_fail_ordered.status_code == 400
    assert "SAMPLE_COLLECTED or PROCESSING" in res_fail_ordered.json()["detail"]

    # 2. Rule Check: Cancelled orders cannot receive results
    # Create another order and cancel it
    ord_to_cancel = client.post("/lab-orders", json={
        "patient_id": pat["id"],
        "doctor_id": doc["id"],
        "test_id": t_cbc["id"],
    }).json()
    client.patch(f"/lab-orders/{ord_to_cancel['id']}/status", json={"status": "CANCELLED"})

    res_fail_cancelled = client.post("/lab-results", json={
        "order_id": ord_to_cancel["id"],
        "result_value": "Test",
        "normal_range": "Test",
        "tested_by": "Dr. House",
    })
    assert res_fail_cancelled.status_code == 400
    assert "CANCELLED" in res_fail_cancelled.json()["detail"]

    # 3. Transition order to SAMPLE_COLLECTED, then to PROCESSING
    up1 = client.patch(f"/lab-orders/{order_id}/status", json={"status": "SAMPLE_COLLECTED"})
    assert up1.status_code == 200
    assert up1.json()["status"] == "SAMPLE_COLLECTED"

    up2 = client.patch(f"/lab-orders/{order_id}/status", json={"status": "PROCESSING"})
    assert up2.status_code == 200
    assert up2.json()["status"] == "PROCESSING"

    # 4. Record test result successfully
    res_record = client.post("/lab-results", json={
        "order_id": order_id,
        "result_value": "WBC: 6,500 /mcL, RBC: 4.8 million/mcL, Platelets: 230,000 /mcL",
        "normal_range": "WBC: 4,500-11,000, RBC: 4.3-5.9 million, Platelets: 150,000-450,000",
        "remarks": "Complete Blood Count is completely normal.",
        "tested_by": "Lab Technician Sarah",
    })
    assert res_record.status_code == 201
    res_data = res_record.json()
    assert res_data["id"] == 1
    assert res_data["order_id"] == order_id
    assert res_data["tested_by"] == "Lab Technician Sarah"

    # 5. Rule Check: Order must be AUTOMATICALLY marked as COMPLETED
    updated_order = client.get(f"/lab-orders/{order_id}").json()
    assert updated_order["status"] == "COMPLETED"

    # 6. Rule Check: Prevent duplicate results for the same order
    res_duplicate = client.post("/lab-results", json={
        "order_id": order_id,
        "result_value": "Duplicate result attempt",
        "normal_range": "Standard",
        "tested_by": "Lab Technician Sarah",
    })
    assert res_duplicate.status_code == 400
    assert "already been recorded" in res_duplicate.json()["detail"]

    # 7. Get Result by Result ID
    res_by_id = client.get(f"/lab-results/{res_data['id']}")
    assert res_by_id.status_code == 200
    assert res_by_id.json()["id"] == res_data["id"]

    # 8. Get Result for Order ID
    res_by_order = client.get(f"/lab-orders/{order_id}/result")
    assert res_by_order.status_code == 200
    assert res_by_order.json()["order_id"] == order_id
    assert res_by_order.json()["remarks"] == "Complete Blood Count is completely normal."

    # 9. Result not found for order without results -> 404
    fresh_order = client.post("/lab-orders", json={
        "patient_id": pat["id"],
        "doctor_id": doc["id"],
        "test_id": t_cbc["id"],
    }).json()
    assert client.get(f"/lab-orders/{fresh_order['id']}/result").status_code == 404
