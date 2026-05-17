#form validation
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, FloatField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Length
from app.models import Company, Student

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class CompanyRegisterForm(FlaskForm):
    company_name = StringField('Company Name', validators=[DataRequired(), Length(min=2, max=255)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    hr_contact = StringField('HR Contact Name', validators=[DataRequired(), Length(min=2, max=120)])
    website = StringField('Company Website')
    submit = SubmitField('Register')
    
    def validate_email(self, email):
        company = Company.query.filter_by(email=email.data).first()
        if company:
            raise ValidationError('Email already registered. Please use a different email.')
    
    def validate_company_name(self, company_name):
        company = Company.query.filter_by(company_name=company_name.data).first()
        if company:
            raise ValidationError('Company already registered.')

class StudentRegisterForm(FlaskForm):
    roll_number = StringField('Roll Number', validators=[DataRequired(), Length(min=2, max=50)])
    name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=255)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    cgpa = FloatField('CGPA', validators=[DataRequired()])
    branch = StringField('Branch', validators=[DataRequired()])
    submit = SubmitField('Register')
    
    def validate_email(self, email):
        student = Student.query.filter_by(email=email.data).first()
        if student:
            raise ValidationError('Email already registered. Please use a different email.')
    
    def validate_roll_number(self, roll_number):
        student = Student.query.filter_by(roll_number=roll_number.data).first()
        if student:
            raise ValidationError('Roll number already registered.')

class CreateDriveForm(FlaskForm):
    job_title = StringField('Job Title', validators=[DataRequired(), Length(min=2, max=255)])
    job_description = TextAreaField('Job Description', validators=[DataRequired()])
    eligibility_criteria = TextAreaField('Eligibility Criteria')
    salary = StringField('Salary Package')
    application_deadline = StringField('Application Deadline', validators=[DataRequired()])
    submit = SubmitField('Create Drive')

class EditDriveForm(FlaskForm):
    job_title = StringField('Job Title', validators=[DataRequired(), Length(min=2, max=255)])
    job_description = TextAreaField('Job Description', validators=[DataRequired()])
    eligibility_criteria = TextAreaField('Eligibility Criteria')
    salary = StringField('Salary Package')
    application_deadline = StringField('Application Deadline', validators=[DataRequired()])
    submit = SubmitField('Update Drive')

class StudentProfileForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=255)])
    cgpa = FloatField('CGPA', validators=[DataRequired()])
    branch = StringField('Branch', validators=[DataRequired()])
    resume = FileField('Upload Resume', validators=[FileAllowed(['pdf', 'doc', 'docx'], 'PDF and Word documents only!')])
    submit = SubmitField('Update Profile')
