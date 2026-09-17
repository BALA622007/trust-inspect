import random
from sqlalchemy import select
from .models import Project, Inspection

def assign_inspection(db, seed=None):
    rng = random.Random(seed)
    projects = db.execute(select(Project)).scalars().all()
    if not projects:
        return None

    # Risk-aware randomized choice: convert risk to weight but keep randomness.
    weights = [max(1.0, 1.0 + p.risk_score / 25.0) for p in projects]
    project = rng.choices(projects, weights=weights, k=1)[0]

    inspectors = ["PMU-101", "PMU-102", "PMU-103", "PMU-104"]
    recent = db.execute(
        select(Inspection).where(Inspection.project_id == project.id)
    ).scalars().all()
    recent_inspectors = {x.inspector_id for x in recent[-2:]}
    eligible = [i for i in inspectors if i not in recent_inspectors] or inspectors
    inspector = rng.choice(eligible)

    reason = (
        f"Risk-aware randomized assignment; current risk={project.risk_score:.1f}"
    )
    return project, inspector, reason
