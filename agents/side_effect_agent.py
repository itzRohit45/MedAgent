"""
Side Effect Agent — Symptom-Drug Correlation Analysis
Cross-references patient-reported symptoms against known drug side effects
using OpenFDA adverse event data.
"""

import json
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google import genai
from tools.openfda_tools import get_drug_adverse_events
import database as db

SIDE_EFFECT_SYSTEM_PROMPT = """You are a medication side effect analysis agent. You receive:
1. A patient's reported symptoms
2. Their active medications
3. OpenFDA adverse event data for those medications

Your job is to identify potential correlations between the symptoms and medications.

Rules:
- Only flag correlations that are supported by the OpenFDA data provided
- Classify each correlation as "likely", "possible", or "unlikely"
- Never diagnose — only highlight data-supported correlations
- Always recommend consulting a doctor for medical decisions
- Be clear about uncertainty

Output strict JSON:
{"correlations": [{"symptom": "", "medication": "", "likelihood": "likely"|"possible"|"unlikely",
  "evidence": "explanation from data", "recommendation": "what to do"}],
 "summary": "brief overall assessment",
 "consult_doctor": true|false}

Return ONLY valid JSON. No markdown, no code fences."""


def analyze_symptoms(patient_id: int, api_key: str) -> dict:
    """Analyze patient symptoms against medication side effects."""
    patient = db.get_patient(patient_id)
    if not patient:
        return {"error": "Patient not found"}

    symptoms = db.get_symptom_logs(patient_id, days=14)
    if not symptoms:
        return {
            "correlations": [],
            "summary": "No symptoms have been reported yet.",
            "consult_doctor": False
        }

    meds = db.get_patient_medications(patient_id)
    if not meds:
        return {
            "correlations": [],
            "summary": "No active medications to correlate against.",
            "consult_doctor": False
        }

    # Gather adverse event data from OpenFDA for each medication
    adverse_data = {}
    for med in meds:
        drug_name = med.get("generic_name") or med.get("drug_name")
        try:
            data = get_drug_adverse_events(drug_name)
            adverse_data[drug_name] = data
        except Exception:
            adverse_data[drug_name] = {"error": "Could not fetch adverse event data"}

    # Build unique symptom list
    unique_symptoms = list(set(s["symptom"] for s in symptoms))

    client = genai.Client(api_key=api_key)
    prompt = f"""Patient: {patient['name']}

Reported symptoms (last 14 days): {json.dumps(unique_symptoms)}
Symptom details: {json.dumps([{"symptom": s["symptom"], "severity": s["severity"], 
  "date": s["timestamp"]} for s in symptoms], default=str)}

Active medications: {json.dumps([{"name": m["drug_name"], "dose": m["dose"]} for m in meds])}

OpenFDA adverse event data:
{json.dumps(adverse_data, default=str)}

Analyze correlations between the symptoms and medications."""

    try:
        response = client.models.generate_content(
            model="gemini-flash-lite-latest",
            contents=[{"role": "user", "parts": [{"text": SIDE_EFFECT_SYSTEM_PROMPT + "\n\n" + prompt}]}],
        )
        t = response.text.strip().removeprefix('```json').removeprefix('```').removesuffix('```').strip()
        return json.loads(t)
    except Exception as e:
        print(f"Side Effect Agent Error: {e}")
        return {
            "correlations": [],
            "summary": "Unable to analyze at this time.",
            "consult_doctor": False
        }
