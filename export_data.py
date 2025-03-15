import sqlite3
import csv

# Connect to the SQLite database
conn = sqlite3.connect('registrations.db')
cursor = conn.cursor()

# Get the table names
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

# Check if there are any tables
if tables:
    # Fetch data from the first table
    table_name = tables[0][0]
    cursor.execute(f"SELECT * FROM {table_name};")
    rows = cursor.fetchall()

    # Export data to CSV
    with open(f'{table_name}.csv', 'w', newline='') as csv_file:
        writer = csv.writer(csv_file)
        # Write the header
        writer.writerow([description[0] for description in cursor.description])
        # Write the data
        writer.writerows(rows)

    print(f"Data from table '{table_name}' has been exported to '{table_name}.csv'.")
else:
    print("No tables found in the database.")

# Close the connection
conn.close()
