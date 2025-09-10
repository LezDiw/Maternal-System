from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL
import MySQLdb.cursors
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

load_dotenv("app.env")
print("API Key Loaded:", os.getenv("OPENAI_API_KEY") is not None)

app = Flask(__name__)
app.secret_key = 'yoursecretkey'

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

if 'CLEARDB_DATABASE_URL' in os.environ:
    # Production database from Heroku Add-on
    url = os.environ.get('CLEARDB_DATABASE_URL')
    app.config['MYSQL_HOST'] = url.split('@')[1].split(':')[0]
    app.config['MYSQL_USER'] = url.split(':')[1][2:]
    app.config['MYSQL_PASSWORD'] = url.split(':')[2].split('@')[0]
    app.config['MYSQL_DB'] = url.split('/')[3].split('?')[0]
    # This is the crucial line: set SQLAlchemy URI from the environment variable
    app.config['SQLALCHEMY_DATABASE_URI'] = url
else:
    # Local development database
    app.config['MYSQL_HOST'] = 'localhost'
    app.config['MYSQL_USER'] = 'root'
    app.config['MYSQL_PASSWORD'] = 'E_lizabeth03'
    app.config['MYSQL_DB'] = 'maternal_care_system'
    # This is the crucial line: set SQLAlchemy URI with local credentials
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://{}:{}@{}/{}'.format(
        app.config['MYSQL_USER'],
        app.config['MYSQL_PASSWORD'],
        app.config['MYSQL_HOST'],
        app.config['MYSQL_DB']
    )

# Now, initialize both the MySQL and SQLAlchemy instances AFTER all configurations are set.
mysql = MySQL(app)
db = SQLAlchemy(app)

class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sender_id = db.Column(db.Integer, nullable=False)
    receiver_id = db.Column(db.Integer)  # Corrected to match table
    content = db.Column(db.Text, nullable=False) # Corrected to match table
    sent_at = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp())

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

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password_hash']
        role = request.form['role_id']

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT id FROM roles WHERE role_name=%s", (role,))
        role_row = cursor.fetchone()

        if not role_row:
            flash("Invalid role", "error")
            return redirect(url_for('login_page'))

        role_id = role_row['id']
        cursor.execute(
            "SELECT * FROM users WHERE username=%s AND password_hash=%s AND role_id=%s",
            (username, password, role_id)
        )
        user = cursor.fetchone()

        if user:
            session['loggedin'] = True
            session['id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role_id']

            # Redirect based on role
            if role == "Patient":
                return redirect(url_for('patient_dashboard'))
            elif role == "Family of Expectant Mother":
                return redirect(url_for('family_dashboard'))
            elif role == "Healthcare Provider":
                return redirect(url_for('healthcare_dashboard'))
            else:
                flash("Incorrect username, password, or role", "error")
                return redirect(url_for('login_page'))
        else:
            flash("Incorrect username, password, or role", "error")
            return render_template('Login.html')
    
    # This part handles the GET request for the login page
    return render_template('Patient.html')

# Registration route
@app.route('/register', methods=['POST'])
def register():
    username = request.form['username']
    email = request.form['email']
    password = request.form['password_hash']
    role = request.form['role_id']

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Check if username exists
    cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
    account = cursor.fetchone()

    if account:
        flash("Username already exists", "error")
        return redirect(url_for('home_page'))
    elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
        flash("Invalid email address", "error")
        return redirect(url_for('home_page'))
    elif not username or not password or not email or not role:
        flash("Please fill out the form completely", "error")
        return redirect(url_for('home_page'))
    else:
        # Look up role_id from roles table
        cursor.execute("SELECT id FROM roles WHERE role_name=%s", (role,))
        role_row = cursor.fetchone()
        if not role_row:
            flash("Invalid role selected", "error")
            return redirect(url_for('home_page'))

        role_id = role_row['id']

        cursor.execute(
            "INSERT INTO users (username, email, password_hash, role_id) VALUES (%s, %s, %s, %s)",
            (username, email, password, role_id)
        )
        mysql.connection.commit()
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
    if 'loggedin' in session:
       # return render_template('Patient.html' , firebase_config=json.dumps(firebase_config))
        return redirect(url_for('login'))

@app.route('/family')
def family_dashboard():
    return render_template('FamilyFriend.html')

@app.route('/healthcare')
def healthcare_dashboard():
    return render_template('HealthCareProvider.html')

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
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT id, username, email FROM users WHERE role_id = (SELECT id FROM roles WHERE role_name='Healthcare Provider')")
    doctors = cursor.fetchall()
    cursor.close()

    # Format doctors for the frontend
    doctor_list = [
        {"id": doc["id"], "name": doc["username"], "specialization": "Healthcare Provider"}
        for doc in doctors
    ]
    return jsonify(doctor_list)

# New route to get all users from the database
@app.route('/api/users', methods=['GET'])
def get_all_users():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT id, username AS name, role_id FROM users")
    users = cursor.fetchall()
    cursor.close()
    return jsonify(users)

# Route to get all patients (role_id = 1)
@app.route('/api/patients', methods=['GET'])
def get_patients():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT id, username AS name, role_id, status, last_checkin FROM users WHERE role_id = 1")
    patients = cursor.fetchall()
    cursor.close()
    return jsonify(patients)

# New route to get healthcare providers (role_id = 3)
@app.route('/api/providers', methods=['GET'])
def get_providers():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT id, username AS name, role_id FROM users WHERE role_id = 3")
    providers = cursor.fetchall()
    cursor.close()
    return jsonify(providers)

# New route to update a user's role to patient
@app.route('/api/add_patient', methods=['POST'])
def add_patient():
    data = request.json
    user_id = data.get('id')
    status = data.get('status')
    last_checkin = data.get('lastCheckin')

    if not user_id:
        return jsonify({'error': 'User ID is required'}), 400

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Update the user's details
    try:
        cursor.execute(
            "UPDATE users SET role_id = 1, status = %s, last_checkin = %s WHERE id = %s",
            (status, last_checkin, user_id)
        )
        mysql.connection.commit()
        
        # Fetch the updated user to return in the response
        cursor.execute("SELECT id, username AS name, role_id, status, last_checkin FROM users WHERE id = %s", (user_id,))
        updated_user = cursor.fetchone()
        cursor.close()
        
        return jsonify({'message': 'Patient details updated successfully', 'patient': updated_user}), 200
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'error': str(e)}), 500
    # New route to update an existing patient's details
@app.route('/api/patients/<string:patient_id>', methods=['PUT'])
def update_patient(patient_id):
    data = request.json
    status = data.get('status')
    last_checkin = data.get('lastCheckin')

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    try:
        cursor.execute(
            "UPDATE users SET status = %s, last_checkin = %s WHERE id = %s",
            (status, last_checkin, patient_id)
        )
        mysql.connection.commit()
        
        cursor.execute("SELECT id, username AS name, status, last_checkin FROM users WHERE id = %s", (patient_id,))
        updated_patient = cursor.fetchone()
        cursor.close()
        
        return jsonify({'message': 'Patient details updated successfully', 'patient': updated_patient}), 200
    except Exception as e:
        mysql.connection.rollback()
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
            model="gpt-4o-mini",   # good for chatbots
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

if __name__ == '__main__':
    app.run(debug=True)
