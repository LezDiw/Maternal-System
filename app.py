from flask import Flask, render_template, request, redirect, url_for, session, flash
import re
import requests
from flask import jsonify 
import json
from openai import OpenAI
from dotenv import load_dotenv
import os
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_bcrypt import Bcrypt
import urllib.parse

load_dotenv("app.env")
print("API Key Loaded:", os.getenv("OPENAI_API_KEY") is not None)

app = Flask(__name__)
app.secret_key = 'yoursecretkey'
bcrypt = Bcrypt(app)

firebase_config = {
    "apiKey": "AIzaSyC3N9k_h5A8vrJJvJHSEnC-iynNMUHUkG4",
    "authDomain": "maternal-care-app-33eac.firebaseapp.com",
    "projectId": "maternal-care-app-33eac",
    "storageBucket": "maternal-care-app-33eac.appspot.com",
    "messagingSenderId": "199844547762",
    "appId": "1:199844547762:web:940f687ec11b3b5d8c0dab",
    "measurementId": "G-EQYXFVCWHK"
 }

# Database Configuration
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

if 'JAWSDB_URL' in os.environ:
    # Production database from Heroku Add-on
    url = os.environ.get('JAWSDB_URL')
    # Use SQLAlchemy URI directly from the environment variable
    url = url.replace("mysql://", "mysql+mysqlconnector://")
    app.config['SQLALCHEMY_DATABASE_URI'] = url
else:
    # Local development database
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root:E_lizabeth03@localhost/maternal_care_system'
db = SQLAlchemy(app)

class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sender_id = db.Column(db.Integer, nullable=False)
    receiver_id = db.Column(db.Integer)  # Corrected to match table
    content = db.Column(db.Text, nullable=False) # Corrected to match table
    sent_at = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp())

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role_id = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(50))
    last_checkin = db.Column(db.DateTime)

class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    role_name = db.Column(db.String(50), unique=True, nullable=False)

@app.route('/')
def home_page():
    return render_template('M-C-S.html') 

@app.route('/about')
def about_page():
    return render_template('About.html') 

@app.route('/contact')
def contact_page():
    return render_template('Contact.html')

@app.route('/login-page')
def login_page():
    return render_template('Login.html') 

#login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password_hash']
        role_name = request.form['role_id']

        # Find the role by name using SQLAlchemy
        role = Role.query.filter_by(role_name=role_name).first()

        if not role:
            flash("Invalid role", "error")
            return redirect(url_for('login_page'))

        # Find the user by username and role_id using SQLAlchemy
        user = User.query.filter_by(
            username=username, 
            role_id=role.id
        ).first()

        # Check if a user exists and if the password matches the stored hash
        if user and bcrypt.check_password_hash(user.password_hash, password):
            session['loggedin'] = True
            session['id'] = user.id
            session['username'] = user.username
            session['role'] = user.role_id

            # NEW: Redirect based on integer role ID
            if role_name == "Patient":
                return redirect(url_for('patient_dashboard'))
            elif role_name == "Family of Expectant Mother":
                return redirect(url_for('family_dashboard'))
            elif role_name == "Healthcare Provider":
                return redirect(url_for('healthcare_dashboard'))
        
        # This code block will only be reached if the login fails
        flash("Incorrect username, password, or role", "error")
        return render_template('Login.html')

    # This handles the GET request, displaying the login page initially
    return render_template('Login.html')

#register route
@app.route('/register', methods=['POST'])
def register():
    username = request.form['username']
    email = request.form['email']
    password = request.form['password_hash']
    role_name = request.form['role_id']

    # Check if username exists using SQLAlchemy
    existing_user = User.query.filter_by(username=username).first()

    if existing_user:
        flash("Username already exists", "error")
        return redirect(url_for('home_page'))
    elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
        flash("Invalid email address", "error")
        return redirect(url_for('home_page'))
    elif not username or not password or not email or not role_name:
        flash("Please fill out the form completely", "error")
        return redirect(url_for('home_page'))
    else:
        # Look up role_id from roles table using SQLAlchemy
        role = Role.query.filter_by(role_name=role_name).first()
        if not role:
            flash("Invalid role selected", "error")
            return redirect(url_for('home_page'))
        
        # HASH THE PASSWORD BEFORE STORING IT
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        
        # Create a new user instance and add to the database
        new_user = User(
            username=username, 
            email=email, 
            password_hash=hashed_password, # Use the hashed password here
            role_id=role.id
        )
        db.session.add(new_user)
        db.session.commit()
        
        flash("You have successfully registered!", "success")
        return redirect(url_for('home_page'))
    
