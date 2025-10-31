from flask import Flask, request, jsonify
import os
import json
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

app = Flask(__name__)

# === GOOGLE CALENDAR ===
creds_json = os.getenv("GOOGLE_CREDENTIALS")
creds = Credentials.from_service_account_info(json.loads(creds_json), scopes=["https://www.googleapis.com/auth/calendar"])
calendar = build("calendar", "v3", credentials=creds)
CALENDAR_ID = os.getenv("CALENDAR_ID")

# === SLOTS ===
def check_slots(date):
    try:
        events = calendar.events().list(calendarId=CALENDAR_ID, timeMin=f"{date}T00:00:00Z", timeMax=f"{date}T23:59:59Z").execute()
        booked = [e['start']['dateTime'][11:16] for e in events.get('items', []) if 'dateTime' in e['start']]
        all_slots = ["09:00", "10:00", "11:00", "14:00", "15:00", "16:00"]
        return [s for s in all_slots if s not in booked][:3]
    except: return ["10:00", "14:00"]

def book_appointment(name, phone, date, time, service):
    try:
        start = f"{date}T{time}:00"
        end = (datetime.fromisoformat(start) + timedelta(minutes=45)).isoformat()
        event = {"summary": f"{service} - {name}", "description": f"Phone: {phone}", "start": {"dateTime": start}, "end": {"dateTime": end}}
        calendar.events().insert(calendarId=CALENDAR_ID, body=event).execute()
        return "Confirmed!"
    except: return "Failed."

# === CUSTOM SERVER WEBHOOK ===
@app.route("/tools", methods=["POST"])
def webhook():
    data = request.json
    message = data.get("message", {}).get("content", "").lower()

    # LOGIKA
    if "book" in message or "cleaning" in message:
        if "name" not in message and "phone" not in message:
            return jsonify({"reply": "Sure! What's your name and phone?"})
        if "date" not in message:
            return jsonify({"reply": "What date? (e.g. November 4th)"})
        if "time" not in message:
            slots = check_slots("2025-11-04")
            return jsonify({"reply": f"Available: {', '.join(slots)}. Which time?"})
        else:
            # Zakazi
            result = book_appointment("John", "+123", "2025-11-04", "10:00", "Cleaning")
            return jsonify({"reply": f"{result} See you then!"})

    return jsonify({"reply": "Hello! I can book dental appointments."})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
