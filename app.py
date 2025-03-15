
from flask import Flask, request, render_template
import sqlite3
import csv
from export_to_csv import export_to_csv
import csv
from export_to_csv import export_to_csv
import qrcode
from io import BytesIO
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import os

app = Flask(__name__)

# Database setup
conn = sqlite3.connect('registrations.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS registrations
                (id INTEGER PRIMARY KEY, name TEXT, email TEXT, event TEXT, qr_code BLOB)''')
conn.commit()

# Removed duplicate export_to_csv function
# Removed duplicate import of csv and export_to_csv

def export_to_csv():
    # Export data from the registrations table to a CSV file
    cursor.execute("SELECT * FROM registrations;")
    rows = cursor.fetchall()

    with open('registrations.csv', 'w', newline='') as csv_file:
        writer = csv.writer(csv_file)
        # Write the header
        writer.writerow([description[0] for description in cursor.description])
        # Write the data
        writer.writerows(rows)

def send_email(email, name, qr_data):
    try:
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        sender_email = "amazonawshyd@gmail.com"
        sender_password = "jdva ogim lmok pnfc" 

        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = email
        msg['Subject'] = "Registration Confirmation"

        body = f"Hi {name},\n\n We are in the process of confirmation . We'll shortly forward the entry pass after the Verification!"
        msg.attach(MIMEText(body, 'plain'))

        # Attach QR code
        qr_img = MIMEImage(qr_data)
        qr_img.add_header('Content-Disposition', 'attachment', filename="qrcode.png")
        msg.attach(qr_img)

        # Debug: Print SMTP connection details
        print("\n=== Attempting to send email ===")
        print(f"SMTP Server: {smtp_server}:{smtp_port}")
        print(f"From: {sender_email}")
        print(f"To: {email}")

        # Connect to SMTP server
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()

        print("✅ Email sent successfully!")
        print("==============================\n")

    except Exception as e:
        print("\n🔥 Error sending email:")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Details: {str(e)}")
        print("==============================\n")
        raise  # Re-raise the error to see the full traceback

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['POST'])
def register():
    name = request.form.get('name')
    email = request.form.get('email')
    event = request.form.get('event')

    # Generate QR code
    qr = qrcode.make(f"Name: {name}\nEmail: {email}\nEvent: {event}")
    qr_bytes = BytesIO()
    qr.save(qr_bytes, format='PNG')
    qr_data = qr_bytes.getvalue()

    # Save to database
    cursor.execute('INSERT INTO registrations (name, email, event, qr_code) VALUES (?, ?, ?, ?)',
                  (name, email, event, qr_data))
    conn.commit()

    # Send email
    send_email(email, name, qr_data)

    # Export data to CSV after successful registration
    export_to_csv()

    return "Registration successful! Check your email."

@app.route('/admin')
def admin():
    return render_template('admin.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
