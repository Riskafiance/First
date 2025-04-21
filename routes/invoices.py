from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from models import Invoice, InvoiceItem, Entity, EntityType, InvoiceStatus, Account, AccountType
from models import JournalEntry, JournalItem, Role
import sys, os
# Add the project root directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import utils
from datetime import datetime

invoices_bp = Blueprint('invoices', __name__)

@invoices_bp.route('/invoices')
@login_required
def index():
    """Show list of invoices"""
    # Get filters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    status = request.args.get('status')
    
    # Base query
    query = Invoice.query
    
    # Apply date filters if provided
    if start_date:
        query = query.filter(Invoice.issue_date >= start_date)
    
    if end_date:
        query = query.filter(Invoice.issue_date <= end_date)
    
    # Apply status filter if provided
    if status:
        query = query.join(InvoiceStatus).filter(InvoiceStatus.name == status)
    
    # Order by date desc
    invoices = query.order_by(Invoice.issue_date.desc()).all()
    
    # Get all statuses for filter dropdown
    statuses = InvoiceStatus.query.all()
    
    return render_template(
        'invoices.html',
        invoices=invoices,
        statuses=statuses
    )

@invoices_bp.route('/invoices/create', methods=['GET', 'POST'])
@login_required
def create():
    """Create a new invoice"""
    # Check permission
    if not current_user.has_permission(Role.CAN_CREATE):
        flash('You do not have permission to create invoices.', 'danger')
        return redirect(url_for('invoices.index'))
    
    if request.method == 'POST':
        # Get form data
        entity_id = request.form.get('entityId')
        issue_date = request.form.get('issueDate')
        due_date = request.form.get('dueDate')
        notes = request.form.get('notes')
        total_amount = float(request.form.get('invoiceTotal', 0))
        
        # Get draft status
        draft_status = InvoiceStatus.query.filter_by(name=InvoiceStatus.DRAFT).first()
        if not draft_status:
            # Create invoice statuses if they don't exist
            draft_status = InvoiceStatus(name=InvoiceStatus.DRAFT)
            sent_status = InvoiceStatus(name=InvoiceStatus.SENT)
            paid_status = InvoiceStatus(name=InvoiceStatus.PAID)
            overdue_status = InvoiceStatus(name=InvoiceStatus.OVERDUE)
            cancelled_status = InvoiceStatus(name=InvoiceStatus.CANCELLED)
            
            db.session.add_all([draft_status, sent_status, paid_status, overdue_status, cancelled_status])
            db.session.commit()
        
        # Generate invoice number
        invoice_number = utils.generate_invoice_number()
        
        # Create invoice
        invoice = Invoice(
            invoice_number=invoice_number,
            entity_id=entity_id,
            issue_date=datetime.strptime(issue_date, '%Y-%m-%d').date(),
            due_date=datetime.strptime(due_date, '%Y-%m-%d').date(),
            status_id=draft_status.id,
            total_amount=total_amount,
            notes=notes,
            created_by_id=current_user.id
        )
        
        db.session.add(invoice)
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
                
                # Create invoice item
                item = InvoiceItem(
                    invoice_id=invoice.id,
                    description=description,
                    quantity=quantity,
                    unit_price=unit_price,
                    account_id=account_id
                )
                
                items.append(item)
        
        # Add all items
        db.session.add_all(items)
        db.session.commit()
        
        flash('Invoice created successfully.', 'success')
        return redirect(url_for('invoices.view', invoice_id=invoice.id))
    
    # Get customers (entities of type Customer)
    customer_type = EntityType.query.filter_by(name=EntityType.CUSTOMER).first()
    if customer_type:
        customers = Entity.query.filter_by(entity_type_id=customer_type.id).all()
    else:
        customers = []
    
    # Get revenue accounts
    revenue_type = AccountType.query.filter_by(name=AccountType.REVENUE).first()
    if revenue_type:
        revenue_accounts = Account.query.filter_by(account_type_id=revenue_type.id, is_active=True).all()
    else:
        revenue_accounts = []
    
    return render_template(
        'invoice_form.html',
        customers=customers,
        revenue_accounts=revenue_accounts,
        today=datetime.now().strftime('%Y-%m-%d')
    )

@invoices_bp.route('/invoices/<int:invoice_id>')
@login_required
def view(invoice_id):
    """View an invoice"""
    invoice = Invoice.query.get_or_404(invoice_id)
    
    return render_template('invoice_view.html', invoice=invoice, now=datetime.now())

