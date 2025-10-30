from flask import Flask, request, jsonify
import google.generativeai as genai
import os
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from datetime import datetime, timedelta

app = Flask(__name__)

# === CONFIG ===
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash")

creds = Credentials.from_service_account_file(
    "credentials.json",
    scopes=["https://www.googleapis.com/auth/calendar"]
)
calendar = build("calendar", "v3", credentials=creds)
CALENDAR_ID = os.getenv("CALENDAR_ID")

with open("knowledge_base.txt", "r", encoding="utf-8") as f:
    KB = f.read()

SYSTEM_PROMPT = f"""
You are Emma, a friendly AI receptionist at BrightSmile Dental.
Use this knowledge:
{KB}

If someone wants to book:
1. Ask for name, phone, service, preferred day
2. Check availability with check_slots()
3. Suggest 1-2 free times
4. Book with book_appointment()

Speak naturally in American English.
"""

# === FUNKCIJE ===
def check_slots(preferred_day):
    try:
        now = datetime.now()
        start = now
        end = now + timedelta(days=14)
        events = calendar.events().list(
            calendarId=CALENDAR_ID,
            timeMin=start.isoformat() + "Z",
            timeMax=end.isoformat() + "Z",
            singleEvents=True,
            orderBy="startTime"
        ).execute()
        booked = [e['start']['dateTime'][11:16] for e in events.get('items', []) if 'dateTime' in e['start']]
        all_slots = ["09:00", "10:00", "11:00", "14:00", "15:00", "16:00"]
        free = [s for s in all_slots if s not in booked]
        return free[:3] if free else ["No slots"]
    except:
        return ["10:00", "14:00"]

def book_appointment(name, phone, date, time, service):
    try:
        start_dt = f"{date}T{time}:00"
        end_dt = (datetime.fromisoformat(start_dt) + timedelta(minutes=45)).isoformat()
        event = {
            "summary": f"{service} - {name}",
            "description": f"Phone: {phone}",
            "start": {"dateTime": start_dt},
            "end": {"dateTime": end_dt}
        }
        calendar.events().insert(calendarId=CALENDAR_ID, body=event).execute()
        return "Your appointment is confirmed!"
    except:
        return "Sorry, booking failed."

# === VAPI WEBHOOK ===
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    message = data.get("message", {}).get("content", "").lower()

    if "book" in message or "appointment" in message:
        slots = check_slots("any")
        reply = f"We have availability at: {', '.join(slots)}. Which works for you?"
    elif "10" in message or "2" in message:
        reply = book_appointment("John Doe", "+1234567890", "2025-11-05", "10:00", "Cleaning")
    else:
        response = model.generate_content([SYSTEM_PROMPT, f"User: {message}"])
        reply = response.text

    return jsonify({"reply": reply})

@app.route("/tools", methods=["POST"])
def tools():
    data = request.json
    tool_name = data.get("toolName")  # Vapi šalje ovo
    parameters = data.get("parameters", {})

    if tool_name == "check_slots":
        date = parameters.get("date", "2025-11-05")  # default ako nema
        slots = check_slots(date)  # tvoja postojeća funkcija
        return jsonify({
            "success": True,
            "result": f"Available times: {', '.join(slots)}"
        })
    elif tool_name == "book_appointment":
        result = book_appointment(
            parameters["name"],
            parameters["phone"],
            parameters["date"],
            parameters["time"],
            parameters["service"]
        )
        return jsonify({
            "success": True,
            "result": result
        })
    else:
        return jsonify({"success": False, "error": "Unknown tool"}), 400

if __name__ == "__main__":

    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
