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

































