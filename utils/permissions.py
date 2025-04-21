from functools import wraps
from flask import redirect, url_for, flash
from flask_login import current_user
from models import Role

def permission_required(permission):
    """Decorator for checking if current user has the required permission"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            
            if not current_user.has_permission(permission):
                flash('You do not have permission to access this page', 'error')
                return redirect(url_for('dashboard.index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Predefined permission decorators for common cases
def view_required(f):
    """Decorator for views that require view permission"""
    return permission_required(Role.CAN_VIEW)(f)

def create_required(f):
    """Decorator for views that require create permission"""
    return permission_required(Role.CAN_CREATE)(f)

def edit_required(f):
    """Decorator for views that require edit permission"""
    return permission_required(Role.CAN_EDIT)(f)

def delete_required(f):
    """Decorator for views that require delete permission"""
    return permission_required(Role.CAN_DELETE)(f)

def approve_required(f):
    """Decorator for views that require approve permission"""
    return permission_required(Role.CAN_APPROVE)(f)

def admin_required(f):
    """Decorator for views that require admin permission"""
    return permission_required(Role.CAN_ADMIN)(f)