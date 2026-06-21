import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.intake_agent import parse_prescription_text, parse_prescription_image, enrich_with_rxcui
from agents.interaction_agent import check_patient_interactions
from agents.scheduler_agent import generate_reminders, handle_dose_response
from agents.monitor_agent import check_and_handle_missed_doses
from agents.caregiver_agent import generate_daily_report, generate_escalation_report, generate_weekly_report
from agents.chat_agent import chat_with_patient
from agents.analytics_agent import generate_analytics
from agents.refill_agent import check_refills
from agents.side_effect_agent import analyze_symptoms
from agents.education_agent import generate_drug_education
from agents.optimization_agent import generate_optimization_suggestions
from agents.risk_agent import calculate_risk_score, get_all_patient_risks
import database as db

class MedAgentOrchestrator:
    """
    Central orchestrator for the MedAgent multi-agent system.
    Routes tasks to specialized agents and manages the overall workflow.
    """

    def __init__(self, api_key: str):
        self.api_key = api_key

    def process_prescription_text(self, patient_id: int, text: str) -> dict:
        medications = parse_prescription_text(text, self.api_key)
        medications = enrich_with_rxcui(medications)
        
        saved = []
        needs_confirmation = []
        for med in medications:
            if med.get("needs_confirmation"):
                needs_confirmation.append(med)
                continue
                
            db.add_medication(
                patient_id=patient_id,
                drug_name=med.get("drug") or med.get("generic_name", "Unknown"),
                generic_name=med.get("generic_name"),
                brand_name=med.get("brand_name"),
                dose=med.get("dose", "Unknown"),
                frequency=med.get("frequency", "Unknown"),
                schedule_rules=med.get("schedule_rules"),
                times=med.get("times", []),
                is_critical=1 if med.get("is_critical") else 0,
                rxcui=med.get("rxcui"),
                refills=med.get("refills", 0)
            )
            saved.append(med)
            
        interactions = self.check_interactions(patient_id)
        return {
            "saved": saved,
            "needs_confirmation": needs_confirmation,
            "interactions": interactions
        }

    def process_prescription_image(self, patient_id: int, image_bytes: bytes, mime_type: str) -> dict:
        medications = parse_prescription_image(image_bytes, mime_type, self.api_key)
        medications = enrich_with_rxcui(medications)
        
        saved = []
        needs_confirmation = []
        for med in medications:
            if med.get("needs_confirmation"):
                needs_confirmation.append(med)
                continue
                
            db.add_medication(
                patient_id=patient_id,
                drug_name=med.get("drug") or med.get("generic_name", "Unknown"),
                generic_name=med.get("generic_name"),
                brand_name=med.get("brand_name"),
                dose=med.get("dose", "Unknown"),
                frequency=med.get("frequency", "Unknown"),
                schedule_rules=med.get("schedule_rules"),
                times=med.get("times", []),
                is_critical=1 if med.get("is_critical") else 0,
                rxcui=med.get("rxcui"),
                refills=med.get("refills", 0)
            )
            saved.append(med)
            
        interactions = self.check_interactions(patient_id)
        return {
            "saved": saved,
            "needs_confirmation": needs_confirmation,
            "interactions": interactions
        }

    def check_interactions(self, patient_id: int) -> dict:
        return check_patient_interactions(patient_id, self.api_key)

    def trigger_scheduler(self, patient_id: int) -> dict:
        return generate_reminders(patient_id, self.api_key)

    def confirm_dose(self, dose_id: int, action: str) -> dict:
        return handle_dose_response(dose_id, action)

    def trigger_monitor(self, patient_id: int) -> dict:
        return check_and_handle_missed_doses(patient_id, self.api_key)

    def get_weekly_report(self, patient_id: int) -> dict:
        return generate_weekly_report(patient_id, self.api_key)

    def get_daily_report(self, patient_id: int) -> dict:
        return generate_daily_report(patient_id, self.api_key)

    def chat(self, patient_id: int, message: str, history: list) -> dict:
        return chat_with_patient(patient_id, message, history, self.api_key)

    def get_analytics(self, patient_id: int) -> dict:
        return generate_analytics(patient_id, self.api_key)

    def check_refills(self, patient_id: int) -> dict:
        return check_refills(patient_id, self.api_key)

    def analyze_symptoms(self, patient_id: int) -> dict:
        return analyze_symptoms(patient_id, self.api_key)

    def get_drug_education(self, medication_id: int) -> dict:
        return generate_drug_education(medication_id, self.api_key)

    def get_optimization(self, patient_id: int) -> dict:
        return generate_optimization_suggestions(patient_id, self.api_key)

    def get_risk_score(self, patient_id: int) -> dict:
        return calculate_risk_score(patient_id)

    def get_all_risks(self) -> list:
        return get_all_patient_risks()