import json, math, random
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sqlalchemy import select, func
from .models import Attendance, CCTVEvent, Evidence, Inspection, Project

MODEL_NAME = "TrustInspectRiskModel"
MODEL_VERSION = "0.1-poc"

def attendance_features(db, project_id):
    rows = db.execute(
        select(Attendance).where(Attendance.project_id == project_id).order_by(Attendance.id)
    ).scalars().all()
    values = [r.reported for r in rows]
    if len(values) < 5:
        return {"attendance_anomaly": 0.0, "attendance_mean": float(np.mean(values)) if values else 0.0}
    x = np.array(values).reshape(-1, 1)
    model = IsolationForest(contamination="auto", random_state=42)
    pred = model.fit_predict(x)
    anomaly_rate = float(np.mean(pred == -1))
    return {"attendance_anomaly": min(anomaly_rate * 2.0, 1.0), "attendance_mean": float(np.mean(values))}

def project_signals(db, project_id):
    p = db.get(Project, project_id)
    att = attendance_features(db, project_id)
    cctv_events = db.execute(
        select(CCTVEvent).where(CCTVEvent.project_id == project_id)
    ).scalars().all()
    evidence = db.execute(
        select(Evidence).where(Evidence.project_id == project_id)
    ).scalars().all()
    inspections = db.execute(
        select(Inspection).where(Inspection.project_id == project_id)
    ).scalars().all()

    cctv_anomaly = min(sum(e.severity for e in cctv_events) / max(len(cctv_events), 1), 1.0)
    evidence_anomaly = min(max(len(evidence) - 10, 0) / 20.0, 1.0)
    inspection_gap = min(len(inspections) / 5.0, 1.0)

    return {
        "attendance_anomaly": att["attendance_anomaly"],
        "evidence_anomaly": evidence_anomaly,
        "cctv_anomaly": cctv_anomaly,
        "inspection_gap": inspection_gap,
        "reported_beneficiaries": p.beneficiaries if p else 0,
    }

def explain_risk(signals):
    weights = {
        "attendance_anomaly": 0.35,
        "evidence_anomaly": 0.25,
        "cctv_anomaly": 0.20,
        "inspection_gap": 0.20,
    }
    contributions = {k: round(signals[k] * w * 100, 2) for k, w in weights.items()}
    raw = sum(contributions.values())
    score = round(min(max(raw, 0), 100), 2)
    # Prototype confidence: grows with the amount of signal available.
    active = sum(1 for k in weights if signals[k] > 0)
    confidence = round(min(0.55 + active * 0.08, 0.87), 2)

    labels = {
        "attendance_anomaly": "Attendance anomaly",
        "evidence_anomaly": "Evidence pattern anomaly",
        "cctv_anomaly": "CCTV/event anomaly",
        "inspection_gap": "Inspection-history signal",
    }
    reasons = [
        {"feature": labels[k], "value": signals[k], "contribution": contributions[k]}
        for k in weights if signals[k] > 0
    ]
    reasons.sort(key=lambda x: x["contribution"], reverse=True)
    level = "LOW" if score < 35 else "MEDIUM" if score < 65 else "HIGH"
    return score, confidence, level, reasons

def analyze_project(db, project_id):
    signals = project_signals(db, project_id)
    score, confidence, level, reasons = explain_risk(signals)
    return {
        "model_name": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "risk_score": score,
        "confidence": confidence,
        "risk_level": level,
        "signals": signals,
        "reasons": reasons,
        "recommendation": (
            "ROUTINE_MONITORING" if level == "LOW"
            else "RANDOM_VC" if level == "MEDIUM"
            else "SURPRISE_INSPECTION"
        ),
    }
