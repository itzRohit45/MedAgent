import json
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google import genai
from tools.schedule_tools import get_adherence_report
from tools.notification_tools import send_caregiver_alert
import database as db

CAREGIVER_SYSTEM_PROMPT = """You are a caregiver communication agent. Turn a patient's medication log 
into a short, warm, non-alarming summary for a family caregiver.

Rules:
- Lead with the headline (all good / one missed dose / needs attention) 
  in the first sentence.
- Use plain language, no medical jargon, no raw data dumps.
- If this is an escalation (not a routine daily/weekly report), say clearly 
  what happened and what action is recommended (e.g. "call them" vs 
  "just a heads up").
- Never diagnose or suggest medical decisions — only report facts and 
  suggest human follow-up.
- Keep it under 80 words for routine reports, under 50 for escalations.
- Include the patient's name in the greeting.
- End with a warm closing.

Output strict JSON:
{"report_type": "routine"|"escalation", "summary": "", "headline": "",
 "action_needed": true|false, "recommended_action": ""}

Return ONLY valid JSON. No markdown, no code fences."""

def generate_daily_report(patient_id: int, api_key: str) -> dict:
    patient = db.get_patient(patient_id)
    if not patient:
        return {"error": f"Patient {patient_id} not found"}

    adherence = get_adherence_report(patient_id, days=1)
    logs = db.get_dose_logs(patient_id, days=1)
    escalations = db.get_escalations(patient_id, days=1)

    client = genai.Client(api_key=api_key)
    prompt = f"""Patient: {patient['name']}
Adherence: {json.dumps(adherence)}
Logs: {json.dumps([dict(l) for l in logs])}
Escalations: {json.dumps([dict(e) for e in escalations])}
Generate a daily caregiver report."""

    try:
        response = client.models.generate_content(
            model="gemini-flash-lite-latest",
            contents=[
                {"role": "user", "parts": [{"text": CAREGIVER_SYSTEM_PROMPT + "\n\n" + prompt}]}
            ],
        )
        
        t = response.text.strip().removeprefix('```json').removeprefix('```').removesuffix('```').strip()
        data = json.loads(t)
        return data
    except Exception as e:
        print(f"Caregiver Agent Error: {e}")
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
            return {"report_type": "routine", "summary": "API Rate Limit reached. Please wait a minute before requesting another AI report.", "headline": "API Quota Exceeded", "action_needed": False, "recommended_action": ""}
        return {"error": "Failed to generate report"}

def generate_weekly_report(patient_id: int, api_key: str) -> dict:
    return generate_daily_report(patient_id, api_key)

def generate_escalation_report(patient_id: int, api_key: str, context: str) -> dict:
    return generate_daily_report(patient_id, api_key)