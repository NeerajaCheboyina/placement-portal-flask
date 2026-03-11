from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from config import Config
from models import db, User, Student, Company, PlacementDrive, Application
from datetime import datetime, date, timedelta
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config.from_object(Config)

UPLOAD_FOLDER = "uploads/resumes"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

db.init_app(app)

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)


# ---------------- USER LOADER ----------------
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ---------------- HOME ----------------
@app.route("/")
def home():
    if current_user.is_authenticated:
        if current_user.role == "admin":
            return redirect(url_for("admin_dashboard"))
        elif current_user.role == "student":
            return redirect(url_for("student_dashboard"))
        elif current_user.role == "company":
            return redirect(url_for("company_dashboard"))
    return redirect(url_for("login"))


# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():

    if current_user.is_authenticated:
        if current_user.role == "admin":
            return redirect(url_for("admin_dashboard"))
        elif current_user.role == "student":
            return redirect(url_for("student_dashboard"))
        elif current_user.role == "company":
            return redirect(url_for("company_dashboard"))

    if request.method == "POST":

        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        user = User.query.filter_by(email=email).first()

        if not user or user.password != password:
            flash("Invalid credentials", "danger")
            return redirect(url_for("login"))

        if user.status == "Blacklisted":
            flash("Your account is blacklisted.", "danger")
            return redirect(url_for("login"))

        if user.role == "company":

            company_profile = Company.query.filter_by(user_id=user.id).first()

            if not company_profile:
                flash("Company profile not found.", "danger")
                return redirect(url_for("login"))

            if company_profile.approval_status == "Pending":
                flash("Your company is awaiting admin approval.", "warning")
                return redirect(url_for("login"))

            if company_profile.approval_status == "Rejected":
                flash("Your company registration was rejected.", "danger")
                return redirect(url_for("login"))

        login_user(user)
        flash("Login successful!", "success")

        if user.role == "admin":
            return redirect(url_for("admin_dashboard"))

        elif user.role == "student":
            return redirect(url_for("student_dashboard"))

        elif user.role == "company":
            return redirect(url_for("company_dashboard"))

    return render_template("login.html")


# ---------------- LOGOUT ----------------
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


# ---------------- ADMIN DASHBOARD ----------------
@app.route("/admin")
@login_required
def admin_dashboard():
    if current_user.role != "admin":
        return "Unauthorized Access"

    total_students = Student.query.count()
    total_companies = Company.query.count()
    total_drives = PlacementDrive.query.count()
    total_applications = Application.query.count()

    pending_companies = Company.query.filter_by(approval_status="Pending").all()

    pending_drives = PlacementDrive.query.filter_by(status="Pending").all()

    return render_template("admin_dash.html",total_students=total_students,total_companies=total_companies,total_drives=total_drives,total_applications=total_applications,pending_companies=pending_companies, pending_drives=pending_drives)


# ---------------- ADMIN VIEW STUDENTS ----------------
@app.route("/admin/students")
@login_required
def view_students():
    if current_user.role != "admin":
        return "Unauthorized Access"

    search = request.args.get("search", "")

    if search:
        students = Student.query.filter(
            Student.name.ilike(f"%{search}%")
        ).all()
    else:
        students = Student.query.all()

    return render_template("admin_stud.html", students=students)


#------------------------- ADMIN DELETE STUDENT -------------------------------------------------------------------
@app.route("/admin/delete_student/<int:student_id>")
@login_required
def delete_student(student_id):

    if current_user.role != "admin":
        return "Unauthorized"

    student = Student.query.get_or_404(student_id)

    db.session.delete(student)
    db.session.commit()

    flash("Student deleted")

    return redirect(url_for("view_students"))


# ---------------- ADMIN APPROVE OR REJECT COMPANIES ----------------
@app.route("/admin/company_action/<int:company_id>/<string:action>")
@login_required
def company_action(company_id, action):
    if current_user.role != "admin":
        return "Unauthorized Access"

    company = Company.query.get_or_404(company_id)

    if action == "approve":
        company.approval_status = "Approved"
    elif action == "reject":
        company.approval_status = "Rejected"
    else:
        return "Invalid Action"

    db.session.commit()

    return redirect(url_for("admin_dashboard"))


