import os
import sys
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import threading
import time

# Add parent dir to path so we can import our existing modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database as db
from agents.orchestrator import MedAgentOrchestrator

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
API_KEY = os.getenv("GOOGLE_API_KEY")

if not API_KEY:
    print("WARNING: GOOGLE_API_KEY not found in .env file. AI features will be disabled.", file=sys.stderr)

# Initialize Orchestrator
orchestrator = MedAgentOrchestrator(API_KEY) if API_KEY else None

# Initialize Database
db.init_db()

app = FastAPI(title="MedAgent API", description="Backend API for MedAgent")

# Allow CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development; restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def background_monitor_loop():
    """Background thread to trigger monitor agent every 60 seconds."""
    while True:
        time.sleep(60)
        if orchestrator:
            try:
                patients = db.get_all_patients()
                for p in patients:
                    orchestrator.trigger_monitor(p['id'])
                    # Also check refill status proactively
                    try:
                        orchestrator.check_refills(p['id'])
                    except Exception:
                        pass
            except Exception as e:
                print(f"Background Monitor Error: {e}", file=sys.stderr)

@app.on_event("startup")
def startup_event():
    # Start the automated monitor thread
    thread = threading.Thread(target=background_monitor_loop, daemon=True)
    thread.start()

# ── Models ──────────────────────────────────────────────────────────────

class PatientCreate(BaseModel):
    name: str
    age: int
    caregiver_name: str
    caregiver_email: str
    caregiver_mobile: str

class TextPrescription(BaseModel):
    patient_id: int
    text: str

class DoseConfirmation(BaseModel):
    action: str  # "taken", "skipped"

class UpdateTimes(BaseModel):
    patient_id: int
    times: List[str]

# ── Endpoints ───────────────────────────────────────────────────────────

@app.get("/api/patients")
def get_patients():
    return db.get_all_patients()

@app.get("/api/patients/{patient_id}")
def get_patient(patient_id: int):
    patient = db.get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient

@app.post("/api/patients")
def add_patient(patient: PatientCreate):
    patient_id = db.add_patient(
        patient.name, 
        patient.age, 
        patient.caregiver_name, 
        patient.caregiver_email,
        patient.caregiver_mobile
    )
    return {"id": patient_id}

@app.delete("/api/patients/{patient_id}")
def delete_patient(patient_id: int):
    # Verify patient exists
    p = db.get_patient(patient_id)
    if not p:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    db.delete_patient(patient_id)
    return {"status": "success", "message": f"Patient {patient_id} deleted"}

@app.get("/api/medications/{patient_id}")
def get_medications(patient_id: int):
    return db.get_patient_medications(patient_id)

@app.delete("/api/medications/{med_id}")
def delete_medication(med_id: int):
    db.deactivate_medication(med_id)
    return {"status": "success"}

@app.put("/api/medications/{med_id}/times")
def update_medication_times(med_id: int, req: UpdateTimes):
    db.update_medication_times(med_id, req.patient_id, req.times)
    return {"status": "success"}

@app.get("/api/schedule/{patient_id}")
def get_schedule(patient_id: int):
    # Ensure schedule is generated for today before returning
    db.generate_daily_schedule(patient_id)
    return db.get_todays_schedule(patient_id)

@app.post("/api/schedule/{dose_id}/confirm")
def confirm_dose(dose_id: int, conf: DoseConfirmation):
    if not orchestrator:
        raise HTTPException(status_code=500, detail="Orchestrator not initialized")
    return orchestrator.confirm_dose(dose_id, conf.action)

@app.post("/api/intake/text")
def process_prescription_text(req: TextPrescription):
    if not orchestrator:
        raise HTTPException(status_code=500, detail="AI Orchestrator not initialized (Check API Key)")
    return orchestrator.process_prescription_text(req.patient_id, req.text)

@app.post("/api/intake/image")
async def process_prescription_image(patient_id: int = Form(...), file: UploadFile = File(...)):
    if not orchestrator:
        raise HTTPException(status_code=500, detail="AI Orchestrator not initialized (Check API Key)")
    image_bytes = await file.read()
    return orchestrator.process_prescription_image(patient_id, image_bytes, file.content_type)

from datetime import datetime, timedelta

_api_cache = {}

def get_cached(key: str, ttl_seconds: int = 120):
    if key in _api_cache:
        entry = _api_cache[key]
        if datetime.now() - entry["time"] < timedelta(seconds=ttl_seconds):
            return entry["data"]
    return None

def set_cache(key: str, data: dict):
    _api_cache[key] = {"time": datetime.now(), "data": data}

@app.get("/api/interactions/{patient_id}")
def check_interactions(patient_id: int):
    if not orchestrator:
        raise HTTPException(status_code=500, detail="AI Orchestrator not initialized")
    cached = get_cached(f"interactions_{patient_id}", 300)
    if cached: return cached
    res = orchestrator.check_interactions(patient_id)
    set_cache(f"interactions_{patient_id}", res)
    return res

@app.post("/api/scheduler/{patient_id}")
def trigger_scheduler(patient_id: int):
    if not orchestrator:
        raise HTTPException(status_code=500, detail="AI Orchestrator not initialized")
    return orchestrator.trigger_scheduler(patient_id)

