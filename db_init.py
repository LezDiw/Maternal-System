import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# This config is only for the script to connect to the database.
# It uses the same logic as your main app.
app = Flask(__name__)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

if 'JAWSDB_URL' in os.environ:
    url = os.environ.get('JAWSDB_URL')
    url = url.replace("mysql://", "mysql+mysqlconnector://")
    app.config['SQLALCHEMY_DATABASE_URI'] = url
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root:E_lizabeth03@localhost/maternal_care_system'

db = SQLAlchemy(app)

# Database Models - Copied from app.py to make this file standalone
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

def initialize_database():
    """Initializes the database tables and populates default roles."""
    with app.app_context():
        # Create all tables defined in your models
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
                print(f"Adding role: {role_name}")
        
        try:
            db.session.commit()
            print("Default roles populated!")
        except Exception as e:
            db.session.rollback()
            print(f"Error populating roles: {e}")
            
if __name__ == '__main__':
    initialize_database()
