from flask import Flask, request, jsonify
import os
import json
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

app = Flask(__name__)

# GOOGLE CALENDAR
creds = Credentials.from_service_account_info(
    json.loads(os.getenv("GOOGLE_CREDENTIALS")),
    scopes=["https://www.googleapis.com/auth/calendar"]
)
calendar = build("calendar", "v3", credentials=creds)
CALENDAR_ID = os.getenv("CALENDAR_ID")  # tvoj ID je dobar

# SLOTS
def check_slots(date):
    try:
        events = calendar.events().list(
            calendarId=CALENDAR_ID,
            timeMin=f"{date}T00:00:00Z",
            timeMax=f"{date}T23:59:59Z",
            singleEvents=True,
            orderBy="startTime"
        ).execute()
        booked = [e['start']['dateTime'][11:16] for e in events.get('items', []) if 'dateTime' in e['start']]
        all_slots = ["09:00", "10:00", "11:00", "14:00", "15:00", "16:00"]
        free = [s for s in all_slots if s not in booked]
        return free[:3] if free else ["10:00", "14:00"]
    except Exception as e:
        print("CHECK ERROR:", e)
        return ["10:00", "14:00"]

# BOOK
def book_appointment(name, phone, date, time, service):
    try:
        start = f"{date}T{time}:00"
        end = (datetime.fromisoformat(start) + timedelta(minutes=45)).isoformat()
        event = {
            "summary": f"{service} - {name}",
            "description": f"Phone: {phone}",
            "start": {"dateTime": start},
            "end": {"dateTime": end}
        }
        calendar.events().insert(calendarId=CALENDAR_ID, body=event).execute()
        return "Confirmed! See you then."
    except Exception as e:
        print("BOOK ERROR:", e)
        return "Failed."

# /tools ENDPOINT (ZA VAPI)
@app.route("/tools", methods=["POST"])
def tools():
    data = request.json
    results = []
    for call in data.get("toolCalls", []):
        tool_id = call["id"]
        func = call["function"]["name"]
        args = json.loads(call["function"]["arguments"])

        if func == "check_slots":
            slots = check_slots(args["date"])
            result = f"Available: {', '.join(slots)}. Which time?"
        elif func == "book_appointment":
            result = book_appointment(args["name"], args["phone"], args["date"], args["time"], args["service"])
        else:
            result = "Unknown."

        results.append({"toolCallId": tool_id, "result": result})

    return jsonify({"results": results})

@app.route("/")
def home():
    return "Bot LIVE! Use /tools for Vapi."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
