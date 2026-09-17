from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine

Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)
client = TestClient(app)

def test_register_duplicate_and_login():
    r = client.post('/auth/register', json={'username': 'test_inspector', 'password': 'StrongPass123!', 'role': 'INSPECTOR'})
    assert r.status_code == 200
    assert client.post('/auth/register', json={'username': 'test_inspector', 'password': 'OtherPass123!', 'role': 'INSPECTOR'}).status_code == 409
    login = client.post('/auth/login', json={'username': 'test_inspector', 'password': 'StrongPass123!'})
    assert login.status_code == 200
    token = login.json()['access_token']
    me = client.get('/auth/me', headers={'Authorization': f'Bearer {token}'})
    assert me.status_code == 200
    assert me.json()['username'] == 'test_inspector'
    assert client.post('/auth/login', json={'username': 'test_inspector', 'password': 'wrong'}).status_code == 401


def test_project_requires_auth():
    response = client.get("/projects")
    assert response.status_code == 401


def test_project_create_with_gps():
    username = "project_inspector"
    password = "StrongPass@2026"
    register = client.post("/auth/register", json={"username": username, "password": password, "role": "INSPECTOR"})
    assert register.status_code == 200
    login = client.post("/auth/login", json={"username": username, "password": password})
    assert login.status_code == 200
    token = login.json()["access_token"]

    payload = {
        "name": "Field Project",
        "organization": "Example Organization",
        "project_type": "NGO",
        "address": "Example address",
        "state": "Tamil Nadu",
        "district": "Coimbatore",
        "latitude": 11.0168,
        "longitude": 76.9558,
        "responsible_person": "Project Officer",
        "status": "ACTIVE",
        "beneficiaries": 25,
    }
    create = client.post("/projects", headers={"Authorization": f"Bearer {token}"}, json=payload)
    assert create.status_code == 200
    data = create.json()
    assert data["latitude"] == payload["latitude"]
    assert data["longitude"] == payload["longitude"]
    assert data["created_by"] == username


def test_token_reusable_for_protected_endpoint():
    login = client.post('/auth/login', json={'username': 'test_inspector', 'password': 'StrongPass123!'})
    assert login.status_code == 200
    token = login.json()['access_token']
    for _ in range(3):
        me = client.get('/auth/me', headers={'Authorization': f'Bearer {token}'})
        assert me.status_code == 200

