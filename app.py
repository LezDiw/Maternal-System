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
CORS(app)

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

# Database Models
class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sender_id = db.Column(db.Integer, nullable=False)
    receiver_id = db.Column(db.Integer)
    content = db.Column(db.Text, nullable=False)
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

# Debug route to check database status
@app.route('/debug/db')
def debug_database():
    try:
        # Test connection
        db.session.execute(db.text('SELECT 1'))
        
        # Check roles
        roles = Role.query.all()
        roles_info = [{"id": r.id, "name": r.role_name} for r in roles]
        
        # Check users
        users = User.query.all()
        users_info = [{"id": u.id, "username": u.username, "role_id": u.role_id} for u in users]
        
        return jsonify({
            "database_connected": True,
            "roles": roles_info,
            "users": users_info,
            "total_users": len(users_info)
        })
    except Exception as e:
        return jsonify({
            "database_connected": False,
            "error": str(e)
        }), 500
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

# FIXED LOGIN ROUTE
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password_hash')
        role_name = request.form.get('role_id')

        print(f"🔍 Login attempt - Username: {username}, Role: {role_name}")

        # Validate input
        if not username or not password or not role_name:
            print("❌ Missing required fields")
            flash("Please fill out all fields", "error")
            return render_template('Login.html')

        # Find the role by name
        role = Role.query.filter_by(role_name=role_name).first()
        if not role:
            print(f"❌ Role not found: {role_name}")
            flash("Invalid role selected", "error")
            return render_template('Login.html')

        print(f"✅ Found role - ID: {role.id}, Name: {role.role_name}")

        # Find the user by username and role_id
        user = User.query.filter_by(username=username, role_id=role.id).first()
        if not user:
            print(f"❌ User not found with username '{username}' and role_id {role.id}")
            flash("Invalid username or role combination", "error")
            return render_template('Login.html')

        print(f"✅ Found user - ID: {user.id}, Username: {user.username}")

        # Verify password
        if bcrypt.check_password_hash(user.password_hash, password):
            print("✅ Password verification successful")
            
            # Set session variables
            session['loggedin'] = True
            session['id'] = user.id
            session['username'] = user.username
            session['role'] = user.role_id
            session['role_name'] = role.role_name

            # --- DEBUGGING PRINT STATEMENT ADDED HERE ---
            print(f"✅ Session created - User ID: {session['id']}, Role: {session['role_name']}, Stored Role ID: {session['role']}")

            # Redirect based on role name
            if role.role_name == "Patient":
                print("🏥 Redirecting to patient dashboard")
                return redirect(url_for('patient_dashboard'))
            elif role.role_name == "Family of Expectant Mother":
                print("👨‍👩‍👧‍👦 Redirecting to family dashboard")
                return redirect(url_for('family_dashboard'))
            elif role.role_name == "Healthcare Provider":
                print("👩‍⚕️ Redirecting to healthcare dashboard")
                return redirect(url_for('healthcare_dashboard'))
            else:
                print(f"❌ Unknown role: {role.role_name}")
                flash("Unknown role", "error")
                return render_template('Login.html')
        else:
            print("❌ Password verification failed")
            flash("Invalid password", "error")
            return render_template('Login.html')

    # GET request - show login page
    print("📄 Displaying login page")
    return render_template('Login.html')

# REGISTER ROUTE
@app.route('/register', methods=['POST'])
def register():
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password_hash')
    role_name = request.form.get('role_id')

    # Validate input
    if not all([username, email, password, role_name]):
        flash("Please fill out the form completely", "error")
        return redirect(url_for('home_page'))

    # Check if username already exists
    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        flash("Username already exists", "error")
        return redirect(url_for('home_page'))

    # Validate email format
    if not re.match(r'[^@]+@[^@]+\.[^@]+', email):
        flash("Invalid email address", "error")
        return redirect(url_for('home_page'))

    # Check if email already exists
    existing_email = User.query.filter_by(email=email).first()
    if existing_email:
        flash("Email already registered", "error")
        return redirect(url_for('home_page'))

    # Look up role_id from roles table
    role = Role.query.filter_by(role_name=role_name).first()
    if not role:
        flash("Invalid role selected", "error")
        return redirect(url_for('home_page'))
    
    # Hash the password before storing
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    
    try:
        # Create a new user instance and add to the database
        new_user = User(
            username=username, 
            email=email, 
            password_hash=hashed_password,
            role_id=role.id
        )
        db.session.add(new_user)
        db.session.commit()
        
        flash("You have successfully registered! Please log in.", "success")
        return redirect(url_for('login_page'))
    
    except Exception as e:
        db.session.rollback()
        flash("Registration failed. Please try again.", "error")
        return redirect(url_for('home_page'))

