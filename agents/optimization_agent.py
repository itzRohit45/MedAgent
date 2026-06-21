"""
Optimization Agent — Adaptive Schedule Optimization
Analyzes when patients actually take their doses vs scheduled times
and suggests schedule adjustments to improve adherence.
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google import genai
import database as db

OPTIMIZATION_SYSTEM_PROMPT = """You are a schedule optimization agent. You receive data about when
patients were scheduled to take medication vs when they actually took it.

Your job is to detect patterns and suggest schedule changes that would improve adherence.

Rules:
- Only suggest changes if there's a clear, consistent pattern (3+ data points)
- Calculate the average actual time for each medication
- If the patient consistently takes a dose 30+ minutes late, suggest moving the schedule
- Consider practical factors (meals, sleep, work schedules)
- Never suggest changing dose amounts — only timing
- Be specific with recommended times

Output strict JSON:
{"suggestions": [{"medication": "drug name", "medication_id": 0,
  "current_time": "HH:MM", "suggested_time": "HH:MM",
  "reason": "explanation", "avg_delay_minutes": 0,
  "data_points": 0, "confidence": "high"|"medium"|"low"}],
 "summary": "overall assessment"}

Return ONLY valid JSON. No markdown, no code fences."""


def generate_optimization_suggestions(patient_id: int, api_key: str) -> dict:
    """Analyze dose timing patterns and suggest schedule optimizations."""
    patient = db.get_patient(patient_id)
    if not patient:
        return {"error": "Patient not found"}

    timing_data = db.get_actual_vs_scheduled(patient_id, days=14)
    if not timing_data:
        return {
            "suggestions": [],
            "summary": "Not enough dose history to analyze patterns yet. Take a few more doses so I can learn your routine! 📊"
        }

    client = genai.Client(api_key=api_key)
    prompt = f"""Patient: {patient['name']}

Dose timing data (scheduled vs actual) over 14 days:
{json.dumps(timing_data, default=str)}

Analyze patterns and suggest schedule optimizations."""

    try:
        response = client.models.generate_content(
            model="gemini-flash-lite-latest",
            contents=[{"role": "user", "parts": [{"text": OPTIMIZATION_SYSTEM_PROMPT + "\n\n" + prompt}]}],
        )
        t = response.text.strip().removeprefix('```json').removeprefix('```').removesuffix('```').strip()
        return json.loads(t)
    except Exception as e:
        print(f"Optimization Agent Error: {e}")
        return {
            "suggestions": [],
            "summary": "Unable to generate suggestions at this time."
        }
