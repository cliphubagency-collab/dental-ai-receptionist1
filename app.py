from flask import Flask, request, jsonify
import os
import json
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

app = Flask(__name__)

# GOOGLE CALENDAR
creds_json = os.getenv("GOOGLE_CREDENTIALS")
if not creds_json:
    raise ValueError("GOOGLE_CREDENTIALS missing!")
creds = Credentials.from_service_account_info(json.loads(creds_json), scopes=["https://www.googleapis.com/auth/calendar"])
calendar = build("calendar", "v3", credentials=creds)
CALENDAR_ID = os.getenv("CALENDAR_ID")

def check_slots(date):
    try:
        start = f"{date}T00:00:00Z"
        end = f"{date}T23:59:59Z"
        events = calendar.events().list(calendarId=CALENDAR_ID, timeMin=start, timeMax=end, singleEvents=True, orderBy="startTime").execute()
        booked = [e['start']['dateTime'][11:16] for e in events.get('items', []) if 'dateTime' in e['start']]
        all_slots = ["09:00", "10:00", "11:00", "14:00", "15:00", "16:00"]
        free = [s for s in all_slots if s not in booked]
        return free[:3] if free else ["10:00", "14:00"]
    except Exception as e:
        print(f"CHECK ERROR: {e}")
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
        print(f"BOOKED: {name} on {date} at {time}")
        return "Your appointment is confirmed!"
    except Exception as e:
        print(f"BOOK ERROR: {e}")
        return "Booking failed."

@app.route("/tools", methods=["POST"])
def tools():
    data = request.json
    tool_calls = data.get("toolCalls", [])
    results = []

    for call in tool_calls:
        tool_id = call["id"]
        func_name = call["function"]["name"]
        args = json.loads(call["function"]["arguments"])

        if func_name == "check_slots":
            slots = check_slots(args.get("date", "2025-11-04"))
            result = f"Available times: {', '.join(slots)}. Which one?"
        elif func_name == "book_appointment":
            result = book_appointment(
                args.get("name", "User"),
                args.get("phone", "+123"),
                args.get("date"),
                args.get("time"),
                args.get("service", "Cleaning")
            )
        else:
            result = "Unknown tool."

        results.append({
            "toolCallId": tool_id,
            "result": result
        })

    return jsonify({"results": results})

@app.route("/")
def home():
    return "Bot LIVE!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
