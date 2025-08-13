from flask import Flask, render_template, request, redirect, session, flash
from flask_mysqldb import MySQL
import hashlib

app = Flask(__name__)
app.secret_key = 'your-secret-key'

# MySQL configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'E_lizabeth03'
app.config['MYSQL_DB'] = 'maternal_care_system'

mysql = MySQL(app)
@app.route('/login', methods=['GET'])
def login_page():
    return render_template('Login.html')
@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    role = request.form['role']

    cur = mysql.connection.cursor()
    cur.execute("SELECT id, password_hash, role_id FROM users WHERE username = %s", (username,))
    user = cur.fetchone()
    cur.close()

    if user:
        user_id, stored_hash, stored_role_id = user
        input_hash = hashlib.sha256(password.encode()).hexdigest()

        if input_hash == stored_hash:
            session['user_id'] = user_id
            session['username'] = username
            session['role'] = role

            # Role-based redirect (optional)
           

    return "Invalid login credentials."
@app.route('/register', methods=['POST'])
def register():
    username = request.form['username']
    email = request.form['email']
    password = request.form['password']
    role = request.form['role']

    password_hash = hashlib.sha256(password.encode()).hexdigest()

    cur = mysql.connection.cursor()

    # Get or insert role into roles table
    cur.execute("SELECT id FROM roles WHERE role_name = %s", (role,))
    role_row = cur.fetchone()

    if not role_row:
        cur.execute("INSERT INTO roles (role_name) VALUES (%s)", (role,))
        mysql.connection.commit()
        cur.execute("SELECT id FROM roles WHERE role_name = %s", (role,))
        role_row = cur.fetchone()

    role_id = role_row[0]

    # Check for duplicate username/email
    cur.execute("SELECT * FROM users WHERE username = %s OR email = %s", (username, email))
    if cur.fetchone():
        cur.close()
        return "Username or email already exists."

    # Insert into users table
    cur.execute("""
        INSERT INTO users (username, email, password_hash, role_id, full_name)
        VALUES (%s, %s, %s, %s, %s)
    """, (username, email, password_hash, role_id, username))

    mysql.connection.commit()
    cur.close()

    return redirect('/login')
    


