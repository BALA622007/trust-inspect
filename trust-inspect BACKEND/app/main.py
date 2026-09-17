import hashlib, json, os, uuid, hmac, secrets, base64, time
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from sqlalchemy import select
from .database import Base, engine, get_db
from .models import Project, Attendance, CCTVEvent, Evidence, Inspection, AIDecision, AuditLog, VCSession, User, AuthToken, AlertMember, Alert, AlertRecipient
from .schemas import ProjectCreate, AttendanceCreate, CCTVCreate, InspectionCreate, InspectionSubmit, VCCreate, RegisterRequest, LoginRequest, AlertMemberCreate, AlertMemberUpdate, AlertCreate
from .ledger import add_ledger, verify_ledger
from .ai import analyze_project
from .assignment import assign_inspection

Base.metadata.create_all(bind=engine)
app = FastAPI(title="TRUST-Inspect POC", version="0.1")
bearer_scheme = HTTPBearer(auto_error=False)

def _ensure_project_columns():
    """Add newly required project columns to an existing SQLite POC database."""
    if engine.url.get_backend_name() != "sqlite":
        return
    columns = {
        "organization": "VARCHAR(200) NOT NULL DEFAULT ''",
        "project_type": "VARCHAR(100) NOT NULL DEFAULT ''",
        "address": "VARCHAR(500) NOT NULL DEFAULT ''",
        "latitude": "FLOAT NOT NULL DEFAULT 0",
        "longitude": "FLOAT NOT NULL DEFAULT 0",
        "responsible_person": "VARCHAR(200) NOT NULL DEFAULT ''",
        "status": "VARCHAR(30) NOT NULL DEFAULT 'ACTIVE'",
    }
    with engine.begin() as conn:
        existing = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(projects)").fetchall()}
        for name, ddl in columns.items():
            if name not in existing:
                conn.exec_driver_sql(f"ALTER TABLE projects ADD COLUMN {name} {ddl}")

_ensure_project_columns()

def audit(db, actor, action, subject, details=""):
    db.add(AuditLog(actor=actor, action=action, subject=str(subject), details=details))

def _hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 310_000)
    return f"pbkdf2_sha256$310000${salt.hex()}${derived.hex()}"

def _verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, iterations, salt_hex, digest_hex = stored.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations))
        return hmac.compare_digest(derived.hex(), digest_hex)
    except (ValueError, TypeError):
        return False

AUTH_TOKEN_TTL_SECONDS = 8 * 60 * 60
AUTH_SECRET_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".auth_secret")

def _load_auth_secret() -> bytes:
    existing = os.getenv("TRUST_INSPECT_AUTH_SECRET")
    if existing:
        return existing.encode("utf-8")
    if os.path.exists(AUTH_SECRET_FILE):
        with open(AUTH_SECRET_FILE, "rb") as f:
            secret = f.read().strip()
            if secret:
                return secret
    secret = secrets.token_bytes(32)
    with open(AUTH_SECRET_FILE, "wb") as f:
        f.write(secret)
    return secret

AUTH_SECRET = _load_auth_secret()

def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