# ---------------- ADMIN VIEW APPLICATIONS ----------------
@app.route("/admin/applications")
@login_required
def admin_applications():

    if current_user.role != "admin":
        return "Unauthorized Access"

    search = request.args.get("search", "")

    if search:
        applications = (Application.query.join(Student).join(PlacementDrive).join(Company).filter((Student.name.ilike(f"%{search}%")) |(Company.company_name.ilike(f"%{search}%")) |(PlacementDrive.job_title.ilike(f"%{search}%"))).all())
    else:
        applications = Application.query.all()

    return render_template("admin_appl.html", applications=applications)


#---------------------------------------- ADMIN DELETE COMPANY ----------------------------------------
@app.route("/admin/delete_company/<int:company_id>")
@login_required
def delete_company(company_id):

    if current_user.role != "admin":
        return "Unauthorized"

    company = Company.query.get_or_404(company_id)

    db.session.delete(company)
    db.session.commit()

    flash("Company deleted")

    return redirect(url_for("manage_companies"))



# ---------------- ADMIN APPROVE COMPANIES ----------------
@app.route('/admin/companies')
@login_required
def manage_companies():

    search = request.args.get('search')

    if search:
        companies = Company.query.filter(
            Company.company_name.ilike(f"%{search}%")
        ).all()
        if not companies:
            flash("No company found with that name.", "warning")

    else:
        companies = Company.query.all()

    return render_template("admin_comp.html",companies=companies)


# ---------------- ADMIN VIEW PLACEMENT DRIVES ----------------
@app.route("/admin/drives")
@login_required
def view_drives():

    if current_user.role != "admin":
        return "Unauthorized Access"

    search = request.args.get("search", "")

    if search:
        drives = PlacementDrive.query.filter(
            PlacementDrive.job_title.ilike(f"%{search}%")
        ).all()
    else:
        drives = PlacementDrive.query.all()

    return render_template("admin_drives.html", drives=drives)


# ---------------- ADMIN APPROVE DRIVES ----------------------
@app.route("/admin/approve_drive/<int:drive_id>")
@login_required
def approve_drive(drive_id):
    if current_user.role != "admin":
        return "Unauthorized Access"

    drive = PlacementDrive.query.get(drive_id)
    drive.status = "Approved"
    db.session.commit()

    return redirect(url_for("view_drives"))


# ---------------- ADMIN REJECT DRIVES ---------------------
@app.route("/admin/reject_drive/<int:drive_id>")
@login_required
def reject_drive(drive_id):

    drive = PlacementDrive.query.get_or_404(drive_id)

    drive.status = "Rejected"
    db.session.commit()

    return redirect(url_for("view_drives"))


# ---------------- ADMIN BLOCK COMP ND STUD ----------------
@app.route("/admin/block/<int:user_id>")
@login_required
def block_user(user_id):
    if current_user.role != "admin":
        return "Unauthorized Access"

    user = User.query.get(user_id)
    user.status = "Blacklisted"
    db.session.commit()

    return redirect(request.referrer)


# ---------------- ADMIN UNBLOVK STUD ND COMP ----------------
@app.route("/admin/unblock/<int:user_id>")
@login_required
def unblock_user(user_id):

    if current_user.role != "admin":
        return "Unauthorized Access"

    user = User.query.get_or_404(user_id)

    user.status = "Active"
    db.session.commit()

    flash("User unblocked successfully!", "success")

    return redirect(request.referrer)


