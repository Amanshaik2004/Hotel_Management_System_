from datetime import date, timedelta


def test_book_appointment_success_and_rules(client):
    # Setup Doctor and Patient
    today = date.today()
    # Find next Monday
    days_ahead = (0 - today.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    target_monday = today + timedelta(days=days_ahead)

    doc = client.post("/doctors", json={
        "full_name": "Dr. House",
        "specialization": "Diagnostics",
        "email": "house@princeton.edu",
        "phone": "555-0199",
        "experience_years": 20,
        "consultation_fee": 300.0,
        "available_days": ["Monday"],
        "is_available": True,
    }).json()

    pat = client.post("/patients", json={
        "full_name": "Patient Zero",
        "age": 45,
        "gender": "Male",
        "email": "zero@test.com",
        "phone": "555-1111",
        "blood_group": "AB-",
        "address": "NJ",
    }).json()

    # 1. Past date fails
    past_date = today - timedelta(days=1)
    res_past = client.post("/appointments", json={
        "patient_id": pat["id"],
        "doctor_id": doc["id"],
        "appointment_date": past_date.isoformat(),
        "appointment_time": "10:00:00",
        "reason": "Checkup",
    })
    assert res_past.status_code == 400
    assert "past" in res_past.json()["detail"]

    # 2. Unavailable day fails (Tuesday)
    tuesday = target_monday + timedelta(days=1)
    res_wrong_day = client.post("/appointments", json={
        "patient_id": pat["id"],
        "doctor_id": doc["id"],
        "appointment_date": tuesday.isoformat(),
        "appointment_time": "10:00:00",
        "reason": "Checkup",
    })
    assert res_wrong_day.status_code == 400
    assert "not available on Tuesday" in res_wrong_day.json()["detail"]

    # 3. Successful booking on Monday
    res_book = client.post("/appointments", json={
        "patient_id": pat["id"],
        "doctor_id": doc["id"],
        "appointment_date": target_monday.isoformat(),
        "appointment_time": "10:00:00",
        "reason": "Leg pain",
    })
    assert res_book.status_code == 201
    appt_id = res_book.json()["id"]
    assert res_book.json()["status"] == "SCHEDULED"

    # 4. Double booking same doctor, same date & time fails
    res_double = client.post("/appointments", json={
        "patient_id": pat["id"],
        "doctor_id": doc["id"],
        "appointment_date": target_monday.isoformat(),
        "appointment_time": "10:00:00",
        "reason": "Second booking attempt",
    })
    assert res_double.status_code == 400
    assert "already has an active appointment" in res_double.json()["detail"]

    # 5. Different doctor at the same time is allowed
    doc2 = client.post("/doctors", json={
        "full_name": "Dr. Cuddy",
        "specialization": "Endocrinology",
        "email": "cuddy@princeton.edu",
        "phone": "555-0200",
        "experience_years": 15,
        "consultation_fee": 250.0,
        "available_days": ["Monday"],
        "is_available": True,
    }).json()

    res_doc2 = client.post("/appointments", json={
        "patient_id": pat["id"],
        "doctor_id": doc2["id"],
        "appointment_date": target_monday.isoformat(),
        "appointment_time": "10:00:00",
        "reason": "Routine consult",
    })
    assert res_doc2.status_code == 201


def test_appointment_cancellation_and_rescheduling(client):
    today = date.today()
    target_date = today + timedelta(days=7)
    day_name = target_date.strftime("%A")

    doc = client.post("/doctors", json={
        "full_name": "Dr. Wilson",
        "specialization": "Oncology",
        "email": "wilson@hospital.com",
        "phone": "555-1234",
        "experience_years": 14,
        "consultation_fee": 200.0,
        "available_days": [day_name],
    }).json()

    pat = client.post("/patients", json={
        "full_name": "Test Patient",
        "age": 29,
        "gender": "Female",
        "email": "testpat@hospital.com",
        "phone": "555-5555",
        "blood_group": "O+",
        "address": "Campus",
    }).json()

    appt = client.post("/appointments", json={
        "patient_id": pat["id"],
        "doctor_id": doc["id"],
        "appointment_date": target_date.isoformat(),
        "appointment_time": "14:00:00",
        "reason": "Oncology consultation",
    }).json()

    # Cancel appointment
    cancel_res = client.patch(f"/appointments/{appt['id']}/cancel")
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "CANCELLED"

    # Cannot reschedule cancelled appointment without confirming status
    reschedule_err = client.put(f"/appointments/{appt['id']}", json={
        "reason": "Trying to edit without confirmation",
    })
    assert reschedule_err.status_code == 400
    assert "without confirming new status" in reschedule_err.json()["detail"]

    # Reconfirm with CONFIRMED status succeeds
    reconfirm_res = client.put(f"/appointments/{appt['id']}", json={
        "status": "CONFIRMED",
        "reason": "Reconfirmed with patient",
    })
    assert reconfirm_res.status_code == 200
    assert reconfirm_res.json()["status"] == "CONFIRMED"

    # Mark completed
    client.put(f"/appointments/{appt['id']}", json={"status": "COMPLETED"})

    # Completed appointment cannot be cancelled
    cant_cancel = client.patch(f"/appointments/{appt['id']}/cancel")
    assert cant_cancel.status_code == 400
    assert "already been completed" in cant_cancel.json()["detail"]


def test_appointment_filters_and_queries(client):
    today = date.today()
    day1 = today + timedelta(days=7)
    day2 = today + timedelta(days=8)

    doc = client.post("/doctors", json={
        "full_name": "Dr. Who",
        "specialization": "Time Medicine",
        "email": "tardis@gallifrey.com",
        "phone": "000-0000",
        "experience_years": 900,
        "consultation_fee": 100.0,
        "available_days": [day1.strftime("%A"), day2.strftime("%A")],
    }).json()

    pat1 = client.post("/patients", json={
        "full_name": "Rose Tyler",
        "age": 25,
        "gender": "Female",
        "email": "rose@badwolf.com",
        "phone": "111",
        "blood_group": "A+",
        "address": "London",
    }).json()

    pat2 = client.post("/patients", json={
        "full_name": "Donna Noble",
        "age": 35,
        "gender": "Female",
        "email": "donna@chiswick.com",
        "phone": "222",
        "blood_group": "B+",
        "address": "Chiswick",
    }).json()

    a1 = client.post("/appointments", json={
        "patient_id": pat1["id"],
        "doctor_id": doc["id"],
        "appointment_date": day1.isoformat(),
        "appointment_time": "09:00:00",
        "reason": "Consult 1",
    }).json()

    a2 = client.post("/appointments", json={
        "patient_id": pat2["id"],
        "doctor_id": doc["id"],
        "appointment_date": day2.isoformat(),
        "appointment_time": "11:00:00",
        "reason": "Consult 2",
    }).json()

    # Filter by patient
    p1_appts = client.get(f"/patients/{pat1['id']}/appointments")
    assert len(p1_appts.json()) == 1

    # Filter by doctor
    doc_appts = client.get(f"/doctors/{doc['id']}/appointments")
    assert len(doc_appts.json()) == 2

    # Filter by date query param
    date_filtered = client.get(f"/appointments?appointment_date={day1.isoformat()}")
    assert len(date_filtered.json()) == 1
    assert date_filtered.json()[0]["id"] == a1["id"]
