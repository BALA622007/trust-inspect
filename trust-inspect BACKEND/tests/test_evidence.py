from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine

Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)
client = TestClient(app)


def auth_headers():
    client.post('/auth/register', json={'username': 'evidence_inspector', 'password': 'StrongPass123!', 'role': 'INSPECTOR'})
    login = client.post('/auth/login', json={'username': 'evidence_inspector', 'password': 'StrongPass123!'})
    return {'Authorization': f"Bearer {login.json()['access_token']}"}


def create_project(headers):
    body = {
        'name': 'Evidence Test Project',
        'organization': 'Real Organization',
        'project_type': 'NGO',
        'address': 'Registered project address',
        'state': 'Tamil Nadu',
        'district': 'Coimbatore',
        'latitude': 11.0168,
        'longitude': 76.9558,
        'responsible_person': 'Project Officer',
        'status': 'ACTIVE',
        'beneficiaries': 10,
    }
    return client.post('/projects', headers=headers, json=body).json()['id']


def test_upload_and_verify_evidence_hash():
    headers = auth_headers()
    project_id = create_project(headers)
    payload = {'project_id': str(project_id), 'evidence_type': 'DOCUMENT'}
    upload = client.post('/evidence', headers=headers, data=payload, files={'file': ('report.txt', b'original evidence', 'text/plain')})
    assert upload.status_code == 200
    evidence_id = upload.json()['id']
    original_hash = upload.json()['sha256']
    assert len(original_hash) == 64

    verify_match = client.post(f'/evidence/{evidence_id}/verify', headers=headers, files={'file': ('report.txt', b'original evidence', 'text/plain')})
    assert verify_match.status_code == 200
    assert verify_match.json()['integrity_status'] == 'MATCH'

    verify_mismatch = client.post(f'/evidence/{evidence_id}/verify', headers=headers, files={'file': ('report.txt', b'changed evidence', 'text/plain')})
    assert verify_mismatch.status_code == 200
    assert verify_mismatch.json()['integrity_status'] == 'MISMATCH'
    assert verify_mismatch.json()['action'] == 'VERIFICATION_ALERT_REQUIRED'


def test_evidence_requires_auth_and_project_exists():
    unauth = client.post('/evidence', data={'project_id': '1'}, files={'file': ('a.txt', b'a', 'text/plain')})
    assert unauth.status_code == 401

    headers = auth_headers()
    missing_project = client.post('/evidence', headers=headers, data={'project_id': '9999'}, files={'file': ('a.txt', b'a', 'text/plain')})
    assert missing_project.status_code == 404


def test_upload_allows_blank_optional_inspection_id():
    headers = auth_headers()
    project_id = create_project(headers)
    upload = client.post(
        '/evidence',
        headers=headers,
        data={
            'project_id': str(project_id),
            'evidence_type': 'DOCUMENT',
            'inspection_id': '',
        },
        files={'file': ('report.txt', b'blank inspection id', 'text/plain')},
    )
    assert upload.status_code == 200
    assert upload.json()['id'] > 0


def test_invalid_inspection_id_is_rejected():
    headers = auth_headers()
    project_id = create_project(headers)
    upload = client.post(
        '/evidence',
        headers=headers,
        data={
            'project_id': str(project_id),
            'evidence_type': 'DOCUMENT',
            'inspection_id': 'abc',
        },
        files={'file': ('report.txt', b'invalid inspection id', 'text/plain')},
    )
    assert upload.status_code == 422
