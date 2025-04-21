from flask import Blueprint, render_template, request, redirect, url_for, flash, Response
from flask_login import login_required, current_user
from app import db
from models import JournalEntry, JournalItem, Account, Role
from datetime import datetime
import csv
from io import StringIO
import utils

journals_bp = Blueprint('journals', __name__)

@journals_bp.route('/journals')
@login_required
def index():
    """Show list of journal entries"""
    # Get filters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    status = request.args.get('status')
    
    # Base query
    query = JournalEntry.query
    
    # Apply date filters if provided
    if start_date:
        query = query.filter(JournalEntry.entry_date >= start_date)
    
    if end_date:
        query = query.filter(JournalEntry.entry_date <= end_date)
    
    # Apply status filter if provided
    if status == 'posted':
        query = query.filter_by(is_posted=True)
    elif status == 'draft':
        query = query.filter_by(is_posted=False)
    
    # Order by date desc
    journals = query.order_by(JournalEntry.entry_date.desc()).all()
    
    return render_template('journals.html', journals=journals)

@journals_bp.route('/journals/create', methods=['GET', 'POST'])
@login_required
def create():
    """Create a new journal entry"""
    # Check permission
    if not current_user.has_permission(Role.CAN_CREATE):
        flash('You do not have permission to create journal entries.', 'danger')
        return redirect(url_for('journals.index'))
    
    if request.method == 'POST':
        # Get form data
        entry_date = request.form.get('entry_date')
        reference = request.form.get('reference')
        description = request.form.get('description')
        
        # Create journal entry
        journal_entry = JournalEntry(
            entry_date=datetime.strptime(entry_date, '%Y-%m-%d').date(),
            reference=reference,
            description=description,
            is_posted=False,  # Default to draft
            created_by_id=current_user.id
        )
        
        db.session.add(journal_entry)
        db.session.flush()  # Get ID without committing
        
        # Process line items
        items = []
        total_debits = 0
        total_credits = 0
        
        for key, value in request.form.items():
            if key.startswith('items[') and key.endswith('[account_id]'):
                # Extract the index from the key
                index = key.split('[')[1].split(']')[0]
                
                account_id = value
                description = request.form.get(f'items[{index}][description]', '')
                entry_type = request.form.get(f'items[{index}][entry_type]')
                amount = float(request.form.get(f'items[{index}][amount]', 0))
                
                # Set debit or credit amount
                debit_amount = amount if entry_type == 'debit' else 0
                credit_amount = amount if entry_type == 'credit' else 0
                
                # Track totals
                total_debits += debit_amount
                total_credits += credit_amount
                
                # Create journal item
                item = JournalItem(
                    journal_entry_id=journal_entry.id,
                    account_id=account_id,
                    description=description,
                    debit_amount=debit_amount,
                    credit_amount=credit_amount
                )
                
                items.append(item)
        
        # Validate debits equal credits (with small margin for floating point errors)
        if abs(total_debits - total_credits) > 0.01:
            flash('Journal entry must be balanced (debits must equal credits).', 'danger')
            # Get accounts for the form
            accounts = Account.query.filter_by(is_active=True).order_by(Account.code).all()
            return render_template('journal_form.html', accounts=accounts)
        
        # Add all items
        db.session.add_all(items)
        db.session.commit()
        
        flash('Journal entry created successfully.', 'success')
        return redirect(url_for('journals.view', journal_id=journal_entry.id))
    
    # Get accounts for the form
    accounts = Account.query.filter_by(is_active=True).order_by(Account.code).all()
    
    return render_template(
        'journal_form.html',
        accounts=accounts,
        today=datetime.now().strftime('%Y-%m-%d')
    )

@journals_bp.route('/journals/<int:journal_id>')
@login_required
def view(journal_id):
    """View a journal entry"""
    journal = JournalEntry.query.get_or_404(journal_id)
    
    return render_template('journal_view.html', journal=journal)

