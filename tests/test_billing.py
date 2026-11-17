from datetime import date, timedelta


def setup_patient_and_appointment(client):
    today = date.today()
    future_date = today + timedelta(days=7)
    day_name = future_date.strftime("%A")

    doc = client.post("/doctors", json={
        "full_name": "Dr. Bones",
        "specialization": "Surgery",
        "email": "bones@enterprise.com",
        "phone": "555-4321",
        "experience_years": 10,
        "consultation_fee": 100.0,
        "available_days": [day_name],
    }).json()

    pat = client.post("/patients", json={
        "full_name": "James Kirk",
        "age": 34,
        "gender": "Male",
        "email": "kirk@enterprise.com",
        "phone": "555-1701",
        "blood_group": "O+",
        "address": "Riverside, Iowa",
    }).json()

    appt = client.post("/appointments", json={
        "patient_id": pat["id"],
        "doctor_id": doc["id"],
        "appointment_date": future_date.isoformat(),
        "appointment_time": "10:00:00",
        "reason": "Routine physical",
    }).json()

    return pat, appt


def test_bill_generation_and_calculations(client):
    pat, appt = setup_patient_and_appointment(client)

    # Calculation test:
    # consultation: 100.0
    # medicine: 50.0
    # lab: 50.0
    # other: 0.0
    # subtotal = 200.0
    # discount = 20.0 -> discounted subtotal = 180.0
    # tax = 10% of 180.0 = 18.0
    # total = 198.0
    # paid = 0, balance = 198.0, status = PENDING

    bill_res = client.post("/bills", json={
        "patient_id": pat["id"],
        "appointment_id": appt["id"],
        "consultation_fee": 100.0,
        "medicine_charges": 50.0,
        "lab_charges": 50.0,
        "other_charges": 0.0,
        "discount": 20.0,
        "tax_percentage": 10.0,
    })
    assert bill_res.status_code == 201
    bill = bill_res.json()
    assert bill["total_amount"] == 198.0
    assert bill["balance_amount"] == 198.0
    assert bill["paid_amount"] == 0.0
    assert bill["payment_status"] == "PENDING"
    assert "BILL-" in bill["bill_number"]


def test_discount_cannot_exceed_subtotal(client):
    pat, appt = setup_patient_and_appointment(client)

    # Subtotal is 100.0, discount is 150.0 -> fails validation
    res = client.post("/bills", json={
        "patient_id": pat["id"],
        "appointment_id": appt["id"],
        "consultation_fee": 100.0,
        "medicine_charges": 0.0,
        "lab_charges": 0.0,
        "other_charges": 0.0,
        "discount": 150.0,
        "tax_percentage": 5.0,
    })
    assert res.status_code == 422


def test_partial_and_full_payments(client):
    pat, appt = setup_patient_and_appointment(client)

    bill = client.post("/bills", json={
        "patient_id": pat["id"],
        "appointment_id": appt["id"],
        "consultation_fee": 100.0,
        "medicine_charges": 0.0,
        "lab_charges": 0.0,
        "other_charges": 0.0,
        "discount": 0.0,
        "tax_percentage": 0.0,
    }).json()

    bill_id = bill["id"]
    assert bill["total_amount"] == 100.0
    assert bill["balance_amount"] == 100.0

    # 1. Partial payment of 40.0
    p1 = client.post(f"/bills/{bill_id}/payments", json={
        "amount": 40.0,
        "payment_method": "UPI",
        "transaction_reference": "UPI-12345",
    })
    assert p1.status_code == 201

    # Check updated bill
    updated_bill = client.get(f"/bills/{bill_id}").json()
    assert updated_bill["paid_amount"] == 40.0
    assert updated_bill["balance_amount"] == 60.0
    assert updated_bill["payment_status"] == "PARTIALLY_PAID"

    # 2. Overpayment attempt (paying 70.0 when balance is 60.0) -> fails
    overpay = client.post(f"/bills/{bill_id}/payments", json={
        "amount": 70.0,
        "payment_method": "CASH",
    })
    assert overpay.status_code == 400
    assert "exceeds outstanding balance" in overpay.json()["detail"]

    # 3. Pay exact remaining balance (60.0)
    p2 = client.post(f"/bills/{bill_id}/payments", json={
        "amount": 60.0,
        "payment_method": "CARD",
    })
    assert p2.status_code == 201

    final_bill = client.get(f"/bills/{bill_id}").json()
    assert final_bill["paid_amount"] == 100.0
    assert final_bill["balance_amount"] == 0.0
    assert final_bill["payment_status"] == "PAID"

    # 4. Payment on fully paid bill fails
    extra_pay = client.post(f"/bills/{bill_id}/payments", json={
        "amount": 10.0,
        "payment_method": "CASH",
    })
    assert extra_pay.status_code == 400
    assert "already fully paid" in extra_pay.json()["detail"]

    # 5. Payment history
    history = client.get(f"/bills/{bill_id}/payments")
    assert len(history.json()) == 2


def test_payment_against_cancelled_bill_rejected(client):
    pat, appt = setup_patient_and_appointment(client)

    bill = client.post("/bills", json={
        "patient_id": pat["id"],
        "appointment_id": appt["id"],
        "consultation_fee": 100.0,
        "medicine_charges": 0.0,
        "lab_charges": 0.0,
        "other_charges": 0.0,
        "discount": 0.0,
        "tax_percentage": 0.0,
    }).json()

    # Cancel the bill
    client.put(f"/bills/{bill['id']}", json={"payment_status": "CANCELLED"})

    # Try recording payment
    pay_res = client.post(f"/bills/{bill['id']}/payments", json={
        "amount": 50.0,
        "payment_method": "CASH",
    })
    assert pay_res.status_code == 400
    assert "CANCELLED" in pay_res.json()["detail"]


def test_patient_billing_history(client):
    pat, appt = setup_patient_and_appointment(client)

    b1 = client.post("/bills", json={
        "patient_id": pat["id"],
        "appointment_id": appt["id"],
        "consultation_fee": 50.0,
    }).json()

    history = client.get(f"/patients/{pat['id']}/bills")
    assert history.status_code == 200
    assert len(history.json()) == 1
    assert history.json()[0]["id"] == b1["id"]
