"""
MedAgent Database Layer
SQLite database for patient medications, schedules, dose logs, and escalations.
"""

import sqlite3
import json
import os
from datetime import datetime, timedelta, date

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "medagent.db")


def get_connection():
    """Get a SQLite connection with row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Initialize database schema and seed demo data."""
    conn = get_connection()
    cursor = conn.cursor()

    # --- Schema ---
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            age INTEGER,
            caregiver_name TEXT,
            caregiver_email TEXT,
            caregiver_mobile TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS medications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            drug_name TEXT NOT NULL,
            generic_name TEXT,
            brand_name TEXT,
            dose TEXT NOT NULL,
            frequency TEXT NOT NULL,
            schedule_rules TEXT,
            times TEXT DEFAULT '[]',
            is_critical INTEGER DEFAULT 0,
            rxcui TEXT,
            start_date DATE,
            end_date DATE,
            refills INTEGER DEFAULT 0,
            active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES patients(id)
        );

        CREATE TABLE IF NOT EXISTS dose_schedule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            medication_id INTEGER NOT NULL,
            patient_id INTEGER NOT NULL,
            scheduled_time TIMESTAMP NOT NULL,
            status TEXT DEFAULT 'pending',
            confirmed_at TIMESTAMP,
            reminder_sent_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (medication_id) REFERENCES medications(id),
            FOREIGN KEY (patient_id) REFERENCES patients(id)
        );

        CREATE TABLE IF NOT EXISTS interaction_flags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            drug_a TEXT NOT NULL,
            drug_b TEXT NOT NULL,
            severity TEXT NOT NULL,
            note TEXT,
            source TEXT DEFAULT 'RxNorm',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES patients(id)
        );

        CREATE TABLE IF NOT EXISTS dose_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dose_schedule_id INTEGER,
            patient_id INTEGER NOT NULL,
            medication_name TEXT,
            action TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notes TEXT,
            FOREIGN KEY (dose_schedule_id) REFERENCES dose_schedule(id),
            FOREIGN KEY (patient_id) REFERENCES patients(id)
        );

        CREATE TABLE IF NOT EXISTS escalations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            dose_schedule_id INTEGER,
            action TEXT NOT NULL,
            reason TEXT,
            urgency TEXT DEFAULT 'low',
            resolved INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES patients(id),
            FOREIGN KEY (dose_schedule_id) REFERENCES dose_schedule(id)
        );

        CREATE TABLE IF NOT EXISTS symptom_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            symptom TEXT NOT NULL,
            severity TEXT DEFAULT 'mild',
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES patients(id)
        );
    """)
    # Migration: Add schedule_rules if not exists
    try:
        conn.execute("ALTER TABLE medications ADD COLUMN schedule_rules TEXT")
    except sqlite3.OperationalError:
        pass # Column already exists
    
    # Migration: Add pills_remaining
    try:
        conn.execute("ALTER TABLE medications ADD COLUMN pills_remaining INTEGER")
    except sqlite3.OperationalError:
        pass # Column already exists
        
    # Migration: Split caregiver_contact into email and mobile
    try:
        conn.execute("ALTER TABLE patients ADD COLUMN caregiver_email TEXT")
        conn.execute("ALTER TABLE patients ADD COLUMN caregiver_mobile TEXT")
        # Migrate existing data (crude heuristic: if @ it's email, else mobile)
        conn.execute("UPDATE patients SET caregiver_email = caregiver_contact WHERE caregiver_contact LIKE '%@%'")
        conn.execute("UPDATE patients SET caregiver_mobile = caregiver_contact WHERE caregiver_contact NOT LIKE '%@%' AND caregiver_contact IS NOT NULL")
    except sqlite3.OperationalError:
        pass # Columns already exist

    conn.commit()
    conn.close()


def seed_demo_data():
    """Seed database with demo patient and medications for demonstration."""
    conn = get_connection()
    cursor = conn.cursor()

    # Check if demo data already exists
    existing = cursor.execute("SELECT COUNT(*) FROM patients").fetchone()[0]
    if existing > 0:
        conn.close()
        return

    # Demo patient
    cursor.execute(
        "INSERT INTO patients (name, age, caregiver_name, caregiver_contact) VALUES (?, ?, ?, ?)",
        ("Rajesh Kumar", 65, "Priya Kumar", "priya.kumar@email.com")
    )
    patient_id = cursor.lastrowid

    # Demo medications
    demo_meds = [
        {
            "drug_name": "Metformin 500mg",
            "generic_name": "metformin",
            "brand_name": "Glucophage",
            "dose": "500mg",
            "frequency": "twice daily",
            "times": json.dumps(["08:00", "20:00"]),
            "is_critical": 1,
            "rxcui": "861004",
            "start_date": str(date.today() - timedelta(days=30)),
            "refills": 3,
        },
        {
            "drug_name": "Lisinopril 10mg",
            "generic_name": "lisinopril",
            "brand_name": "Zestril",
            "dose": "10mg",
            "frequency": "once daily",
            "times": json.dumps(["09:00"]),
            "is_critical": 0,
            "rxcui": "314076",
            "start_date": str(date.today() - timedelta(days=60)),
            "refills": 5,
        },
        {
            "drug_name": "Atorvastatin 20mg",
            "generic_name": "atorvastatin",
            "brand_name": "Lipitor",
            "dose": "20mg",
            "frequency": "once daily",
            "times": json.dumps(["21:00"]),
            "is_critical": 0,
            "rxcui": "259255",
            "start_date": str(date.today() - timedelta(days=90)),
            "refills": 2,
        },
    ]

    for med in demo_meds:
        cursor.execute(
            """INSERT INTO medications 
               (patient_id, drug_name, generic_name, brand_name, dose, frequency, 
                times, is_critical, rxcui, start_date, refills)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (patient_id, med["drug_name"], med["generic_name"], med["brand_name"],
             med["dose"], med["frequency"], med["times"], med["is_critical"],
             med["rxcui"], med["start_date"], med["refills"])
        )

    # Generate today's schedule for demo meds
    generate_daily_schedule(patient_id, date.today())

    # Seed some historical dose logs for adherence chart
    _seed_historical_logs(cursor, patient_id)

    conn.commit()
    conn.close()


