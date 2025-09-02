from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL
import MySQLdb.cursors
import re
import requests
from flask import jsonify, request
import json

firebase_config = {
    "apiKey": "AIzaSyC3N9k_h5A8vrJJvJHSEnC-iynNMUHUkG4",
    "authDomain": "maternal-care-app-33eac.firebaseapp.com",
    "projectId": "maternal-care-app-33eac",
    "storageBucket": "maternal-care-app-33eac.appspot,com",
    "messagingSenderId": "199844547762",
    "appId": "1:199844547762:web:940f687ec11b3b5d8c0dab",
    "measurementId": "G-EQYXFVCWHK"
  };

app = Flask(__name__)
app.secret_key = 'yoursecretkey'


# MySQL configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root' 
app.config['MYSQL_PASSWORD'] = 'E_lizabeth03' 
app.config['MYSQL_DB'] = 'maternal_care_system'

mysql = MySQL(app)

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
@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password_hash']
    role = request.form['role']

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    # Look up role_id from role_name
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
        elif  role== "Healthcare Provider":
            return redirect(url_for('healthcare_dashboard'))
        else:
         #flash("Incorrect username, password, or role", "error")
            return redirect(url_for('login-page'))

# Registration route
@app.route('/register', methods=['POST'])
def register():
    username = request.form['username']
    email = request.form['email']
    password = request.form['password_hash']
    role = request.form['role']

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

# Dashboards
@app.route('/patient')
def patient_dashboard():
    if 'loggedin' in session:
        return render_template('Patient.html' , firebase_config=json.dumps(firebase_config))
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
    session.pop('role', None)
    flash("You have been logged out", "info")
    return redirect(url_for('home_page'))

@app.route('/api/chat/ai', methods=['POST'])
def chat_with_ai():
    data = request.json
    user_message = data.get('message')

    if not user_message:
        return jsonify({'error': 'No message provided'}), 400

    try:
        # Replace with the actual URL and your API key for the AI service you choose
        # For this example, we'll use a placeholder for Google's Gemini API
        API_KEY = "YOUR_GEMINI_API_KEY"
        API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={API_KEY}"

        # Prepare the request payload for the AI model
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": user_message}
                    ]
                }
            ]
        }

        headers = {
            "Content-Type": "application/json"
        }

        # Send the request to the AI service
        response = requests.post(API_URL, json=payload, headers=headers)
        response.raise_for_status()  # Raise an exception for bad status codes

        ai_response_text = response.json()['candidates'][0]['content']['parts'][0]['text']

        return jsonify({'response': ai_response_text})

    except Exception as e:
        print(f"Error communicating with AI service: {e}")
        return jsonify({'error': 'Failed to get a response from the AI agent.'}), 500

if __name__ == '__main__':
    app.run(debug=True)
