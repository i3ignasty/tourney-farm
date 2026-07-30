import sqlite3
import requests
from datetime import date, timedelta
from fastapi import FastAPI
from fastapi.responses import FileResponse

app = FastAPI()


def get_database_connection():
    connection = sqlite3.connect("iowa_tournaments.db")
    connection.row_factory = sqlite3.Row
    return connection


def weather_code_to_text(code):
    weather_codes = {
        0: "Clear",
        1: "Mostly clear",
        2: "Partly cloudy",
        3: "Cloudy",
        45: "Fog",
        48: "Freezing fog",
        51: "Light drizzle",
        53: "Drizzle",
        55: "Heavy drizzle",
        61: "Light rain",
        63: "Rain",
        65: "Heavy rain",
        71: "Light snow",
        73: "Snow",
        75: "Heavy snow",
        80: "Light showers",
        81: "Showers",
        82: "Heavy showers",
        95: "Thunderstorms",
        96: "Thunderstorms with hail",
        99: "Severe thunderstorms with hail"
    }

    return weather_codes.get(code, "Unknown")


def get_weather_for_event(latitude, longitude, event_date, debug=False):
    if latitude is None or longitude is None or event_date is None:
        if debug:
            return {
                "success": False,
                "reason": "Missing latitude, longitude, or event_date",
                "latitude": latitude,
                "longitude": longitude,
                "event_date": event_date
            }

        return None

    weather_url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": "temperature_2m,wind_speed_10m,weather_code",
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "timezone": "America/Chicago",
        "forecast_days": 16
    }

    try:
        response = requests.get(
            weather_url,
            params=params,
            timeout=15
        )

        if response.status_code != 200:
            if debug:
                return {
                    "success": False,
                    "reason": "Open-Meteo returned non-200 status",
                    "status_code": response.status_code,
                    "response_text": response.text[:500],
                    "request_url": response.url
                }

            return None

        data = response.json()

        hourly = data.get("hourly", {})
        times = hourly.get("time", [])
        temperatures = hourly.get("temperature_2m", [])
        winds = hourly.get("wind_speed_10m", [])
        weather_codes = hourly.get("weather_code", [])

        if not times:
            if debug:
                return {
                    "success": False,
                    "reason": "No hourly times returned",
                    "response_keys": list(data.keys()),
                    "request_url": response.url
                }

            return None

        preferred_time = f"{event_date}T12:00"

        if preferred_time in times:
            index = times.index(preferred_time)
        else:
            matching_indexes = [
                i for i, forecast_time in enumerate(times)
                if forecast_time.startswith(event_date)
            ]

            if not matching_indexes:
                if debug:
                    return {
                        "success": False,
                        "reason": "Event date not found in Open-Meteo forecast window",
                        "event_date": event_date,
                        "first_forecast_time": times[0],
                        "last_forecast_time": times[-1],
                        "request_url": response.url
                    }

                return None

            index = matching_indexes[0]

        weather_code = weather_codes[index]

        weather_result = {
            "temperature": temperatures[index],
            "wind_speed": winds[index],
            "weather_code": weather_code,
            "weather": weather_code_to_text(weather_code),
            "forecast_time": times[index]
        }

        if debug:
            return {
                "success": True,
                "latitude": latitude,
                "longitude": longitude,
                "event_date": event_date,
                "request_url": response.url,
                "weather": weather_result
            }

        return weather_result

    except Exception as e:
        if debug:
            return {
                "success": False,
                "reason": "Exception during weather lookup",
                "error": str(e),
                "latitude": latitude,
                "longitude": longitude,
                "event_date": event_date
            }

        print(f"Weather lookup failed: {e}")
        return None


@app.get("/")
def site():
    return FileResponse("static/index.html")


@app.get("/site")
def site_alt():
    return FileResponse("static/index.html")


@app.get("/api/status")
def api_status():
    return {
        "message": "Tourney Farm API is running"
    }


@app.get("/summary")
def get_summary():
    connection = get_database_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT COUNT(*) FROM events")
    total_events = cursor.fetchone()[0]

    cursor.execute("""
    SELECT COUNT(*)
    FROM events
    WHERE event_category = 'Tournament'
    """)
    tournaments = cursor.fetchone()[0]

    cursor.execute("""
    SELECT COUNT(*)
    FROM events
    WHERE event_category = 'Tournament-Free Lake'
    """)
    tournament_free_lakes = cursor.fetchone()[0]

    cursor.execute("""
    SELECT COUNT(*)
    FROM events
    WHERE event_category = 'Educational Tournament'
    """)
    educational_tournaments = cursor.fetchone()[0]

    cursor.execute("""
    SELECT COUNT(DISTINCT lake)
    FROM events
    """)
    unique_lakes = cursor.fetchone()[0]

    connection.close()

    return {
        "total_events": total_events,
        "tournaments": tournaments,
        "tournament_free_lakes": tournament_free_lakes,
        "educational_tournaments": educational_tournaments,
        "unique_lakes": unique_lakes
    }