def _seed_historical_logs(cursor, patient_id):
    """Create 7 days of historical dose logs for demo adherence chart."""
    import random
    meds = cursor.execute(
        "SELECT id, drug_name, times FROM medications WHERE patient_id = ? AND active = 1",
        (patient_id,)
    ).fetchall()

    for day_offset in range(1, 8):
        log_date = date.today() - timedelta(days=day_offset)
        for med in meds:
            times = json.loads(med["times"])
            for t in times:
                # 85% chance of taken, 10% missed, 5% skipped
                roll = random.random()
                if roll < 0.85:
                    action = "taken"
                elif roll < 0.95:
                    action = "missed"
                else:
                    action = "skipped"

                log_time = datetime.combine(log_date, datetime.strptime(t, "%H:%M").time())
                cursor.execute(
                    """INSERT INTO dose_logs (patient_id, medication_name, action, timestamp)
                       VALUES (?, ?, ?, ?)""",
                    (patient_id, med["drug_name"], action, str(log_time))
                )


def generate_daily_schedule(patient_id: int, target_date: date = None):
    """Generate dose schedule entries for a patient for a given date."""
    if target_date is None:
        target_date = date.today()

    conn = get_connection()
    cursor = conn.cursor()

    # Get active medications
    meds = cursor.execute(
        "SELECT * FROM medications WHERE patient_id = ? AND active = 1",
        (patient_id,)
    ).fetchall()

    for med in meds:
        try:
            rules_str = med["schedule_rules"] if "schedule_rules" in med.keys() else None
            rules = json.loads(rules_str) if rules_str else None
        except:
            rules = None
            
        if rules:
            rule_type = rules.get("type", "daily")
            if rule_type == "days_of_week":
                today_name = target_date.strftime("%A")
                days = rules.get("days", [])
                if days and today_name not in days:
                    continue # Skip generating doses for today
            elif rule_type == "interval":
                interval = rules.get("interval_days", 1)
                start_date_str = med["start_date"] if "start_date" in med.keys() else None
                if start_date_str and interval and interval > 1:
                    try:
                        start_dt = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                        days_diff = (target_date - start_dt).days
                        if days_diff % interval != 0:
                            continue # Skip generating doses for today
                    except:
                        pass

        try:
            times_str = med["times"] if "times" in med.keys() else None
            times = json.loads(times_str) if times_str else []
            if isinstance(times, str):
                times = json.loads(times) # Catch any existing double-encoded data
            if not isinstance(times, list):
                times = []
        except:
            times = []
            
        freq = str(dict(med).get("frequency", "")).lower()
        expected_doses = 1
        if "twice" in freq or "2 times" in freq or "bid" in freq:
            expected_doses = 2
        elif "thrice" in freq or "3 times" in freq or "tid" in freq:
            expected_doses = 3
        elif "four" in freq or "4 times" in freq or "qid" in freq:
            expected_doses = 4

        # If we don't have enough explicit times, use sensible defaults
        if len(times) < expected_doses:
            if expected_doses == 2:
                times = ["09:00", "21:00"]
            elif expected_doses == 3:
                times = ["08:00", "14:00", "20:00"]
            elif expected_doses == 4:
                times = ["08:00", "12:00", "16:00", "20:00"]
            else:
                if "bed" in freq or "night" in freq or "evening" in freq or "pm" in freq:
                    times = ["21:00"]
                else:
                    times = ["09:00"]

        for t in times:
            try:
                # Try to parse as HH:MM (24-hour)
                time_obj = datetime.strptime(str(t).strip(), "%H:%M").time()
            except ValueError:
                try:
                    # Try to parse as 12-hour format with AM/PM
                    time_obj = datetime.strptime(str(t).strip(), "%I:%M %p").time()
                except ValueError:
                    # Fallback if somehow invalid time got into DB
                    t_lower = str(t).strip().lower()
                    if "bed" in t_lower or "night" in t_lower or "pm" in t_lower or "evening" in t_lower:
                        time_obj = datetime.strptime("21:00", "%H:%M").time()
                    elif "noon" in t_lower or "afternoon" in t_lower:
                        time_obj = datetime.strptime("12:00", "%H:%M").time()
                    else:
                        time_obj = datetime.strptime("09:00", "%H:%M").time()
                
            scheduled_dt = datetime.combine(target_date, time_obj)

            # Check if already scheduled
            existing = cursor.execute(
                """SELECT id FROM dose_schedule 
                   WHERE medication_id = ? AND scheduled_time = ?""",
                (med["id"], str(scheduled_dt))
            ).fetchone()

            if not existing:
                cursor.execute(
                    """INSERT INTO dose_schedule (medication_id, patient_id, scheduled_time)
                       VALUES (?, ?, ?)""",
                    (med["id"], patient_id, str(scheduled_dt))
                )

    conn.commit()
    conn.close()


