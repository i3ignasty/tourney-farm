import requests
import sqlite3
import re
import time
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from datetime import datetime
import json

# Main Iowa DNR API URLs
events_url = "https://programs.iowadnr.gov/specialevents/Search.aspx/GetEvents"
details_url = "https://programs.iowadnr.gov/specialevents/Search.aspx/GetEventDetail"

headers = {
    "Content-Type": "application/json; charset=UTF-8"
}

# Search date range
start_date = datetime(2026, 1, 1)
end_date = datetime(2026, 12, 31)

# Store all events here before saving to database
all_events = []


def get_event_category(event_type):
    """
    Converts DNR event types into app-friendly categories.
    """

    if event_type == "Fishing Tournament":
        return "Tournament"

    if event_type == "Fishing Tournament - Educational Institutions":
        return "Educational Tournament"

    if event_type == "Reserved for Non-Tournament Anglers":
        return "Tournament-Free Lake"

    return "Other"


def get_event_details(event_id):
    """
    Calls the Iowa DNR event detail endpoint and parses the popup HTML table
    into a dictionary of detail fields.
    """

    payload = {
        "eventID": event_id
    }

    try:
        response = requests.post(
            details_url,
            json=payload,
            headers=headers
        )

        if response.status_code != 200:
            print(f"Detail request failed for Event ID {event_id}. Status Code: {response.status_code}")
            return {}

        data = response.json()
        html = data.get("d", "")

        soup = BeautifulSoup(html, "html.parser")

        detail_fields = {}

        rows = soup.find_all("tr")

        for row in rows:
            cells = row.find_all("td")

            if len(cells) == 2:
                field_name = cells[0].get_text(strip=True).replace(":", "")
                field_value = cells[1].get_text(" ", strip=True)

                detail_fields[field_name] = field_value

        return detail_fields

    except Exception as e:
        print(f"Error getting details for Event ID {event_id}: {e}")
        return {}


def save_event_to_database(event, details):
    """
    Inserts or updates one event record in the SQLite database.
    """

    connection = sqlite3.connect("iowa_tournaments.db")
    cursor = connection.cursor()

    event_id = event["EventID"]
    event_type = event["EventType"]
    event_category = get_event_category(event_type)

    date_string = event["StartDate"]
    timestamp = int(re.search(r"\d+", date_string).group())
    event_date = datetime.fromtimestamp(timestamp / 1000).strftime("%Y-%m-%d")

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
    INSERT OR REPLACE INTO events (
        event_id,
        event_name,
        event_type,
        event_category,
        event_date,
        lake,
        open_to_public,
        status,
        latitude,
        longitude,
        event_description,
        event_date_time,
        detail_location,
        address,
        organization,
        primary_phone,
        organization_email,
        web_address,
        last_updated
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        event_id,
        event["EventName"],
        event_type,
        event_category,
        event_date,
        event["LocationName"],
        "Yes" if event["Public"] == "Y" else "No",
        event["Status"],
        event["PointY"],
        event["PointX"],
        details.get("Event Description", ""),
        details.get("Event Date and Time", ""),
        details.get("Location", ""),
        details.get("Address", ""),
        details.get("Organization", ""),
        details.get("Primary Phone", ""),
        details.get("Organization Email", ""),
        details.get("Web Address", ""),
        now
    ))

    connection.commit()
    connection.close()


# Loop through the year in 7-day windows
current_start = start_date

while current_start <= end_date:

    current_end = current_start + timedelta(days=6)

    if current_end > end_date:
        current_end = end_date

    from_date = current_start.strftime("%m/%d/%Y")
    to_date = current_end.strftime("%m/%d/%Y")

    payload = {
        "xMin": -10834041.328207124,
        "yMin": 4917386.001940063,
        "xMax": -9968162.671792876,
        "yMax": 5404136.998059937,
        "consolidatedEventTypeID": "2",
        "countyNum": None,
        "fromDate": from_date,
        "statePark": None,
        "toDate": to_date
    }

    print(f"Searching: {from_date} to {to_date}")

    response = requests.post(
        events_url,
        json=payload,
        headers=headers
    )

    print("Status Code:", response.status_code)

    data = response.json()

    records_returned = len(data["d"])
    print(f"Records returned: {records_returned}")

    if records_returned >= 100:
        print("WARNING: This date range may still be too large.")

    for event in data["d"]:
        all_events.append(event)

    print("-" * 60)

    current_start = current_end + timedelta(days=1)


# Remove duplicate events by EventID
unique_events = {}

for event in all_events:
    unique_events[event["EventID"]] = event

print()
print(f"Total records collected before removing duplicates: {len(all_events)}")
print(f"Total unique events: {len(unique_events)}")


# Save events to database
saved_count = 0

for event in unique_events.values():

    event_type = event["EventType"]

    # Keep tournaments and tournament-free lake records
    if event_type not in [
        "Fishing Tournament",
        "Fishing Tournament - Educational Institutions",
        "Reserved for Non-Tournament Anglers"
    ]:
        continue

    event_id = event["EventID"]

    print(f"Getting details and saving Event ID: {event_id}")

    details = get_event_details(event_id)

    save_event_to_database(event, details)

    saved_count += 1

    # Small pause so we do not hammer the DNR site
    time.sleep(0.25)


print()
print("Database import complete.")
print(f"Total events saved to database: {saved_count}")

last_updated = {
    "last_updated": datetime.now().isoformat()
}

from pathlib import Path

output_file = Path("static/last_updated.json")

with open(output_file, "w") as f:
    json.dump(last_updated, f)

print(f"Timestamp written to: {output_file.resolve()}")