@app.get("/categories")
def get_categories():
    connection = get_database_connection()
    cursor = connection.cursor()

    cursor.execute("""
    SELECT
        event_category,
        COUNT(*) AS event_count
    FROM events
    GROUP BY event_category
    ORDER BY event_count DESC
    """)

    rows = cursor.fetchall()
    connection.close()

    return [dict(row) for row in rows]


@app.get("/lakes")
def get_lakes():
    connection = get_database_connection()
    cursor = connection.cursor()

    cursor.execute("""
    SELECT
        lake,
        COUNT(*) AS event_count
    FROM events
    GROUP BY lake
    ORDER BY lake
    """)

    rows = cursor.fetchall()
    connection.close()

    return [dict(row) for row in rows]


@app.get("/events/weekend")
def get_weekend_events(
    category: str | None = None,
    public: str | None = None
):
    today = date.today()

    # Monday = 0, Tuesday = 1, Wednesday = 2,
    # Thursday = 3, Friday = 4, Saturday = 5, Sunday = 6
    days_until_saturday = (5 - today.weekday()) % 7

    saturday = today + timedelta(days=days_until_saturday)
    sunday = saturday + timedelta(days=1)

    start_date = saturday.strftime("%Y-%m-%d")
    end_date = sunday.strftime("%Y-%m-%d")

    connection = get_database_connection()
    cursor = connection.cursor()

    query = """
    SELECT
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
    FROM events
    WHERE event_date >= ?
      AND event_date <= ?
    """

    params = [start_date, end_date]

    if category:
        query += " AND event_category = ?"
        params.append(category)

    if public:
        query += " AND open_to_public = ?"
        params.append(public)

    query += " ORDER BY event_date, lake"

    cursor.execute(query, params)

    rows = cursor.fetchall()
    connection.close()

    events = []

    for row in rows:
        event = dict(row)

        event["weather"] = get_weather_for_event(
            event.get("latitude"),
            event.get("longitude"),
            event.get("event_date")
        )

        events.append(event)

    return {
        "start_date": start_date,
        "end_date": end_date,
        "count": len(events),
        "events": events
    }


@app.get("/debug/weather")
def debug_weather(
    latitude: float = 42.4094814528,
    longitude: float = -91.3884579644,
    event_date: str = None
):
    if event_date is None:
        today = date.today()
        days_until_saturday = (5 - today.weekday()) % 7
        saturday = today + timedelta(days=days_until_saturday)
        event_date = saturday.strftime("%Y-%m-%d")

    weather = get_weather_for_event(
        latitude,
        longitude,
        event_date,
        debug=True
    )

    return weather


@app.get("/events")
def get_events(
    category: str | None = None,
    lake: str | None = None,
    public: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None
):
    connection = get_database_connection()
    cursor = connection.cursor()

    query = """
    SELECT
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
    FROM events
    WHERE 1 = 1
    """

    params = []

    if category:
        query += " AND event_category = ?"
        params.append(category)

    if lake:
        query += " AND lake LIKE ?"
        params.append(f"%{lake}%")

    if public:
        query += " AND open_to_public = ?"
        params.append(public)

    # Default behavior:
    # If no start_date is provided, only show events from today forward.
    if start_date:
        query += " AND event_date >= ?"
        params.append(start_date)
    else:
        today_string = date.today().strftime("%Y-%m-%d")
        query += " AND event_date >= ?"
        params.append(today_string)

    if end_date:
        query += " AND event_date <= ?"
        params.append(end_date)

    query += " ORDER BY event_date"

    cursor.execute(query, params)

    rows = cursor.fetchall()
    connection.close()

    events = [dict(row) for row in rows]

    return {
        "count": len(events),
        "events": events
    }


@app.get("/events/{event_id}")
def get_event_by_id(event_id: int):
    connection = get_database_connection()
    cursor = connection.cursor()

    cursor.execute("""
    SELECT
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
    FROM events
    WHERE event_id = ?
    """, (event_id,))

    row = cursor.fetchone()
    connection.close()

    if row is None:
        return {
            "error": "Event not found"
        }

    return dict(row)