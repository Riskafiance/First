from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from models import Expense, ExpenseItem, Entity, EntityType, ExpenseStatus, Account, AccountType
from models import JournalEntry, JournalItem, Role
from datetime import datetime
import sys, os

# Import functions from core_utils.py (renamed utils.py to avoid conflicts)
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
sys.path.insert(0, root_dir)

from core_utils import generate_expense_number

expenses_bp = Blueprint('expenses', __name__)

@expenses_bp.route('/expenses')
@login_required
def index():
    """Show list of expenses"""
    # Get filters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    status = request.args.get('status')
    
    # Base query
    query = Expense.query
    
    # Apply date filters if provided
    if start_date:
        query = query.filter(Expense.expense_date >= start_date)
    
    if end_date:
        query = query.filter(Expense.expense_date <= end_date)
    
    # Apply status filter if provided
    if status:
        query = query.join(ExpenseStatus).filter(ExpenseStatus.name == status)
    
    # Order by date desc
    expenses = query.order_by(Expense.expense_date.desc()).all()
    
    # Get all statuses for filter dropdown
    statuses = ExpenseStatus.query.all()
    
    return render_template(
        'expenses.html',
        expenses=expenses,
        statuses=statuses
    )

@expenses_bp.route('/expenses/create', methods=['GET', 'POST'])
@login_required
def create():
    """Create a new expense"""
    # Check permission
    if not current_user.has_permission(Role.CAN_CREATE):
        flash('You do not have permission to create expenses.', 'danger')
        return redirect(url_for('expenses.index'))
    
    if request.method == 'POST':
        # Get form data
        entity_id = request.form.get('entityId')
        expense_date = request.form.get('expenseDate')
        payment_due_date = request.form.get('paymentDueDate')
        notes = request.form.get('notes')
        total_amount = float(request.form.get('expenseTotal', 0))
        
        # Get draft status
        draft_status = ExpenseStatus.query.filter_by(name=ExpenseStatus.DRAFT).first()
        if not draft_status:
            # Create expense statuses if they don't exist
            draft_status = ExpenseStatus(name=ExpenseStatus.DRAFT)
            pending_status = ExpenseStatus(name=ExpenseStatus.PENDING)
            approved_status = ExpenseStatus(name=ExpenseStatus.APPROVED)
            paid_status = ExpenseStatus(name=ExpenseStatus.PAID)
            rejected_status = ExpenseStatus(name=ExpenseStatus.REJECTED)
            
            db.session.add_all([draft_status, pending_status, approved_status, paid_status, rejected_status])
            db.session.commit()
        
        # Generate expense number
        expense_number = generate_expense_number()
        
        # Create expense
        expense = Expense(
            expense_number=expense_number,
            entity_id=entity_id,
            expense_date=datetime.strptime(expense_date, '%Y-%m-%d').date(),
            payment_due_date=datetime.strptime(payment_due_date, '%Y-%m-%d').date(),
            status_id=draft_status.id,
            total_amount=total_amount,
            notes=notes,
            created_by_id=current_user.id
        )
        
        db.session.add(expense)
        db.session.flush()  # Get ID without committing
        
        # Process line items
        items = []
        
        for key, value in request.form.items():
            if key.startswith('items[') and key.endswith('[description]'):
                # Extract the index from the key
                index = key.split('[')[1].split(']')[0]
                
                description = value
                quantity = float(request.form.get(f'items[{index}][quantity]', 0))
                unit_price = float(request.form.get(f'items[{index}][unit_price]', 0))
                account_id = request.form.get(f'items[{index}][account_id]')
                
                # Create expense item
                item = ExpenseItem(
                    expense_id=expense.id,
                    description=description,
                    quantity=quantity,
                    unit_price=unit_price,
                    account_id=account_id
                )
                
                items.append(item)
        
        # Add all items
        db.session.add_all(items)
        db.session.commit()
        
        flash('Expense created successfully.', 'success')
        return redirect(url_for('expenses.view', expense_id=expense.id))
    
    # Get vendors (entities of type Vendor)
    vendor_type = EntityType.query.filter_by(name=EntityType.VENDOR).first()
    if vendor_type:
        vendors = Entity.query.filter_by(entity_type_id=vendor_type.id).all()
    else:
        vendors = []
    
    # Get expense accounts
    expense_type = AccountType.query.filter_by(name=AccountType.EXPENSE).first()
    if expense_type:
        expense_accounts = Account.query.filter_by(account_type_id=expense_type.id, is_active=True).all()
    else:
        expense_accounts = []
    
    return render_template(
        'expense_form.html',
        vendors=vendors,
        expense_accounts=expense_accounts,
        today=datetime.now().strftime('%Y-%m-%d')
    )

