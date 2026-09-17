# TRUST-Inspect — Backend

FastAPI backend for the TRUST INSPECT prototype.

## Current implemented scope

- Backend authentication with password hashing and unique usernames
- Role and active-user fields
- Project registry with registered GPS coordinates
- Authenticated evidence upload
- SHA-256 hash generation for every uploaded evidence file
- Evidence metadata storage
- Hash-chain ledger entry for evidence capture
- Evidence hash verification (`MATCH` / `MISMATCH`)
- Audit entries for evidence upload and verification
- Existing attendance, CCTV-event, AI analysis, inspection, VC, trust and ledger APIs

## Important data policy

This package does not create project records, officer records, passwords, or fake evidence at startup.
Use real values entered through the API/UI. Test cases use isolated test data only.

## Run on Windows

Open a terminal in the backend folder and run:

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Open Swagger:

`http://127.0.0.1:8000/docs`

## Authentication endpoints

- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`

Authenticated requests use:

`Authorization: Bearer <access-token>`

## Project endpoints

- `POST /projects`
- `GET /projects`

Projects store their registered latitude and longitude. The create/list endpoints require authentication.

## Evidence endpoints

### Upload

`POST /evidence`

Multipart fields:

- `project_id`
- `evidence_type`
- `latitude` (optional)
- `longitude` (optional)
- `inspection_id` (optional)
- `file`

The server calculates a SHA-256 hash from the uploaded bytes and stores the evidence metadata and hash.

### Verify integrity

`POST /evidence/{evidence_id}/verify`

Upload the file that needs to be checked. The server calculates its SHA-256 hash and compares it with the stored hash.

- `MATCH` = same content hash
- `MISMATCH` = different content hash

A mismatch is an integrity warning requiring verification; it is not automatically treated as fraud.

### Read evidence metadata

`GET /evidence/{evidence_id}`

## Existing endpoints

- `POST /attendance`
- `POST /cctv/events`
- `POST /ai/analyze/{project_id}`
- `POST /inspections/assign`
- `POST /vc/random`
- `POST /inspections`
- `POST /inspections/{inspection_id}/submit`
- `GET /projects/{project_id}/trust`
- `GET /ledger/verify`
- `GET /audit`

## Production security notes

The current POC stores uploaded files in local `uploads/` storage and uses a local SQLite database. Production deployment should use controlled object storage, PostgreSQL, encrypted secrets, role-based authorization, device attestation where required, and an appropriate tamper-evident/immutable records service. The local hash-chain ledger is not by itself a legal blockchain or immutable government archive.
