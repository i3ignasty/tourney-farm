import requests
import pandas as pd
import re
import time
from datetime import datetime
import json
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

# Main Iowa DNR API URLs
events_url = "https://programs.iowadnr.gov/specialevents/Search.aspx/GetEvents"
details_url = "https://programs.iowadnr.gov/specialevents/Search.aspx/GetEventDetail"

headers = {
    "Content-Type": "application/json; charset=UTF-8"
}

# Search date range
start_date = datetime(2026, 1, 1)
end_date = datetime(2026, 12, 31)

# Store all events here
all_tournaments = []


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

    for tournament in data["d"]:
        all_tournaments.append(tournament)

    print("-" * 60)

    # Move to next 7-day period
    current_start = current_end + timedelta(days=1)


# Remove duplicate tournaments by EventID
unique_tournaments = {}

for tournament in all_tournaments:
    unique_tournaments[tournament["EventID"]] = tournament

print()
print(f"Total records collected before removing duplicates: {len(all_tournaments)}")
print(f"Total unique tournaments: {len(unique_tournaments)}")


# Build Excel rows
tournament_rows = []

for tournament in unique_tournaments.values():

    event_id = tournament["EventID"]

    # Keep only tournament-related records
    if tournament["EventType"] not in [
        "Fishing Tournament",
        "Fishing Tournament - Educational Institutions"
    ]:
        continue

    print(f"Getting details for Event ID: {event_id}")

    details = get_event_details(event_id)

    date_string = tournament["StartDate"]

    timestamp = int(
        re.search(r"\d+", date_string).group()
    )

    tournament_date = datetime.fromtimestamp(timestamp / 1000)

    tournament_rows.append({
        "Date": tournament_date.strftime("%m/%d/%Y"),
        "Tournament Name": tournament["EventName"],
        "Lake": tournament["LocationName"],
        "Open To Public": "Yes" if tournament["Public"] == "Y" else "No",
        "Event ID": event_id,
        "Status": tournament["Status"],
        "Event Type": tournament["EventType"],
        "Latitude": tournament["PointY"],
        "Longitude": tournament["PointX"],

        # Detail fields from popup
        "Event Description": details.get("Event Description", ""),
        "Event Date and Time": details.get("Event Date and Time", ""),
        "Detail Open To Public": details.get("Open to Public", ""),
        "Detail Location": details.get("Location", ""),
        "Address": details.get("Address", ""),
        "Organization": details.get("Organization", ""),
        "Primary Phone": details.get("Primary Phone", ""),
        "Organization Email": details.get("Organization Email", ""),
        "Web Address": details.get("Web Address", "")
    })

    # Small pause so we do not hammer the DNR site too hard
    time.sleep(0.25)


# Create DataFrame
df = pd.DataFrame(tournament_rows)

print()
print("Final Event Type Counts:")
print(df["Event Type"].value_counts())

print()
print("Top Tournament Names:")
print(df["Tournament Name"].value_counts().head(10))

# Sort by date
df["Date Sort"] = pd.to_datetime(df["Date"])
df = df.sort_values("Date Sort")
df = df.drop(columns=["Date Sort"])

# Export to Excel
output_file = "iowa_fishing_tournaments_2026.xlsx"
df.to_excel(output_file, index=False)

print()
print(f"Excel file created: {output_file}")
print(f"Total tournaments exported: {len(df)}")

last_updated = {
    "last_updated": datetime.now().isoformat()
}

with open("static/last_updated.json", "w") as f:
    json.dump(last_updated, f)