@expenses_bp.route('/expenses/<int:expense_id>')
@login_required
def view(expense_id):
    """View an expense"""
    expense = Expense.query.get_or_404(expense_id)
    
    return render_template('expense_view.html', expense=expense, now=datetime.now())

@expenses_bp.route('/expenses/<int:expense_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(expense_id):
    """Edit an expense"""
    # Check permission
    if not current_user.has_permission(Role.CAN_EDIT):
        flash('You do not have permission to edit expenses.', 'danger')
        return redirect(url_for('expenses.index'))
    
    expense = Expense.query.get_or_404(expense_id)
    
    # Can only edit draft expenses
    if expense.status.name != ExpenseStatus.DRAFT:
        flash('Cannot edit an expense that is not in draft status.', 'danger')
        return redirect(url_for('expenses.view', expense_id=expense_id))
    
    if request.method == 'POST':
        # Update expense
        expense.entity_id = request.form.get('entityId')
        expense.expense_date = datetime.strptime(request.form.get('expenseDate'), '%Y-%m-%d').date()
        expense.payment_due_date = datetime.strptime(request.form.get('paymentDueDate'), '%Y-%m-%d').date()
        expense.notes = request.form.get('notes')
        expense.total_amount = float(request.form.get('expenseTotal', 0))
        
        # Delete existing items
        for item in expense.items:
            db.session.delete(item)
        
        # Process line items
        items = []
        
        for key, value in request.form.items():
            if key.startswith('items[') and key.endswith('[description]'):
                # Extract the index from the key
                index = key.split('[')[1].split(']')[0]
                
                description = value
                quantity = float(request.form.get(f'items[{index}][quantity]', 0))
                unit_price = float(request.form.get(f'items[{index}][unit_price]', 0))
                account_id = request.form.get(f'items[{index}][account_id]')
                
                # Create expense item
                item = ExpenseItem(
                    expense_id=expense.id,
                    description=description,
                    quantity=quantity,
                    unit_price=unit_price,
                    account_id=account_id
                )
                
                items.append(item)
        
        # Add all items
        db.session.add_all(items)
        db.session.commit()
        
        flash('Expense updated successfully.', 'success')
        return redirect(url_for('expenses.view', expense_id=expense.id))
    
    # Get vendors (entities of type Vendor)
    vendor_type = EntityType.query.filter_by(name=EntityType.VENDOR).first()
    if vendor_type:
        vendors = Entity.query.filter_by(entity_type_id=vendor_type.id).all()
    else:
        vendors = []
    
    # Get expense accounts
    expense_type = AccountType.query.filter_by(name=AccountType.EXPENSE).first()
    if expense_type:
        expense_accounts = Account.query.filter_by(account_type_id=expense_type.id, is_active=True).all()
    else:
        expense_accounts = []
    
    return render_template(
        'expense_form.html',
        expense=expense,
        vendors=vendors,
        expense_accounts=expense_accounts
    )

@expenses_bp.route('/expenses/<int:expense_id>/submit', methods=['POST'])
@login_required
def submit(expense_id):
    """Submit expense for approval"""
    # Check permission
    if not current_user.has_permission(Role.CAN_EDIT):
        flash('You do not have permission to update expenses.', 'danger')
        return redirect(url_for('expenses.index'))
    
    expense = Expense.query.get_or_404(expense_id)
    
    # Can only submit draft expenses
    if expense.status.name != ExpenseStatus.DRAFT:
        flash('Expense is not in draft status.', 'danger')
        return redirect(url_for('expenses.view', expense_id=expense_id))
    
    # Get pending status
    pending_status = ExpenseStatus.query.filter_by(name=ExpenseStatus.PENDING).first()
    
    if not pending_status:
        flash('Expense status not found.', 'danger')
        return redirect(url_for('expenses.view', expense_id=expense_id))
    
    # Update status
    expense.status_id = pending_status.id
    db.session.commit()
    
    flash('Expense submitted for approval.', 'success')
    return redirect(url_for('expenses.view', expense_id=expense_id))

@expenses_bp.route('/expenses/<int:expense_id>/approve', methods=['POST'])
@login_required
def approve(expense_id):
    """Approve an expense"""
    # Check permission
    if not current_user.has_permission(Role.CAN_APPROVE):
        flash('You do not have permission to approve expenses.', 'danger')
        return redirect(url_for('expenses.index'))
    
    expense = Expense.query.get_or_404(expense_id)
    
    # Can only approve pending expenses
    if expense.status.name != ExpenseStatus.PENDING:
        flash('Expense must be pending to approve.', 'danger')
        return redirect(url_for('expenses.view', expense_id=expense_id))
    
    # Get approved status
    approved_status = ExpenseStatus.query.filter_by(name=ExpenseStatus.APPROVED).first()
    
    if not approved_status:
        flash('Expense status not found.', 'danger')
        return redirect(url_for('expenses.view', expense_id=expense_id))
    
    # Update status
    expense.status_id = approved_status.id
    
    # Create journal entry for the expense
    # This creates the accounting entry when an expense is approved
    journal_entry = JournalEntry(
        entry_date=expense.expense_date,
        reference=expense.expense_number,
        description=f"Expense to {expense.entity.name}",
        is_posted=True,  # Automatically post the entry
        created_by_id=current_user.id
    )
    
    db.session.add(journal_entry)
    db.session.flush()  # Get ID without committing
    
    # Add line items
    journal_items = []
    
    # Get accounts payable account
    liability_type = AccountType.query.filter_by(name=AccountType.LIABILITY).first()
    if liability_type:
        ap_account = Account.query.filter(
            Account.account_type_id == liability_type.id,
            Account.name.like('%Accounts Payable%')
        ).first()
    
    if not ap_account:
        # Create default AP account if it doesn't exist
        ap_account = Account(
            code='2000',
            name='Accounts Payable',
            account_type_id=liability_type.id,
            is_active=True,
            created_by_id=current_user.id
        )
        db.session.add(ap_account)
        db.session.flush()
    
    # Credit AP
    ap_item = JournalItem(
        journal_entry_id=journal_entry.id,
        account_id=ap_account.id,
        description=f"Expense {expense.expense_number}",
        debit_amount=0,
        credit_amount=expense.total_amount
    )
    journal_items.append(ap_item)
    
    # Debit Expense accounts
    for item in expense.items:
        expense_item = JournalItem(
            journal_entry_id=journal_entry.id,
            account_id=item.account_id,
            description=item.description,
            debit_amount=item.quantity * item.unit_price,
            credit_amount=0
        )
        journal_items.append(expense_item)
    
    # Add journal items
    db.session.add_all(journal_items)
    
    # Link the journal entry to the expense
    expense.journal_entry_id = journal_entry.id
    
    db.session.commit()
    
    flash('Expense approved. Accounting entries have been created.', 'success')
    return redirect(url_for('expenses.view', expense_id=expense_id))

@expenses_bp.route('/expenses/<int:expense_id>/reject', methods=['POST'])
@login_required
def reject(expense_id):
    """Reject an expense"""
    # Check permission
    if not current_user.has_permission(Role.CAN_APPROVE):
        flash('You do not have permission to reject expenses.', 'danger')
        return redirect(url_for('expenses.index'))
    
    expense = Expense.query.get_or_404(expense_id)
    
    # Can only reject pending expenses
    if expense.status.name != ExpenseStatus.PENDING:
        flash('Expense must be pending to reject.', 'danger')
        return redirect(url_for('expenses.view', expense_id=expense_id))
    
    # Get rejected status
    rejected_status = ExpenseStatus.query.filter_by(name=ExpenseStatus.REJECTED).first()
    
    if not rejected_status:
        flash('Expense status not found.', 'danger')
        return redirect(url_for('expenses.view', expense_id=expense_id))
    
    # Update status
    expense.status_id = rejected_status.id
    db.session.commit()
    
    flash('Expense has been rejected.', 'danger')
    return redirect(url_for('expenses.view', expense_id=expense_id))

@expenses_bp.route('/expenses/<int:expense_id>/mark-paid', methods=['POST'])
@login_required
def mark_paid(expense_id):
    """Mark expense as paid"""
    # Check permission
    if not current_user.has_permission(Role.CAN_EDIT):
        flash('You do not have permission to update expenses.', 'danger')
        return redirect(url_for('expenses.index'))
    
    expense = Expense.query.get_or_404(expense_id)
    
    # Can only mark approved expenses as paid
    if expense.status.name != ExpenseStatus.APPROVED:
        flash('Expense must be approved to mark as paid.', 'danger')
        return redirect(url_for('expenses.view', expense_id=expense_id))
    
    # Get paid status
    paid_status = ExpenseStatus.query.filter_by(name=ExpenseStatus.PAID).first()
    
    if not paid_status:
        flash('Expense status not found.', 'danger')
        return redirect(url_for('expenses.view', expense_id=expense_id))
    
    # Update status
    expense.status_id = paid_status.id
    
    # Create payment journal entry
    # This creates the accounting entry for payment made
    payment_date = request.form.get('payment_date') or datetime.now().strftime('%Y-%m-%d')
    payment_date = datetime.strptime(payment_date, '%Y-%m-%d').date()
    
    journal_entry = JournalEntry(
        entry_date=payment_date,
        reference=f"PMT-{expense.expense_number}",
        description=f"Payment for expense {expense.expense_number} to {expense.entity.name}",
        is_posted=True,  # Automatically post the entry
        created_by_id=current_user.id
    )
    
    db.session.add(journal_entry)
    db.session.flush()  # Get ID without committing
    
    # Add line items
    journal_items = []
    
    # Get accounts payable account
    liability_type = AccountType.query.filter_by(name=AccountType.LIABILITY).first()
    asset_type = AccountType.query.filter_by(name=AccountType.ASSET).first()
    
    if liability_type and asset_type:
        ap_account = Account.query.filter(
            Account.account_type_id == liability_type.id,
            Account.name.like('%Accounts Payable%')
        ).first()
        
        cash_account = Account.query.filter(
            Account.account_type_id == asset_type.id,
            Account.name.like('%Cash%')
        ).first()
    
    if not ap_account or not cash_account:
        flash('Required accounts not found.', 'danger')
        return redirect(url_for('expenses.view', expense_id=expense_id))
    
    # Debit AP
    ap_item = JournalItem(
        journal_entry_id=journal_entry.id,
        account_id=ap_account.id,
        description=f"Payment for expense {expense.expense_number}",
        debit_amount=expense.total_amount,
        credit_amount=0
    )
    journal_items.append(ap_item)
    
    # Credit Cash
    cash_item = JournalItem(
        journal_entry_id=journal_entry.id,
        account_id=cash_account.id,
        description=f"Payment for expense {expense.expense_number}",
        debit_amount=0,
        credit_amount=expense.total_amount
    )
    journal_items.append(cash_item)
    
    # Add journal items
    db.session.add_all(journal_items)
    db.session.commit()
    
    flash('Expense marked as paid. Payment has been recorded.', 'success')
    return redirect(url_for('expenses.view', expense_id=expense_id))