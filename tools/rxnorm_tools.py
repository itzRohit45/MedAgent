"""
RxNorm API Tools
Resolves drug names to RxCUI identifiers and checks drug-drug interactions
via the free NLM RxNav REST API.
"""

import requests
from typing import Optional

RXNORM_BASE = "https://rxnav.nlm.nih.gov/REST"


def resolve_drug_to_rxcui(drug_name: str) -> dict:
    """
    Look up a drug name and return its RxNorm Concept Unique Identifier (RxCUI).

    Args:
        drug_name: The drug name to look up (generic or brand), e.g. "metformin"

    Returns:
        A dictionary with the rxcui and matched name, or an error message.
    """
    try:
        url = f"{RXNORM_BASE}/rxcui.json"
        resp = requests.get(url, params={"name": drug_name}, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        id_group = data.get("idGroup", {})
        rxnorm_ids = id_group.get("rxnormId", [])

        if rxnorm_ids:
            return {
                "found": True,
                "drug_name": drug_name,
                "rxcui": rxnorm_ids[0],
            }

        # Try approximate match
        url2 = f"{RXNORM_BASE}/approximateTerm.json"
        resp2 = requests.get(url2, params={"term": drug_name, "maxEntries": 1}, timeout=10)
        resp2.raise_for_status()
        data2 = resp2.json()

        candidates = data2.get("approximateGroup", {}).get("candidate", [])
        if candidates:
            return {
                "found": True,
                "drug_name": drug_name,
                "rxcui": candidates[0].get("rxcui", ""),
                "matched_name": candidates[0].get("name", ""),
                "note": "approximate match",
            }

        return {"found": False, "drug_name": drug_name, "error": "No RxCUI found"}

    except requests.RequestException as e:
        return {"found": False, "drug_name": drug_name, "error": str(e)}


def get_drug_properties(rxcui: str) -> dict:
    """
    Get properties for a drug given its RxCUI.

    Args:
        rxcui: The RxNorm Concept Unique Identifier.

    Returns:
        A dictionary with drug properties including name, synonym, and TTY.
    """
    try:
        url = f"{RXNORM_BASE}/rxcui/{rxcui}/properties.json"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        props = data.get("properties", {})
        return {
            "rxcui": rxcui,
            "name": props.get("name", ""),
            "synonym": props.get("synonym", ""),
            "tty": props.get("tty", ""),
        }
    except requests.RequestException as e:
        return {"rxcui": rxcui, "error": str(e)}


def check_drug_interactions(rxcui_list: list) -> dict:
    """
    Check for drug-drug interactions among a list of RxCUIs using the
    NLM Interaction API. Falls back gracefully if the endpoint is
    unavailable (the NLM interaction service was retired in 2025;
    OpenFDA labels are now the primary interaction data source).

    Args:
        rxcui_list: List of RxCUI strings to check interactions between,
                    e.g. ["207106", "656659"]

    Returns:
        A dictionary containing a list of interaction flags with severity
        and descriptions, or an empty list if no interactions found.
    """
    if len(rxcui_list) < 2:
        return {"interactions": [], "note": "Need at least 2 drugs to check interactions"}

    try:
        joined = "+".join(str(r) for r in rxcui_list)
        url = f"{RXNORM_BASE}/interaction/list.json"
        resp = requests.get(url, params={"rxcuis": joined}, timeout=15)

        # Handle retired endpoint gracefully
        if resp.status_code == 404:
            return {
                "interactions": [],
                "count": 0,
                "rxcuis_checked": rxcui_list,
                "note": "RxNorm interaction endpoint unavailable. Using OpenFDA labels for interaction data.",
            }

        resp.raise_for_status()
        data = resp.json()

        interactions = []
        interaction_groups = data.get("fullInteractionTypeGroup", [])

        for group in interaction_groups:
            source = group.get("sourceName", "unknown")
            for interaction_type in group.get("fullInteractionType", []):
                for pair in interaction_type.get("interactionPair", []):
                    severity = pair.get("severity", "N/A")
                    description = pair.get("description", "")

                    # Extract drug names from the pair
                    concepts = pair.get("interactionConcept", [])
                    drug_names = []
                    for concept in concepts:
                        min_concept = concept.get("minConceptItem", {})
                        drug_names.append(min_concept.get("name", "unknown"))

                    interactions.append({
                        "drugs": drug_names,
                        "severity": severity.lower() if severity != "N/A" else "moderate",
                        "description": description,
                        "source": source,
                    })

        return {
            "interactions": interactions,
            "count": len(interactions),
            "rxcuis_checked": rxcui_list,
        }

    except (requests.RequestException, ValueError) as e:
        return {
            "interactions": [],
            "count": 0,
            "rxcuis_checked": rxcui_list,
            "note": f"RxNorm interaction check unavailable ({e}). Using OpenFDA labels instead.",
        }


def resolve_and_check_interactions(drug_names: list) -> dict:
    """
    End-to-end: resolve a list of drug names to RxCUIs, then check interactions.

    Args:
        drug_names: List of drug names (generic or brand) to check.

    Returns:
        A dictionary with resolved drugs and any interactions found.
    """
    resolved = []
    rxcui_list = []
    errors = []

    for name in drug_names:
        result = resolve_drug_to_rxcui(name)
        resolved.append(result)
        if result.get("found") and result.get("rxcui"):
            rxcui_list.append(result["rxcui"])
        else:
            errors.append(f"Could not resolve: {name}")

    interaction_result = {"interactions": [], "count": 0}
    if len(rxcui_list) >= 2:
        interaction_result = check_drug_interactions(rxcui_list)

    return {
        "resolved_drugs": resolved,
        "interaction_check": interaction_result,
        "unresolved_errors": errors,
    }
