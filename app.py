from flask import Flask, render_template, request, redirect, url_for, flash
import os
from werkzeug.utils import secure_filename
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import csv
import qrcode
import uuid
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from io import BytesIO
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB

# Email configuration (verify these settings)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'amazonawshyd@gmail.com'
app.config['MAIL_PASSWORD'] = 'jdvaogimlmokpnfc'

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_qr_pdf(email, data):
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        pdf_filename = f"TechFest_{email}_{uuid.uuid4().hex[:6]}.pdf"
        pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], pdf_filename)
        
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        
        c = canvas.Canvas(pdf_path, pagesize=letter)
        width, height = letter
        
        # Header
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, height - 50, "Tech Fest 2024 Registration Confirmation")
        
        # Details
        c.setFont("Helvetica", 12)
        details = [
            f"Name: {request.form['full_name']}",
            f"Email: {email}",
            f"College: {request.form['college']}",
            f"Transaction ID: {request.form['transaction_id']}"
        ]
        
        y_position = height - 100
        for line in details:
            c.drawString(50, y_position, line)
            y_position -= 20
        
        # QR Code
        img_reader = ImageReader(buffer)
        c.drawImage(img_reader, 50, y_position - 200, width=200, height=200)
        c.save()
        
        return pdf_path
    
    except Exception as e:
        logging.error(f"PDF Generation Error: {str(e)}")
        raise

def send_confirmation_email(recipient, pdf_path):
    try:
        msg = MIMEMultipart()
        msg['From'] = app.config['MAIL_USERNAME']
        msg['To'] = recipient
        msg['Subject'] = "Tech Fest 2024 Registration Confirmation"
        
        body = f"""
        <h2>Registration Successful!</h2>
        <p>Thank you for registering for Tech Fest 2024.</p>
        <p>Your registration details and entry QR code are attached.</p>
        <p><strong>Bring either:</strong></p>
        <ul>
            <li>This PDF document</li>
            <li>Your registered email ID</li>
        </ul>
        <p>Contact: techfest2024@yourcollege.edu for queries</p>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        # Attach PDF
        with open(pdf_path, 'rb') as f:
            attach = MIMEApplication(f.read(), _subtype="pdf")
            attach.add_header('Content-Disposition', 'attachment', 
                            filename=os.path.basename(pdf_path))
            msg.attach(attach)
        
        # SMTP Connection
        with smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT']) as server:
            server.starttls()
            server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
            server.sendmail(app.config['MAIL_USERNAME'], recipient, msg.as_string())
        
        logging.info(f"Email sent to {recipient}")
        
    except Exception as e:
        logging.error(f"Email Error: {str(e)}")
        raise
    finally:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['POST'])
def register():
    try:
        # Validate form data
        required_fields = ['full_name', 'email', 'college', 'rollno',
                          'branch', 'section', 'transaction_id']
        missing = [f.replace('_', ' ') for f in required_fields if not request.form.get(f)]
        if missing:
            raise ValueError(f"Missing fields: {', '.join(missing)}")

        email = request.form['email'].strip().lower()
        file = request.files['payment_proof']

        # File validation
        if file.filename == '':
            raise ValueError("Please select a payment screenshot")
        if not allowed_file(file.filename):
            raise ValueError("Only PNG/JPG/JPEG files allowed (max 5MB)")

        # Save payment proof
        filename = secure_filename(f"{email}_{file.filename}")
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        logging.info(f"File saved: {file_path}")

        # Generate PDF
        qr_data = f"""
        Name: {request.form['full_name']}
        Email: {email}
        College: {request.form['college']}
        Transaction ID: {request.form['transaction_id']}
        """
        pdf_path = generate_qr_pdf(email, qr_data)
        logging.info(f"PDF generated: {pdf_path}")

        # Save to CSV
        csv_data = [
            request.form['full_name'], email,
            request.form['college'], request.form['rollno'],
            request.form['branch'], request.form['section'],
            request.form['transaction_id'], filename,
            os.path.basename(pdf_path)
        ]
        
        with open('registrations.csv', 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(csv_data)
        logging.info("CSV entry added")

        # Send email
        send_confirmation_email(email, pdf_path)
        
        return redirect(url_for('success', email=email))

    except Exception as e:
        logging.error(f"Registration Error: {str(e)}")
        flash(str(e))
        return redirect(url_for('index'))

@app.route('/success')
def success():
    email = request.args.get('email', '')
    if not email:
        return redirect(url_for('index'))
    return render_template('success.html', email=email)

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    try:
        app.run(host='0.0.0.0', port=5000, debug=True)
    except Exception as e:
        logging.error(f"Server Error: {str(e)}")













































# from flask import Flask, render_template, request, redirect, url_for, flash
# import os
# from werkzeug.utils import secure_filename
# import smtplib
# from email.mime.text import MIMEText
# from email.mime.multipart import MIMEMultipart
# import csv

# app = Flask(__name__)
# app.secret_key = os.urandom(24)  # Use a proper secret key
# app.config['UPLOAD_FOLDER'] = 'static/uploads'
# app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024

# # Email configuration (update with your credentials)
# app.config['MAIL_SERVER'] = 'smtp.gmail.com'
# app.config['MAIL_PORT'] = 587
# app.config['MAIL_USE_TLS'] = True
# app.config['MAIL_USERNAME'] = 'amazonawshyd@gmail.com'
# app.config['MAIL_PASSWORD'] = 'jdvaogimlmokpnfc'

# ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

# def allowed_file(filename):
#     return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# def send_confirmation_email(recipient):
#     msg = MIMEMultipart()
#     msg['From'] = app.config['MAIL_USERNAME']
#     msg['To'] = recipient
#     msg['Subject'] = "Tech Fest 2024 Registration Confirmation"
    
#     body = f"""
#     <h2>Registration Successful!</h2>
#     <p>Thank you for registering for Tech Fest 2024.</p>
#     <p>We've received your submission with the following details:</p>
#     <ul>
#         <li>Name: {request.form['full_name']}</li>
#         <li>Email: {recipient}</li>
#         <li>College: {request.form['college']}</li>
#     </ul>
#     <p>Keep this email for future reference.</p>
#     """
    