@app.post("/api/monitor/{patient_id}")
def trigger_monitor(patient_id: int):
    if not orchestrator:
        raise HTTPException(status_code=500, detail="AI Orchestrator not initialized")
    return orchestrator.trigger_monitor(patient_id)

@app.get("/api/report/{patient_id}")
def get_report(patient_id: int, type: str = "daily"):
    if not orchestrator:
        raise HTTPException(status_code=500, detail="AI Orchestrator not initialized")
        
    cache_key = f"report_{patient_id}_{type}"
    cached = get_cached(cache_key, 120)
    if cached: return cached
    
    if type.lower() == "weekly":
        res = orchestrator.get_weekly_report(patient_id)
    else:
        res = orchestrator.get_daily_report(patient_id)
        
    set_cache(cache_key, res)
    return res

@app.get("/api/adherence/{patient_id}")
def get_adherence(patient_id: int, days: int = 7):
    return db.get_adherence_stats(patient_id, days)

@app.get("/api/logs/{patient_id}")
def get_logs(patient_id: int, days: int = 7):
    return db.get_dose_logs(patient_id, days)

# ── Chat Agent ──────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    patient_id: int
    message: str
    history: List[dict] = []

@app.post("/api/chat")
def chat(req: ChatMessage):
    if not orchestrator:
        raise HTTPException(status_code=500, detail="AI Orchestrator not initialized")
    return orchestrator.chat(req.patient_id, req.message, req.history)

# ── Analytics Agent ─────────────────────────────────────────────────────

@app.get("/api/analytics/{patient_id}")
def get_analytics(patient_id: int):
    if not orchestrator:
        raise HTTPException(status_code=500, detail="AI Orchestrator not initialized")
    cached = get_cached(f"analytics_{patient_id}", 120)
    if cached: return cached
    res = orchestrator.get_analytics(patient_id)
    set_cache(f"analytics_{patient_id}", res)
    return res

@app.get("/api/adherence/{patient_id}/trend")
def get_adherence_trend(patient_id: int, days: int = 14):
    return db.get_adherence_trend(patient_id, days)

@app.get("/api/adherence/{patient_id}/breakdown")
def get_adherence_breakdown(patient_id: int, days: int = 14):
    return db.get_medication_adherence_breakdown(patient_id, days)

# ── Refill Prediction ───────────────────────────────────────────────────

@app.get("/api/refills/{patient_id}")
def get_refills(patient_id: int):
    return db.get_refill_status(patient_id)

class SetPillCount(BaseModel):
    count: int

@app.put("/api/medications/{med_id}/pills")
def set_pills(med_id: int, req: SetPillCount):
    db.set_pill_count(med_id, req.count)
    return {"status": "success"}

# ── Symptom / Side Effect Monitoring ────────────────────────────────────

class SymptomLog(BaseModel):
    symptom: str
    severity: str = "mild"

@app.post("/api/symptoms/{patient_id}")
def log_symptom(patient_id: int, req: SymptomLog):
    log_id = db.add_symptom_log(patient_id, req.symptom, req.severity)
    return {"id": log_id, "status": "logged"}

@app.get("/api/symptoms/{patient_id}")
def get_symptoms(patient_id: int, days: int = 30):
    return db.get_symptom_logs(patient_id, days)

@app.get("/api/symptoms/{patient_id}/analyze")
def analyze_symptoms_endpoint(patient_id: int):
    if not orchestrator:
        raise HTTPException(status_code=500, detail="AI Orchestrator not initialized")
    cached = get_cached(f"symptoms_analysis_{patient_id}", 120)
    if cached: return cached
    res = orchestrator.analyze_symptoms(patient_id)
    set_cache(f"symptoms_analysis_{patient_id}", res)
    return res

# ── Drug Education (RAG) ───────────────────────────────────────────────

@app.get("/api/education/{medication_id}")
def get_education(medication_id: int):
    if not orchestrator:
        raise HTTPException(status_code=500, detail="AI Orchestrator not initialized")
    cached = get_cached(f"education_{medication_id}", 600)
    if cached: return cached
    res = orchestrator.get_drug_education(medication_id)
    set_cache(f"education_{medication_id}", res)
    return res

# ── Schedule Optimization ──────────────────────────────────────────────

@app.get("/api/optimize/{patient_id}")
def get_optimization(patient_id: int):
    if not orchestrator:
        raise HTTPException(status_code=500, detail="AI Orchestrator not initialized")
    cached = get_cached(f"optimize_{patient_id}", 120)
    if cached: return cached
    res = orchestrator.get_optimization(patient_id)
    set_cache(f"optimize_{patient_id}", res)
    return res

# ── Risk Dashboard ─────────────────────────────────────────────────────

@app.get("/api/dashboard/overview")
def dashboard_overview():
    from agents.risk_agent import get_all_patient_risks
    return get_all_patient_risks()

@app.get("/api/risk/{patient_id}")
def get_risk(patient_id: int):
    from agents.risk_agent import calculate_risk_score
    return calculate_risk_score(patient_id)
