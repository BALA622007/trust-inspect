from datetime import datetime, timedelta
import random
from app.database import Base, engine, SessionLocal
from app.models import Project, Attendance, CCTVEvent
from app.ledger import add_ledger

Base.metadata.create_all(bind=engine)
db = SessionLocal()

if db.query(Project).count() == 0:
    projects = [
        Project(name="ABC Rehabilitation Centre", state="Tamil Nadu", district="Coimbatore", beneficiaries=55),
        Project(name="XYZ Skill Development Institute", state="Tamil Nadu", district="Madurai", beneficiaries=80),
        Project(name="Community Support NGO", state="Tamil Nadu", district="Trichy", beneficiaries=42),
        Project(name="Inclusive Education Centre", state="Tamil Nadu", district="Salem", beneficiaries=63),
        Project(name="Livelihood Training Centre", state="Tamil Nadu", district="Erode", beneficiaries=47),
    ]
    db.add_all(projects)
    db.flush()

    rng = random.Random(42)
    for p in projects:
        base = max(10, int(p.beneficiaries * 0.75))
        for i in range(30):
            val = int(max(0, rng.gauss(base, 4)))
            if p.id == projects[1].id and i in (24, 25, 26, 27, 28):
                val += 30
            row = Attendance(
                project_id=p.id,
                date=(datetime.utcnow() - timedelta(days=29-i)).strftime("%Y-%m-%d"),
                reported=val
            )
            db.add(row)
            add_ledger(db, "EVIDENCE", "ATTENDANCE_SEEDED", f"{p.id}-{i}", {
                "project_id": p.id, "reported": val, "date": row.date
            })

        for j in range(rng.randint(1, 4)):
            event = CCTVEvent(
                project_id=p.id,
                camera_id=f"CAM-{p.id}-{j+1}",
                event_type=rng.choice(["STREAM_OK", "CAMERA_OFFLINE", "LOW_ACTIVITY", "UNUSUAL_ACTIVITY"]),
                severity=rng.random()
            )
            db.add(event)

    db.commit()
    print("Seeded demo data.")
else:
    print("Database already contains data.")

db.close()
