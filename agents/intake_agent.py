import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google import genai
from tools.rxnorm_tools import resolve_drug_to_rxcui

INTAKE_SYSTEM_PROMPT = """You are a medical intake agent. Your job is to extract structured medication 
data from a prescription, which may be an image or free text.

Extract: drug name (generic + brand if given), dosage (amount + unit), 
frequency (times per day), specific times if mentioned, duration/refill info.

Rules:
- If critical fields (drug name, dosage, or frequency) are unclear or missing, mark it as "needs_confirmation": true and ask the user a specific clarifying question. Never guess a dosage.
- Do NOT flag as needs_confirmation if only optional fields like duration, times, or refills are missing. Just leave them empty or 0.
- Normalize drug names to their generic form when confident, but keep the 
  original text too.
- Output strict JSON only, no prose. Return a JSON array if multiple medications
  are found. Each medication object should have:
  {"drug": "", "generic_name": "", "brand_name": "", "dose": "", "frequency": "", 
   "schedule_rules": {"type": "daily", "days": [], "interval_days": null},
   "times": [], "duration": "", "refills": 0, "is_critical": false,
   "needs_confirmation": false, "question": ""}
  For `schedule_rules`: 
    - `type` can be "daily" (every day), "days_of_week" (e.g. Mon/Wed/Fri), or "interval" (e.g. every 3 days).
    - `days` should be an array of full day names (e.g. ["Monday", "Wednesday"]) if type is "days_of_week".
    - `interval_days` should be an integer (e.g. 2 for alternate days, 3 for every 3 days) if type is "interval".
- Common critical medications include: insulin, warfarin, blood thinners,
  anti-seizure meds, heart rhythm meds. Flag these as is_critical: true.
- You are not a doctor. Never suggest changing a dose or stopping a medication.
- If you see an image, use your vision capability to read the prescription text.

IMPORTANT: Return ONLY the JSON array. No markdown, no code fences, no explanation."""

def parse_prescription_text(prescription_text: str, api_key: str) -> list:
    client = genai.Client(api_key=api_key)
    try:
        response = client.models.generate_content(
            model="gemini-flash-lite-latest",
            contents=[
                {"role": "user", "parts": [{"text": INTAKE_SYSTEM_PROMPT + "\n\nPrescription Text:\n" + prescription_text}]}
            ],
        )
        t = response.text.strip().removeprefix('```json').removeprefix('```').removesuffix('```').strip()
        return json.loads(t)
    except Exception as e:
        print(f"Intake Agent Error (Text): {e}")
        return []

def parse_prescription_image(image_bytes: bytes, mime_type: str, api_key: str) -> list:
    client = genai.Client(api_key=api_key)
    try:
        response = client.models.generate_content(
            model="gemini-flash-lite-latest",
            contents=[
                {"role": "user", "parts": [
                    {"text": INTAKE_SYSTEM_PROMPT + "\n\nAnalyze this prescription image:"},
                    {"inline_data": {"mime_type": mime_type, "data": image_bytes}}
                ]}
            ],
        )
        t = response.text.strip().removeprefix('```json').removeprefix('```').removesuffix('```').strip()
        return json.loads(t)
    except Exception as e:
        print(f"Intake Agent Error (Image): {e}")
        return []

def enrich_with_rxcui(medications: list) -> list:
    for med in medications:
        if med.get("needs_confirmation"):
            continue
        res = resolve_drug_to_rxcui(med.get("generic_name") or med.get("drug"))
        if res.get("found"):
            med["rxcui"] = res.get("rxcui")
    return medications