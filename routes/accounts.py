from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from models import Account, AccountType, JournalItem
from models import Role

accounts_bp = Blueprint('accounts', __name__)

@accounts_bp.route('/accounts')
@login_required
def index():
    """Show chart of accounts"""
    # Get filter by account type
    account_type_id = request.args.get('type')
    
    # Query accounts
    query = Account.query
    if account_type_id:
        query = query.filter_by(account_type_id=account_type_id)
    
    # Order by code
    accounts = query.order_by(Account.code).all()
    
    # Get all account types for filter dropdown
    account_types = AccountType.query.all()
    
    return render_template(
        'accounts/chart_accounts.html',
        accounts=accounts,
        account_types=account_types
    )

@accounts_bp.route('/accounts/create', methods=['POST'])
@login_required
def create():
    """Create a new account"""
    # Check permission
    if not current_user.has_permission(Role.CAN_CREATE):
        flash('You do not have permission to create accounts.', 'danger')
        return redirect(url_for('accounts.index'))
    
    # Get form data
    code = request.form.get('code')
    name = request.form.get('name')
    account_type_id = request.form.get('account_type_id')
    parent_id = request.form.get('parent_id') or None
    description = request.form.get('description')
    is_active = True if request.form.get('is_active') else False
    
    # Check if code already exists
    existing_account = Account.query.filter_by(code=code).first()
    if existing_account:
        flash('Account code already exists.', 'danger')
        return redirect(url_for('accounts.index'))
    
    # Create account
    new_account = Account(
        code=code,
        name=name,
        account_type_id=account_type_id,
        parent_id=parent_id,
        description=description,
        is_active=is_active,
        created_by_id=current_user.id
    )
    
    db.session.add(new_account)
    db.session.commit()
    
    flash('Account created successfully.', 'success')
    return redirect(url_for('accounts.index'))

@accounts_bp.route('/accounts/<int:account_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(account_id):
    """Edit an existing account"""
    # Check permission
    if not current_user.has_permission(Role.CAN_EDIT):
        flash('You do not have permission to edit accounts.', 'danger')
        return redirect(url_for('accounts.index'))
    
    # Get account
    account = Account.query.get_or_404(account_id)
    
    if request.method == 'POST':
        # Get form data
        account.name = request.form.get('name')
        account.description = request.form.get('description')
        account.is_active = True if request.form.get('is_active') else False
        
        # Parent account
        parent_id = request.form.get('parent_id') or None
        
        # Prevent circular reference - account can't be its own parent
        if parent_id and int(parent_id) == account_id:
            flash('An account cannot be its own parent.', 'danger')
            return redirect(url_for('accounts.edit', account_id=account_id))
        
        account.parent_id = parent_id
        
        # Save changes
        db.session.commit()
        
        flash('Account updated successfully.', 'success')
        return redirect(url_for('accounts.index'))
    
    # Get all account types and accounts for dropdowns
    account_types = AccountType.query.all()
    accounts = Account.query.filter(Account.id != account_id).order_by(Account.code).all()
    
    return render_template(
        'accounts/chart_accounts.html',
        account=account,
        account_types=account_types,
        accounts=accounts,
        editing=True
    )

@accounts_bp.route('/accounts/<int:account_id>/delete', methods=['POST'])
@login_required
def delete(account_id):
    """Delete an account"""
    # Check permission
    if not current_user.has_permission(Role.CAN_DELETE):
        flash('You do not have permission to delete accounts.', 'danger')
        return redirect(url_for('accounts.index'))
    
    # Get account
    account = Account.query.get_or_404(account_id)
    
    # Check if account has transactions
    has_transactions = JournalItem.query.filter_by(account_id=account_id).first() is not None
    
    if has_transactions:
        flash('Cannot delete account with existing transactions.', 'danger')
        return redirect(url_for('accounts.index'))
    
    # Check if account has sub-accounts
    has_sub_accounts = Account.query.filter_by(parent_id=account_id).first() is not None
    
    if has_sub_accounts:
        flash('Cannot delete account with sub-accounts.', 'danger')
        return redirect(url_for('accounts.index'))
    
    # Delete account
    db.session.delete(account)
    db.session.commit()
    
    flash('Account deleted successfully.', 'success')
    return redirect(url_for('accounts.index'))