# ---------------- STUDENT DASHBOARD ----------------
@app.route('/student/dashboard')
@login_required
def student_dashboard():

    student = Student.query.filter_by(user_id=current_user.id).first()

    if not student:
        flash("Student profile not found.")
        return redirect(url_for("login"))

    drives_count = PlacementDrive.query.filter_by(status="Approved").count()
    applications = Application.query.filter_by(student_id=student.id).all()
    
    applications_count = len(applications)
    pending_count = len([a for a in applications if a.status == "Applied"])
    selected_count = len([a for a in applications if a.status == "Selected"])

    today = date.today()
    upcoming_deadline = today + timedelta(days=5)
    urgent_drives = PlacementDrive.query.filter(PlacementDrive.status == "Approved",PlacementDrive.deadline >= today,PlacementDrive.deadline <= upcoming_deadline).all()

    return render_template("stud_dash.html",student=student,drives_count=drives_count,applications_count=applications_count,pending_count=pending_count,selected_count=selected_count,urgent_drives=urgent_drives)


#----------------------------------- STUDENT VIEWING DRIVES -----------------------------
@app.route('/student/drives')
@login_required
def student_drives():

    drives = PlacementDrive.query.filter_by(status="Approved").all()

    student = Student.query.filter_by(user_id=current_user.id).first()

    applications = Application.query.filter_by(student_id=student.id).all()

    applied_drives = [app.drive_id for app in applications]

    today = date.today()

    return render_template("stud_drives.html",drives=drives,applied_drives=applied_drives,student=student,today=date.today())


#---------------------------------- STUDENT APPLYING TO DRIVES ----------------------------
@app.route('/student/apply/<int:drive_id>')
@login_required
def apply_drive(drive_id):

    student = Student.query.filter_by(user_id=current_user.id).first()

    existing = Application.query.filter_by(
        student_id=student.id,
        drive_id=drive_id
    ).first()

    if existing:
        flash("You have already applied", "warning")
        return redirect(url_for('student_drives'))

    drive = PlacementDrive.query.get_or_404(drive_id)

    if drive.deadline and drive.deadline < datetime.today().date():
        flash("Application deadline has passed")
        return redirect(url_for("student_drives"))

    if float(student.cgpa) < float(drive.eligibility):
        flash("You are not eligible for this drive due to CGPA criteria.", "warning")
        return redirect(url_for("student_drives"))

    new_application = Application(student_id=student.id,drive_id=drive_id,resume_file=student.resume,status="Applied")

    db.session.add(new_application)
    db.session.commit()

    flash("Application submitted successfully", "success")

    return redirect(url_for('student_drives'))

# ----------------STUDENT APPLICATIONS----------------
@app.route("/student/applications")
@login_required
def my_applications():

    if current_user.role != "student":
        return redirect(url_for("admin_dashboard"))

    student = Student.query.filter_by(user_id=current_user.id).first()

    if not student:
        flash("Student profile not found.", "danger")
        return redirect(url_for("student_dashboard"))

    applications = Application.query.filter_by(student_id=student.id).all()

    return render_template("stud_appl.html", applications=applications)


#---------------------------------- STUDENT PROFILE EDIT ------------------------------------ 
@app.route("/student/edit_profile", methods=["GET","POST"])
@login_required
def edit_student_profile():

    if current_user.role != "student":
        return "Unauthorized"

    student = Student.query.filter_by(user_id=current_user.id).first()

    if request.method == "POST":
        student.name = request.form.get("name")
        student.contact = request.form.get("contact")
        student.branch = request.form.get("branch")
        student.cgpa = request.form.get("cgpa")
        student.year = request.form.get("year")

        resume_file = request.files.get("resume")

        if resume_file and resume_file.filename != "":
            filename = secure_filename(resume_file.filename)
            upload_path = os.path.join("static/resumes", filename)
            resume_file.save(upload_path)
            student.resume = filename

        db.session.commit()

        flash("Profile updated successfully")
        return redirect(url_for("student_dashboard"))

    return render_template("edit_student.html", student=student)


