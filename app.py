import streamlit as st
import pandas as pd
import datetime
import time
from datetime import timedelta, timezone, datetime
import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


SCOPES = ["https://www.googleapis.com/auth/calendar"]

def get_event():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open("token.json", "w") as token:
            token.write(creds.to_json())

    try:
        service = build("calendar", "v3", credentials=creds)

        now = datetime.now().isoformat() + "Z"
        events_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=now,
                maxResults=10,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        events = events_result.get("items", [])

        if not events:
            print("No upcoming events found.")
            return []
        book_times = []
        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date"))
            book_times.append(start)
            # print(start)
        return book_times

    except HttpError as error:
        print(f"An error occurred: {error}")
        return []

def create_event(name, email, selected_time):
    """Creates a new event on the user's primary calendar."""
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    try:
        service = build("calendar", "v3", credentials=creds)

        # Prepare start and end times
        start_time = {
            "dateTime": selected_time,
            "timeZone": "Asia/Karachi"  # Adjust the time zone as needed
        }
        end_time = {
            "dateTime": (datetime.strptime(selected_time, "%Y-%m-%dT%H:%M:%S") + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S"),
            "timeZone": "Asia/Karachi"  # Adjust the time zone as needed
        }

        # Prepare event body
        event = {
            "summary": name,
            "start": start_time,
            "end": end_time,
            "attendees": [{"email": email}],
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "email", "minutes": 24 * 60},
                    {"method": "popup", "minutes": 10},
                ],
            },
        }

        # Call the Calendar API to insert the event
        event = service.events().insert(calendarId="primary", sendNotifications=True, body=event).execute()
        start = event["start"].get("dateTime", event["start"].get("date"))
        # print(start, event["summary"])
        st.success(f"Event '{event['summary']}' successfully created at {start}.")
        time.sleep(3)

    except HttpError as error:
        print(f"An error occurred: {error}")


def generate_time_list(start_date, days, start_hour, end_hour, time_zone):
    # Define time zone
    tz = timezone(timedelta(hours=5))  # +05:00 timezone offset

    # Parse start date and time
    start_datetime = datetime.strptime(
        f"{start_date}T{start_hour:02d}:00:00", "%Y-%m-%dT%H:%M:%S"
    )

    # Create list of times
    time_list = []
    for day in range(days):
        current_date = start_datetime + timedelta(days=day)
        for hour in range(start_hour, end_hour):
            dt = current_date.replace(hour=hour)
            dt_tz = dt.replace(tzinfo=tz)
            time_list.append(dt_tz)

    return time_list

def main():
    st.title("Appointment Booking")

    st.write("Welcome!")

    st.write('Fill the form to book an appointment')
    
    name = st.text_input("Enter your name", key="name")
    email = st.text_input("Enter your email address", key="email")
    min_date = datetime.now().date()
    days = 7
    start_hour = 9
    end_hour = 15
    time_zone = "Asia/Karachi"

    start_date = st.date_input("Select start date", min_value=min_date, max_value=min_date + timedelta(days=days - 1))

    time_left = get_event()
    time_list = generate_time_list(start_date, days, start_hour, end_hour, time_zone)

    time_left = [datetime.strptime(time, "%Y-%m-%dT%H:%M:%S%z") for time in time_left]
       
    current_time = datetime.now(time_list[0].tzinfo)
    free_slots = [time for time in time_list if time > current_time and time not in time_left]

    selected_date_slots = [slot for slot in free_slots if slot.date() == start_date]
    st.write("Select Time Slots")



    if selected_date_slots:
        col1, col2, col3 = st.columns(3)
        for i, slot in enumerate(selected_date_slots):
            if i % 3 == 0:
                button_container = col1
            elif i % 3 == 1:
                button_container = col2
            else:
                button_container = col3
                    
            selected = button_container.button(slot.strftime("%Y-%m-%d %I:%M %p"))
            if selected:
                selected_time = slot.strftime("%Y-%m-%dT%H:%M:%S")
                st.write("You selected:", slot.strftime("%Y-%m-%d %I:%M %p"))
                if name and email:
                    create_event(name, email, selected_time)
                    st.success("Event created successfully! We'll see you then.")
                
    else:
        st.write("No free slots available for the selected date.")


if __name__ == "__main__":
    main()