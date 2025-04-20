from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from app import db
from models import User, Role

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        
        user = User.query.filter_by(email=email).first()
        
        # Check if user exists and password is correct
        if not user or not user.check_password(password):
            flash('Please check your login details and try again.', 'danger')
            return redirect(url_for('auth.login'))
        
        # Log in the user
        login_user(user, remember=remember)
        
        # Redirect to the page the user was trying to access
        next_page = request.args.get('next')
        if not next_page or not next_page.startswith('/'):
            next_page = url_for('dashboard.index')
        
        flash(f'Welcome back, {user.first_name or user.username}!', 'success')
        return redirect(next_page)
    
    return render_template('login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Handle user registration"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        # Get form data
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        
        # Validate passwords match
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('auth.register'))
        
        # Check if username or email already exists
        existing_user = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()
        
        if existing_user:
            flash('Username or email already exists.', 'danger')
            return redirect(url_for('auth.register'))
        
        # Get the default role (viewer)
        default_role = Role.query.filter_by(name='Viewer').first()
        if not default_role:
            # Create basic roles if they don't exist
            admin_role = Role(name='Admin', description='Administrator with full access', 
                             permissions=Role.CAN_VIEW | Role.CAN_CREATE | Role.CAN_EDIT | 
                                         Role.CAN_DELETE | Role.CAN_APPROVE | Role.CAN_ADMIN)
            
            accountant_role = Role(name='Accountant', description='Can manage financial records',
                                  permissions=Role.CAN_VIEW | Role.CAN_CREATE | Role.CAN_EDIT | 
                                             Role.CAN_APPROVE)
            
            viewer_role = Role(name='Viewer', description='Can only view records',
                              permissions=Role.CAN_VIEW)
            
            db.session.add_all([admin_role, accountant_role, viewer_role])
            db.session.commit()
            
            default_role = viewer_role
        
        # Create new user
        new_user = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            role_id=default_role.id
        )
        new_user.set_password(password)
        
        # Save user to database
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! You can now login.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('register.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """Handle user logout"""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """User profile management"""
    if request.method == 'POST':
        # Handle profile update
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # Update name information
        if first_name:
            current_user.first_name = first_name
        if last_name:
            current_user.last_name = last_name
        
        # Update password if provided
        if current_password and new_password and confirm_password:
            # Verify current password
            if not current_user.check_password(current_password):
                flash('Current password is incorrect.', 'danger')
                return redirect(url_for('auth.profile'))
            
            # Verify new passwords match
            if new_password != confirm_password:
                flash('New passwords do not match.', 'danger')
                return redirect(url_for('auth.profile'))
            
            # Update password
            current_user.set_password(new_password)
            flash('Password updated successfully.', 'success')
        
        # Save changes
        db.session.commit()
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('auth.profile'))
    
    return render_template('profile.html')