#------------------ STUDENT'S HISTORY -----------------------------------------------------------------
@app.route("/student/history")
@login_required
def placement_history():

    if current_user.role != "student":
        return "Unauthorized"

    student = Student.query.filter_by(user_id=current_user.id).first()

    applications = Application.query.filter_by(student_id=student.id,status="Selected").all()

    return render_template("placement_history.html", applications=applications)


# ---------------- COMPANY DASHBOARD ----------------
@app.route("/company/dashboard")
@login_required
def company_dashboard():

    if current_user.role != "company":
        return "Unauthorized Access"

    company = Company.query.filter_by(user_id=current_user.id).first()

    drives = PlacementDrive.query.filter_by(company_id=company.id).all()

    total_drives = len(drives)

    total_applications = Application.query.join(PlacementDrive).filter(
        PlacementDrive.company_id == company.id
    ).count()

    approved_drives = PlacementDrive.query.filter_by(
        company_id=company.id, status="Approved"
    ).count()

    pending_drives = PlacementDrive.query.filter_by(
        company_id=company.id, status="Pending"
    ).count()

    return render_template("comp_dash.html",company=company,drives=drives,total_drives=total_drives,total_applications=total_applications,approved_drives=approved_drives,pending_drives=pending_drives)


# ---------------- COMPANY CREATE DRIVES ----------------  
from datetime import datetime, date, timedelta

@app.route("/company/create_drive", methods=["GET", "POST"])
@login_required
def create_drive():

    if current_user.role != "company":
        return "Unauthorized Access"

    company = Company.query.filter_by(user_id=current_user.id).first()

    if request.method == "POST":

        deadline = datetime.strptime(request.form.get("deadline"), "%Y-%m-%d").date()

        if deadline < date.today() + timedelta(days=1):
            flash("Deadline must be at least tomorrow.", "warning")
            return redirect(url_for("create_drive"))

        new_drive = PlacementDrive(job_title=request.form.get("job_title"),job_description=request.form.get("job_description"),eligibility=float(request.form.get("eligibility")),deadline=deadline,company_id=company.id )

        db.session.add(new_drive)
        db.session.commit()

        flash("Placement drive created successfully!", "success")

        return redirect(url_for("company_dashboard"))

    tomorrow = date.today() + timedelta(days=1)

    return render_template("create_drive.html", tomorrow=tomorrow)

#------------------------------COMPANY EDIT PROFILE ---------------------------------
@app.route("/company/edit_profile", methods=["GET","POST"])
@login_required
def edit_company_profile():

    if current_user.role != "company":
        return "Unauthorized"

    company = Company.query.filter_by(user_id=current_user.id).first()

    if request.method == "POST":

        company.company_name = request.form.get("company_name")
        company.hr_contact = request.form.get("hr_contact")
        company.website = request.form.get("website")

        db.session.commit()

        flash("Company profile updated")
        return redirect(url_for("company_dashboard"))

    return render_template("edit_company.html", company=company)


#------------------------------COMPANY EDIT DRIVE------------------------
@app.route("/company/edit_drive/<int:drive_id>", methods=["GET", "POST"])
@login_required
def edit_drive(drive_id):
    if current_user.role != "company":
        return "Unauthorized Access"

    drive = PlacementDrive.query.get_or_404(drive_id)

    applications_exist = Application.query.filter_by(drive_id=drive.id).first()

    if applications_exist:
        flash("Drive cannot be edited once students have applied !!", "warning")
        return redirect(url_for("company_dashboard"))

    if request.method == "POST":
        drive.job_title = request.form.get("job_title")
        drive.job_description = request.form.get("job_description")
        drive.eligibility = float(request.form.get("eligibility"))
        deadline = datetime.strptime(request.form.get("deadline"), "%Y-%m-%d").date()
        drive.deadline = deadline

        db.session.commit()

        flash("Drive updated successfully!", "success")
        return redirect(url_for("company_dashboard"))

    return render_template("edit_drive.html", drive=drive)


