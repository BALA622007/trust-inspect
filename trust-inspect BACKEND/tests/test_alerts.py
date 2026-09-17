from fastapi.testclient import TestClient
import uuid
from app.main import app
from app.database import Base, engine, SessionLocal
from app.models import AlertMember

Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)
client = TestClient(app)


def auth():
    username = f'alert_tester_{uuid.uuid4().hex[:8]}'
    password = 'StrongPass123!'
    reg = client.post('/auth/register', json={'username': username, 'password': password, 'role': 'INSPECTOR'})
    assert reg.status_code == 200
    login = client.post('/auth/login', json={'username': username, 'password': password})
    return {'Authorization': f"Bearer {login.json()['access_token']}"}


def project(headers):
    body = {
        'name': 'Alert Test Project', 'organization': 'Test Organization', 'project_type': 'NGO',
        'address': 'Test address', 'state': 'Tamil Nadu', 'district': 'Coimbatore',
        'latitude': 11.0168, 'longitude': 76.9558, 'responsible_person': 'Project Officer',
        'status': 'ACTIVE', 'beneficiaries': 10,
    }
    return client.post('/projects', headers=headers, json=body).json()['id']


def test_alert_member_crud_and_mismatch_alert():
    headers = auth()
    member = client.post('/alert-members', headers=headers, json={
        'name': 'Officer One', 'role': 'OFFICIAL', 'email': 'officer@example.org', 'phone': '9876543210'
    })
    assert member.status_code == 200
    member_id = member.json()['id']
    listed = client.get('/alert-members', headers=headers)
    assert listed.status_code == 200 and listed.json()[0]['id'] == member_id

    pid = project(headers)
    upload = client.post('/evidence', headers=headers, data={'project_id': str(pid), 'evidence_type': 'DOCUMENT'}, files={'file': ('report.txt', b'original', 'text/plain')})
    assert upload.status_code == 200
    eid = upload.json()['id']

    mismatch = client.post(f'/evidence/{eid}/verify', headers=headers, files={'file': ('report.txt', b'changed', 'text/plain')})
    assert mismatch.status_code == 200
    data = mismatch.json()
    assert data['integrity_status'] == 'MISMATCH'
    assert data['alert']['recipient_count'] == 1
    assert data['alert']['delivery_status'] == 'PENDING_PROVIDER'

    alerts = client.get('/alerts', headers=headers)
    assert alerts.status_code == 200
    assert alerts.json()[0]['recipients'][0]['member_id'] == member_id
    assert alerts.json()[0]['recipients'][0]['delivery_status'] == 'PENDING'


def test_mismatch_with_no_alert_members_does_not_fake_delivery():
    with SessionLocal() as db:
        db.query(AlertMember).delete()
        db.commit()
    headers = auth()
    pid = project(headers)
    upload = client.post('/evidence', headers=headers, data={'project_id': str(pid), 'evidence_type': 'DOCUMENT'}, files={'file': ('report.txt', b'original', 'text/plain')})
    eid = upload.json()['id']
    mismatch = client.post(f'/evidence/{eid}/verify', headers=headers, files={'file': ('report.txt', b'changed', 'text/plain')})
    assert mismatch.status_code == 200
    assert mismatch.json()['alert']['recipient_count'] == 0
    assert mismatch.json()['alert']['delivery_status'] == 'NO_RECIPIENTS_CONFIGURED'
