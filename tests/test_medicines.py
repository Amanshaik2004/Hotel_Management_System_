from datetime import date, timedelta


def test_medicine_crud_and_validation(client):
    today = date.today()
    future_expiry = today + timedelta(days=120)

    # Validation errors: unit_price <= 0
    err_res = client.post("/medicines", json={
        "medicine_name": "Bad Price Med",
        "generic_name": "Test",
        "manufacturer": "Pharma",
        "category": "Painkiller",
        "batch_number": "B01",
        "quantity": 10,
        "unit_price": 0.0,
        "expiry_date": future_expiry.isoformat(),
    })
    assert err_res.status_code == 422

    # Successful creation
    create_res = client.post("/medicines", json={
        "medicine_name": "Ibuprofen 400mg",
        "generic_name": "Ibuprofen",
        "manufacturer": "Abbott",
        "category": "NSAID",
        "batch_number": "IBU-100",
        "quantity": 50,
        "unit_price": 5.0,
        "expiry_date": future_expiry.isoformat(),
        "minimum_stock": 10,
        "is_active": True,
    })
    assert create_res.status_code == 201
    med = create_res.json()
    assert med["id"] == 1
    assert med["is_low_stock"] is False

    # Get by ID
    get_res = client.get(f"/medicines/{med['id']}")
    assert get_res.status_code == 200
    assert get_res.json()["medicine_name"] == "Ibuprofen 400mg"

    # Update
    up_res = client.put(f"/medicines/{med['id']}", json={"unit_price": 6.5})
    assert up_res.status_code == 200
    assert up_res.json()["unit_price"] == 6.5

    # Delete
    del_res = client.delete(f"/medicines/{med['id']}")
    assert del_res.status_code == 200
    assert client.get(f"/medicines/{med['id']}").status_code == 404


def test_stock_management_and_alerts(client):
    today = date.today()
    med = client.post("/medicines", json={
        "medicine_name": "Cough Syrup",
        "generic_name": "Dextromethorphan",
        "manufacturer": "Cipla",
        "category": "Antitussive",
        "batch_number": "CS-99",
        "quantity": 20,
        "unit_price": 8.0,
        "expiry_date": (today + timedelta(days=15)).isoformat(),  # Expiring soon
        "minimum_stock": 15,
    }).json()

    # Add stock
    add_res = client.patch(f"/medicines/{med['id']}/stock/add", json={"quantity": 10})
    assert add_res.status_code == 200
    assert add_res.json()["quantity"] == 30

    # Reduce stock beyond available fails
    err_red = client.patch(f"/medicines/{med['id']}/stock/reduce", json={"quantity": 50})
    assert err_red.status_code == 400
    assert "Available stock is only 30" in err_red.json()["detail"]

    # Reduce stock so it falls below minimum_stock (30 - 20 = 10 <= 15)
    red_res = client.patch(f"/medicines/{med['id']}/stock/reduce", json={"quantity": 20})
    assert red_res.status_code == 200
    assert red_res.json()["quantity"] == 10
    assert red_res.json()["is_low_stock"] is True

    # Check low-stock endpoint
    low_stock = client.get("/medicines/low-stock")
    assert low_stock.status_code == 200
    assert len(low_stock.json()) == 1

    # Check expiring endpoint (within 30 days)
    expiring = client.get("/medicines/expiring?days=30")
    assert expiring.status_code == 200
    assert len(expiring.json()) == 1


def test_medicine_sales_and_business_rules(client):
    today = date.today()

    # Patient setup
    pat = client.post("/patients", json={
        "full_name": "Clark Kent",
        "age": 33,
        "gender": "Male",
        "email": "clark@dailyplanet.com",
        "phone": "555-8888",
        "blood_group": "O-",
        "address": "Metropolis",
    }).json()

    # Active medicine with stock 10
    med_active = client.post("/medicines", json={
        "medicine_name": "Super Vitamin",
        "generic_name": "Multivitamin",
        "manufacturer": "Wayne Corp",
        "category": "Supplement",
        "batch_number": "SUP-1",
        "quantity": 10,
        "unit_price": 15.0,
        "expiry_date": (today + timedelta(days=90)).isoformat(),
        "is_active": True,
    }).json()

    # Inactive medicine
    med_inactive = client.post("/medicines", json={
        "medicine_name": "Discontinued Pill",
        "generic_name": "OldMed",
        "manufacturer": "Wayne Corp",
        "category": "Supplement",
        "batch_number": "SUP-2",
        "quantity": 50,
        "unit_price": 5.0,
        "expiry_date": (today + timedelta(days=90)).isoformat(),
        "is_active": False,
    }).json()

    # Expired medicine
    med_expired = client.post("/medicines", json={
        "medicine_name": "Expired Syrup",
        "generic_name": "OldSyrup",
        "manufacturer": "Wayne Corp",
        "category": "Supplement",
        "batch_number": "SUP-3",
        "quantity": 50,
        "unit_price": 5.0,
        "expiry_date": (today - timedelta(days=5)).isoformat(),
        "is_active": True,
    }).json()

    # 1. Selling inactive medicine fails
    res_inact = client.post("/medicine-sales", json={
        "medicine_id": med_inactive["id"],
        "patient_id": pat["id"],
        "quantity_sold": 2,
    })
    assert res_inact.status_code == 400
    assert "inactive" in res_inact.json()["detail"]

    # 2. Selling expired medicine fails
    res_exp = client.post("/medicine-sales", json={
        "medicine_id": med_expired["id"],
        "patient_id": pat["id"],
        "quantity_sold": 2,
    })
    assert res_exp.status_code == 400
    assert "expired" in res_exp.json()["detail"]

    # 3. Selling more than available stock fails
    res_insuf = client.post("/medicine-sales", json={
        "medicine_id": med_active["id"],
        "patient_id": pat["id"],
        "quantity_sold": 15,  # only 10 available
    })
    assert res_insuf.status_code == 400
    assert "Insufficient stock" in res_insuf.json()["detail"]

    # 4. Successful sale of 3 units
    sale_res = client.post("/medicine-sales", json={
        "medicine_id": med_active["id"],
        "patient_id": pat["id"],
        "quantity_sold": 3,
    })
    assert sale_res.status_code == 201
    sale_data = sale_res.json()
    assert sale_data["quantity_sold"] == 3
    assert sale_data["unit_price"] == 15.0
    assert sale_data["total_amount"] == 45.0

    # Stock should be automatically reduced to 7
    updated_med = client.get(f"/medicines/{med_active['id']}").json()
    assert updated_med["quantity"] == 7

    # 5. Patient purchase history
    pat_history = client.get(f"/patients/{pat['id']}/medicine-sales")
    assert pat_history.status_code == 200
    assert len(pat_history.json()) == 1
    assert pat_history.json()[0]["medicine_id"] == med_active["id"]