@app.route('/api/chat/send', methods=['POST'])
def send_message():
    data = request.json
    sender_id_str = data.get('sender_id')
    receiver_id_str = data.get('receiver_id')
    message_content = data.get('message')

    # Ensure required fields are present
    if not all([sender_id_str, receiver_id_str, message_content]):
        return jsonify({"error": "Missing required fields"}), 400

    # Convert sender and receiver IDs to integers
    try:
        sender_id = int(sender_id_str)
        receiver_id = int(receiver_id_str)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid sender_id or receiver_id format"}), 400

    # Create a new message instance and add it to the database
    new_message = Message(
        sender_id=sender_id,
        receiver_id=receiver_id,
        content=message_content
    )
    db.session.add(new_message)
    db.session.commit()

    return jsonify({"status": "success", "message": "Message sent"}), 200
# New API endpoint to get chat history
@app.route('/api/chat/history/<user_id>/<recipient_id>', methods=['GET'])
def get_chat_history(user_id, recipient_id):
    # Convert IDs to integers
    try:
        user_id_int = int(user_id)
        recipient_id_int = int(recipient_id)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid user ID or recipient ID"}), 400

    # Query for messages where the user is either the sender or receiver
    messages = Message.query.filter(
        db.or_(
            db.and_(Message.sender_id == user_id_int, Message.receiver_id == recipient_id_int),
            db.and_(Message.sender_id == recipient_id_int, Message.receiver_id == user_id_int)
        )
    ).order_by(Message.sent_at.asc()).all()

    # Format the data for the front-end
    messages_list = [{
        "sender_id": m.sender_id,
        "receiver_id": m.receiver_id,
        "message": m.content,
        "timestamp": m.sent_at.isoformat()
    } for m in messages]

    return jsonify(messages_list)


# Dashboards
@app.route('/patient')
def patient_dashboard():
    # Corrected: Check against the integer role_id for a patient (assuming 1)
    if 'loggedin' in session and session.get('role') == 1:
        # This is the crucial check for Heroku. It ensures the app serves over HTTPS.
        if request.scheme == 'https' or request.headers.get('X-Forwarded-Proto') == 'https':
            return render_template('Patient.html')
        else:
            # If not on HTTPS, redirect to the secure version to avoid issues
            url = url_for('patient_dashboard', _external=True, _scheme='https')
            return redirect(url)
    else:
        # If not logged in or role is wrong, redirect to the login page
        return redirect(url_for('login-page'))

@app.route('/family')
def family_dashboard():
    # Corrected: Check against the integer role_id for a family member (assuming 2)
    if 'loggedin' in session and session.get('role') == 2:
        # Check for the correct protocol on Heroku
        if request.scheme == 'https' or request.headers.get('X-Forwarded-Proto') == 'https':
            return render_template('FamilyFriend.html')
        else:
            # Redirect to the secure version
            url = url_for('family_dashboard', _external=True, _scheme='https')
            return redirect(url)
    else:
        # If not logged in or role is wrong, redirect to the login page
        return redirect(url_for('login-page'))

@app.route('/healthcare')
def healthcare_dashboard():
    # Corrected: Check against the integer role_id for a healthcare provider (assuming 3)
    if 'loggedin' in session and session.get('role') == 3:
        # Check for the correct protocol on Heroku
        if request.scheme == 'https' or request.headers.get('X-Forwarded-Proto') == 'https':
            return render_template('HealthCareProvider.html')
        else:
            # Redirect to the secure version
            url = url_for('healthcare_dashboard', _external=True, _scheme='https')
            return redirect(url)
    else:
        # If not logged in or role is wrong, redirect to the login page
        return redirect(url_for('login-page'))


# Logout
@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('username', None)
    session.pop('role_id', None)
    flash("You have been logged out", "info")
    return redirect(url_for('home_page'))

@app.route('/get_doctors')
def get_doctors():
    # Query the database to get the ID for the 'Healthcare Provider' role
    provider_role = Role.query.filter_by(role_name='Healthcare Provider').first()
    
    if not provider_role:
        return jsonify({"error": "Healthcare Provider role not found"}), 404

    # Use SQLAlchemy to find all users with that role ID
    doctors = User.query.filter_by(role_id=provider_role.id).all()

    # Format doctors for the frontend
    doctor_list = [
        {"id": doc.id, "name": doc.username, "specialization": "Healthcare Provider"}
        for doc in doctors
    ]
    
    return jsonify(doctor_list)

# New route to get all users from the database
@app.route('/api/users', methods=['GET'])
def get_all_users():
    # Use SQLAlchemy to get all users
    users = User.query.with_entities(User.id, User.username, User.role_id).all()
    
    # Format the results into a list of dictionaries
    users_list = [
        {"id": user.id, "name": user.username, "role_id": user.role_id} 
        for user in users
    ]
    
    return jsonify(users_list)

