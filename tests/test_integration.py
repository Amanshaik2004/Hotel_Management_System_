from datetime import date, timedelta


def test_seed_and_reset_endpoints(client):
    # Test reset
    res = client.post("/reset-data")
    assert res.status_code == 200
    root = client.get("/").json()
    assert root["statistics"]["total_patients"] == 0

    # Test seed
    seed_res = client.post("/seed-data")
    assert seed_res.status_code == 200
    assert seed_res.json()["counts"]["patients"] == 2
    assert seed_res.json()["counts"]["doctors"] == 2
    assert seed_res.json()["counts"]["appointments"] == 1
    assert seed_res.json()["counts"]["bills"] == 1
    assert seed_res.json()["counts"]["medicines"] == 2
    assert seed_res.json()["counts"]["lab_tests"] == 4
    assert seed_res.json()["counts"]["lab_orders"] == 2
    assert seed_res.json()["counts"]["lab_results"] == 1

    # Root stats updated
    root_after = client.get("/").json()
    assert root_after["statistics"]["total_patients"] == 2
    assert root_after["statistics"]["total_doctors"] == 2
    assert root_after["statistics"]["total_lab_tests"] == 4
    assert root_after["statistics"]["total_lab_orders"] == 2
    assert root_after["statistics"]["total_lab_results"] == 1


def test_full_patient_to_billing_and_pharmacy_lifecycle(client):
    today = date.today()
    future_date = today + timedelta(days=5)
    target_day = future_date.strftime("%A")

    # 1. Register Doctor
    doc = client.post("/doctors", json={
        "full_name": "Dr. Clara Oswald",
        "specialization": "Pediatrics",
        "email": "clara@tardis.org",
        "phone": "+44-20-1111-2222",
        "experience_years": 7,
        "consultation_fee": 150.0,
        "available_days": [target_day],
    }).json()

    # 2. Register Patient
    pat = client.post("/patients", json={
        "full_name": "Little Amelia Pond",
        "age": 10,
        "gender": "Female",
        "email": "amelia@leadworth.com",
        "phone": "555-0909",
        "blood_group": "A+",
        "address": "Leadworth Village",
    }).json()

    # 3. Assign Doctor to Patient
    assign_res = client.post(f"/patients/{pat['id']}/assign-doctor/{doc['id']}")
    assert assign_res.status_code == 200

    assigned_doc = client.get(f"/patients/{pat['id']}/doctor").json()
    assert assigned_doc["id"] == doc["id"]

    # 4. Book Appointment
    appt = client.post("/appointments", json={
        "patient_id": pat["id"],
        "doctor_id": doc["id"],
        "appointment_date": future_date.isoformat(),
        "appointment_time": "15:30:00",
        "reason": "Annual pediatric checkup",
    }).json()
    assert appt["status"] == "SCHEDULED"

    # 5. Add Medicine to Pharmacy
    med = client.post("/medicines", json={
        "medicine_name": "Pediatric Multivitamin Drops",
        "generic_name": "Multivitamin",
        "manufacturer": "ChildHealth Inc",
        "category": "Nutritional",
        "batch_number": "VIT-2026-X",
        "quantity": 25,
        "unit_price": 10.0,
        "expiry_date": (today + timedelta(days=365)).isoformat(),
        "minimum_stock": 5,
    }).json()

    # 6. Patient purchases medicine
    sale = client.post("/medicine-sales", json={
        "medicine_id": med["id"],
        "patient_id": pat["id"],
        "quantity_sold": 2,
    }).json()
    assert sale["total_amount"] == 20.0  # 2 * 10.0

    # 7. Generate Bill for Consultation + Medicine + Lab
    # Consultation fee auto-defaults to doctor's 150.0 when consultation_fee is 0.0 or specified
    bill = client.post("/bills", json={
        "patient_id": pat["id"],
        "appointment_id": appt["id"],
        "consultation_fee": 0.0,  # should auto-populate doctor fee 150.0
        "medicine_charges": 20.0,
        "lab_charges": 30.0,
        "other_charges": 0.0,
        "discount": 10.0,  # subtotal = 200, discounted = 190
        "tax_percentage": 10.0,  # tax = 19
    }).json()

    assert bill["consultation_fee"] == 150.0
    assert bill["total_amount"] == 209.0
    assert bill["balance_amount"] == 209.0
    assert bill["payment_status"] == "PENDING"

    # 8. Record Payment in two installments: first 100 via UPI, second 109 via CARD
    p1 = client.post(f"/bills/{bill['id']}/payments", json={
        "amount": 100.0,
        "payment_method": "UPI",
        "transaction_reference": "UPI-TXN-001",
    }).json()
    assert p1["status"] == "SUCCESS"

    b_mid = client.get(f"/bills/{bill['id']}").json()
    assert b_mid["payment_status"] == "PARTIALLY_PAID"
    assert b_mid["paid_amount"] == 100.0
    assert b_mid["balance_amount"] == 109.0

    p2 = client.post(f"/bills/{bill['id']}/payments", json={
        "amount": 109.0,
        "payment_method": "CARD",
        "transaction_reference": "CARD-TXN-002",
    }).json()
    assert p2["status"] == "SUCCESS"

    b_final = client.get(f"/bills/{bill['id']}").json()
    assert b_final["payment_status"] == "PAID"
    assert b_final["balance_amount"] == 0.0

    # Check individual payment details endpoint
    pay_detail = client.get(f"/payments/{p1['id']}").json()
    assert pay_detail["payment_method"] == "UPI"
    assert pay_detail["amount"] == 100.0


