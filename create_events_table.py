import sqlite3

# Connect to the SQLite database file
connection = sqlite3.connect("iowa_tournaments.db")

# Create a cursor so we can run SQL commands
cursor = connection.cursor()

# Create the real events table
cursor.execute("""
CREATE TABLE IF NOT EXISTS events (
    event_id INTEGER PRIMARY KEY,
    event_name TEXT,
    event_type TEXT,
    event_category TEXT,
    event_date TEXT,
    lake TEXT,
    open_to_public TEXT,
    status TEXT,
    latitude REAL,
    longitude REAL,
    event_description TEXT,
    event_date_time TEXT,
    detail_location TEXT,
    address TEXT,
    organization TEXT,
    primary_phone TEXT,
    organization_email TEXT,
    web_address TEXT,
    last_updated TEXT
)
""")

# Save changes
connection.commit()

# Verify the table exists
cursor.execute("""
SELECT name 
FROM sqlite_master 
WHERE type='table'
""")

tables = cursor.fetchall()

print("Tables in database:")
print("-" * 40)

for table in tables:
    print(table[0])

# Close the database connection
connection.close()

print()
print("Events table created successfully.")