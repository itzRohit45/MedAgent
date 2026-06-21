"""
Schedule Tools
Functions for managing dose schedules, checking due reminders,
and handling dose confirmations. Wraps database operations as
ADK-compatible tool functions.
"""

import json
from datetime import datetime, timedelta, date
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import database as db


def get_due_reminders(patient_id: int) -> list:
    """
    Get medication doses that are due within the next 30 minutes for a patient.

    Args:
        patient_id: The ID of the patient to check reminders for.

    Returns:
        A list of due doses with drug name, dose amount, and scheduled time.
    """
    due = db.get_due_doses(patient_id, window_minutes=30)
    reminders = []
    for d in due:
        reminders.append({
            "dose_id": d["id"],
            "drug_name": d["drug_name"],
            "dose": d["dose"],
            "scheduled_time": d["scheduled_time"],
            "is_critical": bool(d["is_critical"]),
        })
    return reminders


def confirm_dose_taken(dose_id: int) -> dict:
    """
    Mark a scheduled dose as taken by the patient.

    Args:
        dose_id: The ID of the dose schedule entry to confirm.

    Returns:
        A confirmation dict with the dose_id, action, and timestamp.
    """
    return db.mark_dose(dose_id, "taken")


def skip_dose(dose_id: int) -> dict:
    """
    Mark a scheduled dose as skipped by the patient.

    Args:
        dose_id: The ID of the dose schedule entry to skip.

    Returns:
        A confirmation dict with the dose_id, action, and timestamp.
    """
    return db.mark_dose(dose_id, "skipped")


def get_missed_dose_info(dose_id: int, patient_id: int) -> dict:
    """
    Get detailed information about a potentially missed dose, including
    elapsed time, whether the medication is critical, and how many
    doses were missed in the last 24 hours.

    Args:
        dose_id: The ID of the specific dose schedule entry.
        patient_id: The patient's ID.

    Returns:
        A dictionary with dose details, elapsed time, critical status,
        and recent miss count for escalation decisions.
    """
    conn = db.get_connection()
    dose = conn.execute(
        """SELECT ds.*, m.drug_name, m.dose, m.is_critical, m.generic_name
           FROM dose_schedule ds
           JOIN medications m ON ds.medication_id = m.id
           WHERE ds.id = ?""",
        (dose_id,)
    ).fetchone()
    conn.close()

    if not dose:
        return {"error": f"Dose {dose_id} not found"}

    scheduled = datetime.fromisoformat(dose["scheduled_time"])
    elapsed = datetime.now() - scheduled
    elapsed_minutes = int(elapsed.total_seconds() / 60)

    missed_24h = db.get_missed_doses_24h(patient_id)

    return {
        "dose_id": dose_id,
        "drug_name": dose["drug_name"],
        "dose": dose["dose"],
        "scheduled_time": dose["scheduled_time"],
        "status": dose["status"],
        "is_critical": bool(dose["is_critical"]),
        "elapsed_minutes": elapsed_minutes,
        "missed_in_24h": missed_24h,
        "patient_id": patient_id,
    }


def get_overdue_doses_for_patient(patient_id: int) -> list:
    """
    Get all doses that are overdue (past grace window) for a patient.

    Args:
        patient_id: The ID of the patient.

    Returns:
        A list of overdue dose details with drug name, elapsed time, etc.
    """
    overdue = db.get_overdue_doses(patient_id, grace_minutes=30)
    results = []
    for d in overdue:
        scheduled = datetime.fromisoformat(d["scheduled_time"])
        elapsed = datetime.now() - scheduled
        results.append({
            "dose_id": d["id"],
            "drug_name": d["drug_name"],
            "dose": d["dose"],
            "scheduled_time": d["scheduled_time"],
            "is_critical": bool(d["is_critical"]),
            "elapsed_minutes": int(elapsed.total_seconds() / 60),
        })
    return results


def get_daily_schedule(patient_id: int) -> list:
    """
    Get the full day's medication schedule for a patient.

    Args:
        patient_id: The ID of the patient.

    Returns:
        A list of all scheduled doses for today, with status and drug info.
    """
    return db.get_todays_schedule(patient_id)


def get_adherence_report(patient_id: int, days: int = 7) -> dict:
    """
    Get adherence statistics for a patient over the specified number of days.

    Args:
        patient_id: The ID of the patient.
        days: Number of days to calculate adherence over (default 7).

    Returns:
        A dictionary with total doses, taken count, missed count,
        skipped count, and overall adherence percentage.
    """
    return db.get_adherence_stats(patient_id, days)