# Route to get all patients (role_id = 1)
@app.route('/api/patients', methods=['GET'])
def get_patients():
    # Use SQLAlchemy to find all users where role_id is 1 (Patient)
    # The `with_entities` method is used for an efficient query
    patients = User.query.with_entities(
        User.id, 
        User.username.label('name'), 
        User.role_id, 
        User.status, 
        User.last_checkin
    ).filter_by(role_id=1).all()

    # Format the results into a list of dictionaries
    patients_list = [
        {
            "id": patient.id,
            "name": patient.name,
            "role_id": patient.role_id,
            "status": patient.status,
            "last_checkin": patient.last_checkin
        }
        for patient in patients
    ]

    return jsonify(patients_list)

# New route to get healthcare providers (role_id = 3)
@app.route('/api/providers', methods=['GET'])
def get_providers():
    # Use SQLAlchemy to find all users where role_id is 3 (Healthcare Provider)
    # The with_entities method is used for an efficient query
    providers = User.query.with_entities(
        User.id, 
        User.username.label('name'), 
        User.role_id
    ).filter_by(role_id=3).all()
    
    # Format the results into a list of dictionaries
    providers_list = [
        {"id": provider.id, "name": provider.name, "role_id": provider.role_id}
        for provider in providers
    ]
    
    return jsonify(providers_list)

# New route to update a user's role to patient
@app.route('/api/add_patient', methods=['POST'])
def add_patient():
    data = request.json
    user_id = data.get('id')
    status = data.get('status')
    last_checkin = data.get('lastCheckin')

    if not user_id:
        return jsonify({'error': 'User ID is required'}), 400

    try:
        # Use SQLAlchemy to find the user by ID
        user_to_update = User.query.get(user_id)

        if not user_to_update:
            return jsonify({'error': 'User not found'}), 404

        # Update the user's details using object attributes
        user_to_update.role_id = 1  # 1 is the ID for the 'Patient' role
        user_to_update.status = status
        user_to_update.last_checkin = last_checkin

        # Commit the changes to the database
        db.session.commit()

        # Format the updated user data to return in the response
        updated_user_data = {
            "id": user_to_update.id,
            "name": user_to_update.username,
            "role_id": user_to_update.role_id,
            "status": user_to_update.status,
            "last_checkin": user_to_update.last_checkin
        }
        
        return jsonify({'message': 'Patient details updated successfully', 'patient': updated_user_data}), 200

    except Exception as e:
        db.session.rollback()  # Roll back the session on error
        return jsonify({'error': str(e)}), 500
@app.route('/api/patients/<string:patient_id>', methods=['PUT'])
def update_patient(patient_id):
    data = request.json
    status = data.get('status')
    last_checkin_str = data.get('lastCheckin')  # Get the string value

    try:
        # Check if the datetime string is provided
        if last_checkin_str:
            # Convert the string to a datetime object
            # The format string must match how your frontend sends the date
            # Example format: '2025-09-10T20:30:50'
            last_checkin = datetime.fromisoformat(last_checkin_str.replace('Z', ''))
        else:
            last_checkin = None
            
        # Use SQLAlchemy to find the patient by ID
        patient_to_update = User.query.get(patient_id)

        if not patient_to_update:
            return jsonify({'error': 'Patient not found'}), 404

        # Update the patient's details
        patient_to_update.status = status
        patient_to_update.last_checkin = last_checkin

        # Commit the changes to the database
        db.session.commit()
        
        # Format the updated patient data to return in the response
        updated_patient_data = {
            "id": patient_to_update.id,
            "name": patient_to_update.username,
            "status": patient_to_update.status,
            "last_checkin": patient_to_update.last_checkin.isoformat() if patient_to_update.last_checkin else None
        }
        
        return jsonify({'message': 'Patient details updated successfully', 'patient': updated_patient_data}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Set your API key (better:environment variable)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.route("/api/chat/ai", methods=["POST"])
def ai_chat():
    data = request.get_json()
    user_message = data.get("message", "")

    # Error handling: block empty messages
    if not user_message.strip():
        return jsonify({"response": "Please enter a question."}), 400

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # good for chatbots
            messages=[
                {"role": "system", "content": "You are a maternal healthcare assistant. Provide accurate, structured, and safe health guidance in simple language."},
                {"role": "user", "content": user_message}
            ],
            max_tokens=300,
            temperature=0.4
        )

        ai_reply = response.choices[0].message.content
        return jsonify({"response": ai_reply})

    except Exception as e:
        return jsonify({"error": str(e), "response": "I am unable to generate a response at the moment."}), 500
    
with app.app_context():
    db.create_all()
    print("Database tables created!")

if __name__ == '__main__':
    app.run(debug=True)
