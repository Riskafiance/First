from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from models import User, Role
from datetime import datetime

profile_bp = Blueprint('profile', __name__)

@profile_bp.route('/profile')
@login_required
def view_profile():
    """View user profile"""
    # Get the user's role information
    user_permissions = current_user.get_permissions_list()
    
    # Get member since date
    member_since = current_user.created_at.strftime("%b %d, %Y")
    
    # Get all available roles for admin users
    roles = None
    if current_user.has_permission(Role.CAN_ADMIN):
        roles = Role.query.all()
        
    return render_template(
        'profile.html', 
        user=current_user,
        permissions=user_permissions,
        member_since=member_since,
        roles=roles
    )

@profile_bp.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    """Update user profile"""
    # Only allow updating certain fields based on permissions
    if request.method == 'POST':
        # Everyone can update their own basic info
        if current_user.has_permission(Role.CAN_EDIT):
            current_user.first_name = request.form.get('first_name', current_user.first_name)
            current_user.last_name = request.form.get('last_name', current_user.last_name)
        
        # Admin users can change roles
        if current_user.has_permission(Role.CAN_ADMIN):
            role_id = request.form.get('role_id')
            if role_id and role_id.isdigit():
                role = Role.query.get(int(role_id))
                if role:
                    current_user.role = role
        
        db.session.commit()
        flash('Profile updated successfully', 'success')
        
    return redirect(url_for('profile.view_profile'))

@profile_bp.route('/profile/change-password', methods=['POST'])
@login_required
def change_password():
    """Change user password"""
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # Validate inputs
        if not current_password or not new_password or not confirm_password:
            flash('All password fields are required', 'error')
        elif not current_user.check_password(current_password):
            flash('Current password is incorrect', 'error')
        elif new_password != confirm_password:
            flash('New passwords do not match', 'error')
        elif len(new_password) < 8:
            flash('Password must be at least 8 characters long', 'error')
        else:
            # Update password
            current_user.set_password(new_password)
            db.session.commit()
            flash('Password updated successfully', 'success')
        
    return redirect(url_for('profile.view_profile'))