# ── CRUD Helpers ──────────────────────────────────────────────────────────

def update_medication_times(medication_id: int, patient_id: int, times: list):
    """Update the scheduled times for a medication and regenerate schedule."""
    conn = get_connection()
    try:
        # Update JSON array of times
        conn.execute(
            "UPDATE medications SET times = ? WHERE id = ?",
            (json.dumps(times), medication_id)
        )
        
        # Delete pending doses for today (so we don't have old alarms hanging around)
        today_str = str(date.today())
        conn.execute(
            """DELETE FROM dose_schedule 
               WHERE medication_id = ? 
               AND status = 'pending' 
               AND scheduled_time >= ?""",
            (medication_id, today_str)
        )
        conn.commit()
    finally:
        conn.close()
        
    # Regenerate schedule with new times
    generate_daily_schedule(patient_id)

def get_all_patients():
    """Return all patients."""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM patients ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def delete_patient(patient_id: int):
    """Delete a patient and all associated records."""
    conn = get_connection()
    try:
        # Delete dependent records first to maintain data integrity
        conn.execute("DELETE FROM escalations WHERE patient_id = ?", (patient_id,))
        conn.execute("DELETE FROM dose_logs WHERE patient_id = ?", (patient_id,))
        conn.execute("DELETE FROM interaction_flags WHERE patient_id = ?", (patient_id,))
        conn.execute("DELETE FROM dose_schedule WHERE patient_id = ?", (patient_id,))
        conn.execute("DELETE FROM medications WHERE patient_id = ?", (patient_id,))
        # Delete the patient record
        conn.execute("DELETE FROM patients WHERE id = ?", (patient_id,))
        conn.commit()
    finally:
        conn.close()

