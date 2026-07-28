import requests
from bs4 import BeautifulSoup

url = "https://programs.iowadnr.gov/specialevents/Search.aspx/GetEventDetail"

payload = {
    "eventID": 25164
}

headers = {
    "Content-Type": "application/json; charset=UTF-8"
}

response = requests.post(
    url,
    json=payload,
    headers=headers
)

print("Status Code:", response.status_code)

data = response.json()

html = data["d"]

soup = BeautifulSoup(html, "html.parser")

detail_fields = {}

rows = soup.find_all("tr")

for row in rows:
    cells = row.find_all("td")

    if len(cells) == 2:
        field_name = cells[0].get_text(strip=True).replace(":", "")
        field_value = cells[1].get_text(" ", strip=True)

        detail_fields[field_name] = field_value

print()
print("Parsed Event Details:")
print("-" * 50)

for key, value in detail_fields.items():
    print(f"{key}: {value}")
