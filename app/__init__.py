#creates flask app
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os

db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    
    # Configuration
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "..", "placement_portal.db")}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    
    # Create tables and seed data
    with app.app_context():
        from app.models import Admin, Company, Student, PlacementDrive, Application
        db.create_all()
        
        # Create default admin if not exists
        if Admin.query.first() is None:
            admin = Admin(
                username='admin',
                email='admin@placement.edu'
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
    
    # Register blueprints
    from app.routes import auth_bp, admin_bp, company_bp, student_bp, main_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(company_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(main_bp)
    
    @login_manager.user_loader
    def load_user(user_id):
        from app.models import Admin, Company, Student
        
        # Parse the user_id format: "type_id"
        if '_' in user_id:
            user_type, user_num = user_id.split('_', 1)
            try:
                user_num = int(user_num)
            except ValueError:
                return None
            
            if user_type == 'admin':
                return Admin.query.get(user_num)
            elif user_type == 'company':
                return Company.query.get(user_num)
            elif user_type == 'student':
                return Student.query.get(user_num)
        
        return None
    
    return app