@invoices_bp.route('/invoices/<int:invoice_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(invoice_id):
    """Edit an invoice"""
    # Check permission
    if not current_user.has_permission(Role.CAN_EDIT):
        flash('You do not have permission to edit invoices.', 'danger')
        return redirect(url_for('invoices.index'))
    
    invoice = Invoice.query.get_or_404(invoice_id)
    
    # Can only edit draft invoices
    if invoice.status.name != InvoiceStatus.DRAFT:
        flash('Cannot edit an invoice that is not in draft status.', 'danger')
        return redirect(url_for('invoices.view', invoice_id=invoice_id))
    
    if request.method == 'POST':
        # Update invoice
        invoice.entity_id = request.form.get('entityId')
        invoice.issue_date = datetime.strptime(request.form.get('issueDate'), '%Y-%m-%d').date()
        invoice.due_date = datetime.strptime(request.form.get('dueDate'), '%Y-%m-%d').date()
        invoice.notes = request.form.get('notes')
        invoice.total_amount = float(request.form.get('invoiceTotal', 0))
        
        # Delete existing items
        for item in invoice.items:
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
                
                # Create invoice item
                item = InvoiceItem(
                    invoice_id=invoice.id,
                    description=description,
                    quantity=quantity,
                    unit_price=unit_price,
                    account_id=account_id
                )
                
                items.append(item)
        
        # Add all items
        db.session.add_all(items)
        db.session.commit()
        
        flash('Invoice updated successfully.', 'success')
        return redirect(url_for('invoices.view', invoice_id=invoice.id))
    
    # Get customers (entities of type Customer)
    customer_type = EntityType.query.filter_by(name=EntityType.CUSTOMER).first()
    if customer_type:
        customers = Entity.query.filter_by(entity_type_id=customer_type.id).all()
    else:
        customers = []
    
    # Get revenue accounts
    revenue_type = AccountType.query.filter_by(name=AccountType.REVENUE).first()
    if revenue_type:
        revenue_accounts = Account.query.filter_by(account_type_id=revenue_type.id, is_active=True).all()
    else:
        revenue_accounts = []
    
    return render_template(
        'invoice_form.html',
        invoice=invoice,
        customers=customers,
        revenue_accounts=revenue_accounts
    )

@invoices_bp.route('/invoices/<int:invoice_id>/send', methods=['POST'])
@login_required
def send(invoice_id):
    """Mark invoice as sent"""
    # Check permission
    if not current_user.has_permission(Role.CAN_EDIT):
        flash('You do not have permission to update invoices.', 'danger')
        return redirect(url_for('invoices.index'))
    
    invoice = Invoice.query.get_or_404(invoice_id)
    
    # Can only send draft invoices
    if invoice.status.name != InvoiceStatus.DRAFT:
        flash('Invoice is not in draft status.', 'danger')
        return redirect(url_for('invoices.view', invoice_id=invoice_id))
    
    # Get sent status
    sent_status = InvoiceStatus.query.filter_by(name=InvoiceStatus.SENT).first()
    
    if not sent_status:
        flash('Invoice status not found.', 'danger')
        return redirect(url_for('invoices.view', invoice_id=invoice_id))
    
    # Update status
    invoice.status_id = sent_status.id
    
    # Create journal entry for the invoice
    # This creates the accounting entry when an invoice is sent
    journal_entry = JournalEntry(
        entry_date=invoice.issue_date,
        reference=invoice.invoice_number,
        description=f"Invoice to {invoice.entity.name}",
        is_posted=True,  # Automatically post the entry
        created_by_id=current_user.id
    )
    
    db.session.add(journal_entry)
    db.session.flush()  # Get ID without committing
    
    # Add line items
    journal_items = []
    
    # Get accounts receivable account
    asset_type = AccountType.query.filter_by(name=AccountType.ASSET).first()
    if asset_type:
        ar_account = Account.query.filter(
            Account.account_type_id == asset_type.id,
            Account.name.like('%Accounts Receivable%')
        ).first()
    
    if not ar_account:
        # Create default AR account if it doesn't exist
        ar_account = Account(
            code='1200',
            name='Accounts Receivable',
            account_type_id=asset_type.id,
            is_active=True,
            created_by_id=current_user.id
        )
        db.session.add(ar_account)
        db.session.flush()
    
    # Debit AR
    ar_item = JournalItem(
        journal_entry_id=journal_entry.id,
        account_id=ar_account.id,
        description=f"Invoice {invoice.invoice_number}",
        debit_amount=invoice.total_amount,
        credit_amount=0
    )
    journal_items.append(ar_item)
    
    # Credit Revenue accounts
    for item in invoice.items:
        revenue_item = JournalItem(
            journal_entry_id=journal_entry.id,
            account_id=item.account_id,
            description=item.description,
            debit_amount=0,
            credit_amount=item.quantity * item.unit_price
        )
        journal_items.append(revenue_item)
    
    # Add journal items
    db.session.add_all(journal_items)
    
    # Link the journal entry to the invoice
    invoice.journal_entry_id = journal_entry.id
    
    db.session.commit()
    
    flash('Invoice marked as sent. Accounting entries have been created.', 'success')
    return redirect(url_for('invoices.view', invoice_id=invoice_id))

@invoices_bp.route('/invoices/<int:invoice_id>/mark-paid', methods=['POST'])
@login_required
def mark_paid(invoice_id):
    """Mark invoice as paid"""
    # Check permission
    if not current_user.has_permission(Role.CAN_EDIT):
        flash('You do not have permission to update invoices.', 'danger')
        return redirect(url_for('invoices.index'))
    
    invoice = Invoice.query.get_or_404(invoice_id)
    
    # Can only mark sent or overdue invoices as paid
    if invoice.status.name not in [InvoiceStatus.SENT, InvoiceStatus.OVERDUE]:
        flash('Invoice must be sent or overdue to mark as paid.', 'danger')
        return redirect(url_for('invoices.view', invoice_id=invoice_id))
    
    # Get paid status
    paid_status = InvoiceStatus.query.filter_by(name=InvoiceStatus.PAID).first()
    
    if not paid_status:
        flash('Invoice status not found.', 'danger')
        return redirect(url_for('invoices.view', invoice_id=invoice_id))
    
    # Update status
    invoice.status_id = paid_status.id
    
    # Create payment journal entry
    # This creates the accounting entry for payment received
    payment_date = request.form.get('payment_date') or datetime.now().strftime('%Y-%m-%d')
    payment_date = datetime.strptime(payment_date, '%Y-%m-%d').date()
    
    journal_entry = JournalEntry(
        entry_date=payment_date,
        reference=f"PMT-{invoice.invoice_number}",
        description=f"Payment for invoice {invoice.invoice_number} from {invoice.entity.name}",
        is_posted=True,  # Automatically post the entry
        created_by_id=current_user.id
    )
    
    db.session.add(journal_entry)
    db.session.flush()  # Get ID without committing
    
    # Add line items
    journal_items = []
    
    # Get accounts receivable account
    asset_type = AccountType.query.filter_by(name=AccountType.ASSET).first()
    if asset_type:
        ar_account = Account.query.filter(
            Account.account_type_id == asset_type.id,
            Account.name.like('%Accounts Receivable%')
        ).first()
        
        cash_account = Account.query.filter(
            Account.account_type_id == asset_type.id,
            Account.name.like('%Cash%')
        ).first()
    
    if not ar_account or not cash_account:
        flash('Required accounts not found.', 'danger')
        return redirect(url_for('invoices.view', invoice_id=invoice_id))
    
    # Debit Cash
    cash_item = JournalItem(
        journal_entry_id=journal_entry.id,
        account_id=cash_account.id,
        description=f"Payment for invoice {invoice.invoice_number}",
        debit_amount=invoice.total_amount,
        credit_amount=0
    )
    journal_items.append(cash_item)
    
    # Credit AR
    ar_item = JournalItem(
        journal_entry_id=journal_entry.id,
        account_id=ar_account.id,
        description=f"Payment for invoice {invoice.invoice_number}",
        debit_amount=0,
        credit_amount=invoice.total_amount
    )
    journal_items.append(ar_item)
    
    # Add journal items
    db.session.add_all(journal_items)
    db.session.commit()
    
    flash('Invoice marked as paid. Payment has been recorded.', 'success')
    return redirect(url_for('invoices.view', invoice_id=invoice_id))

@invoices_bp.route('/invoices/<int:invoice_id>/cancel', methods=['POST'])
@login_required
def cancel(invoice_id):
    """Cancel an invoice"""
    # Check permission
    if not current_user.has_permission(Role.CAN_DELETE):
        flash('You do not have permission to cancel invoices.', 'danger')
        return redirect(url_for('invoices.index'))
    
    invoice = Invoice.query.get_or_404(invoice_id)
    
    # Cannot cancel paid invoices
    if invoice.status.name == InvoiceStatus.PAID:
        flash('Cannot cancel a paid invoice.', 'danger')
        return redirect(url_for('invoices.view', invoice_id=invoice_id))
    
    # Get cancelled status
    cancelled_status = InvoiceStatus.query.filter_by(name=InvoiceStatus.CANCELLED).first()
    
    if not cancelled_status:
        flash('Invoice status not found.', 'danger')
        return redirect(url_for('invoices.view', invoice_id=invoice_id))
    
    # Update status
    invoice.status_id = cancelled_status.id
    
    # If the invoice was sent and has a journal entry, create a reversing entry
    if invoice.journal_entry_id:
        original_entry = JournalEntry.query.get(invoice.journal_entry_id)
        
        # Create reversing journal entry
        journal_entry = JournalEntry(
            entry_date=datetime.now().date(),
            reference=f"VOID-{invoice.invoice_number}",
            description=f"Cancellation of invoice {invoice.invoice_number} to {invoice.entity.name}",
            is_posted=True,  # Automatically post the entry
            created_by_id=current_user.id
        )
        
        db.session.add(journal_entry)
        db.session.flush()  # Get ID without committing
        
        # Add reversing line items (reverse debits and credits)
        journal_items = []
        
        for item in original_entry.items:
            # Reverse the entry
            reversal_item = JournalItem(
                journal_entry_id=journal_entry.id,
                account_id=item.account_id,
                description=f"Reversal: {item.description}",
                debit_amount=item.credit_amount,
                credit_amount=item.debit_amount
            )
            journal_items.append(reversal_item)
        
        # Add journal items
        db.session.add_all(journal_items)
    
    db.session.commit()
    
    flash('Invoice cancelled successfully.', 'success')
    return redirect(url_for('invoices.view', invoice_id=invoice_id))
