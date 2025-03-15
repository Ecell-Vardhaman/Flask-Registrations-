import sqlite3
import csv

def export_to_csv():
    # Connect to the SQLite database
    conn = sqlite3.connect('registrations.db')
    cursor = conn.cursor()

    # Export data from the registrations table to a CSV file
    cursor.execute("SELECT * FROM registrations;")
    rows = cursor.fetchall()

    with open('registrations.csv', 'w', newline='') as csv_file:
        writer = csv.writer(csv_file)
        # Write the header
        writer.writerow([description[0] for description in cursor.description])
        # Write the data
        writer.writerows(rows)

    # Close the connection
    conn.close()
