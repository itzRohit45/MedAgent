import json
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google import genai
from tools.schedule_tools import get_due_reminders, confirm_dose_taken, skip_dose
from tools.notification_tools import send_patient_reminder

SCHEDULER_SYSTEM_PROMPT = """You are a reminder agent for a patient's medication schedule.
Given today's dose schedule and the current time, decide which reminders are due now.

Rules:
- Generate one short, friendly reminder message per due dose. Plain language, 
  one sentence, include drug name and dose.
- Do not include reminders that are more than 30 minutes early.
- Keep messages warm and encouraging, not clinical.
- Include a simple emoji to make it friendly.

Output strict JSON only:
{"reminders": [{"dose_id": 0, "drug_name": "", "dose": "", "message": ""}]}

Return ONLY valid JSON. No markdown, no code fences."""

def generate_reminders(patient_id: int, api_key: str) -> dict:
    due_doses = get_due_reminders(patient_id)

    if not due_doses:
        return {
            "reminders": [],
            "note": "No doses are due right now. All caught up! ✅",
        }

    client = genai.Client(api_key=api_key)

    prompt = f"""Current time: {datetime.now().strftime('%I:%M %p')}

These doses are due now:
{json.dumps(due_doses, indent=2)}

Generate a friendly, warm reminder for each dose."""

    try:
        response = client.models.generate_content(
            model="gemini-flash-lite-latest",
            contents=[
                {"role": "user", "parts": [{"text": SCHEDULER_SYSTEM_PROMPT + "\n\n" + prompt}]}
            ],
        )
        
        t = response.text.strip().removeprefix('```json').removeprefix('```').removesuffix('```').strip()
        data = json.loads(t)
        for r in data.get("reminders", []):
            send_patient_reminder(patient_id, r.get("message"))
        return data
    except Exception as e:
        print(f"Scheduler Agent Error: {e}")
        return {"reminders": [], "note": "Error generating reminders. " + str(e)}

def handle_dose_response(dose_id: int, action: str) -> dict:
    if action == "taken":
        return confirm_dose_taken(dose_id)
    elif action == "skipped":
        return skip_dose(dose_id)
    return {"error": "Unknown action"}