#     msg.attach(MIMEText(body, 'html'))
    
#     try:
#         server = smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT'])
#         server.starttls()
#         server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
#         server.sendmail(app.config['MAIL_USERNAME'], recipient, msg.as_string())
#         server.quit()
#     except Exception as e:
#         print(f"Error sending email: {str(e)}")

# @app.route('/')
# def index():
#     return render_template('index.html')

# @app.route('/register', methods=['POST'])
# def register():
#     try:
#         # Validate required fields
#         required_fields = ['full_name', 'email', 'college', 'rollno', 
#                           'branch', 'section', 'transaction_id']
#         for field in required_fields:
#             if not request.form.get(field):
#                 raise ValueError(f"Missing required field: {field.replace('_', ' ')}")

#         email = request.form['email']
#         file = request.files['payment_proof']

#         # File validation
#         if file.filename == '':
#             raise ValueError("Please select a payment screenshot")
#         if not allowed_file(file.filename):
#             raise ValueError("Only PNG, JPG, and JPEG files allowed")

#         # Save file
#         filename = secure_filename(f"{email}_{file.filename}")
#         file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

#         # Save to CSV
#         with open('registrations.csv', 'a', newline='') as csvfile:
#             writer = csv.writer(csvfile)
#             writer.writerow([
#                 request.form['full_name'],
#                 email,
#                 request.form['college'],
#                 request.form['rollno'],
#                 request.form['branch'],
#                 request.form['section'],
#                 request.form['transaction_id'],
#                 filename
#             ])

#         # Send confirmation email
#         send_confirmation_email(email)

#         return redirect(url_for('success', email=email))

#     except Exception as e:
#         flash(str(e))
#         return redirect(url_for('index'))

# @app.route('/success')
# def success():
#     email = request.args.get('email', '')
#     if not email:
#         return redirect(url_for('index'))
#     return render_template('success.html', email=email)

# if __name__ == '__main__':
#     os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
#     app.run(debug=False)  # Run with debug=False for production






























# from flask import Flask, render_template, request, jsonify, redirect, url_for
# import sqlite3
# import os
# import qrcode
# from io import BytesIO
# from werkzeug.utils import secure_filename
# from datetime import datetime

# app = Flask(__name__)
# app.config.update({
#     'UPLOAD_FOLDER': 'static/uploads',
#     'MAX_CONTENT_LENGTH': 2 * 1024 * 1024,  # 2MB
#     'DATABASE': 'registrations.db',
#     'SECRET_KEY': 'your-secret-key-here'
# })

# ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

# # Database Helper Functions
# def get_db():
#     conn = sqlite3.connect(app.config['DATABASE'])
#     conn.row_factory = sqlite3.Row
#     return conn

