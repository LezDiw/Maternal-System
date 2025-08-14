from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL
import MySQLdb.cursors
import re

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
    password = request.form['password']
    role = request.form['role']

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute(
        "SELECT * FROM users WHERE username=%s AND password=%s AND role=%s",
        (username, password, role)
    )
    user = cursor.fetchone()

    if user:
        session['loggedin'] = True
        session['id'] = user['id']
        session['username'] = user['username']
        session['role'] = user['role']

        # Redirect based on role
        if role == "Patient":
            return redirect(url_for('patient_dashboard'))
        elif role == "Family":
            return redirect(url_for('family_dashboard'))
        elif role == "Healthcare":
            return redirect(url_for('healthcare_dashboard'))
    else:
        flash("Incorrect username, password, or role", "error")
        return redirect(url_for('home'))

# Registration route
@app.route('/register', methods=['POST'])
def register():
    username = request.form['username']
    email = request.form['email']
    password = request.form['password']
    role = request.form['role']

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Check if username exists
    cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
    account = cursor.fetchone()

    if account:
        flash("Username already exists", "error")
        return redirect(url_for('home'))
    elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
        flash("Invalid email address", "error")
        return redirect(url_for('home'))
    elif not username or not password or not email or not role:
        flash("Please fill out the form completely", "error")
        return redirect(url_for('home'))
    else:
        cursor.execute(
            "INSERT INTO users (username, email, password, role) VALUES (%s, %s, %s, %s)",
            (username, email, password, role)
        )
        mysql.connection.commit()
        flash("You have successfully registered!", "success")
        return redirect(url_for('home'))

# Dashboards
@app.route('/patient')
def patient_dashboard():
    return render_template('Patient.html')

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
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