@journals_bp.route('/journals/<int:journal_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(journal_id):
    """Edit a journal entry"""
    # Check permission
    if not current_user.has_permission(Role.CAN_EDIT):
        flash('You do not have permission to edit journal entries.', 'danger')
        return redirect(url_for('journals.index'))
    
    journal = JournalEntry.query.get_or_404(journal_id)
    
    # Can't edit posted entries
    if journal.is_posted:
        flash('Cannot edit a posted journal entry.', 'danger')
        return redirect(url_for('journals.view', journal_id=journal_id))
    
    if request.method == 'POST':
        # Update journal header
        journal.entry_date = datetime.strptime(request.form.get('entry_date'), '%Y-%m-%d').date()
        journal.reference = request.form.get('reference')
        journal.description = request.form.get('description')
        
        # Delete existing items
        for item in journal.items:
            db.session.delete(item)
        
        # Process line items
        items = []
        total_debits = 0
        total_credits = 0
        
        for key, value in request.form.items():
            if key.startswith('items[') and key.endswith('[account_id]'):
                # Extract the index from the key
                index = key.split('[')[1].split(']')[0]
                
                account_id = value
                description = request.form.get(f'items[{index}][description]', '')
                entry_type = request.form.get(f'items[{index}][entry_type]')
                amount = float(request.form.get(f'items[{index}][amount]', 0))
                
                # Set debit or credit amount
                debit_amount = amount if entry_type == 'debit' else 0
                credit_amount = amount if entry_type == 'credit' else 0
                
                # Track totals
                total_debits += debit_amount
                total_credits += credit_amount
                
                # Create journal item
                item = JournalItem(
                    journal_entry_id=journal.id,
                    account_id=account_id,
                    description=description,
                    debit_amount=debit_amount,
                    credit_amount=credit_amount
                )
                
                items.append(item)
        
        # Validate debits equal credits (with small margin for floating point errors)
        if abs(total_debits - total_credits) > 0.01:
            flash('Journal entry must be balanced (debits must equal credits).', 'danger')
            # Get accounts for the form
            accounts = Account.query.filter_by(is_active=True).order_by(Account.code).all()
            return render_template('journal_form.html', journal=journal, accounts=accounts)
        
        # Add all items
        db.session.add_all(items)
        db.session.commit()
        
        flash('Journal entry updated successfully.', 'success')
        return redirect(url_for('journals.view', journal_id=journal.id))
    
    # Get accounts for the form
    accounts = Account.query.filter_by(is_active=True).order_by(Account.code).all()
    
    return render_template(
        'journal_form.html',
        journal=journal,
        accounts=accounts
    )

@journals_bp.route('/journals/<int:journal_id>/post', methods=['POST'])
@login_required
def post(journal_id):
    """Post a journal entry"""
    # Check permission
    if not current_user.has_permission(Role.CAN_APPROVE):
        flash('You do not have permission to post journal entries.', 'danger')
        return redirect(url_for('journals.index'))
    
    journal = JournalEntry.query.get_or_404(journal_id)
    
    # Can't post an already posted entry
    if journal.is_posted:
        flash('Journal entry is already posted.', 'info')
        return redirect(url_for('journals.view', journal_id=journal_id))
    
    # Check if entry is balanced
    total_debits = sum(item.debit_amount for item in journal.items)
    total_credits = sum(item.credit_amount for item in journal.items)
    
    if abs(total_debits - total_credits) > 0.01:
        flash('Cannot post an unbalanced journal entry.', 'danger')
        return redirect(url_for('journals.view', journal_id=journal_id))
    
    # Post the entry
    journal.is_posted = True
    db.session.commit()
    
    flash('Journal entry posted successfully.', 'success')
    return redirect(url_for('journals.view', journal_id=journal_id))

@journals_bp.route('/journals/<int:journal_id>/delete', methods=['POST'])
@login_required
def delete(journal_id):
    """Delete a journal entry"""
    # Check permission
    if not current_user.has_permission(Role.CAN_DELETE):
        flash('You do not have permission to delete journal entries.', 'danger')
        return redirect(url_for('journals.index'))
    
    journal = JournalEntry.query.get_or_404(journal_id)
    
    # Can't delete posted entries
    if journal.is_posted:
        flash('Cannot delete a posted journal entry.', 'danger')
        return redirect(url_for('journals.view', journal_id=journal_id))
    
    # First delete all journal items
    for item in journal.items:
        db.session.delete(item)
    
    # Then delete the journal entry
    db.session.delete(journal)
    db.session.commit()
    
    flash('Journal entry deleted successfully.', 'success')
    return redirect(url_for('journals.index'))

@journals_bp.route('/journals/export/csv')
@login_required
def export_csv():
    """Export journal entries to CSV"""
    # Get date range filters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Parse dates if provided
    start_date = datetime.strptime(start_date, '%Y-%m-%d').date() if start_date else None
    end_date = datetime.strptime(end_date, '%Y-%m-%d').date() if end_date else None
    
    # Get entries and items
    entries_df, items_df = utils.export_journal_entries_to_csv(start_date, end_date)
    
    # Create CSV output
    output = StringIO()
    writer = csv.writer(output)
    
    # Write headers
    writer.writerow(['Journal Entries'])
    writer.writerow(['ID', 'Date', 'Reference', 'Description', 'Status', 'Created By'])
    
    # Write entries
    for _, entry in entries_df.iterrows():
        writer.writerow([
            entry['id'],
            entry['entry_date'],
            entry['reference'],
            entry['description'],
            entry['status'],
            entry['created_by']
        ])
    
    # Add a blank row
    writer.writerow([])
    
    # Write item headers
    writer.writerow(['Journal Items'])
    writer.writerow(['Journal Entry ID', 'Account Code', 'Account Name', 'Description', 'Debit Amount', 'Credit Amount'])
    
    # Write items
    for _, item in items_df.iterrows():
        writer.writerow([
            item['journal_entry_id'],
            item['account_code'],
            item['account_name'],
            item['description'],
            item['debit_amount'],
            item['credit_amount']
        ])
    
    # Create response
    response = Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={
            'Content-Disposition': 'attachment;filename=journal_entries.csv'
        }
    )
    
    return response
