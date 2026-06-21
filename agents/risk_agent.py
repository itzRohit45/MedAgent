"""
Risk Agent — Multi-Patient Risk Scoring
Calculates a risk score (0-100) for each patient based on adherence,
critical medications, missed doses, and drug interactions.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database as db


def calculate_risk_score(patient_id: int) -> dict:
    """
    Calculate a risk score (0-100, higher = riskier) for a patient.
    
    Scoring formula:
    - Base: 100 (best possible)
    - -1 point per 1% below 100% adherence (max -50)
    - -10 per critical medication with missed dose in last 24h
    - -5 per any missed dose in last 24h
    - -10 per severe drug interaction
    - -5 per moderate drug interaction
    
    Final score inverted: risk = 100 - health_score
    """
    stats = db.get_adherence_stats(patient_id, days=7)
    meds = db.get_patient_medications(patient_id)
    interactions = db.get_interaction_flags(patient_id)
    missed_24h = db.get_missed_doses_24h(patient_id)
    logs = db.get_dose_logs(patient_id, days=1)

    health_score = 100

    # Adherence penalty
    adherence = stats.get("adherence_pct", 100)
    adherence_penalty = min(50, max(0, 100 - adherence))
    health_score -= adherence_penalty

    # Missed dose penalty
    health_score -= missed_24h * 5

    # Critical medication miss check
    critical_meds = [m for m in meds if m.get("is_critical")]
    missed_critical = 0
    for log in logs:
        if log["action"] == "missed":
            for cm in critical_meds:
                if cm["drug_name"] in log.get("medication_name", ""):
                    missed_critical += 1
    health_score -= missed_critical * 10

    # Interaction penalty
    for flag in interactions:
        sev = flag.get("severity", "").lower()
        if sev == "severe":
            health_score -= 10
        elif sev == "moderate":
            health_score -= 5

    health_score = max(0, min(100, health_score))
    risk_score = 100 - health_score

    # Determine risk level
    if risk_score >= 60:
        risk_level = "high"
    elif risk_score >= 30:
        risk_level = "medium"
    else:
        risk_level = "low"

    return {
        "patient_id": patient_id,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "adherence_pct": adherence,
        "active_meds": len(meds),
        "critical_meds": len(critical_meds),
        "missed_24h": missed_24h,
        "interactions": len(interactions),
    }


def get_all_patient_risks() -> list:
    """Get risk scores for all patients, sorted by risk (highest first)."""
    patients = db.get_all_patients()
    risks = []
    for p in patients:
        try:
            risk = calculate_risk_score(p["id"])
            risk["patient_name"] = p["name"]
            risk["patient_age"] = p.get("age")
            risks.append(risk)
        except Exception as e:
            risks.append({
                "patient_id": p["id"],
                "patient_name": p["name"],
                "risk_score": 0,
                "risk_level": "unknown",
                "error": str(e)
            })
    
    risks.sort(key=lambda x: x.get("risk_score", 0), reverse=True)
    return risks