#------------------------------- COMPANY DELETES DRIVE ------------------------------------------------------
@app.route("/company/close_drive/<int:drive_id>")
@login_required
def close_drive(drive_id):

    if current_user.role != "company":
        return "Unauthorized"

    drive = PlacementDrive.query.get_or_404(drive_id)

    drive.status = "Closed"

    db.session.commit()

    flash("Drive closed successfully")

    return redirect(url_for("company_dashboard"))


#------------------------------- COMPANY DELETE DRIVE -----------------------------
@app.route("/company/delete_drive/<int:drive_id>")
@login_required
def delete_drive(drive_id):
    if current_user.role != "company":
        return "Unauthorized Access"

    drive = PlacementDrive.query.get_or_404(drive_id)
    db.session.delete(drive)
    db.session.commit()

    return redirect(url_for("company_dashboard"))

#---------------------------------- COMPANY VIEW STUDENT APPLICATIONS ----------------------
@app.route("/company/applications")
@login_required
def company_applications():
    if current_user.role != "company":
        return "Unauthorized Access"

    company = Company.query.filter_by(user_id=current_user.id).first()

    applications = (Application.query.join(PlacementDrive).filter(PlacementDrive.company_id == company.id).all())

    return render_template("comp_appl.html", applications=applications)


# ---------------- COMPANY VIEW STUDENT APPLICATIONS ----------------
@app.route("/company/application_action/<int:app_id>/<string:action>")
@login_required
def update_application(app_id, action):

    application = Application.query.get_or_404(app_id)

    if application.status in ["Selected", "Rejected"]:
        return redirect(url_for("company_applications"))

    if action == "shortlist":
        application.status = "Shortlisted"

    elif action == "reject":
        application.status = "Rejected"

    elif action == "select":
        application.status = "Selected"

    db.session.commit()

    return redirect(url_for("company_applications"))

# --------------------------- STUDENT REGISTER -----------------------
@app.route("/student/register", methods=["GET", "POST"])
def student_register():

    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        contact = request.form.get("contact")
        branch = request.form.get("branch")
        cgpa = request.form.get("cgpa")
        year = request.form.get("year")
        resume_file = request.files.get("resume")

        if User.query.filter_by(email=email).first():
            flash("Email already registered")
            return redirect(url_for("student_register"))

        new_user = User(email=email,password=password,role="student")

        db.session.add(new_user)
        db.session.commit()

        filename = None

        if resume_file and resume_file.filename != "":
            filename = secure_filename(resume_file.filename)

            upload_path = os.path.join("static/resumes", filename)

            resume_file.save(upload_path)

        student_profile = Student(user_id=new_user.id,name=name,contact=contact,branch=branch,cgpa=cgpa,year=year,resume=filename)

        db.session.add(student_profile)
        db.session.commit()

        flash("Registration successful. Please login.")
        return redirect(url_for("login"))

    return render_template("stud_reg.html")


# ---------------- COMPANY REGISTER ----------------
@app.route("/company/register", methods=["GET", "POST"])
def company_register():
    if request.method == "POST":
        company_name = request.form.get("company_name")
        email = request.form.get("email")
        password = request.form.get("password")
        hr_contact = request.form.get("hr_contact")
        website = request.form.get("website")

        if User.query.filter_by(email=email).first():
            flash("Email already registered")
            return redirect(url_for("company_register"))

        new_user = User(email=email,password=password,role="company")
        db.session.add(new_user)
        db.session.commit()

        company_profile = Company(user_id=new_user.id,company_name=company_name,hr_contact=hr_contact,website=website,approval_status="Pending")

        db.session.add(company_profile)
        db.session.commit()

        flash("Company registered. Wait for admin approval.")
        return redirect(url_for("login"))

    return render_template("comp_reg.html")



# ---------------- MAIN ----------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()

        # Create default admin if not exists
        if not User.query.filter_by(role="admin").first():
            admin_user = User(
                email="admin@mail.com",
                password="admin123",
                role="admin"
            )
            db.session.add(admin_user)
            db.session.commit()
            print("Default Admin Created")

    app.run(debug=True)