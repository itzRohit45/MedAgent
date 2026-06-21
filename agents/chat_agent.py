"""
Chat Agent — Natural Language Conversational Interface
Uses ReAct (Reasoning + Acting) pattern: the AI reasons about the user's question,
decides which tools (database queries) to call, retrieves data, then formulates
a natural language answer grounded in real patient data.
"""

import json
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google import genai
import database as db
from tools import openfda_tools

CHAT_SYSTEM_PROMPT = """You are MedAgent AI, a friendly and knowledgeable medication management assistant.
You help caregivers and patients understand their medication schedules, adherence, and health data.

You have access to the following tools to query real patient data. You MUST use these tools 
to answer questions — never make up data or guess.

Available Tools (call by returning a JSON tool_call):
1. "get_medications" — Get all active medications for the patient
2. "get_schedule" — Get today's dose schedule (what's due, taken, missed)
3. "get_adherence" — Get adherence statistics (taken/missed/skipped counts and %)
4. "get_dose_logs" — Get recent dose history (last N days)
5. "get_interactions" — Get known drug interaction flags
6. "get_patient_info" — Get patient details (name, age, caregiver)
7. "get_symptom_logs" — Get symptoms logged by the patient recently
8. "get_drug_info" — Get FDA educational information about a specific drug (requires "drug_name" argument)

When you need data to answer a question, respond with:
{"tool_calls": [{"tool": "tool_name", "reason": "why you need this", "args": {"drug_name": "metformin"}}]}

When you have enough data to answer, respond with:
{"answer": "your friendly, helpful response here"}

Rules:
- Always be warm, supportive, and non-clinical in tone
- Use simple language a family member would understand
- Never diagnose, prescribe, or suggest changing medications
- If asked about drug safety, always add "Please consult your doctor for medical advice"
- Include relevant numbers and specifics from the data
- Keep responses concise (under 100 words for simple questions)
- Use emoji sparingly for warmth (1-2 per response max)

Return ONLY valid JSON. No markdown, no code fences."""


def _execute_tool(tool_name: str, patient_id: int, args: dict = None) -> dict:
    """Execute a tool call and return the data."""
    if args is None:
        args = {}
    try:
        if tool_name == "get_medications":
            meds = db.get_patient_medications(patient_id)
            return {"medications": [{"name": m["drug_name"], "dose": m["dose"], 
                     "frequency": m["frequency"], "is_critical": bool(m["is_critical"]),
                     "times": m["times"]} for m in meds]}
        
        elif tool_name == "get_schedule":
            schedule = db.get_todays_schedule(patient_id)
            return {"schedule": [{"drug": s["drug_name"], "dose": s["dose"],
                     "time": s["scheduled_time"], "status": s["status"]} for s in schedule]}
        
        elif tool_name == "get_adherence":
            return db.get_adherence_stats(patient_id, days=7)
        
        elif tool_name == "get_dose_logs":
            logs = db.get_dose_logs(patient_id, days=7)
            return {"logs": [{"drug": l["medication_name"], "action": l["action"],
                     "time": l["timestamp"]} for l in logs]}
        
        elif tool_name == "get_interactions":
            flags = db.get_interaction_flags(patient_id)
            return {"interactions": [{"drugs": f"{f['drug_a']} + {f['drug_b']}",
                     "severity": f["severity"], "note": f["note"]} for f in flags]}
        
        elif tool_name == "get_patient_info":
            patient = db.get_patient(patient_id)
            if patient:
                return {"name": patient["name"], "age": patient.get("age"),
                        "caregiver": patient.get("caregiver_name")}
            return {"error": "Patient not found"}
        
        elif tool_name == "get_symptom_logs":
            logs = db.get_symptom_logs(patient_id, days=14)
            return {"symptoms": [{"symptom": l["symptom"], "severity": l["severity"], "time": l["timestamp"]} for l in logs]}
            
        elif tool_name == "get_drug_info":
            drug_name = args.get("drug_name")
            if not drug_name:
                return {"error": "Missing 'drug_name' argument"}
            return openfda_tools.get_drug_education_info(drug_name)
        
        else:
            return {"error": f"Unknown tool: {tool_name}"}
    except Exception as e:
        return {"error": str(e)}


def chat_with_patient(patient_id: int, message: str, history: list, api_key: str) -> dict:
    """
    Process a chat message using ReAct pattern.
    The AI reasons about the question, calls tools to get data, then answers.
    """
    client = genai.Client(api_key=api_key)
    
    # Build conversation context
    patient = db.get_patient(patient_id)
    patient_name = patient["name"] if patient else f"Patient #{patient_id}"
    
    context = f"You are assisting with patient: {patient_name} (ID: {patient_id})\n"
    context += f"Current date/time: {datetime.now().strftime('%A, %B %d, %Y at %I:%M %p')}\n\n"
    
    # Build messages from history
    messages = [{"role": "user", "parts": [{"text": CHAT_SYSTEM_PROMPT + "\n\n" + context}]}]
    
    for h in history[-6:]:  # Keep last 6 messages for context
        role = "user" if h.get("role") == "user" else "model"
        messages.append({"role": role, "parts": [{"text": h.get("content", "")}]})
    
    messages.append({"role": "user", "parts": [{"text": message}]})
    
    tools_used = []
    max_iterations = 3  # Prevent infinite tool-calling loops
    
    for iteration in range(max_iterations):
        try:
            response = client.models.generate_content(
                model="gemini-flash-lite-latest",
                contents=messages,
            )
            
            raw = response.text.strip()
            # Clean markdown fences
            raw = raw.removeprefix('```json').removeprefix('```').removesuffix('```').strip()
            
            result = json.loads(raw)
            
            # Check if AI wants to call tools
            if "tool_calls" in result:
                tool_data = {}
                for tc in result["tool_calls"]:
                    tool_name = tc.get("tool", "")
                    reason = tc.get("reason", "")
                    args = tc.get("args", {})
                    data = _execute_tool(tool_name, patient_id, args)
                    tool_data[tool_name] = data
                    tools_used.append({"tool": tool_name, "reason": reason, "args": args})
                
                # Feed tool results back to AI
                tool_result_msg = f"Tool results:\n{json.dumps(tool_data, indent=2, default=str)}\n\nNow answer the user's question based on this data. Respond with: {{\"answer\": \"your response\"}}"
                messages.append({"role": "model", "parts": [{"text": raw}]})
                messages.append({"role": "user", "parts": [{"text": tool_result_msg}]})
                continue  # Let AI process the tool results
            
            # AI has an answer
            if "answer" in result:
                return {
                    "reply": result["answer"],
                    "tools_used": tools_used
                }
            
            # Fallback: treat entire response as the answer
            return {
                "reply": raw,
                "tools_used": tools_used
            }
            
        except json.JSONDecodeError:
            # If AI didn't return JSON, use the raw text as the answer
            return {
                "reply": response.text.strip(),
                "tools_used": tools_used
            }
        except Exception as e:
            print(f"Chat Agent Error: {e}")
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                return {
                    "reply": "I'm a bit overwhelmed right now! 😅 Please wait a moment and try again.",
                    "tools_used": tools_used,
                    "error": "rate_limit"
                }
            return {
                "reply": "I'm sorry, I encountered an error processing your question. Please try again.",
                "tools_used": tools_used,
                "error": str(e)
            }
    
    # If we exhausted iterations
    return {
        "reply": "I gathered some information but couldn't formulate a complete answer. Could you rephrase your question?",
        "tools_used": tools_used
    }
