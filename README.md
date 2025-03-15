This project is a Flask-based event registration system designed to streamline event sign-ups. The system allows users to register for an event by providing their details, 
which are stored in a SQLite database. Upon successful registration, a QR code is generated for each participant, and a confirmation email containing the QR code is sent to their 
email address. This enables event organizers to verify registrations efficiently. Additionally, administrators can export all registration data to a CSV file for easy access and record-keeping.

/Flask-Registrations
│-- app.py  # Main Flask application
│-- templates/
│   ├── index.html  # User registration page
│   ├── admin.html  # Admin panel
│-- registrations.db  # SQLite database
│-- registrations.csv  # Exported registration data
│-- export_to_csv.py  # CSV export function
