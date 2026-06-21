"""
Education Agent — RAG-Based Drug Information
Retrieves drug information from OpenFDA labels and transforms complex medical text
into patient-friendly education cards using Retrieval Augmented Generation (RAG).
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google import genai
from tools.openfda_tools import get_drug_education_info
import database as db

EDUCATION_SYSTEM_PROMPT = """You are a patient education agent. You receive raw drug label data 
from the FDA (OpenFDA) and must transform it into a simple, friendly, easy-to-understand
information card for patients and caregivers.

Rules:
- Use simple, non-medical language that a 12-year-old could understand
- Structure the response clearly with distinct sections
- Include practical tips (e.g., "take with food", "avoid grapefruit")
- Highlight important warnings in a caring, non-alarming way
- Keep each section to 1-3 sentences max
- Never suggest changing doses or stopping medication
- Always note that the doctor's instructions take priority

Output strict JSON:
{"drug_name": "", "purpose": "what this medicine does in simple terms",
 "how_to_take": "practical instructions",
 "common_side_effects": ["side effect 1", "side effect 2"],
 "important_warnings": ["warning 1", "warning 2"],
 "tips": ["helpful tip 1", "helpful tip 2"],
 "interactions_to_avoid": "foods, drinks, or activities to avoid",
 "disclaimer": "Always follow your doctor's instructions."}

Return ONLY valid JSON. No markdown, no code fences."""


def generate_drug_education(medication_id: int, api_key: str) -> dict:
    """Generate a patient-friendly drug education card using RAG."""
    conn = db.get_connection()
    med = conn.execute(
        "SELECT * FROM medications WHERE id = ?", (medication_id,)
    ).fetchone()
    conn.close()

    if not med:
        return {"error": "Medication not found"}

    drug_name = med["generic_name"] or med["drug_name"]

    # RAG Step 1: Retrieve — Fetch raw data from OpenFDA
    raw_data = get_drug_education_info(drug_name)

    # RAG Step 2: Augment + Generate — Feed raw data to AI for simplification
    client = genai.Client(api_key=api_key)
    prompt = f"""Drug: {drug_name} ({med['dose']})
Frequency: {med['frequency']}

Raw FDA Label Data:
{json.dumps(raw_data, default=str)}

Transform this into a simple, friendly patient education card."""

    try:
        response = client.models.generate_content(
            model="gemini-flash-lite-latest",
            contents=[{"role": "user", "parts": [{"text": EDUCATION_SYSTEM_PROMPT + "\n\n" + prompt}]}],
        )
        t = response.text.strip().removeprefix('```json').removeprefix('```').removesuffix('```').strip()
        result = json.loads(t)
        result["source"] = "OpenFDA + AI"
        return result
    except Exception as e:
        print(f"Education Agent Error: {e}")
        return {
            "drug_name": drug_name,
            "purpose": "Information temporarily unavailable.",
            "how_to_take": f"Take as prescribed: {med['dose']} {med['frequency']}",
            "common_side_effects": [],
            "important_warnings": [],
            "tips": [],
            "interactions_to_avoid": "",
            "disclaimer": "Always follow your doctor's instructions.",
            "source": "fallback"
        }
