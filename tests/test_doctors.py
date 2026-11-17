def test_register_doctor_success(client):
    payload = {
        "full_name": "Dr. Watson",
        "specialization": "General Medicine",
        "email": "watson@bakerstreet.com",
        "phone": "+44-20-7946-0958",
        "experience_years": 10,
        "consultation_fee": 120.0,
        "available_days": ["Monday", "Wednesday", "Friday"],
        "is_available": True,
    }
    res = client.post("/doctors", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["id"] == 1
    assert data["full_name"] == "Dr. Watson"
    assert data["consultation_fee"] == 120.0


def test_doctor_validation_errors(client):
    # Negative experience
    res1 = client.post("/doctors", json={
        "full_name": "Dr. Neg Exp",
        "specialization": "Surgery",
        "email": "neg@doc.com",
        "phone": "123",
        "experience_years": -2,
        "consultation_fee": 100.0,
    })
    assert res1.status_code == 422

    # Zero or negative fee
    res2 = client.post("/doctors", json={
        "full_name": "Dr. Zero Fee",
        "specialization": "Surgery",
        "email": "zero@doc.com",
        "phone": "123",
        "experience_years": 5,
        "consultation_fee": 0.0,
    })
    assert res2.status_code == 422

    # Duplicate email
    payload = {
        "full_name": "Dr. Unique",
        "specialization": "Pediatrics",
        "email": "unique@doc.com",
        "phone": "123",
        "experience_years": 3,
        "consultation_fee": 80.0,
    }
    client.post("/doctors", json=payload)
    dup_res = client.post("/doctors", json=payload)
    assert dup_res.status_code == 400
    assert "already exists" in dup_res.json()["detail"]


def test_doctor_search_filter_sort(client):
    client.post("/doctors", json={
        "full_name": "Dr. Stephen Strange",
        "specialization": "Neuro",
        "email": "strange@marvel.com",
        "phone": "111",
        "experience_years": 15,
        "consultation_fee": 300.0,
        "is_available": True,
    })
    client.post("/doctors", json={
        "full_name": "Dr. Leonard McCoy",
        "specialization": "General",
        "email": "mccoy@enterprise.com",
        "phone": "222",
        "experience_years": 8,
        "consultation_fee": 150.0,
        "is_available": True,
    })
    client.post("/doctors", json={
        "full_name": "Dr. Beverly Crusher",
        "specialization": "General",
        "email": "crusher@enterprise.com",
        "phone": "333",
        "experience_years": 12,
        "consultation_fee": 200.0,
        "is_available": False,
    })

    # Search name
    res = client.get("/doctors?search=Strange")
    assert len(res.json()) == 1

    # Filter specialization
    res = client.get("/doctors?specialization=General")
    assert len(res.json()) == 2

    # Filter experience
    res = client.get("/doctors?min_experience=10")
    assert len(res.json()) == 2

    # Filter fee range
    res = client.get("/doctors?min_fee=140&max_fee=250")
    assert len(res.json()) == 2

    # Filter availability
    res = client.get("/doctors?is_available=false")
    assert len(res.json()) == 1
    assert res.json()[0]["full_name"] == "Dr. Beverly Crusher"

    # Sort by consultation fee desc
    res = client.get("/doctors?sort_by=fee&sort_order=desc")
    fees = [d["consultation_fee"] for d in res.json()]
    assert fees == [300.0, 200.0, 150.0]

    # Sort by experience asc
    res = client.get("/doctors?sort_by=experience&sort_order=asc")
    exp = [d["experience_years"] for d in res.json()]
    assert exp == [8, 12, 15]


def test_doctor_patient_assignment_and_retrieval(client):
    # Create doctor
    doc = client.post("/doctors", json={
        "full_name": "Dr. Meredith Grey",
        "specialization": "General Surgery",
        "email": "grey@seattlegrace.com",
        "phone": "123",
        "experience_years": 7,
        "consultation_fee": 180.0,
    }).json()

    # Create patient
    pat = client.post("/patients", json={
        "full_name": "Cristina Yang",
        "age": 32,
        "gender": "Female",
        "email": "yang@hospital.com",
        "phone": "999",
        "blood_group": "B+",
        "address": "Seattle",
    }).json()

    # Assign non-existent
    err1 = client.post(f"/patients/{pat['id']}/assign-doctor/999")
    assert err1.status_code == 404
    err2 = client.post(f"/patients/999/assign-doctor/{doc['id']}")
    assert err2.status_code == 404

    # Successful assign
    assign_res = client.post(f"/patients/{pat['id']}/assign-doctor/{doc['id']}")
    assert assign_res.status_code == 200
    assert assign_res.json()["doctor_id"] == doc["id"]

    # Retrieve doctor details for patient
    doc_for_pat = client.get(f"/patients/{pat['id']}/doctor")
    assert doc_for_pat.status_code == 200
    assert doc_for_pat.json()["id"] == doc["id"]

    # Retrieve all patients for doctor
    pats_for_doc = client.get(f"/doctors/{doc['id']}/patients")
    assert pats_for_doc.status_code == 200
    assert len(pats_for_doc.json()) == 1
    assert pats_for_doc.json()[0]["id"] == pat["id"]
