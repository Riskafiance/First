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
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///riskas_finance.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
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
    from models import User
    db.create_all()
    
    # Setup user loader for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

# Import and register blueprint routes
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.accounts import accounts_bp
from routes.journals import journals_bp
from routes.invoices import invoices_bp
from routes.expenses import expenses_bp
from routes.entities import entities_bp
from routes.inventory import inventory_bp
from routes.reports import reports_bp

app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(accounts_bp)
app.register_blueprint(journals_bp)
app.register_blueprint(invoices_bp)
app.register_blueprint(expenses_bp)
app.register_blueprint(entities_bp)
app.register_blueprint(inventory_bp, url_prefix='/inventory')
app.register_blueprint(reports_bp)

# Register error handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('layout.html', error="Page not found"), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('layout.html', error="Internal server error"), 500

# Import this after the app is created to avoid circular imports
from flask import render_template
