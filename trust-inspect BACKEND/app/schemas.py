from datetime import datetime
from pydantic import BaseModel, Field

class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    organization: str = Field(min_length=1, max_length=200)
    project_type: str = Field(min_length=1, max_length=100)
    address: str = Field(min_length=1, max_length=500)
    state: str = Field(min_length=1, max_length=100)
    district: str = Field(min_length=1, max_length=100)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    responsible_person: str = Field(min_length=1, max_length=200)
    status: str = Field(default="ACTIVE", min_length=1, max_length=30)
    beneficiaries: int = Field(ge=0)

class AttendanceCreate(BaseModel):
    project_id: int
    date: str
    reported: int = Field(ge=0)
    verified: int = -1

class CCTVCreate(BaseModel):
    project_id: int
    camera_id: str
    event_type: str
    severity: float = Field(ge=0, le=1)

class InspectionCreate(BaseModel):
    project_id: int
    inspector_id: str
    reason: str
    latitude: float | None = None
    longitude: float | None = None

class InspectionSubmit(BaseModel):
    findings: str
    latitude: float | None = None
    longitude: float | None = None
    attendance_verified: bool = False
    documents_verified: bool = False
    cctv_verified: bool = False
    beneficiaries_verified: bool = False

class VCCreate(BaseModel):
    project_id: int
    participant_role: str = "PROJECT_INCHARGE"


class AlertCreate(BaseModel):
    alert_type: str = Field(min_length=1, max_length=100)
    project_id: int
    evidence_id: int | None = None
    title: str = Field(min_length=1, max_length=300)
    message: str = Field(min_length=1)
    recipient_member_ids: list[int] = Field(min_length=1)


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=8, max_length=128)
    role: str = Field(default="INSPECTOR", min_length=3, max_length=50)

class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=128)


class AlertMemberCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    role: str = Field(min_length=1, max_length=100)
    email: str = Field(default="", max_length=320)
    phone: str = Field(default="", max_length=30)
    active: bool = True

class AlertMemberUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    role: str | None = Field(default=None, min_length=1, max_length=100)
    email: str | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, max_length=30)
    active: bool | None = None