def _issue_access_token(user_id: int) -> str:
    payload = {"sub": str(user_id), "exp": int(time.time()) + AUTH_TOKEN_TTL_SECONDS}
    body = _b64(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = hmac.new(AUTH_SECRET, body.encode("ascii"), hashlib.sha256).digest()
    return f"{body}.{_b64(signature)}"

def _read_access_token(token_value: str) -> int:
    try:
        body, signature = token_value.split(".", 1)
        expected = hmac.new(AUTH_SECRET, body.encode("ascii"), hashlib.sha256).digest()
        supplied = base64.urlsafe_b64decode(signature + "=" * (-len(signature) % 4))
        if not hmac.compare_digest(expected, supplied):
            raise ValueError("bad signature")
        payload = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
        if int(payload["exp"]) <= int(time.time()):
            raise ValueError("expired")
        return int(payload["sub"])
    except (ValueError, KeyError, TypeError, json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(401, "Invalid authentication token")

def _get_current_user(credentials: HTTPAuthorizationCredentials | None, db: Session) -> User:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(401, "Authentication required")
    token_value = credentials.credentials.strip()
    if not token_value:
        raise HTTPException(401, "Authentication required")
    user_id = _read_access_token(token_value)
    user = db.get(User, user_id)
    if not user or not user.active:
        raise HTTPException(401, "User is inactive or unavailable")
    return user

@app.post("/alert-members")
def create_alert_member(
    body: AlertMemberCreate,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    user = _get_current_user(credentials, db)
    row = AlertMember(
        name=body.name.strip(),
        role=body.role.strip(),
        email=body.email.strip(),
        phone=body.phone.strip(),
        active=body.active,
        created_by=user.username,
    )
    db.add(row); db.flush()
    add_ledger(db, "GOVERNANCE", "ALERT_MEMBER_CREATED", row.id, {
        "name": row.name, "role": row.role, "email": row.email, "phone": row.phone,
        "active": row.active, "created_by": user.username
    })
    audit(db, user.username, "CREATE_ALERT_MEMBER", row.id)
    db.commit()
    return {"id": row.id, "name": row.name, "role": row.role, "email": row.email, "phone": row.phone, "active": row.active}


@app.get("/alert-members")
def list_alert_members(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    _get_current_user(credentials, db)
    rows = db.execute(select(AlertMember).order_by(AlertMember.id)).scalars().all()
    return [{
        "id": row.id, "name": row.name, "role": row.role, "email": row.email,
        "phone": row.phone, "active": row.active,
    } for row in rows]


@app.patch("/alert-members/{member_id}")
def update_alert_member(
    member_id: int,
    body: AlertMemberUpdate,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    user = _get_current_user(credentials, db)
    row = db.get(AlertMember, member_id)
    if not row:
        raise HTTPException(404, "Alert member not found")
    changes = body.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(row, key, value.strip() if isinstance(value, str) else value)
    add_ledger(db, "GOVERNANCE", "ALERT_MEMBER_UPDATED", row.id, {"changes": changes, "updated_by": user.username})
    audit(db, user.username, "UPDATE_ALERT_MEMBER", row.id)
    db.commit()
    return {"id": row.id, "name": row.name, "role": row.role, "email": row.email, "phone": row.phone, "active": row.active}


@app.delete("/alert-members/{member_id}")
def delete_alert_member(
    member_id: int,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    user = _get_current_user(credentials, db)
    row = db.get(AlertMember, member_id)
    if not row:
        raise HTTPException(404, "Alert member not found")
    other_count = db.execute(select(AlertMember).where(AlertMember.id != member_id, AlertMember.active.is_(True))).scalars().all()
    if other_count:
        pre_delete_note = f"{len(other_count)} other configured alert member(s) remain; deletion notification is queued for governance handling."
        audit(db, user.username, "ALERT_MEMBER_DELETE_NOTIFICATION_REQUIRED", row.id, pre_delete_note)
    else:
        audit(db, user.username, "ALERT_MEMBER_DELETE_NO_OTHER_RECIPIENTS", row.id, "No other active alert members configured.")
    add_ledger(db, "GOVERNANCE", "ALERT_MEMBER_DELETED", row.id, {"deleted_by": user.username, "other_active_member_count": len(other_count)})
    db.delete(row)
    db.commit()
    return {"id": member_id, "deleted": True, "other_active_member_count": len(other_count)}


@app.get("/alerts")
def list_alerts(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    _get_current_user(credentials, db)
    rows = db.execute(select(Alert).order_by(Alert.id.desc())).scalars().all()
    result = []
    for row in rows:
        recipients = db.execute(
            select(AlertRecipient, AlertMember)
            .join(AlertMember, AlertMember.id == AlertRecipient.alert_member_id)
            .where(AlertRecipient.alert_id == row.id)
        ).all()
        result.append({
            "id": row.id, "alert_type": row.alert_type, "project_id": row.project_id,
            "evidence_id": row.evidence_id, "title": row.title, "message": row.message,
            "status": row.status, "created_by": row.created_by, "created_at": row.created_at,
            "recipients": [{"member_id": member.id, "name": member.name, "delivery_status": recipient.delivery_status} for recipient, member in recipients],
        })
    return result



@app.post("/alerts")
def create_alert(
    body: AlertCreate,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    user = _get_current_user(credentials, db)

    if not db.get(Project, body.project_id):
        raise HTTPException(404, "Project not found")

    if body.evidence_id is not None:
        evidence = db.get(Evidence, body.evidence_id)
        if not evidence:
            raise HTTPException(404, "Evidence not found")

    members = db.execute(
        select(AlertMember)
        .where(
            AlertMember.id.in_(body.recipient_member_ids),
            AlertMember.active.is_(True),
        )
        .order_by(AlertMember.id)
    ).scalars().all()

    if len(members) != len(set(body.recipient_member_ids)):
        raise HTTPException(
            400,
            "One or more selected alert members are invalid or inactive",
        )

    alert = Alert(
        alert_type=body.alert_type.strip(),
        project_id=body.project_id,
        evidence_id=body.evidence_id,
        title=body.title.strip(),
        message=body.message.strip(),
        status="PENDING",
        created_by=user.username,
    )
    db.add(alert)
    db.flush()

    for member in members:
        db.add(
            AlertRecipient(
                alert_id=alert.id,
                alert_member_id=member.id,
                delivery_status="PENDING",
            )
        )

    add_ledger(
        db,
        "GOVERNANCE",
        "ALERT_CREATED",
        alert.id,
        {
            "alert_type": alert.alert_type,
            "project_id": alert.project_id,
            "evidence_id": alert.evidence_id,
            "title": alert.title,
            "recipient_member_ids": [member.id for member in members],
            "created_by": user.username,
        },
    )

    audit(
        db,
        user.username,
        "CREATE_ALERT",
        alert.id,
        json.dumps(
            {
                "project_id": alert.project_id,
                "recipient_count": len(members),
            }
        ),
    )

    db.commit()

    return {
        "id": alert.id,
        "alert_type": alert.alert_type,
        "project_id": alert.project_id,
        "evidence_id": alert.evidence_id,
        "title": alert.title,
        "message": alert.message,
        "status": alert.status,
        "created_by": alert.created_by,
        "recipient_count": len(members),
    }

@app.post("/auth/register")
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.execute(select(User).where(User.username == body.username)).scalar_one_or_none()
    if existing:
        raise HTTPException(409, "Username already exists")
    user = User(username=body.username, password_hash=_hash_password(body.password), role=body.role.upper())
    db.add(user); db.flush()
    audit(db, "SYSTEM", "USER_REGISTERED", user.id, json.dumps({"username": user.username, "role": user.role}))
    db.commit()
    return {"id": user.id, "username": user.username, "role": user.role, "active": user.active}

@app.post("/auth/login")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.execute(select(User).where(User.username == body.username)).scalar_one_or_none()
    if not user or not user.active or not _verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Invalid username or password")
    token_value = _issue_access_token(user.id)
    audit(db, user.username, "LOGIN", user.id)
    db.commit()
    return {"access_token": token_value, "token_type": "bearer", "user": {"id": user.id, "username": user.username, "role": user.role}}

@app.get("/auth/me")
def me(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    user = _get_current_user(credentials, db)
    return {"id": user.id, "username": user.username, "role": user.role, "active": user.active}

@app.get("/")
def root():
    return {"name": "TRUST-Inspect", "status": "running", "purpose": "SIH26095 POC"}

@app.post("/projects")
def create_project(
    body: ProjectCreate,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    user = _get_current_user(credentials, db)
    p = Project(**body.model_dump())
    db.add(p); db.flush()
    add_ledger(db, "GOVERNANCE", "PROJECT_CREATED", p.id, {**body.model_dump(), "created_by": user.username})
    audit(db, user.username, "CREATE_PROJECT", p.id, json.dumps({"status": p.status}))
    db.commit()
    return {"id": p.id, **body.model_dump(), "created_by": user.username}

@app.get("/projects")
def projects(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    _get_current_user(credentials, db)
    rows = db.execute(select(Project).order_by(Project.id)).scalars().all()
    return [{
        "id": p.id,
        "name": p.name,
        "organization": p.organization,
        "project_type": p.project_type,
        "address": p.address,
        "state": p.state,
        "district": p.district,
        "latitude": p.latitude,
        "longitude": p.longitude,
        "responsible_person": p.responsible_person,
        "status": p.status,
        "beneficiaries": p.beneficiaries,
        "risk_score": p.risk_score,
        "trust_score": p.trust_score,
    } for p in rows]

@app.post("/attendance")
def add_attendance(body: AttendanceCreate, db: Session = Depends(get_db)):
    if not db.get(Project, body.project_id):
        raise HTTPException(404, "Project not found")
    row = Attendance(**body.model_dump())
    db.add(row); db.flush()
    add_ledger(db, "EVIDENCE", "ATTENDANCE_RECORDED", row.id, body.model_dump())
    audit(db, "INSTITUTE", "ATTENDANCE_RECORDED", row.id)
    db.commit()
    return {"id": row.id}

@app.post("/cctv/events")
def cctv_event(body: CCTVCreate, db: Session = Depends(get_db)):
    row = CCTVEvent(**body.model_dump())
    db.add(row); db.flush()
    add_ledger(db, "EVIDENCE", "CCTV_EVENT", row.id, body.model_dump())
    audit(db, "CCTV-GATEWAY", "CCTV_EVENT", row.id, body.event_type)
    db.commit()
    return {"id": row.id}

@app.post("/evidence")
async def upload_evidence(
    project_id: int = Form(...),
    evidence_type: str = Form("INSPECTION_PHOTO"),
    latitude: float | None = Form(None),
    longitude: float | None = Form(None),
    inspection_id: str | None = Form(None),
    file: UploadFile = File(...),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    user = _get_current_user(credentials, db)
    if not db.get(Project, project_id):
        raise HTTPException(404, "Project not found")
    parsed_inspection_id = None
    if inspection_id is not None:
        value = inspection_id.strip()
        if value:
            try:
                parsed_inspection_id = int(value)
            except ValueError:
                raise HTTPException(422, "inspection_id must be a valid integer")
            if not db.get(Inspection, parsed_inspection_id):
                raise HTTPException(404, "Inspection not found")

    content = await file.read()
    if not content:
        raise HTTPException(400, "Evidence file is empty")
    sha = hashlib.sha256(content).hexdigest()

    os.makedirs("uploads", exist_ok=True)
    original_name = os.path.basename(file.filename or "evidence.bin")
    safe_name = f"{uuid.uuid4().hex}_{original_name}"
    path = os.path.join("uploads", safe_name)
    with open(path, "wb") as f:
        f.write(content)

    metadata = {
        "content_type": file.content_type,
        "size": len(content),
        "original_filename": original_name,
        "stored_filename": safe_name,
        "capture_mode": "SERVER_UPLOAD",
    }
    row = Evidence(
        project_id=project_id, inspection_id=parsed_inspection_id,
        evidence_type=evidence_type, filename=safe_name, sha256=sha,
        latitude=latitude, longitude=longitude, metadata_json=json.dumps(metadata)
    )
    db.add(row); db.flush()
    add_ledger(db, "EVIDENCE", "EVIDENCE_CAPTURED", row.id, {
        "project_id": project_id, "sha256": sha, "latitude": latitude,
        "longitude": longitude, "uploader": user.username, "evidence_type": evidence_type
    })
    audit(db, user.username, "UPLOAD_EVIDENCE", row.id, sha)
    db.commit()
    return {
        "id": row.id, "project_id": row.project_id, "evidence_type": row.evidence_type,
        "sha256": row.sha256, "stored_as": safe_name, "size": len(content)
    }

@app.post("/evidence/{evidence_id}/verify")
async def verify_evidence(
    evidence_id: int,
    file: UploadFile = File(...),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    user = _get_current_user(credentials, db)
    row = db.get(Evidence, evidence_id)
    if not row:
        raise HTTPException(404, "Evidence not found")

    content = await file.read()
    if not content:
        raise HTTPException(400, "Verification file is empty")
    current_sha256 = hashlib.sha256(content).hexdigest()
    matches = hmac.compare_digest(current_sha256, row.sha256)

    result = {
        "evidence_id": row.id,
        "project_id": row.project_id,
        "stored_sha256": row.sha256,
        "current_sha256": current_sha256,
        "integrity_status": "MATCH" if matches else "MISMATCH",
        "action": "NO_ACTION" if matches else "VERIFICATION_ALERT_REQUIRED",
    }
    add_ledger(db, "EVIDENCE", "EVIDENCE_HASH_VERIFIED", row.id, {
        **result, "verified_by": user.username
    })
    audit(db, user.username, "VERIFY_EVIDENCE", row.id, result["integrity_status"])

    if not matches:
        alert = Alert(
            alert_type="EVIDENCE_INTEGRITY_MISMATCH",
            project_id=row.project_id,
            evidence_id=row.id,
            title="Evidence integrity mismatch detected",
            message=(
                f"Evidence {row.id} for project {row.project_id} does not match its stored SHA-256 hash. "
                "Verification is required; the system does not automatically classify this as fraud."
            ),
            status="PENDING",
            created_by="SYSTEM",
        )
        db.add(alert); db.flush()
        active_members = db.execute(
            select(AlertMember).where(AlertMember.active.is_(True)).order_by(AlertMember.id)
        ).scalars().all()
        for member in active_members:
            db.add(AlertRecipient(alert_id=alert.id, alert_member_id=member.id, delivery_status="PENDING"))

        recipient_count = len(active_members)
        result["alert"] = {
            "alert_id": alert.id,
            "recipient_count": recipient_count,
            "delivery_status": "PENDING_PROVIDER" if recipient_count else "NO_RECIPIENTS_CONFIGURED",
        }
        add_ledger(db, "GOVERNANCE", "EVIDENCE_MISMATCH_ALERT_CREATED", alert.id, {
            "evidence_id": row.id, "project_id": row.project_id,
            "recipient_count": recipient_count,
        })
        audit(db, "SYSTEM", "CREATE_INTEGRITY_ALERT", alert.id, json.dumps(result["alert"]))

    db.commit()
    return result

@app.get("/evidence/{evidence_id}")
def get_evidence(
    evidence_id: int,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    _get_current_user(credentials, db)
    row = db.get(Evidence, evidence_id)
    if not row:
        raise HTTPException(404, "Evidence not found")
    return {
        "id": row.id, "project_id": row.project_id, "inspection_id": row.inspection_id,
        "evidence_type": row.evidence_type, "filename": row.filename,
        "sha256": row.sha256, "latitude": row.latitude, "longitude": row.longitude,
        "captured_at": row.captured_at, "metadata": json.loads(row.metadata_json or "{}")
    }

@app.post("/ai/analyze/{project_id}")
def analyze(project_id: int, db: Session = Depends(get_db)):
    if not db.get(Project, project_id):
        raise HTTPException(404, "Project not found")
    result = analyze_project(db, project_id)
    p = db.get(Project, project_id)
    p.risk_score = result["risk_score"]
    p.trust_score = round(100 - result["risk_score"], 2)

    decision = AIDecision(
        project_id=project_id,
        model_name=result["model_name"],
        model_version=result["model_version"],
        risk_score=result["risk_score"],
        confidence=result["confidence"],
        explanation_json=json.dumps(result),
    )
    db.add(decision); db.flush()

    add_ledger(db, "AI", "AI_RISK_DECISION", decision.id, result)
    audit(db, "AI", "RISK_ASSESSMENT", project_id, json.dumps(result))
    db.commit()
    return result

@app.post("/inspections/assign")
def assign(db: Session = Depends(get_db)):
    result = assign_inspection(db)
    if not result:
        raise HTTPException(404, "No projects available")
    project, inspector, reason = result
    row = Inspection(
        project_id=project.id, inspector_id=inspector,
        assignment_reason=reason, status="ASSIGNED"
    )
    db.add(row); db.flush()
    add_ledger(db, "GOVERNANCE", "INSPECTION_ASSIGNED", row.id, {
        "project_id": project.id, "inspector_id": inspector, "reason": reason
    })
    audit(db, "ASSIGNMENT-ENGINE", "ASSIGN_INSPECTION", row.id, reason)
    db.commit()
    return {"inspection_id": row.id, "project_id": project.id, "inspector_id": inspector, "reason": reason}

@app.post("/vc/random")
def random_vc(body: VCCreate, db: Session = Depends(get_db)):
    if not db.get(Project, body.project_id):
        raise HTTPException(404, "Project not found")
    row = VCSession(project_id=body.project_id, participant_role=body.participant_role)
    db.add(row); db.flush()
    add_ledger(db, "GOVERNANCE", "RANDOM_VC_REQUESTED", row.id, body.model_dump())
    audit(db, "DECISION-ENGINE", "RANDOM_VC_REQUESTED", row.id)
    db.commit()
    return {"vc_id": row.id, "status": row.status}

@app.post("/inspections")
def create_inspection(body: InspectionCreate, db: Session = Depends(get_db)):
    row = Inspection(
        project_id=body.project_id, inspector_id=body.inspector_id,
        assignment_reason=body.reason, started_lat=body.latitude,
        started_lon=body.longitude, started_at=datetime.utcnow(), status="IN_PROGRESS"
    )
    db.add(row); db.flush()
    add_ledger(db, "GOVERNANCE", "INSPECTION_STARTED", row.id, body.model_dump())
    audit(db, body.inspector_id, "INSPECTION_STARTED", row.id)
    db.commit()
    return {"inspection_id": row.id}

@app.post("/inspections/{inspection_id}/submit")
def submit_inspection(inspection_id: int, body: InspectionSubmit, db: Session = Depends(get_db)):
    row = db.get(Inspection, inspection_id)
    if not row:
        raise HTTPException(404, "Inspection not found")
    row.findings = body.findings
    row.attendance_verified = body.attendance_verified
    row.documents_verified = body.documents_verified
    row.cctv_verified = body.cctv_verified
    row.beneficiaries_verified = body.beneficiaries_verified
    row.started_lat = row.started_lat if row.started_lat is not None else body.latitude
    row.started_lon = row.started_lon if row.started_lon is not None else body.longitude
    row.submitted_at = datetime.utcnow()
    row.status = "SUBMITTED"
    add_ledger(db, "GOVERNANCE", "INSPECTION_SUBMITTED", row.id, {
        "findings": body.findings, "latitude": body.latitude, "longitude": body.longitude
    })
    audit(db, row.inspector_id, "INSPECTION_SUBMITTED", row.id)
    db.commit()
    return {"inspection_id": row.id, "status": row.status}

@app.get("/inspections")
def list_inspections(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    _get_current_user(credentials, db)
    rows = db.execute(select(Inspection).order_by(Inspection.id.desc())).scalars().all()
    result = []
    for row in rows:
        project = db.get(Project, row.project_id)
        result.append({
            "id": row.id,
            "project_id": row.project_id,
            "project_name": project.name if project else "Unknown Project",
            "inspector_id": row.inspector_id,
            "assignment_reason": row.assignment_reason,
            "status": row.status,
            "started_lat": row.started_lat,
            "started_lon": row.started_lon,
            "started_at": row.started_at,
            "submitted_at": row.submitted_at,
            "findings": row.findings,
            "attendance_verified": row.attendance_verified,
            "documents_verified": row.documents_verified,
            "cctv_verified": row.cctv_verified,
            "beneficiaries_verified": row.beneficiaries_verified,
        })
    return result


@app.get("/projects/{project_id}/trust")
def trust(project_id: int, db: Session = Depends(get_db)):
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "Project not found")
    latest = db.execute(
        select(AIDecision).where(AIDecision.project_id == project_id).order_by(AIDecision.id.desc())
    ).scalars().first()
    return {
        "project_id": p.id, "project": p.name,
        "trust_score": p.trust_score, "risk_score": p.risk_score,
        "latest_ai_decision": json.loads(latest.explanation_json) if latest else None
    }

@app.get("/ledger/verify")
def ledger_verify(db: Session = Depends(get_db)):
    return verify_ledger(db)

@app.get("/audit")
def audit_logs(db: Session = Depends(get_db)):
    rows = db.execute(select(AuditLog).order_by(AuditLog.id.desc())).scalars().all()
    return [{
        "id": x.id, "actor": x.actor, "action": x.action,
        "subject": x.subject, "details": x.details, "created_at": x.created_at
    } for x in rows[:200]]