def test_full_patient_laboratory_lifecycle(client):
    today = date.today()

    # 1. Register Doctor
    doc = client.post("/doctors", json={
        "full_name": "Dr. Allison Cameron",
        "specialization": "Immunology",
        "email": "cameron@princeton.edu",
        "phone": "+1-555-0301",
        "experience_years": 8,
        "consultation_fee": 180.0,
        "available_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
    }).json()

    # 2. Register Patient
    pat = client.post("/patients", json={
        "full_name": "Robert Chase",
        "age": 36,
        "gender": "Male",
        "email": "chase@princeton.edu",
        "phone": "+1-555-0302",
        "blood_group": "O+",
        "address": "Princeton, NJ",
    }).json()

    # 3. Add Diagnostic Tests
    t1 = client.post("/lab-tests", json={
        "test_name": "Erythrocyte Sedimentation Rate",
        "test_code": "ESR-001",
        "category": "Hematology",
        "price": 25.0,
        "sample_type": "Whole Blood",
        "preparation_instructions": "Fasting not needed",
    }).json()

    t2 = client.post("/lab-tests", json={
        "test_name": "C-Reactive Protein",
        "test_code": "CRP-002",
        "category": "Immunology",
        "price": 45.0,
        "sample_type": "Serum",
        "preparation_instructions": "Fasting not needed",
    }).json()

    # 4. Batch order both tests for patient
    batch_res = client.post("/lab-orders/batch", json={
        "patient_id": pat["id"],
        "doctor_id": doc["id"],
        "test_ids": [t1["id"], t2["id"]],
        "notes": "Assess systemic inflammation markers",
    })
    assert batch_res.status_code == 201
    batch_data = batch_res.json()
    assert batch_data["total_cost"] == 70.0  # 25.0 + 45.0
    orders = batch_data["orders"]
    assert len(orders) == 2

    order_esr = orders[0]
    order_crp = orders[1]

    # 5. Transition ESR Order status through lifecycle: ORDERED -> SAMPLE_COLLECTED -> PROCESSING
    up_collected = client.patch(f"/lab-orders/{order_esr['id']}/status", json={"status": "SAMPLE_COLLECTED"})
    assert up_collected.status_code == 200

    up_proc = client.patch(f"/lab-orders/{order_esr['id']}/status", json={"status": "PROCESSING"})
    assert up_proc.status_code == 200

    # 6. Record Lab Result for ESR
    res_esr = client.post("/lab-results", json={
        "order_id": order_esr["id"],
        "result_value": "8 mm/hr",
        "normal_range": "0-15 mm/hr",
        "remarks": "Normal sedimentation rate, no active inflammation detected.",
        "tested_by": "MLS Cameron",
    })
    assert res_esr.status_code == 201

    # Order automatically COMPLETED
    esr_completed = client.get(f"/lab-orders/{order_esr['id']}").json()
    assert esr_completed["status"] == "COMPLETED"

    # 7. Check result via order endpoint
    ord_res = client.get(f"/lab-orders/{order_esr['id']}/result")
    assert ord_res.status_code == 200
    assert ord_res.json()["result_value"] == "8 mm/hr"

    # 8. Check patient summary & total cost
    summary = client.get(f"/patients/{pat['id']}/lab-orders/summary").json()
    assert summary["total_orders"] == 2
    assert summary["total_cost"] == 70.0
