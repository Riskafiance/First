from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from app import db, login_manager
from models import User, Role
from datetime import datetime
from functools import wraps

auth_bp = Blueprint('auth', __name__)

def admin_required(f):
    """Decorator for views that require admin permission"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.has_permission(Role.CAN_ADMIN):
            flash('You do not have permission to access this page', 'error')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated_function

@login_manager.user_loader
def load_user(user_id):
    """Load user by ID"""
    return User.query.get(int(user_id))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Simple validation
        if not username or not password:
            flash('Please provide both username and password', 'error')
            return render_template('login.html')
        
        # Authenticate user
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            # Get next page from query string or default to dashboard
            next_page = request.args.get('next', url_for('dashboard.index'))
            return redirect(next_page)
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        
        # Validate inputs
        if not username or not email or not password or not confirm_password:
            flash('All fields are required', 'error')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('register.html')
        
        # Check if user already exists
        if User.query.filter_by(username=username).first():
            flash(f'Username {username} already exists', 'error')
            return render_template('register.html')
        
        if User.query.filter_by(email=email).first():
            flash(f'Email {email} already exists', 'error')
            return render_template('register.html')
        
        # Create new user
        user = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name
        )
        user.set_password(password)
        
        # Assign default viewer role
        default_role = Role.query.filter_by(name='Viewer').first()
        if default_role:
            user.role = default_role
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('register.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    return redirect(url_for('auth.login'))

@auth_bp.route('/user-management')
@login_required
@admin_required
def user_management():
    """User management page"""
    users = User.query.order_by(User.username).all()
    roles = Role.query.all()
    return render_template('user_management.html', users=users, roles=roles)

@auth_bp.route('/create-user', methods=['POST'])
@login_required
@admin_required
def create_user():
    """Create new user"""
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    role_id = request.form.get('role_id')
    
    # Validate inputs
    if not username or not email or not password:
        flash('Username, email, and password are required', 'error')
        return redirect(url_for('auth.user_management'))
    
    # Check if user already exists
    if User.query.filter_by(username=username).first():
        flash(f'Username {username} already exists', 'error')
        return redirect(url_for('auth.user_management'))
    
    if User.query.filter_by(email=email).first():
        flash(f'Email {email} already exists', 'error')
        return redirect(url_for('auth.user_management'))
    
    # Create new user
    user = User(
        username=username,
        email=email,
        first_name=first_name,
        last_name=last_name
    )
    user.set_password(password)
    
    # Set role if provided
    if role_id and role_id.isdigit():
        role = Role.query.get(int(role_id))
        if role:
            user.role = role
    
    db.session.add(user)
    db.session.commit()
    
    flash(f'User {username} created successfully', 'success')
    return redirect(url_for('auth.user_management'))

@auth_bp.route('/edit-user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def edit_user(user_id):
    """Edit existing user"""
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        # Check email uniqueness
        email = request.form.get('email')
        if email != user.email and User.query.filter_by(email=email).first():
            flash(f'Email {email} already exists', 'error')
            return redirect(url_for('auth.user_management'))
        
        # Update user data
        user.email = email
        user.first_name = request.form.get('first_name')
        user.last_name = request.form.get('last_name')
        
        # Update role if provided
        role_id = request.form.get('role_id')
        if role_id:
            if role_id.isdigit():
                role = Role.query.get(int(role_id))
                if role:
                    user.role = role
            else:
                user.role = None
        
        # Reset password if requested
        if request.form.get('reset_password'):
            new_password = request.form.get('new_password')
            if new_password:
                user.set_password(new_password)
        
        db.session.commit()
        flash(f'User {user.username} updated successfully', 'success')
    
    return redirect(url_for('auth.user_management'))

@auth_bp.route('/delete-user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    """Delete user"""
    user = User.query.get_or_404(user_id)
    
    # Don't allow deleting the current user
    if user.id == current_user.id:
        flash('You cannot delete your own account', 'error')
        return redirect(url_for('auth.user_management'))
    
    username = user.username
    db.session.delete(user)
    db.session.commit()
    
    flash(f'User {username} deleted successfully', 'success')
    return redirect(url_for('auth.user_management'))

@auth_bp.route('/role-management')
@login_required
@admin_required
def role_management():
    """Role management page"""
    roles = Role.query.order_by(Role.name).all()
    return render_template('role_management.html', roles=roles)

@auth_bp.route('/create-role', methods=['POST'])
@login_required
@admin_required
def create_role():
    """Create new role"""
    name = request.form.get('name')
    description = request.form.get('description')
    permissions = request.form.getlist('permissions')
    
    # Validate inputs
    if not name:
        flash('Role name is required', 'error')
        return redirect(url_for('auth.role_management'))
    
    # Check if role already exists
    if Role.query.filter_by(name=name).first():
        flash(f'Role {name} already exists', 'error')
        return redirect(url_for('auth.role_management'))
    
    # Calculate permissions value from checkboxes
    perm_value = 0
    for perm in permissions:
        if perm.isdigit():
            perm_value |= int(perm)
    
    # Create new role
    role = Role(
        name=name,
        description=description,
        permissions=perm_value
    )
    
    db.session.add(role)
    db.session.commit()
    
    flash(f'Role {name} created successfully', 'success')
    return redirect(url_for('auth.role_management'))

@auth_bp.route('/edit-role/<int:role_id>', methods=['POST'])
@login_required
@admin_required
def edit_role(role_id):
    """Edit existing role"""
    role = Role.query.get_or_404(role_id)
    
    if request.method == 'POST':
        name = request.form.get('name')
        
        # Check name uniqueness
        if name != role.name and Role.query.filter_by(name=name).first():
            flash(f'Role {name} already exists', 'error')
            return redirect(url_for('auth.role_management'))
        
        # Calculate permissions value from checkboxes
        permissions = request.form.getlist('permissions')
        perm_value = 0
        for perm in permissions:
            if perm.isdigit():
                perm_value |= int(perm)
        
        # Update role data
        role.name = name
        role.description = request.form.get('description')
        role.permissions = perm_value
        
        db.session.commit()
        flash(f'Role {role.name} updated successfully', 'success')
    
    return redirect(url_for('auth.role_management'))

@auth_bp.route('/delete-role/<int:role_id>', methods=['POST'])
@login_required
@admin_required
def delete_role(role_id):
    """Delete role"""
    role = Role.query.get_or_404(role_id)
    
    # Check if role is in use
    users_with_role = User.query.filter_by(role_id=role.id).count()
    if users_with_role > 0:
        flash(f'Cannot delete role {role.name}: it is assigned to {users_with_role} users', 'error')
        return redirect(url_for('auth.role_management'))
    
    name = role.name
    db.session.delete(role)
    db.session.commit()
    
    flash(f'Role {name} deleted successfully', 'success')
    return redirect(url_for('auth.role_management'))