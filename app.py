from flask import Flask, render_template, request
from flask_mysqldb import MySQL

app = Flask(__name__)

# Connect Flask to the MySQL DB you created above
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'E_lizabeth03'  # your MySQL password
app.config['MYSQL_DB'] = 'maternal_care_system'

mysql = MySQL(app)
