"""
OpenFDA API Tools
Retrieves drug label information and interaction sections from FDA's
Structured Product Labeling (SPL) data. Free, no API key required.
"""

import requests
from typing import Optional

OPENFDA_BASE = "https://api.fda.gov/drug"


def get_drug_label_interactions(drug_name: str) -> dict:
    """
    Retrieve the drug interactions section from FDA-approved drug labeling
    for a given drug name.

    Args:
        drug_name: Generic drug name to look up, e.g. "metformin"

    Returns:
        A dictionary containing the drug_interactions text from the label,
        or an error if not found.
    """
    try:
        url = f"{OPENFDA_BASE}/label.json"
        params = {
            "search": f'openfda.generic_name:"{drug_name}"',
            "limit": 1,
        }
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        results = data.get("results", [])
        if not results:
            return {
                "found": False,
                "drug_name": drug_name,
                "error": "No FDA label found for this drug",
            }

        label = results[0]
        interactions = label.get("drug_interactions", ["No interaction section in label"])
        warnings = label.get("warnings", ["No warnings section"])
        contraindications = label.get("contraindications", ["No contraindications section"])

        return {
            "found": True,
            "drug_name": drug_name,
            "brand_name": label.get("openfda", {}).get("brand_name", [""])[0],
            "generic_name": label.get("openfda", {}).get("generic_name", [""])[0],
            "drug_interactions": interactions[0] if interactions else "Not available",
            "warnings_excerpt": (warnings[0][:500] + "...") if warnings and len(warnings[0]) > 500 else (warnings[0] if warnings else "Not available"),
            "contraindications_excerpt": (contraindications[0][:300] + "...") if contraindications and len(contraindications[0]) > 300 else (contraindications[0] if contraindications else "Not available"),
        }

    except requests.RequestException as e:
        return {"found": False, "drug_name": drug_name, "error": str(e)}


def get_drug_adverse_events(drug_name: str, limit: int = 5) -> dict:
    """
    Retrieve recent adverse event reports for a drug from FDA FAERS.

    Args:
        drug_name: Drug name to search adverse events for.
        limit: Maximum number of event reports to return (default 5).

    Returns:
        A dictionary with a list of adverse event summaries.
    """
    try:
        url = f"{OPENFDA_BASE}/event.json"
        params = {
            "search": f'patient.drug.openfda.generic_name:"{drug_name}"',
            "limit": min(limit, 10),
        }
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        results = data.get("results", [])
        events = []
        for result in results:
            reactions = []
            for reaction in result.get("patient", {}).get("reaction", []):
                reactions.append(reaction.get("reactionmeddrapt", ""))

            seriousness = "serious" if result.get("serious", 0) == 1 else "non-serious"

            events.append({
                "reactions": reactions[:5],
                "seriousness": seriousness,
                "date": result.get("receivedate", ""),
            })

        return {
            "drug_name": drug_name,
            "event_count": len(events),
            "events": events,
        }

    except requests.RequestException as e:
        return {"drug_name": drug_name, "events": [], "error": str(e)}


def get_drug_education_info(drug_name: str) -> dict:
    """
    Retrieve comprehensive drug label information for patient education.
    Fetches purpose, dosage instructions, warnings, side effects from FDA labels.

    Args:
        drug_name: Generic drug name to look up.

    Returns:
        A dictionary with raw FDA label sections for AI simplification.
    """
    try:
        url = f"{OPENFDA_BASE}/label.json"
        params = {
            "search": f'openfda.generic_name:"{drug_name}"',
            "limit": 1,
        }
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        results = data.get("results", [])
        if not results:
            return {"found": False, "drug_name": drug_name, "error": "No FDA label found"}

        label = results[0]

        def truncate(text_list, max_len=800):
            if not text_list:
                return "Not available"
            text = text_list[0]
            return (text[:max_len] + "...") if len(text) > max_len else text

        return {
            "found": True,
            "drug_name": drug_name,
            "purpose": truncate(label.get("purpose") or label.get("indications_and_usage", [])),
            "dosage_and_administration": truncate(label.get("dosage_and_administration", [])),
            "warnings": truncate(label.get("warnings", [])),
            "adverse_reactions": truncate(label.get("adverse_reactions", [])),
            "drug_interactions": truncate(label.get("drug_interactions", [])),
            "how_supplied": truncate(label.get("how_supplied", []), 300),
        }

    except requests.RequestException as e:
        return {"found": False, "drug_name": drug_name, "error": str(e)}
