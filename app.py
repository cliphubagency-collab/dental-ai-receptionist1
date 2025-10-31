from flask import Flask, request, jsonify
import google.generativeai as genai
import os, json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from datetime import datetime, timedelta

app = Flask(__name__)

# GEMINI
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash")

# GOOGLE CREDENTIALS
creds_json = os.getenv("GOOGLE_CREDENTIALS")
creds = Credentials.from_service_account_info(json.loads(creds_json), scopes=["https://www.googleapis.com/auth/calendar"])
calendar = build("calendar", "v3", credentials=creds)
CALENDAR_ID = os.getenv("CALENDAR_ID")

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
        end = (datetime.fromisoformat(start.replace("Z", "")) + timedelta(minutes=45)).isoformat()
        event = {"summary": f"{service} - {name}", "description": f"Phone: {phone}", "start": {"dateTime": start}, "end": {"dateTime": end}}
        calendar.events().insert(calendarId=CALENDAR_ID, body=event).execute()
        return "Confirmed!"
    except: return "Failed."

@app.route("/tools", methods=["POST"])
def tools():
    data = request.json
    name = data.get("toolName")
    p = data.get("parameters", {})
    if name == "check_slots":
        slots = check_slots(p["date"])
        return jsonify({"success": True, "result": f"Available: {', '.join(slots)}"})
    if name == "book_appointment":
        msg = book_appointment(p["name"], p["phone"], p["date"], p["time"], p["service"])
        return jsonify({"success": True, "result": msg})
    return jsonify({"success": False})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
