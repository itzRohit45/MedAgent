"""
Refill Agent — Smart Refill Prediction
Tracks remaining pill counts and proactively predicts when refills are needed.
Sends caregiver alerts when medications are running low.
"""

import json
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google import genai
from tools.notification_tools import send_caregiver_alert
import database as db


def check_refills(patient_id: int, api_key: str = None) -> dict:
    """
    Check all medications for a patient and predict refill needs.
    Sends caregiver alerts for medications running low (≤3 days supply).
    """
    refill_status = db.get_refill_status(patient_id)
    alerts = []

    for med in refill_status:
        if med["days_remaining"] is not None and med["days_remaining"] <= 3:
            urgency = "high" if med["days_remaining"] <= 1 else "medium"
            msg = (
                f"⚠️ Refill needed: {med['drug_name']} has only {med['pills_remaining']} "
                f"pills left (~{med['days_remaining']} days). Please arrange a refill."
            )
            send_caregiver_alert(patient_id, msg, urgency)
            alerts.append({
                "drug": med["drug_name"],
                "pills_remaining": med["pills_remaining"],
                "days_remaining": med["days_remaining"],
                "urgency": urgency
            })

    return {
        "refill_status": refill_status,
        "alerts_sent": len(alerts),
        "alerts": alerts
    }
