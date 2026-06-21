"""
Notification Tools
Handles sending reminders and alerts to patients and caregivers.
Currently outputs to console — easily extensible to email/SMS.
"""

import sys
import os
import smtplib

from email.message import EmailMessage
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import database as db

# In-memory notification log
_notification_log = []

def get_notification_log():
    return _notification_log.copy()

def clear_notification_log():
    _notification_log.clear()

def _send_email(to_email: str, subject: str, body: str) -> bool:
    """Send an email using SMTP."""
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = os.getenv("SMTP_PORT", "587")
    smtp_user = os.getenv("SMTP_USERNAME")
    smtp_pass = os.getenv("SMTP_PASSWORD")
    
    if not all([smtp_server, smtp_user, smtp_pass]):
        return False
        
    try:
        msg = EmailMessage()
        msg.set_content(body)
        msg["Subject"] = subject
        msg["From"] = smtp_user
        msg["To"] = to_email
        
        with smtplib.SMTP(smtp_server, int(smtp_port)) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Email failed: {e}")
        return False


def send_patient_reminder(patient_id: int, message: str) -> dict:
    """Send a medication reminder to the patient via SMS, WhatsApp, and Email, or fallback to console."""
    patient = db.get_patient(patient_id)
    patient_name = patient["name"] if patient else f"Patient #{patient_id}"
    
    email = patient.get("caregiver_email", "") if patient else ""
    mobile = patient.get("caregiver_mobile", "") if patient else ""
    
    channels_sent = []
    
    # Attempt Email
    if email:
        sent = _send_email(email, f"MedAgent Reminder: {patient_name}", message)
        if sent:
            channels_sent.append("email")
        else:
            print(f"\n📧 EMAIL REMINDER → {email}: {message}")
            channels_sent.append("email_simulated")
            
    # Console fallback for mobile if no email provided
    if mobile and not email:
        print(f"\n📱 SMS/WHATSAPP REMINDER (Simulated) → {mobile}: {message}")
        channels_sent.append("mobile_simulated")
            
    if not channels_sent:
        print(f"\n📱 CONSOLE REMINDER → {patient_name}: {message}")
        channels_sent.append("console")

    notification = {
        "type": "patient_reminder",
        "recipient": patient_name,
        "patient_id": patient_id,
        "message": message,
        "timestamp": str(datetime.now()),
        "channel": ",".join(channels_sent),
    }

    _notification_log.append(notification)
    return {
        "sent": True,
        "recipient": patient_name,
        "message": message,
        "timestamp": notification["timestamp"],
        "channel": notification["channel"]
    }

def send_caregiver_alert(patient_id: int, message: str, urgency: str = "medium") -> dict:
    """Send an alert to the caregiver via Email/SMS or fallback to console."""
    patient = db.get_patient(patient_id)
    caregiver_name = patient.get("caregiver_name", "Caregiver") if patient else "Caregiver"
    
    email = patient.get("caregiver_email", "") if patient else ""
    mobile = patient.get("caregiver_mobile", "") if patient else ""
    patient_name = patient["name"] if patient else f"Patient #{patient_id}"

    urgency_emoji = {"low": "ℹ️", "medium": "⚠️", "high": "🚨"}.get(urgency, "⚠️")
    
    channels_sent = []
    
    body = f"Caregiver Alert regarding {patient_name}:\n\n{message}"
    
    if email:
        if _send_email(email, f"MedAgent Alert: {patient_name}", body):
            channels_sent.append("email")
            
    if mobile and not email:
        print(f"\n📱 SMS/WHATSAPP ALERT (Simulated) → {mobile}: {message}")
        channels_sent.append("mobile_simulated")
            
    if not channels_sent:
        print(f"\n{urgency_emoji} CAREGIVER ALERT → {caregiver_name} (Email: {email}, Mobile: {mobile}):")
        print(f"   Re: {patient_name}")
        print(f"   {message}\n")
        channels_sent.append("console")
        
    channel_str = ",".join(channels_sent)

    notification = {
        "type": "caregiver_alert",
        "recipient": caregiver_name,
        "recipient_email": email,
        "recipient_mobile": mobile,
        "patient_id": patient_id,
        "patient_name": patient_name,
        "message": message,
        "urgency": urgency,
        "timestamp": str(datetime.now()),
        "channel": channel_str,
    }

    _notification_log.append(notification)
    return {
        "sent": True,
        "recipient": caregiver_name,
        "email": email,
        "mobile": mobile,
        "patient_name": patient_name,
        "urgency": urgency,
        "message": message,
        "timestamp": notification["timestamp"],
        "channel": channel_str
    }
