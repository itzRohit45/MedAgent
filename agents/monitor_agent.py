import json
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google import genai
from tools.schedule_tools import get_overdue_doses_for_patient, get_missed_dose_info
from tools.notification_tools import send_patient_reminder, send_caregiver_alert
import database as db

MONITOR_SYSTEM_PROMPT = """You are a monitoring agent deciding how to respond to missed medication doses.

Input: dose details, time since due, number of prior missed doses this week, 
whether this is a critical medication (e.g. insulin, blood thinners).

Decide one of three actions:
1. "gentle_nudge" — send one more reminder to the patient (default for 
   first miss, non-critical med)
2. "escalate_caregiver" — notify the caregiver now (critical med missed, 
   or 2+ misses in 24h, or patient explicitly said "skip" on a critical med)
3. "log_only" — patient confirmed taken late, just record it

Always err toward escalate_caregiver when the medication is flagged critical 
and more than 1 hour has passed with no response.

Output strict JSON for EACH missed dose:
{"action": "", "reason": "", "urgency": "low"|"medium"|"high", 
 "dose_id": 0, "drug_name": "", "scheduled_time": ""}

If multiple doses are missed, return a JSON array.
Return ONLY valid JSON. No markdown, no code fences."""

def check_and_handle_missed_doses(patient_id: int, api_key: str) -> dict:
    overdue = get_overdue_doses_for_patient(patient_id)
    if not overdue:
        return {
            "actions": [],
            "note": "No overdue doses detected."
        }

    missed_info = []
    for d in overdue:
        missed_info.append(get_missed_dose_info(d["dose_id"], patient_id))

    client = genai.Client(api_key=api_key)
    prompt = f"Missed doses info:\n{json.dumps(missed_info, indent=2)}"
    
    try:
        response = client.models.generate_content(
            model="gemini-flash-lite-latest",
            contents=[
                {"role": "user", "parts": [{"text": MONITOR_SYSTEM_PROMPT + "\n\n" + prompt}]}
            ],
        )
        
        t = response.text.strip().removeprefix('```json').removeprefix('```').removesuffix('```').strip()
        actions = json.loads(t)
        if not isinstance(actions, list):
            actions = [actions]
            
        for a in actions:
            if a.get("action") == "gentle_nudge":
                t_str = a.get('scheduled_time', 'their scheduled time')
                msg = f"You missed your medicine {a.get('drug_name')} scheduled at {t_str}. Please take it as early as possible."
                send_patient_reminder(patient_id, msg)
            elif a.get("action") == "escalate_caregiver":
                send_caregiver_alert(patient_id, f"Missed dose: {a.get('drug_name')}. Reason: {a.get('reason')}", a.get("urgency", "medium"))
            
            if a.get("dose_id"):
                db.mark_reminder_sent(a.get("dose_id"))
                
        return {"actions": actions}
    except Exception as e:
        print(f"Monitor Agent Error: {e}")
        return {"actions": [], "error": str(e)}