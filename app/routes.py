#all website logic
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, send_file, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import Admin, Company, Student, PlacementDrive, Application
from app.forms import (LoginForm, CompanyRegisterForm, StudentRegisterForm, 
                       CreateDriveForm, EditDriveForm, StudentProfileForm)
from datetime import datetime, timedelta
from functools import wraps
from werkzeug.utils import secure_filename
import os

# Define blueprints
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
company_bp = Blueprint('company', __name__, url_prefix='/company')
student_bp = Blueprint('student', __name__, url_prefix='/student')
main_bp = Blueprint('main', __name__)

# Role checking decorators
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not isinstance(current_user, Admin):
            flash('You must be logged in as admin to access this page.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def company_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not isinstance(current_user, Company):
            flash('You must be logged in as company to access this page.', 'danger')
            return redirect(url_for('auth.login'))
        if current_user.approval_status != 'Approved':
            flash('Your company account is not approved yet.', 'warning')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

def student_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not isinstance(current_user, Student):
            flash('You must be logged in as student to access this page.', 'danger')
            return redirect(url_for('auth.login'))
        if current_user.is_blacklisted:
            flash('Your account has been blacklisted.', 'danger')
            return redirect(url_for('auth.logout'))
        return f(*args, **kwargs)
    return decorated_function

# ==================== AUTHENTICATION ROUTES ====================

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if isinstance(current_user, Admin):
            return redirect(url_for('admin.dashboard'))
        elif isinstance(current_user, Company):
            return redirect(url_for('company.dashboard'))
        elif isinstance(current_user, Student):
            return redirect(url_for('student.dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        # Try admin login
        admin = Admin.query.filter_by(email=form.email.data).first()
        if admin and admin.check_password(form.password.data):
            login_user(admin)
            flash('Admin login successful!', 'success')
            return redirect(url_for('admin.dashboard'))
        
        # Try company login
        company = Company.query.filter_by(email=form.email.data).first()
        if company and company.check_password(form.password.data):
            if company.approval_status != 'Approved':
                flash('Your company account is not approved yet. Contact admin.', 'warning')
                return redirect(url_for('auth.login'))
            login_user(company)
            flash('Company login successful!', 'success')
            return redirect(url_for('company.dashboard'))
        
        # Try student login
        student = Student.query.filter_by(email=form.email.data).first()
        if student and student.check_password(form.password.data):
            if student.is_blacklisted:
                flash('Your account has been blacklisted.', 'danger')
                return redirect(url_for('auth.login'))
            login_user(student)
            flash('Student login successful!', 'success')
            return redirect(url_for('student.dashboard'))
        
        flash('Invalid email or password.', 'danger')
    
    return render_template('auth/login.html', form=form)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    user_type = request.args.get('type', 'student')
    
    if user_type == 'company':
        form = CompanyRegisterForm()
        if form.validate_on_submit():
            company = Company(
                company_name=form.company_name.data,
                email=form.email.data,
                hr_contact=form.hr_contact.data,
                website=form.website.data
            )
            company.set_password(form.password.data)
            db.session.add(company)
            db.session.commit()
            flash('Company registered successfully! Please wait for admin approval.', 'success')
            return redirect(url_for('auth.login'))
        return render_template('auth/company_register.html', form=form)
    else:
        form = StudentRegisterForm()
        if form.validate_on_submit():
            student = Student(
                roll_number=form.roll_number.data,
                name=form.name.data,
                email=form.email.data,
                cgpa=form.cgpa.data,
                branch=form.branch.data
            )
            student.set_password(form.password.data)
            db.session.add(student)
            db.session.commit()
            flash('Student registered successfully! You can now login.', 'success')
            return redirect(url_for('auth.login'))
        return render_template('auth/student_register.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))

# ==================== MAIN ROUTES ====================

@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        if isinstance(current_user, Admin):
            return redirect(url_for('admin.dashboard'))
        elif isinstance(current_user, Company):
            return redirect(url_for('company.dashboard'))
        elif isinstance(current_user, Student):
            return redirect(url_for('student.dashboard'))
    
    return render_template('index.html')

# ==================== ADMIN ROUTES ====================

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    total_students = Student.query.count()
    total_companies = Company.query.count()
    total_applications = Application.query.count()
    total_drives = PlacementDrive.query.count()
    
    pending_companies = Company.query.filter_by(approval_status='Pending').count()
    pending_drives = PlacementDrive.query.filter_by(status='Pending').count()
    
    # Get actual data for dashboard sections
    companies = Company.query.limit(10).all()
    students = Student.query.limit(10).all()
    drives = PlacementDrive.query.all()
    applications = Application.query.limit(10).all()
    
    return render_template('admin/dashboard.html',
                         total_students=total_students,
                         total_companies=total_companies,
                         total_applications=total_applications,
                         total_drives=total_drives,
                         pending_companies=pending_companies,
                         pending_drives=pending_drives,
                         companies=companies,
                         students=students,
                         drives=drives,
                         applications=applications)

@admin_bp.route('/companies')
@admin_required
def manage_companies():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    
    query = Company.query
    if search:
        query = query.filter(Company.company_name.ilike(f'%{search}%'))
    
    companies = query.paginate(page=page, per_page=10)
    return render_template('admin/manage_companies.html', companies=companies, search=search)

@admin_bp.route('/company/<int:company_id>/approve', methods=['POST'])
@admin_required
def approve_company(company_id):
    company = Company.query.get_or_404(company_id)
    company.approval_status = 'Approved'
    db.session.commit()
    flash(f'{company.company_name} approved successfully!', 'success')
    return redirect(url_for('admin.manage_companies'))

@admin_bp.route('/company/<int:company_id>/reject', methods=['POST'])
@admin_required
def reject_company(company_id):
    company = Company.query.get_or_404(company_id)
    company.approval_status = 'Rejected'
    db.session.commit()
    flash(f'{company.company_name} rejected.', 'info')
    return redirect(url_for('admin.manage_companies'))

@admin_bp.route('/company/<int:company_id>/delete', methods=['POST'])
@admin_required
def delete_company(company_id):
    company = Company.query.get_or_404(company_id)
    db.session.delete(company)
    db.session.commit()
    flash(f'{company.company_name} deleted successfully!', 'success')
    return redirect(url_for('admin.manage_companies'))

@admin_bp.route('/students')
@admin_required
def manage_students():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    
    query = Student.query
    if search:
        query = query.filter((Student.name.ilike(f'%{search}%')) | 
                            (Student.roll_number.ilike(f'%{search}%')))
    
    students = query.paginate(page=page, per_page=10)
    return render_template('admin/manage_students.html', students=students, search=search)

@admin_bp.route('/student/<int:student_id>/blacklist', methods=['POST'])
@admin_required
def blacklist_student(student_id):
    student = Student.query.get_or_404(student_id)
    student.is_blacklisted = True
    db.session.commit()
    flash(f'{student.name} blacklisted.', 'success')
    return redirect(url_for('admin.manage_students'))

@admin_bp.route('/student/<int:student_id>/unblacklist', methods=['POST'])
@admin_required
def unblacklist_student(student_id):
    student = Student.query.get_or_404(student_id)
    student.is_blacklisted = False
    db.session.commit()
    flash(f'{student.name} removed from blacklist.', 'success')
    return redirect(url_for('admin.manage_students'))

@admin_bp.route('/student/<int:student_id>/delete', methods=['POST'])
@admin_required
def delete_student(student_id):
    student = Student.query.get_or_404(student_id)
    db.session.delete(student)
    db.session.commit()
    flash(f'{student.name} deleted successfully!', 'success')
    return redirect(url_for('admin.manage_students'))

@admin_bp.route('/drives')
@admin_required
def manage_drives():
    page = request.args.get('page', 1, type=int)
    drives = PlacementDrive.query.paginate(page=page, per_page=10)
    return render_template('admin/manage_drives.html', drives=drives)

@admin_bp.route('/drive/<int:drive_id>/approve', methods=['POST'])
@admin_required
def approve_drive(drive_id):
    drive = PlacementDrive.query.get_or_404(drive_id)
    drive.status = 'Approved'
    db.session.commit()
    flash('Drive approved successfully!', 'success')
    return redirect(url_for('admin.manage_drives'))

@admin_bp.route('/drive/<int:drive_id>/reject', methods=['POST'])
@admin_required
def reject_drive(drive_id):
    drive = PlacementDrive.query.get_or_404(drive_id)
    drive.status = 'Rejected'
    db.session.commit()
    flash('Drive rejected.', 'info')
    return redirect(url_for('admin.manage_drives'))

@admin_bp.route('/applications')
@admin_required
def view_applications():
    page = request.args.get('page', 1, type=int)
    applications = Application.query.paginate(page=page, per_page=10)
    return render_template('admin/manage_applications.html', applications=applications)

# ==================== COMPANY ROUTES ====================

@company_bp.route('/dashboard')
@company_required
def dashboard():
    drives = PlacementDrive.query.filter_by(company_id=current_user.id).all()
    
    total_drives = len(drives)
    total_applications = sum(drive.get_application_count() for drive in drives)
    total_shortlisted = sum(drive.get_shortlisted_count() for drive in drives)
    total_selected = sum(drive.get_selected_count() for drive in drives)
    
    return render_template('company/dashboard.html',
                         company=current_user,
                         total_drives=total_drives,
                         total_applications=total_applications,
                         total_shortlisted=total_shortlisted,
                         total_selected=total_selected,
                         drives=drives)

@company_bp.route('/create-drive', methods=['GET', 'POST'])
@company_required
def create_drive():
    form = CreateDriveForm()
    if form.validate_on_submit():
        try:
            deadline = datetime.strptime(form.application_deadline.data, '%Y-%m-%d')
        except ValueError:
            flash('Invalid date format. Use YYYY-MM-DD.', 'danger')
            return render_template('company/create_drive.html', form=form)
        
        drive = PlacementDrive(
            company_id=current_user.id,
            job_title=form.job_title.data,
            job_description=form.job_description.data,
            eligibility_criteria=form.eligibility_criteria.data,
            salary=form.salary.data,
            application_deadline=deadline,
            status='Pending'
        )
        db.session.add(drive)
        db.session.commit()
        flash('Placement drive created! Waiting for admin approval.', 'success')
        return redirect(url_for('company.dashboard'))
    
    return render_template('company/create_drive.html', form=form)

@company_bp.route('/drives')
@company_required
def view_drives():
    page = request.args.get('page', 1, type=int)
    drives = PlacementDrive.query.filter_by(company_id=current_user.id).paginate(page=page, per_page=10)
    return render_template('company/view_drives.html', drives=drives)

@company_bp.route('/drive/<int:drive_id>/edit', methods=['GET', 'POST'])
@company_required
def edit_drive(drive_id):
    drive = PlacementDrive.query.get_or_404(drive_id)
    
    if drive.company_id != current_user.id:
        flash('You do not have permission to edit this drive.', 'danger')
        return redirect(url_for('company.view_drives'))
    
    form = EditDriveForm()
    if form.validate_on_submit():
        try:
            deadline = datetime.strptime(form.application_deadline.data, '%Y-%m-%d')
        except ValueError:
            flash('Invalid date format. Use YYYY-MM-DD.', 'danger')
            return render_template('company/edit_drive.html', form=form, drive=drive)
        
        drive.job_title = form.job_title.data
        drive.job_description = form.job_description.data
        drive.eligibility_criteria = form.eligibility_criteria.data
        drive.salary = form.salary.data
        drive.application_deadline = deadline
        db.session.commit()
        flash('Drive updated successfully!', 'success')
        return redirect(url_for('company.view_drives'))
    
    if request.method == 'GET':
        form.job_title.data = drive.job_title
        form.job_description.data = drive.job_description
        form.eligibility_criteria.data = drive.eligibility_criteria
        form.salary.data = drive.salary
        form.application_deadline.data = drive.application_deadline.strftime('%Y-%m-%d')
    
    return render_template('company/edit_drive.html', form=form, drive=drive)

@company_bp.route('/drive/<int:drive_id>/close', methods=['POST'])
@company_required
def close_drive(drive_id):
    drive = PlacementDrive.query.get_or_404(drive_id)
    
    if drive.company_id != current_user.id:
        flash('You do not have permission to close this drive.', 'danger')
        return redirect(url_for('company.view_drives'))
    
    drive.status = 'Closed'
    db.session.commit()
    flash('Drive closed successfully!', 'success')
    return redirect(url_for('company.view_drives'))

@company_bp.route('/drive/<int:drive_id>/delete', methods=['POST'])
@company_required
def delete_drive(drive_id):
    drive = PlacementDrive.query.get_or_404(drive_id)
    
    if drive.company_id != current_user.id:
        flash('You do not have permission to delete this drive.', 'danger')
        return redirect(url_for('company.view_drives'))
    
    db.session.delete(drive)
    db.session.commit()
    flash('Drive deleted successfully!', 'success')
    return redirect(url_for('company.view_drives'))

@company_bp.route('/drive/<int:drive_id>/applications')
@company_required
def view_applications(drive_id):
    drive = PlacementDrive.query.get_or_404(drive_id)
    
    if drive.company_id != current_user.id:
        flash('You do not have permission to view these applications.', 'danger')
        return redirect(url_for('company.view_drives'))
    
    page = request.args.get('page', 1, type=int)
    applications = Application.query.filter_by(drive_id=drive_id).paginate(page=page, per_page=10)
    
    return render_template('company/view_applications.html', applications=applications, drive=drive)

@company_bp.route('/application/<int:app_id>/shortlist', methods=['POST'])
@company_required
def shortlist_application(app_id):
    app = Application.query.get_or_404(app_id)
    
    if app.placement_drive.company_id != current_user.id:
        flash('You do not have permission to update this application.', 'danger')
        return redirect(url_for('company.view_drives'))
    
    app.status = 'Shortlisted'
    app.updated_at = datetime.utcnow()
    db.session.commit()
    flash('Student shortlisted!', 'success')
    return redirect(request.referrer or url_for('company.view_drives'))

@company_bp.route('/application/<int:app_id>/select', methods=['POST'])
@company_required
def select_application(app_id):
    app = Application.query.get_or_404(app_id)
    
    if app.placement_drive.company_id != current_user.id:
        flash('You do not have permission to update this application.', 'danger')
        return redirect(url_for('company.view_drives'))
    
    app.status = 'Selected'
    app.updated_at = datetime.utcnow()
    db.session.commit()
    flash('Student selected!', 'success')
    return redirect(request.referrer or url_for('company.view_drives'))

@company_bp.route('/application/<int:app_id>/reject', methods=['POST'])
@company_required
def reject_application(app_id):
    app = Application.query.get_or_404(app_id)
    
    if app.placement_drive.company_id != current_user.id:
        flash('You do not have permission to update this application.', 'danger')
        return redirect(url_for('company.view_drives'))
    
    app.status = 'Rejected'
    app.updated_at = datetime.utcnow()
    db.session.commit()
    flash('Application rejected.', 'info')
    return redirect(request.referrer or url_for('company.view_drives'))

@company_bp.route('/application/<int:app_id>/review')
@company_required
def review_application(app_id):
    application = Application.query.get_or_404(app_id)
    
    if application.placement_drive.company_id != current_user.id:
        flash('You do not have permission to view this application.', 'danger')
        return redirect(url_for('company.view_drives'))
    
    return render_template('company/review_application.html', application=application)

@company_bp.route('/application/<int:app_id>/update-status', methods=['POST'])
@company_required
def update_application_status(app_id):
    application = Application.query.get_or_404(app_id)
    
    if application.placement_drive.company_id != current_user.id:
        flash('You do not have permission to update this application.', 'danger')
        return redirect(url_for('company.view_drives'))
    
    status = request.form.get('status')
    
    if status not in ['Applied', 'Shortlisted', 'Selected', 'Rejected']:
        flash('Invalid status.', 'danger')
        return redirect(url_for('company.review_application', app_id=app_id))
    
    application.status = status
    application.updated_at = datetime.utcnow()
    db.session.commit()
    flash(f'Application status updated to {status}!', 'success')
    return redirect(url_for('company.review_application', app_id=app_id))

@company_bp.route('/student/<int:student_id>/resume/download')
@company_required
def download_student_resume(student_id):
    """Allow companies to download student resumes for their applications"""
    student = Student.query.get_or_404(student_id)
    
    if not student.resume_path:
        flash('Student has not uploaded a resume.', 'warning')
        return redirect(request.referrer or url_for('company.view_drives'))
    
    file_path = os.path.join('uploads', student.resume_path)
    if not os.path.exists(file_path):
        flash('Resume file not found.', 'danger')
        return redirect(request.referrer or url_for('company.view_drives'))
    
    return send_file(file_path, as_attachment=True, download_name=f"{student.name}_resume.pdf")

# ==================== STUDENT ROUTES ====================

@student_bp.route('/dashboard')
@student_required
def dashboard():
    available_drives = PlacementDrive.query.filter_by(status='Approved').all()
    applied_drives = db.session.query(PlacementDrive).join(
        Application
    ).filter(Application.student_id == current_user.id).all()
    
    user_applications = Application.query.filter_by(student_id=current_user.id).all()
    app_map = {app.drive_id: app for app in user_applications}
    
    # Get all approved companies for Organizations section
    companies = Company.query.filter_by(approval_status='Approved').all()
    
    return render_template('student/dashboard.html',
                         available_drives=available_drives,
                         applied_drives=applied_drives,
                         app_map=app_map,
                         companies=companies)

@student_bp.route('/drives')
@student_required
def view_drives():
    page = request.args.get('page', 1, type=int)
    drives = PlacementDrive.query.filter_by(status='Approved').paginate(page=page, per_page=10)
    
    # Get student's applications
    student_apps = Application.query.filter_by(student_id=current_user.id).all()
    applied_drives = {app.drive_id for app in student_apps}
    
    return render_template('student/view_drives.html', drives=drives, applied_drives=applied_drives)

@student_bp.route('/drive/<int:drive_id>/apply', methods=['POST'])
@student_required
def apply_for_drive(drive_id):
    drive = PlacementDrive.query.get_or_404(drive_id)
    
    if drive.status != 'Approved':
        flash('This drive is not open for applications.', 'danger')
        return redirect(url_for('student.view_drives'))
    
    # Check for duplicate application
    existing_app = Application.query.filter_by(
        student_id=current_user.id,
        drive_id=drive_id
    ).first()
    
    if existing_app:
        flash('You have already applied for this drive.', 'warning')
        return redirect(url_for('student.view_drives'))
    
    # Check deadline
    if datetime.utcnow() > drive.application_deadline:
        flash('Application deadline has passed.', 'danger')
        return redirect(url_for('student.view_drives'))
    
    application = Application(
        student_id=current_user.id,
        drive_id=drive_id,
        status='Applied'
    )
    db.session.add(application)
    db.session.commit()
    flash('Application submitted successfully!', 'success')
    return redirect(url_for('student.view_drives'))

@student_bp.route('/applications')
@student_required
def view_applications():
    page = request.args.get('page', 1, type=int)
    applications = Application.query.filter_by(student_id=current_user.id).paginate(page=page, per_page=10)
    return render_template('student/view_applications.html', applications=applications)

@student_bp.route('/profile', methods=['GET', 'POST'])
@student_required
def profile():
    form = StudentProfileForm()
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.cgpa = form.cgpa.data
        current_user.branch = form.branch.data
        
        # Handle resume upload
        if form.resume.data:
            file = form.resume.data
            filename = secure_filename(f"{current_user.id}_{current_user.roll_number}_{file.filename}")
            file.save(os.path.join('uploads', filename))
            current_user.resume_path = filename
            flash('Resume uploaded successfully!', 'success')
        
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('student.profile'))
    
    if request.method == 'GET':
        form.name.data = current_user.name
        form.cgpa.data = current_user.cgpa
        form.branch.data = current_user.branch
    
    return render_template('student/profile.html', form=form)

@student_bp.route('/history')
@student_required
def placement_history():
    applications = Application.query.filter_by(student_id=current_user.id).all()
    return render_template('student/placement_history.html', applications=applications)

@student_bp.route('/resume/download')
@student_required
def download_resume():
    if not current_user.resume_path:
        flash('No resume uploaded.', 'warning')
        return redirect(url_for('student.profile'))
    
    file_path = os.path.join('uploads', current_user.resume_path)
    if not os.path.exists(file_path):
        flash('Resume file not found.', 'danger')
        return redirect(url_for('student.profile'))
    
    return send_file(file_path, as_attachment=True)

# ==================== API ENDPOINTS FOR REAL-TIME UPDATES ====================

@company_bp.route('/api/dashboard-data')
@company_required
def api_dashboard_data():
    """API endpoint for real-time dashboard data refresh"""
    drives = PlacementDrive.query.filter_by(company_id=current_user.id).all()
    
    total_drives = len(drives)
    total_applications = sum(drive.get_application_count() for drive in drives)
    total_shortlisted = sum(drive.get_shortlisted_count() for drive in drives)
    total_selected = sum(drive.get_selected_count() for drive in drives)
    
    return jsonify({
        'total_drives': total_drives,
        'total_applications': total_applications,
        'total_shortlisted': total_shortlisted,
        'total_selected': total_selected
    })

@admin_bp.route('/api/dashboard-data')
@admin_required
def api_admin_dashboard_data():
    """API endpoint for admin dashboard real-time data refresh"""
    total_students = Student.query.count()
    total_companies = Company.query.count()
    total_applications = Application.query.count()
    total_drives = PlacementDrive.query.count()
    pending_companies = Company.query.filter_by(approval_status='Pending').count()
    
    return jsonify({
        'total_students': total_students,
        'total_companies': total_companies,
        'total_applications': total_applications,
        'total_drives': total_drives,
        'pending_companies': pending_companies
    })

@student_bp.route('/api/dashboard-data')
@student_required
def api_student_dashboard_data():
    """API endpoint for student dashboard real-time data refresh"""
    applications = Application.query.filter_by(student_id=current_user.id).all()
    
    total_applications = len(applications)
    shortlisted = len([app for app in applications if app.status == 'Shortlisted'])
    selected = len([app for app in applications if app.status == 'Selected'])
    rejected = len([app for app in applications if app.status == 'Rejected'])
    
    return jsonify({
        'total_applications': total_applications,
        'shortlisted': shortlisted,
        'selected': selected,
        'rejected': rejected
    })
