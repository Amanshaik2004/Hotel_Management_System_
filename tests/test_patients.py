def test_register_patient_success(client):
    payload = {
        "full_name": "Alice Wonderland",
        "age": 30,
        "gender": "Female",
        "email": "alice@example.com",
        "phone": "+1-555-1234",
        "blood_group": "B+",
        "address": "42 Rabbit Hole Lane",
        "is_active": True,
    }
    response = client.post("/patients", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == 1
    assert data["full_name"] == "Alice Wonderland"
    assert data["email"] == "alice@example.com"
    assert data["assigned_doctor_id"] is None


def test_duplicate_email_validation(client):
    payload = {
        "full_name": "Alice One",
        "age": 30,
        "gender": "Female",
        "email": "alice@example.com",
        "phone": "+1-555-1234",
        "blood_group": "B+",
        "address": "Lane 1",
    }
    res1 = client.post("/patients", json=payload)
    assert res1.status_code == 201

    payload2 = {
        "full_name": "Alice Two",
        "age": 25,
        "gender": "Female",
        "email": "alice@example.com",
        "phone": "+1-555-5678",
        "blood_group": "A+",
        "address": "Lane 2",
    }
    res2 = client.post("/patients", json=payload2)
    assert res2.status_code == 400
    assert "already exists" in res2.json()["detail"]


def test_invalid_age_and_email_format(client):
    # Age > 120
    res1 = client.post("/patients", json={
        "full_name": "Too Old",
        "age": 150,
        "gender": "Male",
        "email": "old@example.com",
        "phone": "+1-555-0000",
        "blood_group": "O+",
        "address": "Street",
    })
    assert res1.status_code == 422

    # Age <= 0
    res2 = client.post("/patients", json={
        "full_name": "Zero Age",
        "age": 0,
        "gender": "Male",
        "email": "zero@example.com",
        "phone": "+1-555-0000",
        "blood_group": "O+",
        "address": "Street",
    })
    assert res2.status_code == 422

    # Invalid email
    res3 = client.post("/patients", json={
        "full_name": "Bad Email",
        "age": 25,
        "gender": "Male",
        "email": "not-an-email",
        "phone": "+1-555-0000",
        "blood_group": "O+",
        "address": "Street",
    })
    assert res3.status_code == 422


def test_blank_required_fields(client):
    res = client.post("/patients", json={
        "full_name": "   ",
        "age": 25,
        "gender": "Male",
        "email": "valid@example.com",
        "phone": "+1-555-0000",
        "blood_group": "O+",
        "address": "Street",
    })
    assert res.status_code == 422


def test_patient_crud_and_not_found(client):
    # 404 for non-existent
    res = client.get("/patients/999")
    assert res.status_code == 404

    # Create
    created = client.post("/patients", json={
        "full_name": "Bob Builder",
        "age": 40,
        "gender": "Male",
        "email": "bob@example.com",
        "phone": "+1-555-9999",
        "blood_group": "AB+",
        "address": "Can Fix It Road",
    }).json()

    pid = created["id"]

    # Get by ID
    get_res = client.get(f"/patients/{pid}")
    assert get_res.status_code == 200
    assert get_res.json()["full_name"] == "Bob Builder"

    # Update
    update_res = client.put(f"/patients/{pid}", json={"age": 41, "address": "New Road"})
    assert update_res.status_code == 200
    assert update_res.json()["age"] == 41
    assert update_res.json()["address"] == "New Road"

    # Delete
    del_res = client.delete(f"/patients/{pid}")
    assert del_res.status_code == 200

    # Verify deleted
    assert client.get(f"/patients/{pid}").status_code == 404


def test_patient_search_and_filters(client):
    # Insert test data
    client.post("/patients", json={
        "full_name": "John Smith",
        "age": 20,
        "gender": "Male",
        "email": "john@test.com",
        "phone": "123",
        "blood_group": "O+",
        "address": "Addr 1",
        "is_active": True,
    })
    client.post("/patients", json={
        "full_name": "Jane Doe",
        "age": 30,
        "gender": "Female",
        "email": "jane@test.com",
        "phone": "456",
        "blood_group": "A+",
        "address": "Addr 2",
        "is_active": False,
    })
    client.post("/patients", json={
        "full_name": "Johnny English",
        "age": 50,
        "gender": "Male",
        "email": "agent@test.com",
        "phone": "789",
        "blood_group": "O+",
        "address": "Addr 3",
        "is_active": True,
    })

    # Search by name
    res = client.get("/patients?search=John")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 2

    # Filter gender
    res = client.get("/patients?gender=Female")
    assert len(res.json()) == 1
    assert res.json()[0]["full_name"] == "Jane Doe"

    # Filter blood group
    res = client.get("/patients?blood_group=O%2B")
    assert len(res.json()) == 2

    # Filter age range
    res = client.get("/patients?min_age=25&max_age=40")
    assert len(res.json()) == 1
    assert res.json()[0]["full_name"] == "Jane Doe"

    # Filter active
    res = client.get("/patients?is_active=false")
    assert len(res.json()) == 1
    assert res.json()[0]["full_name"] == "Jane Doe"