# DASHBOARD ROUTES - SIMPLIFIED AND FIXED
@app.route('/patient')
def patient_dashboard():
    # --- DEBUGGING PRINT STATEMENT ADDED HERE ---
    print(f"➡️ Entering patient dashboard. Session role: {session.get('role')}, Session loggedin: {session.get('loggedin')}")

    # Check if user is logged in
    if 'loggedin' not in session:
        flash("Please log in to access the dashboard", "error")
        return redirect(url_for('login_page'))
    
    # Use the role_id to check the user's role
    patient_role_id = Role.query.filter_by(role_name='Patient').first().id
    if session.get('role') != patient_role_id:
        flash("Access denied. Incorrect role.", "error")
        return redirect(url_for('login_page'))
    
    return render_template('Patient.html')

@app.route('/family')
def family_dashboard():
    # --- DEBUGGING PRINT STATEMENT ADDED HERE ---
    print(f"➡️ Entering family dashboard. Session role: {session.get('role')}, Session loggedin: {session.get('loggedin')}")

    # Check if user is logged in
    if 'loggedin' not in session:
        flash("Please log in to access the dashboard", "error")
        return redirect(url_for('login_page'))
    
    # Use the role_id to check the user's role
    family_role_id = Role.query.filter_by(role_name='Family of Expectant Mother').first().id
    if session.get('role') != family_role_id:
        flash("Access denied. Incorrect role.", "error")
        return redirect(url_for('login_page'))
    
    return render_template('FamilyFriend.html')

@app.route('/healthcare')
def healthcare_dashboard():
    # --- DEBUGGING PRINT STATEMENT ADDED HERE ---
    print(f"➡️ Entering healthcare dashboard. Session role: {session.get('role')}, Session loggedin: {session.get('loggedin')}")

    # Check if user is logged in
    if 'loggedin' not in session:
        flash("Please log in to access the dashboard", "error")
        return redirect(url_for('login_page'))
    
    # Use the role_id to check the user's role
    provider_role_id = Role.query.filter_by(role_name='Healthcare Provider').first().id
    if session.get('role') != provider_role_id:
        flash("Access denied. Incorrect role.", "error")
        return redirect(url_for('login_page'))
    
    return render_template('HealthCareProvider.html')

# LOGOUT ROUTE
@app.route('/logout')
def logout():
    session.clear() 
    flash("You have been logged out successfully", "info")
    return redirect(url_for('home_page'))

# MESSAGE API ROUTES
@app.route('/api/chat/send', methods=['POST'])
def send_message():
    data = request.json
    sender_id_str = data.get('sender_id')
    receiver_id_str = data.get('receiver_id')
    message_content = data.get('message')

    # Validate required fields
    if not all([sender_id_str, receiver_id_str, message_content]):
        return jsonify({"error": "Missing required fields"}), 400

    # Convert IDs to integers
    try:
        sender_id = int(sender_id_str)
        receiver_id = int(receiver_id_str)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid sender_id or receiver_id format"}), 400

    try:
        # Create and save new message
        new_message = Message(
            sender_id=sender_id,
            receiver_id=receiver_id,
            content=message_content
        )
        db.session.add(new_message)
        db.session.commit()

        return jsonify({"status": "success", "message": "Message sent"}), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/chat/history/<user_id>/<recipient_id>', methods=['GET'])
def get_chat_history(user_id, recipient_id):
    try:
        user_id_int = int(user_id)
        recipient_id_int = int(recipient_id)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid user ID or recipient ID"}), 400

    # Query for messages between the two users
    messages = Message.query.filter(
        db.or_(
            db.and_(Message.sender_id == user_id_int, Message.receiver_id == recipient_id_int),
            db.and_(Message.sender_id == recipient_id_int, Message.receiver_id == user_id_int)
        )
    ).order_by(Message.sent_at.asc()).all()

    # Format messages for frontend
    messages_list = [{
        "sender_id": m.sender_id,
        "receiver_id": m.receiver_id,
        "message": m.content,
        "timestamp": m.sent_at.isoformat()
    } for m in messages]

    return jsonify(messages_list)

