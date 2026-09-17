import hashlib, json
from sqlalchemy import select
from .models import LedgerEntry

def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)

def add_ledger(db, ledger_type, event_type, subject_id, payload):
    previous = db.execute(
        select(LedgerEntry).order_by(LedgerEntry.id.desc())
    ).scalars().first()
    previous_hash = previous.entry_hash if previous else "GENESIS"
    material = f"{previous_hash}|{ledger_type}|{event_type}|{subject_id}|{canonical(payload)}"
    entry_hash = hashlib.sha256(material.encode()).hexdigest()
    row = LedgerEntry(
        ledger_type=ledger_type,
        event_type=event_type,
        subject_id=str(subject_id),
        payload_json=canonical(payload),
        previous_hash=previous_hash,
        entry_hash=entry_hash,
    )
    db.add(row)
    db.flush()
    return row

def verify_ledger(db):
    rows = db.execute(select(LedgerEntry).order_by(LedgerEntry.id)).scalars().all()
    previous = "GENESIS"
    failures = []
    for row in rows:
        material = f"{previous}|{row.ledger_type}|{row.event_type}|{row.subject_id}|{row.payload_json}"
        expected = hashlib.sha256(material.encode()).hexdigest()
        if row.previous_hash != previous or row.entry_hash != expected:
            failures.append(row.id)
        previous = row.entry_hash
    return {"valid": not failures, "entries": len(rows), "failed_entry_ids": failures}