def get_patient(patient_id: int):
    """Return a single patient."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM patients WHERE id = ?", (patient_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def add_patient(name: str, age: int = None, caregiver_name: str = None, caregiver_email: str = None, caregiver_mobile: str = None):
    """Add a new patient."""
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO patients (name, age, caregiver_name, caregiver_email, caregiver_mobile) VALUES (?, ?, ?, ?, ?)",
        (name, age, caregiver_name, caregiver_email, caregiver_mobile)
    )
    patient_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return patient_id


def add_medication(patient_id: int, drug_name: str, generic_name: str, dose: str,
                   frequency: str, schedule_rules: dict = None, times: list = None, is_critical: bool = False,
                   brand_name: str = None, rxcui: str = None, refills: int = 0,
                   start_date: str = None, end_date: str = None):
    """Add a medication for a patient and generate today's schedule."""
    conn = get_connection()
    cursor = conn.execute(
        """INSERT INTO medications 
           (patient_id, drug_name, generic_name, brand_name, dose, frequency, schedule_rules,
            times, is_critical, rxcui, start_date, end_date, refills)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (patient_id, drug_name, generic_name, brand_name, dose, frequency, json.dumps(schedule_rules) if schedule_rules else None,
         json.dumps(times or []), int(is_critical), rxcui,
         start_date or str(date.today()), end_date, refills)
    )
    med_id = cursor.lastrowid
    conn.commit()
    conn.close()

    # Generate schedule for today
    generate_daily_schedule(patient_id)
    return med_id


def get_patient_medications(patient_id: int, active_only: bool = True):
    """Get all medications for a patient."""
    conn = get_connection()
    query = "SELECT * FROM medications WHERE patient_id = ?"
    if active_only:
        query += " AND active = 1"
    query += " ORDER BY created_at DESC"
    rows = conn.execute(query, (patient_id,)).fetchall()
    conn.close()
    results = []
    for r in rows:
        d = dict(r)
        d["times"] = json.loads(d["times"]) if d["times"] else []
        results.append(d)
    return results


def deactivate_medication(med_id: int):
    """Deactivate a medication (soft delete)."""
    conn = get_connection()
    conn.execute("UPDATE medications SET active = 0 WHERE id = ?", (med_id,))
    conn.commit()
    conn.close()


def get_todays_schedule(patient_id: int):
    """Get today's dose schedule for a patient."""
    conn = get_connection()
    today_start = str(datetime.combine(date.today(), datetime.min.time()))
    today_end = str(datetime.combine(date.today(), datetime.max.time()))

    rows = conn.execute(
        """SELECT ds.*, m.drug_name, m.dose, m.is_critical, m.generic_name
           FROM dose_schedule ds
           JOIN medications m ON ds.medication_id = m.id
           WHERE ds.patient_id = ? AND ds.scheduled_time BETWEEN ? AND ?
           ORDER BY ds.scheduled_time""",
        (patient_id, today_start, today_end)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_due_doses(patient_id: int, window_minutes: int = 30):
    """Get doses that are due within a time window from now."""
    conn = get_connection()
    now = datetime.now()
    window_start = str(now - timedelta(minutes=window_minutes))
    window_end = str(now + timedelta(minutes=window_minutes))

    rows = conn.execute(
        """SELECT ds.*, m.drug_name, m.dose, m.is_critical, m.generic_name
           FROM dose_schedule ds
           JOIN medications m ON ds.medication_id = m.id
           WHERE ds.patient_id = ? 
             AND ds.status = 'pending'
             AND ds.scheduled_time BETWEEN ? AND ?
           ORDER BY ds.scheduled_time""",
        (patient_id, window_start, window_end)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_dose(dose_id: int, action: str):
    """Mark a dose as taken, skipped, or missed."""
    conn = get_connection()
    now = str(datetime.now())

    conn.execute(
        "UPDATE dose_schedule SET status = ?, confirmed_at = ? WHERE id = ?",
        (action, now, dose_id)
    )

    # Get dose details for logging
    dose = conn.execute(
        """SELECT ds.*, m.drug_name FROM dose_schedule ds
           JOIN medications m ON ds.medication_id = m.id WHERE ds.id = ?""",
        (dose_id,)
    ).fetchone()

    if dose:
        conn.execute(
            """INSERT INTO dose_logs (dose_schedule_id, patient_id, medication_name, action, timestamp)
               VALUES (?, ?, ?, ?, ?)""",
            (dose_id, dose["patient_id"], dose["drug_name"], action, now)
        )
        # Auto-decrement pill count when dose is taken
        if action == "taken":
            conn.execute(
                "UPDATE medications SET pills_remaining = MAX(0, pills_remaining - 1) WHERE id = ? AND pills_remaining IS NOT NULL",
                (dose["medication_id"],)
            )

    conn.commit()
    conn.close()
    return {"dose_id": dose_id, "action": action, "timestamp": now}


def get_missed_doses_24h(patient_id: int):
    """Count missed doses in the last 24 hours."""
    conn = get_connection()
    cutoff = str(datetime.now() - timedelta(hours=24))
    count = conn.execute(
        """SELECT COUNT(*) FROM dose_logs 
           WHERE patient_id = ? AND action = 'missed' AND timestamp > ?""",
        (patient_id, cutoff)
    ).fetchone()[0]
    conn.close()
    return count


def get_overdue_doses(patient_id: int, grace_minutes: int = 30):
    """Get doses that are past due + grace period and still pending."""
    conn = get_connection()
    cutoff = str(datetime.now() - timedelta(minutes=grace_minutes))

    rows = conn.execute(
        """SELECT ds.*, m.drug_name, m.dose, m.is_critical, m.generic_name
           FROM dose_schedule ds
           JOIN medications m ON ds.medication_id = m.id
           WHERE ds.patient_id = ? 
             AND ds.status = 'pending'
             AND ds.reminder_sent_at IS NULL
             AND ds.scheduled_time < ?
           ORDER BY ds.scheduled_time""",
        (patient_id, cutoff)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def mark_reminder_sent(dose_id: int):
    """Mark that an automated monitor alert was sent for this dose."""
    conn = get_connection()
    conn.execute(
        "UPDATE dose_schedule SET reminder_sent_at = ? WHERE id = ?",
        (str(datetime.now()), dose_id)
    )
    conn.commit()
    conn.close()


def add_interaction_flag(patient_id: int, drug_a: str, drug_b: str,
                         severity: str, note: str, source: str = "RxNorm"):
    """Record a drug interaction flag."""
    conn = get_connection()

    # Check for duplicate
    existing = conn.execute(
        """SELECT id FROM interaction_flags 
           WHERE patient_id = ? AND 
           ((drug_a = ? AND drug_b = ?) OR (drug_a = ? AND drug_b = ?))""",
        (patient_id, drug_a, drug_b, drug_b, drug_a)
    ).fetchone()

    if not existing:
        conn.execute(
            """INSERT INTO interaction_flags (patient_id, drug_a, drug_b, severity, note, source)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (patient_id, drug_a, drug_b, severity, note, source)
        )
        conn.commit()

    conn.close()


def get_interaction_flags(patient_id: int):
    """Get all interaction flags for a patient."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM interaction_flags WHERE patient_id = ? ORDER BY severity DESC, created_at DESC",
        (patient_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_escalation(patient_id: int, dose_schedule_id: int, action: str,
                   reason: str, urgency: str = "low"):
    """Record an escalation event."""
    conn = get_connection()
    conn.execute(
        """INSERT INTO escalations (patient_id, dose_schedule_id, action, reason, urgency)
           VALUES (?, ?, ?, ?, ?)""",
        (patient_id, dose_schedule_id, action, reason, urgency)
    )
    conn.commit()
    conn.close()


def get_dose_logs(patient_id: int, days: int = 7):
    """Get dose logs for the last N days."""
    conn = get_connection()
    cutoff = str(datetime.now() - timedelta(days=days))
    rows = conn.execute(
        """SELECT * FROM dose_logs 
           WHERE patient_id = ? AND timestamp > ?
           ORDER BY timestamp DESC""",
        (patient_id, cutoff)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_adherence_stats(patient_id: int, days: int = 7):
    """Calculate adherence percentage over the last N days."""
    logs = get_dose_logs(patient_id, days)
    if not logs:
        return {"total": 0, "taken": 0, "missed": 0, "skipped": 0, "adherence_pct": 0}

    total = len(logs)
    taken = sum(1 for l in logs if l["action"] == "taken")
    missed = sum(1 for l in logs if l["action"] == "missed")
    skipped = sum(1 for l in logs if l["action"] == "skipped")

    adherence_pct = round((taken / total) * 100, 1) if total > 0 else 0
    return {
        "total": total,
        "taken": taken,
        "missed": missed,
        "skipped": skipped,
        "adherence_pct": adherence_pct,
    }


def get_escalations(patient_id: int, unresolved_only: bool = False, days: int = 7):
    """Get escalation events."""
    conn = get_connection()
    query = "SELECT * FROM escalations WHERE patient_id = ?"
    params = [patient_id]
    
    if unresolved_only:
        query += " AND resolved = 0"
        
    if days is not None:
        query += " AND created_at >= date('now', ?)"
        params.append(f"-{days} days")
        
    query += " ORDER BY created_at DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Feature 2: Adherence Analytics ────────────────────────────────────────

def get_adherence_trend(patient_id: int, days: int = 14):
    """Get day-by-day adherence breakdown for trend charts."""
    conn = get_connection()
    cutoff = str(datetime.now() - timedelta(days=days))
    rows = conn.execute(
        """SELECT DATE(timestamp) as day, action, COUNT(*) as count
           FROM dose_logs
           WHERE patient_id = ? AND timestamp > ?
           GROUP BY DATE(timestamp), action
           ORDER BY day""",
        (patient_id, cutoff)
    ).fetchall()
    conn.close()

    trend = {}
    for r in rows:
        day = r["day"]
        if day not in trend:
            trend[day] = {"date": day, "taken": 0, "missed": 0, "skipped": 0, "total": 0}
        action = r["action"]
        if action in trend[day]:
            trend[day][action] = r["count"]
        trend[day]["total"] += r["count"]

    result = list(trend.values())
    for entry in result:
        entry["adherence_pct"] = round((entry["taken"] / entry["total"]) * 100, 1) if entry["total"] > 0 else 0
    return result


def get_medication_adherence_breakdown(patient_id: int, days: int = 14):
    """Get per-medication adherence rates."""
    conn = get_connection()
    cutoff = str(datetime.now() - timedelta(days=days))
    rows = conn.execute(
        """SELECT medication_name, action, COUNT(*) as count
           FROM dose_logs
           WHERE patient_id = ? AND timestamp > ?
           GROUP BY medication_name, action""",
        (patient_id, cutoff)
    ).fetchall()
    conn.close()

    breakdown = {}
    for r in rows:
        med = r["medication_name"]
        if med not in breakdown:
            breakdown[med] = {"medication": med, "taken": 0, "missed": 0, "skipped": 0, "total": 0}
        action = r["action"]
        if action in breakdown[med]:
            breakdown[med][action] = r["count"]
        breakdown[med]["total"] += r["count"]

    result = list(breakdown.values())
    for entry in result:
        entry["adherence_pct"] = round((entry["taken"] / entry["total"]) * 100, 1) if entry["total"] > 0 else 0
    return result


# ── Feature 3: Refill Prediction ──────────────────────────────────────────

def get_refill_status(patient_id: int):
    """Calculate refill status for all active medications."""
    conn = get_connection()
    meds = conn.execute(
        "SELECT * FROM medications WHERE patient_id = ? AND active = 1",
        (patient_id,)
    ).fetchall()
    conn.close()

    result = []
    for med in meds:
        med_dict = dict(med)
        pills = med_dict.get("pills_remaining")
        freq = (med_dict.get("frequency") or "").lower()

        # Estimate daily consumption
        daily_doses = 1
        if "twice" in freq or "2 times" in freq or "bid" in freq:
            daily_doses = 2
        elif "thrice" in freq or "3 times" in freq or "tid" in freq:
            daily_doses = 3
        elif "four" in freq or "4 times" in freq or "qid" in freq:
            daily_doses = 4

        days_remaining = None
        if pills is not None and daily_doses > 0:
            days_remaining = pills // daily_doses

        result.append({
            "medication_id": med_dict["id"],
            "drug_name": med_dict["drug_name"],
            "dose": med_dict["dose"],
            "pills_remaining": pills,
            "daily_doses": daily_doses,
            "days_remaining": days_remaining,
            "refills_left": med_dict.get("refills", 0)
        })
    return result


def decrement_pill_count(medication_id: int):
    """Decrement the pill count when a dose is taken."""
    conn = get_connection()
    conn.execute(
        "UPDATE medications SET pills_remaining = MAX(0, pills_remaining - 1) WHERE id = ? AND pills_remaining IS NOT NULL",
        (medication_id,)
    )
    conn.commit()
    conn.close()


def set_pill_count(medication_id: int, count: int):
    """Set the pill count for a medication."""
    conn = get_connection()
    conn.execute(
        "UPDATE medications SET pills_remaining = ? WHERE id = ?",
        (count, medication_id)
    )
    conn.commit()
    conn.close()


# ── Feature 4: Symptom Logs ───────────────────────────────────────────────

def add_symptom_log(patient_id: int, symptom: str, severity: str = "mild"):
    """Log a patient symptom."""
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO symptom_logs (patient_id, symptom, severity) VALUES (?, ?, ?)",
        (patient_id, symptom, severity)
    )
    log_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return log_id


def get_symptom_logs(patient_id: int, days: int = 30):
    """Get symptom logs for a patient."""
    conn = get_connection()
    cutoff = str(datetime.now() - timedelta(days=days))
    rows = conn.execute(
        """SELECT * FROM symptom_logs
           WHERE patient_id = ? AND timestamp > ?
           ORDER BY timestamp DESC""",
        (patient_id, cutoff)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Feature 6: Schedule Optimization ──────────────────────────────────────

def get_actual_vs_scheduled(patient_id: int, days: int = 14):
    """Get pairs of (scheduled_time, confirmed_at) for timing analysis."""
    conn = get_connection()
    cutoff = str(datetime.now() - timedelta(days=days))
    rows = conn.execute(
        """SELECT ds.scheduled_time, ds.confirmed_at, m.drug_name, m.id as medication_id
           FROM dose_schedule ds
           JOIN medications m ON ds.medication_id = m.id
           WHERE ds.patient_id = ? AND ds.status = 'taken'
             AND ds.confirmed_at IS NOT NULL
             AND ds.scheduled_time > ?
           ORDER BY ds.scheduled_time""",
        (patient_id, cutoff)
    ).fetchall()
    conn.close()

    result = []
    for r in rows:
        try:
            scheduled = datetime.fromisoformat(r["scheduled_time"])
            confirmed = datetime.fromisoformat(r["confirmed_at"])
            delay_minutes = int((confirmed - scheduled).total_seconds() / 60)
            result.append({
                "drug_name": r["drug_name"],
                "medication_id": r["medication_id"],
                "scheduled_time": r["scheduled_time"],
                "actual_time": r["confirmed_at"],
                "delay_minutes": delay_minutes
            })
        except Exception:
            continue
    return result


# Initialize on import
init_db()