# USER API ROUTES
@app.route('/get_doctors')
def get_doctors():
    provider_role = Role.query.filter_by(role_name='Healthcare Provider').first()
    
    if not provider_role:
        return jsonify({"error": "Healthcare Provider role not found"}), 404

    doctors = User.query.filter_by(role_id=provider_role.id).all()

    doctor_list = [
        {"id": doc.id, "name": doc.username, "specialization": "Healthcare Provider"}
        for doc in doctors
    ]
    
    return jsonify(doctor_list)

@app.route('/api/users', methods=['GET'])
def get_all_users():
    users = User.query.with_entities(User.id, User.username, User.role_id).all()
    
    users_list = [
        {"id": user.id, "name": user.username, "role_id": user.role_id} 
        for user in users
    ]
    
    return jsonify(users_list)

@app.route('/api/patients', methods=['GET'])
def get_patients():
    patients = User.query.with_entities(
        User.id, 
        User.username.label('name'), 
        User.role_id, 
        User.status, 
        User.last_checkin
    ).filter_by(role_id=1).all()

    patients_list = [
        {
            "id": patient.id,
            "name": patient.name,
            "role_id": patient.role_id,
            "status": patient.status,
            "last_checkin": patient.last_checkin.isoformat() if patient.last_checkin else None
        }
        for patient in patients
    ]

    return jsonify(patients_list)

@app.route('/api/providers', methods=['GET'])
def get_providers():
    providers = User.query.with_entities(
        User.id, 
        User.username.label('name'), 
        User.role_id
    ).filter_by(role_id=3).all()
    
    providers_list = [
        {"id": provider.id, "name": provider.name, "role_id": provider.role_id}
        for provider in providers
    ]
    
    return jsonify(providers_list)

@app.route('/api/add_patient', methods=['POST'])
def add_patient():
    data = request.json
    user_id = data.get('id')
    status = data.get('status')
    last_checkin = data.get('lastCheckin')

    if not user_id:
        return jsonify({'error': 'User ID is required'}), 400

    try:
        user_to_update = User.query.get(user_id)

        if not user_to_update:
            return jsonify({'error': 'User not found'}), 404

        # Update user details
        user_to_update.role_id = 1 
        user_to_update.status = status
        if last_checkin:
            user_to_update.last_checkin = datetime.fromisoformat(last_checkin.replace('Z', ''))

        db.session.commit()

        updated_user_data = {
            "id": user_to_update.id,
            "name": user_to_update.username,
            "role_id": user_to_update.role_id,
            "status": user_to_update.status,
            "last_checkin": user_to_update.last_checkin.isoformat() if user_to_update.last_checkin else None
        }
        
        return jsonify({'message': 'Patient details updated successfully', 'patient': updated_user_data}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/patients/<string:patient_id>', methods=['PUT'])
def update_patient(patient_id):
    data = request.json
    status = data.get('status')
    last_checkin_str = data.get('lastCheckin')

    try:
        # Parse datetime if provided
        last_checkin = None
        if last_checkin_str:
            last_checkin = datetime.fromisoformat(last_checkin_str.replace('Z', ''))
            
        patient_to_update = User.query.get(patient_id)

        if not patient_to_update:
            return jsonify({'error': 'Patient not found'}), 404

        # Update patient details
        patient_to_update.status = status
        patient_to_update.last_checkin = last_checkin

        db.session.commit()
        
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

# AI CHAT ROUTE
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.route("/api/chat/ai", methods=["POST"])
def ai_chat():
    data = request.get_json()
    user_message = data.get("message", "")

    if not user_message.strip():
        return jsonify({"response": "Please enter a question."}), 400

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
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

# Initialize database and run app
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print("Database tables created!")
        
        # Create default roles if they don't exist
        roles = [
            "Patient",
            "Family of Expectant Mother", 
            "Healthcare Provider"
        ]
        
        for role_name in roles:
            if not Role.query.filter_by(role_name=role_name).first():
                new_role = Role(role_name=role_name)
                db.session.add(new_role)
        
        try:
            db.session.commit()
            print("Default roles created!")
        except Exception as e:
            db.session.rollback()
            print(f"Error creating roles: {e}")
    
    app.run(debug=True)
