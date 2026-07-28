import sqlite3

# Create or open a SQLite database file
connection = sqlite3.connect("iowa_tournaments.db")

# Create a cursor, which lets us run SQL commands
cursor = connection.cursor()

# Create a simple test table
cursor.execute("""
CREATE TABLE IF NOT EXISTS test_table (
    id INTEGER PRIMARY KEY,
    message TEXT
)
""")

# Insert one test record
cursor.execute("""
INSERT INTO test_table (message)
VALUES (?)
""", ("Hello from Nate's first database",))

# Save the changes
connection.commit()

# Read the data back out
cursor.execute("SELECT * FROM test_table")

rows = cursor.fetchall()

print("Database test results:")
print("-" * 40)

for row in rows:
    print(row)

# Close the database connection
connection.close()

print()
print("Database file created: iowa_tournaments.db")