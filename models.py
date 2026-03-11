from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

# ---------------- USER ----------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # admin / student / company
    status = db.Column(db.String(50), default="Active")


# ---------------- STUDENT PROFILE ----------------
class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    contact = db.Column(db.String(20), nullable=False)
    resume = db.Column(db.String(200))
    branch = db.Column(db.String(100),nullable=False)
    cgpa = db.Column(db.Float,nullable=False)
    year = db.Column(db.String(10))
    user = db.relationship("User", backref="student_profile")
    applications = db.relationship("Application", backref="student", cascade="all, delete")


# ---------------- COMPANY PROFILE ----------------
class Company(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    company_name = db.Column(db.String(150), nullable=False)
    hr_contact = db.Column(db.String(20),nullable=False)
    website = db.Column(db.String(200),nullable=False)
    approval_status = db.Column(db.String(50), default="Pending")
    user = db.relationship("User", backref="company_profile")
    placement_drives = db.relationship("PlacementDrive", backref="company", cascade="all, delete")


# ---------------- PLACEMENT DRIVE ----------------
class PlacementDrive(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_title = db.Column(db.String(150), nullable=False)
    job_description = db.Column(db.Text, nullable=False)
    eligibility = db.Column(db.Float, nullable=False)
    deadline = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(50), default="Pending")
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    applications = db.relationship("Application",backref="drive",lazy=True,cascade="all, delete")

# ---------------- APPLICATION ----------------
class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    application_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default="Applied")
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    drive_id = db.Column(db.Integer, db.ForeignKey('placement_drive.id'), nullable=False)
    resume_file = db.Column(db.String(200))
    __table_args__ = (db.UniqueConstraint('student_id', 'drive_id', name='unique_application'),)