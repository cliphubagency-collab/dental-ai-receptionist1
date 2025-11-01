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
        print(f"CHECK_SLOTS CALLED FOR DATE: {date}, CALENDAR_ID: {CALENDAR_ID}")  # Log
        events = calendar.events().list(calendarId=CALENDAR_ID, timeMin=f"{date}T00:00:00Z", timeMax=f"{date}T23:59:59Z", singleEvents=True, orderBy="startTime").execute()
        booked = [e['start']['dateTime'][11:16] for e in events.get('items', []) if 'dateTime' in e['start']]
        all_slots = ["09:00", "10:00", "11:00", "14:00", "15:00", "16:00"]
        free = [s for s in all_slots if s not in booked]
        result = free[:3] if free else ["10:00", "14:00"]
        print(f"CHECK_SLOTS RESULT: {result}")  # Log
        return result
    except Exception as e:
        print(f"CHECK_SLOTS ERROR: {e}")  # Log
        return ["10:00", "14:00"]

def book_appointment(name, phone, date, time, service):
    try:
        print(f"BOOK_APPOINTMENT CALLED: {name}, {date}, {time}")  # Log
        start = f"{date}T{time}:00"
        end = (datetime.fromisoformat(start) + timedelta(minutes=45)).isoformat()
        event = {"summary": f"{service} - {name}", "description": f"Phone: {phone}", "start": {"dateTime": start}, "end": {"dateTime": end}}
        calendar.events().insert(calendarId=CALENDAR_ID, body=event).execute()
        print("BOOK_APPOINTMENT SUCCESS")  # Log
        return "Your appointment is confirmed!"
    except Exception as e:
        print(f"BOOK_APPOINTMENT ERROR: {e}")  # Log
        return "Booking failed."

@app.route("/tools", methods=["POST"])
def tools():
    print("TOOLS CALLED")  # Log
    data = request.json
    tool_calls = data.get("toolCalls", [])
    results = []

    for call in tool_calls:
        tool_id = call["id"]
        func_name = call["function"]["name"]
        args = json.loads(call["function"]["arguments"])
        print(f"TOOL: {func_name}, ARGS: {args}")  # Log

        if func_name == "check_slots":
            result = f"Available times: {', '.join(check_slots(args.get('date', '2025-11-04')))}. Which one?"
        elif func_name == "book_appointment":
            result = book_appointment(args.get('name', 'User'), args.get('phone', '+123'), args.get('date'), args.get('time'), args.get('service', 'Cleaning'))
        else:
            result = "Unknown tool."

        results.append({
            "toolCallId": tool_id,
            "result": result
        })

    print(f"TOOLS RESPONSE: {results}")  # Log
    return jsonify({"results": results})

@app.route("/")
def home():
    return "Dental Bot LIVE!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