# def init_db():
#     with app.app_context():
#         conn = get_db()
#         conn.execute('''
#             CREATE TABLE IF NOT EXISTS registrations (
#                 id INTEGER PRIMARY KEY AUTOINCREMENT,
#                 full_name TEXT NOT NULL,
#                 college TEXT NOT NULL,
#                 rollno TEXT UNIQUE NOT NULL,
#                 branch TEXT NOT NULL,
#                 section TEXT NOT NULL,
#                 transaction_id TEXT UNIQUE NOT NULL,
#                 payment_proof TEXT NOT NULL,
#                 qr_code BLOB NOT NULL,
#                 registration_date DATETIME DEFAULT CURRENT_TIMESTAMP,
#                 checked_in BOOLEAN DEFAULT FALSE
#             )
#         ''')
#         conn.commit()
#         conn.close()

# init_db()

# # Utility Functions
# def allowed_file(filename):
#     return '.' in filename and \
#            filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# def generate_qr_code(data):
#     qr = qrcode.QRCode(
#         version=1,
#         error_correction=qrcode.constants.ERROR_CORRECT_H,
#         box_size=10,
#         border=4,
#     )
#     qr.add_data(data)
#     qr.make(fit=True)
#     img = qr.make_image(fill_color="#2c3e50", back_color="white")
#     buffered = BytesIO()
#     img.save(buffered, format="PNG")
#     return buffered.getvalue()

# # Routes
# @app.route('/')
# def home():
#     return render_template('index.html')

# @app.route('/register', methods=['GET', 'POST'])
# def register():
#     if request.method == 'GET':
#         return redirect(url_for('home'))
    
#     try:
#         if 'payment_proof' not in request.files:
#             return jsonify({"error": "No file uploaded"}), 400
            
#         file = request.files['payment_proof']
#         if not (file and allowed_file(file.filename)):
#             return jsonify({"error": "Invalid file type"}), 400

#         # Process form data
#         form_data = {
#             'full_name': request.form.get('full_name'),
#             'college': request.form.get('college'),
#             'rollno': request.form.get('rollno', '').upper(),
#             'branch': request.form.get('branch'),
#             'section': request.form.get('section'),
#             'transaction_id': request.form.get('transaction_id'),
#         }

#         # Validate required fields
#         for field in ['full_name', 'college', 'rollno', 'branch', 'section', 'transaction_id']:
#             if not form_data[field]:
#                 return jsonify({"error": f"Missing required field: {field}"}), 400

#         # Save uploaded file
#         filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{secure_filename(file.filename)}"
#         file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
#         file.save(file_path)

#         # Generate QR Code
#         qr_data = f"{form_data['rollno']}|{form_data['transaction_id']}"
#         qr_blob = generate_qr_code(qr_data)

#         # Save to database
#         conn = get_db()
#         conn.execute('''
#             INSERT INTO registrations 
#             (full_name, college, rollno, branch, section, 
#              transaction_id, payment_proof, qr_code)
#             VALUES (?, ?, ?, ?, ?, ?, ?, ?)
#         ''', (
#             form_data['full_name'],
#             form_data['college'],
#             form_data['rollno'],
#             form_data['branch'],
#             form_data['section'],
#             form_data['transaction_id'],
#             filename,
#             qr_blob
#         ))
#         conn.commit()
#         conn.close()

#         return jsonify({
#             "success": True,
#             "message": "Registration successful!",
#             "qr_code": qr_data
#         })

#     except sqlite3.IntegrityError as e:
#         return jsonify({
#             "error": "Duplicate entry - Roll Number or Transaction ID already exists"
#         }), 400
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500

# @app.route('/admin')
# def admin():
#     conn = get_db()
#     registrations = conn.execute('''
#         SELECT id, full_name, rollno, branch, 
#                transaction_id, checked_in
#         FROM registrations
#         ORDER BY registration_date DESC
#     ''').fetchall()
#     conn.close()
#     return render_template('admin.html', registrations=registrations)

# @app.route('/checkin', methods=['POST'])
# def check_in():
#     try:
#         data = request.get_json()
#         qr_data = data.get('qr_data')
        
#         if not qr_data:
#             return jsonify({"error": "No QR data provided"}), 400

#         rollno, transaction_id = qr_data.split('|')
        
#         conn = get_db()
#         registration = conn.execute('''
#             SELECT * FROM registrations
#             WHERE rollno = ? AND transaction_id = ?
#         ''', (rollno, transaction_id)).fetchone()

