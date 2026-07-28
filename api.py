import sqlite3
from datetime import date, timedelta
from fastapi import FastAPI
from fastapi.responses import FileResponse

app = FastAPI()


def get_database_connection():
    connection = sqlite3.connect("iowa_tournaments.db")
    connection.row_factory = sqlite3.Row
    return connection


@app.get("/")
def home():
    return {
        "message": "Iowa Tournament API is running"
    }
@app.get("/site")
def site():
    return FileResponse("static/index.html")

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

    events = [dict(row) for row in rows]

    return {
        "start_date": start_date,
        "end_date": end_date,
        "count": len(events),
        "events": events
    }


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

    if start_date:
        query += " AND event_date >= ?"
        params.append(start_date)

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