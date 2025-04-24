import os
import logging

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_login import LoginManager
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Setup database base class
class Base(DeclarativeBase):
    pass

# Initialize database
db = SQLAlchemy(model_class=Base)

# Create the Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "riska_finance_enterprise_secret")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure database
# Handle potential 'postgres://' URLs from some providers by converting to 'postgresql://'
database_url = os.environ.get("DATABASE_URL", "sqlite:///riskas_finance.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
    "pool_size": 10,  # Optimal for most PostgreSQL connections
    "max_overflow": 20  # Allow additional temporary connections if needed
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize database with app
db.init_app(app)

# Setup login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

# Create database tables
with app.app_context():
    import models  # noqa: F401
    from models import User, Role
    db.create_all()
    
    # Create default roles
    Role.insert_roles()
    
    # Create a default admin user if none exists
    if not User.query.filter_by(username='admin').first():
        admin_role = Role.query.filter_by(name='Admin').first()
        if admin_role:
            admin = User(
                username='admin',
                email='admin@riskasfinance.com',
                first_name='System',
                last_name='Admin',
                role=admin_role
            )
            admin.set_password('adminpassword')
            db.session.add(admin)
            db.session.commit()
            print("Created default admin user: admin / adminpassword")
    
    # If using PostgreSQL, apply database optimizations
    if database_url.startswith(("postgres://", "postgresql://")):
        print("PostgreSQL detected - applying optimizations...")
        try:
            from utils.database import optimize_queries
            optimize_queries()
            print("PostgreSQL optimizations applied!")
        except Exception as e:
            print(f"Error applying PostgreSQL optimizations: {e}")
    
    # Setup user loader for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

# Import and register blueprint routes
from routes.auth import auth_bp
from routes.profile import profile_bp
from routes.dashboard import dashboard_bp
from routes.accounts import accounts_bp
from routes.journals import journals_bp
from routes.invoices import invoices_bp
from routes.expenses import expenses_bp
from routes.entities import entities_bp
from routes.inventory import inventory_bp
from routes.reports import reports_bp
from routes.fixed_assets import setup_assets_blueprint
from routes.budgeting import budgeting_bp
from routes.bank_reconciliation import bank_reconciliation_bp
from routes.projects import projects_bp

app.register_blueprint(auth_bp)
app.register_blueprint(profile_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(accounts_bp)
app.register_blueprint(journals_bp)
app.register_blueprint(invoices_bp)
app.register_blueprint(expenses_bp)
app.register_blueprint(entities_bp)
app.register_blueprint(inventory_bp, url_prefix='/inventory')
app.register_blueprint(reports_bp)
app.register_blueprint(budgeting_bp, url_prefix='/budgeting')
app.register_blueprint(bank_reconciliation_bp, url_prefix='/banking')
app.register_blueprint(projects_bp, url_prefix='/projects')

# Setup fixed assets blueprint
setup_assets_blueprint(app)

# Register error handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('layout.html', error="Page not found"), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('layout.html', error="Internal server error"), 500

# Import this after the app is created to avoid circular imports
from flask import render_template
from markupsafe import Markup

# Register custom Jinja2 filters
@app.template_filter('nl2br')
def nl2br_filter(s):
    if s is None:
        return ""
    return Markup(s.replace('\n', '<br>'))

# Add context processors
@app.context_processor
def inject_role():
    """Make Role model available in all templates"""
    from models import Role, ProjectStatus
    return {'Role': Role, 'statuses': ProjectStatus}
