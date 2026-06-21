import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google import genai
from tools.rxnorm_tools import check_drug_interactions, resolve_drug_to_rxcui
from tools.openfda_tools import get_drug_label_interactions
import database as db

INTERACTION_SYSTEM_PROMPT = """You are a medication safety agent. You receive a patient's full current 
medication list and drug interaction data retrieved from RxNorm and OpenFDA APIs.

Rules:
- Only flag interactions actually present in the provided tool data. Never invent 
  or recall interactions from memory — only cite what is in the data provided.
- Classify each flag as "minor", "moderate", or "severe" based on the 
  source data's own severity rating, not your judgment.
- For "severe", set escalate to true for the caregiver agent.
- For "minor" or "moderate", include a plain-language note for the patient 
  summary, no escalation.
- Always include a disclaimer that this is not a substitute for pharmacist 
  or doctor review.

Output strict JSON only:
{"flags": [{"drugs": [], "severity": "", "note": "", "source": ""}], 
 "escalate": false,
 "disclaimer": "This is an automated check and is not a substitute for review by a pharmacist or doctor."}

If no interactions are found, return:
{"flags": [], "escalate": false, "disclaimer": "..."}

Return ONLY valid JSON. No markdown, no code fences, no explanation."""

def check_patient_interactions(patient_id: int, api_key: str) -> dict:
    meds = db.get_patient_medications(patient_id)
    if not meds:
        return {"flags": [], "escalate": False, "disclaimer": "No active medications."}
    
    # In a real scenario we'd query RxNorm and OpenFDA tools here.
    # We will simulate the gathered data for the prompt.
    gathered_data = []
    for med in meds:
        rxcui = med.get("rxcui")
        if rxcui:
            gathered_data.append(check_drug_interactions(rxcui))
        gathered_data.append(get_drug_label_interactions(med.get("generic_name") or med.get("drug_name")))
        
    client = genai.Client(api_key=api_key)
    prompt = INTERACTION_SYSTEM_PROMPT + f"\n\nMedications: {json.dumps([m['drug_name'] for m in meds])}\n\nData:\n{json.dumps(gathered_data)}"
    try:
        response = client.models.generate_content(
            model="gemini-flash-lite-latest",
            contents=[{"role": "user", "parts": [{"text": prompt}]}]
        )
        
        # Clean the response text from markdown code blocks
        raw_text = response.text
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
            
        return json.loads(raw_text)
    except Exception as e:
        print(f"Interaction Agent Error: {e}")
        # Return a soft fallback if we hit a rate limit (429) instead of crashing
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
            return [{"drug1": "API Rate Limit", "drug2": "Reached", "severity": "low", "description": "Google API 5 requests/minute limit reached. Please wait 60s for full interaction checking."}]
        return []
    except:
        return {"flags": [], "escalate": False, "disclaimer": "Error parsing interactions."}