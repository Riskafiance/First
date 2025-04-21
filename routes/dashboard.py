from flask import Blueprint, render_template
from flask_login import login_required, current_user
from models import Role

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
@login_required
def index():
    """Dashboard index page"""
    permissions = current_user.get_permissions_list()
    
    return render_template('dashboard.html', permissions=permissions)