#         if not registration:
#             return jsonify({"error": "Registration not found"}), 404

#         if registration['checked_in']:
#             return jsonify({"warning": "Already checked in"}), 200

#         conn.execute('''
#             UPDATE registrations
#             SET checked_in = TRUE
#             WHERE id = ?
#         ''', (registration['id'],))
#         conn.commit()
#         conn.close()

#         return jsonify({
#             "success": True,
#             "message": "Successfully checked in",
#             "data": dict(registration)
#         })

#     except Exception as e:
#         return jsonify({"error": str(e)}), 500

# if __name__ == '__main__':
#     if not os.path.exists(app.config['UPLOAD_FOLDER']):
#         os.makedirs(app.config['UPLOAD_FOLDER'])
#     app.run(host='0.0.0.0', port=5000, debug=True)









# from flask import Flask, request, render_template
# import sqlite3
# import csv
# from export_to_csv import export_to_csv
# import csv
# from export_to_csv import export_to_csv
# import qrcode
# from io import BytesIO
# import smtplib
# from email.mime.multipart import MIMEMultipart
# from email.mime.text import MIMEText
# from email.mime.image import MIMEImage
# import os

# app = Flask(__name__)


# conn = sqlite3.connect('registrations.db', check_same_thread=False)
# cursor = conn.cursor()
# cursor.execute('''CREATE TABLE IF NOT EXISTS registrations
#                 (id INTEGER PRIMARY KEY, name TEXT, email TEXT, event TEXT, qr_code BLOB)''')
# conn.commit()


# def export_to_csv():``
   
#     cursor.execute("SELECT * FROM registrations;")
#     rows = cursor.fetchall()

#     with open('registrations.csv', 'w', newline='') as csv_file:
#         writer = csv.writer(csv_file)
       
#         writer.writerow([description[0] for description in cursor.description])
 
#         writer.writerows(rows)

# def send_email(email, name, qr_data):
#     try:
#         smtp_server = "smtp.gmail.com"
#         smtp_port = 587
#         sender_email = "amazonawshyd@gmail.com"
#         sender_password = "jdva ogim lmok pnfc" 

#         msg = MIMEMultipart()
#         msg['From'] = sender_email
#         msg['To'] = email
#         msg['Subject'] = "Registration Confirmation"

#         body = f"Hi {name},\n\n We are in the process of confirmation . We'll shortly forward the entry pass after the Verification!"
#         msg.attach(MIMEText(body, 'plain'))

#         # Attach QR code
#         qr_img = MIMEImage(qr_data)
#         qr_img.add_header('Content-Disposition', 'attachment', filename="qrcode.png")
#         msg.attach(qr_img)

#         # Debug: Print SMTP connection details
#         print("\n=== Attempting to send email ===")
#         print(f"SMTP Server: {smtp_server}:{smtp_port}")
#         print(f"From: {sender_email}")
#         print(f"To: {email}")

#         # Connect to SMTP server
#         server = smtplib.SMTP(smtp_server, smtp_port)
#         server.starttls()
#         server.login(sender_email, sender_password)
#         server.send_message(msg)
#         server.quit()

#         print("✅ Email sent successfully!")
#         print("==============================\n")

#     except Exception as e:
#         print("\n🔥 Error sending email:")
#         print(f"Error Type: {type(e).__name__}")
#         print(f"Error Details: {str(e)}")
#         print("==============================\n")
#         raise  

# @app.route('/')
# def home():
#     return render_template('index.html')

# @app.route('/register', methods=['POST'])
# def register():
#     name = request.form.get('name')
#     email = request.form.get('email')
#     event = request.form.get('event')

#     qr = qrcode.make(f"Name: {name}\nEmail: {email}\nEvent: {event}")
#     qr_bytes = BytesIO()
#     qr.save(qr_bytes, format='PNG')
#     qr_data = qr_bytes.getvalue()

   
#     cursor.execute('INSERT INTO registrations (name, email, event, qr_code) VALUES (?, ?, ?, ?)',
#                   (name, email, event, qr_data))
#     conn.commit()

   
#     send_email(email, name, qr_data)

  
#     export_to_csv()

#     return "Registration successful! Check your email."

# @app.route('/admin')
# def admin():
#     return render_template('admin.html')

# if __name__ == '__main__':
#     app.run(host='0.0.0.0', port=5000, debug=True)
