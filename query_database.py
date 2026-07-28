import sqlite3

# Connect to the database
connection = sqlite3.connect("iowa_tournaments.db")

# Create cursor
cursor = connection.cursor()

# Count total records
cursor.execute("""
SELECT COUNT(*)
FROM events
""")

total_count = cursor.fetchone()[0]

print(f"Total events in database: {total_count}")

print()
print("Event category counts:")
print("-" * 40)

cursor.execute("""
SELECT event_category, COUNT(*)
FROM events
GROUP BY event_category
ORDER BY COUNT(*) DESC
""")

category_rows = cursor.fetchall()

for row in category_rows:
    print(f"{row[0]}: {row[1]}")

print()
print("First 10 events:")
print("-" * 40)

cursor.execute("""
SELECT
    event_date,
    event_name,
    lake,
    event_category,
    open_to_public
FROM events
ORDER BY event_date
LIMIT 10
""")

event_rows = cursor.fetchall()

for row in event_rows:
    print(f"{row[0]} | {row[1]} | {row[2]} | {row[3]} | Public: {row[4]}")

# Close connection
connection.close()