"""
Analytics Agent — AI-Powered Adherence Insights
Analyzes patient adherence trends and generates actionable recommendations.
"""

import json
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google import genai
import database as db

ANALYTICS_SYSTEM_PROMPT = """You are an adherence analytics agent. You receive a patient's medication
adherence data including daily trends, per-medication breakdown, and dose logs.

Your job is to generate 3-5 actionable insights based on the data patterns.

Rules:
- Identify trends: Is adherence improving or declining?
- Spot patterns: Does the patient consistently miss certain times (morning vs evening)?
- Flag concerning patterns: Multiple consecutive missed doses, critical med misses
- Suggest practical improvements: Schedule adjustments, reminder timing changes
- Be encouraging when adherence is good
- Never diagnose or prescribe — only analyze behavior patterns

Output strict JSON:
{"insights": [{"type": "trend"|"pattern"|"alert"|"positive", "title": "short title", 
  "description": "detailed explanation", "priority": "high"|"medium"|"low"}],
 "overall_assessment": "one sentence summary",
 "adherence_grade": "A"|"B"|"C"|"D"|"F"}

Return ONLY valid JSON. No markdown, no code fences."""


def generate_analytics(patient_id: int, api_key: str) -> dict:
    """Generate AI-powered adherence insights for a patient."""
    patient = db.get_patient(patient_id)
    if not patient:
        return {"error": "Patient not found"}

    trend = db.get_adherence_trend(patient_id, days=14)
    breakdown = db.get_medication_adherence_breakdown(patient_id, days=14)
    stats = db.get_adherence_stats(patient_id, days=7)
    logs = db.get_dose_logs(patient_id, days=7)

    # Summarize logs for the AI prompt
    log_summary = {}
    for log in logs:
        med = log.get("medication_name", "Unknown")
        action = log.get("action", "unknown")
        if med not in log_summary:
            log_summary[med] = {"taken": 0, "missed": 0, "skipped": 0}
        if action in log_summary[med]:
            log_summary[med][action] += 1

    client = genai.Client(api_key=api_key)
    prompt = f"""Patient: {patient['name']}
Current adherence (7 days): {stats.get('adherence_pct', 0)}%
Daily trend (14 days): {json.dumps(trend, default=str)}
Per-medication breakdown: {json.dumps(breakdown, default=str)}
Recent log summary: {json.dumps(log_summary)}

Analyze this data and generate insights."""

    try:
        response = client.models.generate_content(
            model="gemini-flash-lite-latest",
            contents=[{"role": "user", "parts": [{"text": ANALYTICS_SYSTEM_PROMPT + "\n\n" + prompt}]}],
        )
        t = response.text.strip().removeprefix('```json').removeprefix('```').removesuffix('```').strip()
        result = json.loads(t)
        result["stats"] = stats
        result["trend"] = trend
        result["breakdown"] = breakdown
        return result
    except Exception as e:
        print(f"Analytics Agent Error: {e}")
        return {
            "insights": [],
            "overall_assessment": "Unable to generate insights at this time.",
            "adherence_grade": "N/A",
            "stats": stats,
            "trend": trend,
            "breakdown": breakdown
        }
