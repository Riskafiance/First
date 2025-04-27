from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from models import Role
from app import db
from flask_login import current_user
from utils.user_data import get_financial_summary as get_user_financial_summary
from utils.user_data import get_monthly_trends as get_user_monthly_trends

def get_financial_summary(start_date=None, end_date=None):
    """Get financial summary for dashboard
    
    This is a wrapper function that redirects to the user-specific function
    if a user is logged in, otherwise it uses the database
    """
    if current_user.is_authenticated:
        return get_user_financial_summary(current_user.username, start_date, end_date)
    
    if not start_date:
        start_date = datetime.now().date().replace(day=1)  # First day of current month
    if not end_date:
        end_date = datetime.now().date()  # Current date
    
    # Get income (revenue accounts)
    revenue_type = db.session.query(AccountType).filter_by(name=AccountType.REVENUE).first()
    if revenue_type:
        revenue_accounts = db.session.query(Account.id).filter_by(account_type_id=revenue_type.id).all()
        revenue_account_ids = [acc.id for acc in revenue_accounts]
        
        income_entries = db.session.query(
            db.func.sum(JournalItem.credit_amount - JournalItem.debit_amount)
        ).join(
            JournalEntry, JournalItem.journal_entry_id == JournalEntry.id
        ).filter(
            JournalItem.account_id.in_(revenue_account_ids),
            JournalEntry.entry_date.between(start_date, end_date),
            JournalEntry.is_posted == True
        ).scalar() or 0
    else:
        income_entries = 0
    
    # Get expenses
    expense_type = db.session.query(AccountType).filter_by(name=AccountType.EXPENSE).first()
    if expense_type:
        expense_accounts = db.session.query(Account.id).filter_by(account_type_id=expense_type.id).all()
        expense_account_ids = [acc.id for acc in expense_accounts]
        
        expense_entries = db.session.query(
            db.func.sum(JournalItem.debit_amount - JournalItem.credit_amount)
        ).join(
            JournalEntry, JournalItem.journal_entry_id == JournalEntry.id
        ).filter(
            JournalItem.account_id.in_(expense_account_ids),
            JournalEntry.entry_date.between(start_date, end_date),
            JournalEntry.is_posted == True
        ).scalar() or 0
    else:
        expense_entries = 0
    
    # Get receivables (outstanding invoice amounts)
    outstanding_invoices = db.session.query(
        db.func.sum(Invoice.total_amount)
    ).join(
        InvoiceStatus, Invoice.status_id == InvoiceStatus.id
    ).filter(
        InvoiceStatus.name.in_([InvoiceStatus.SENT, InvoiceStatus.OVERDUE])
    ).scalar() or 0
    
    # Build response dictionary
    return {
        'income': float(income_entries),
        'expenses': float(expense_entries),
        'net_income': float(income_entries - expense_entries),
        'accounts_receivable': float(outstanding_invoices)
    }

def get_monthly_trends(months=6):
    """Get monthly income and expense trends for the last X months
    
    This is a wrapper function that redirects to the user-specific function
    if a user is logged in, otherwise it uses the database
    """
    if current_user.is_authenticated:
        return get_user_monthly_trends(current_user.username, months)
        
    today = datetime.now().date()
    data = []
    
    revenue_type = db.session.query(AccountType).filter_by(name=AccountType.REVENUE).first()
    expense_type = db.session.query(AccountType).filter_by(name=AccountType.EXPENSE).first()
    
    revenue_account_ids = []
    if revenue_type:
        revenue_accounts = db.session.query(Account.id).filter_by(account_type_id=revenue_type.id).all()
        revenue_account_ids = [acc.id for acc in revenue_accounts]
    
    expense_account_ids = []
    if expense_type:
        expense_accounts = db.session.query(Account.id).filter_by(account_type_id=expense_type.id).all()
        expense_account_ids = [acc.id for acc in expense_accounts]
    
    # Loop through recent months
    for i in range(months-1, -1, -1):
        start_date = (today.replace(day=1) - timedelta(days=i*30)).replace(day=1)
        if i > 0:
            end_date = (today.replace(day=1) - timedelta(days=(i-1)*30)).replace(day=1) - timedelta(days=1)
        else:
            end_date = today
        
        # Get income for month
        income = 0
        if revenue_account_ids:
            income = db.session.query(
                db.func.sum(JournalItem.credit_amount - JournalItem.debit_amount)
            ).join(
                JournalEntry, JournalItem.journal_entry_id == JournalEntry.id
            ).filter(
                JournalItem.account_id.in_(revenue_account_ids),
                JournalEntry.entry_date.between(start_date, end_date),
                JournalEntry.is_posted == True
            ).scalar() or 0
        
        # Get expenses for month
        expenses = 0
        if expense_account_ids:
            expenses = db.session.query(
                db.func.sum(JournalItem.debit_amount - JournalItem.credit_amount)
            ).join(
                JournalEntry, JournalItem.journal_entry_id == JournalEntry.id
            ).filter(
                JournalItem.account_id.in_(expense_account_ids),
                JournalEntry.entry_date.between(start_date, end_date),
                JournalEntry.is_posted == True
            ).scalar() or 0
        
        month_name = start_date.strftime("%b %Y")
        data.append({
            'month': month_name,
            'income': float(income),
            'expenses': float(expenses)
        })
    
    return data

def generate_pl_report(start_date=None, end_date=None):
    """Generate a Profit and Loss report for the given period"""
    if not start_date:
        start_date = datetime.now().date().replace(day=1)  # First day of current month
    if not end_date:
        end_date = datetime.now().date()  # Current date
    
    # Get account types
    revenue_type = db.session.query(AccountType).filter_by(name=AccountType.REVENUE).first()
    expense_type = db.session.query(AccountType).filter_by(name=AccountType.EXPENSE).first()
    
    report_data = {
        'period': f"{start_date.strftime('%b %d, %Y')} to {end_date.strftime('%b %d, %Y')}",
        'revenue': [],
        'expenses': [],
        'totals': {
            'revenue': 0,
            'expenses': 0,
            'net_income': 0
        }
    }
    
    # Get revenue data
    if revenue_type:
        revenue_accounts = db.session.query(Account).filter_by(account_type_id=revenue_type.id).all()
        total_revenue = 0
        
        for account in revenue_accounts:
            # Query journal items for this account in the date range
            balance = db.session.query(
                db.func.sum(JournalItem.credit_amount - JournalItem.debit_amount)
            ).join(
                JournalEntry, JournalItem.journal_entry_id == JournalEntry.id
            ).filter(
                JournalItem.account_id == account.id,
                JournalEntry.entry_date.between(start_date, end_date),
                JournalEntry.is_posted == True
            ).scalar() or 0
            
            if balance != 0:
                report_data['revenue'].append({
                    'account_code': account.code,
                    'account_name': account.name,
                    'balance': float(balance)
                })
                total_revenue += float(balance)
        
        report_data['totals']['revenue'] = total_revenue
    
    # Get expense data
    if expense_type:
        expense_accounts = db.session.query(Account).filter_by(account_type_id=expense_type.id).all()
        total_expenses = 0
        
        for account in expense_accounts:
            # Query journal items for this account in the date range
            balance = db.session.query(
                db.func.sum(JournalItem.debit_amount - JournalItem.credit_amount)
            ).join(
                JournalEntry, JournalItem.journal_entry_id == JournalEntry.id
            ).filter(
                JournalItem.account_id == account.id,
                JournalEntry.entry_date.between(start_date, end_date),
                JournalEntry.is_posted == True
            ).scalar() or 0
            
            if balance != 0:
                report_data['expenses'].append({
                    'account_code': account.code,
                    'account_name': account.name,
                    'balance': float(balance)
                })
                total_expenses += float(balance)
        
        report_data['totals']['expenses'] = total_expenses
    
    # Calculate net income
    report_data['totals']['net_income'] = report_data['totals']['revenue'] - report_data['totals']['expenses']
    
    return report_data

def generate_invoice_number():
    """Generate a unique invoice number"""
    # Format: INV-YYYYMMDD-XXX where XXX is a sequential number
    today = datetime.now().date()
    date_part = today.strftime("%Y%m%d")
    
    # Get the latest invoice for today
    latest_invoice = db.session.query(Invoice).filter(
        Invoice.invoice_number.like(f"INV-{date_part}-%")
    ).order_by(
        Invoice.invoice_number.desc()
    ).first()
    
    if latest_invoice:
        # Extract the sequence number and increment
        seq_part = latest_invoice.invoice_number.split('-')[2]
        new_seq = int(seq_part) + 1
    else:
        new_seq = 1
    
    return f"INV-{date_part}-{new_seq:03d}"

def generate_expense_number():
    """Generate a unique expense number"""
    # Format: EXP-YYYYMMDD-XXX where XXX is a sequential number
    today = datetime.now().date()
    date_part = today.strftime("%Y%m%d")
    
    # Get the latest expense for today
    latest_expense = db.session.query(Expense).filter(
        Expense.expense_number.like(f"EXP-{date_part}-%")
    ).order_by(
        Expense.expense_number.desc()
    ).first()
    
    if latest_expense:
        # Extract the sequence number and increment
        seq_part = latest_expense.expense_number.split('-')[2]
        new_seq = int(seq_part) + 1
    else:
        new_seq = 1
    
    return f"EXP-{date_part}-{new_seq:03d}"

def generate_product_sku():
    """Generate a unique product SKU"""
    # Format: PRD-XXXXXX where X is alphanumeric
    import random
    import string
    
    # Generate random part
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    sku = f"PRD-{random_part}"
    
    # Check if it exists already
    while db.session.query(Product).filter_by(sku=sku).first():
        random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        sku = f"PRD-{random_part}"
    
    return sku

def generate_po_number():
    """Generate a unique purchase order number"""
    # Format: PO-YYYYMMDD-XXX where XXX is a sequential number
    today = datetime.now().date()
    date_part = today.strftime("%Y%m%d")
    
    # Get the latest PO for today
    latest_po = db.session.query(PurchaseOrder).filter(
        PurchaseOrder.po_number.like(f"PO-{date_part}-%")
    ).order_by(
        PurchaseOrder.po_number.desc()
    ).first()
    
    if latest_po:
        # Extract the sequence number and increment
        seq_part = latest_po.po_number.split('-')[2]
        new_seq = int(seq_part) + 1
    else:
        new_seq = 1
    
    return f"PO-{date_part}-{new_seq:03d}"

def record_inventory_transaction(product_id, quantity, transaction_type, transaction_type_id=None, 
                                unit_price=None, location=None, reference_type=None, reference_id=None, 
                                notes=None, journal_entry_id=None, created_by_id=None):
    """Record an inventory transaction"""
    # Create inventory transaction
    transaction = InventoryTransaction(
        transaction_date=datetime.now(),
        transaction_type=transaction_type,  # 'IN' or 'OUT'
        transaction_type_id=transaction_type_id,
        product_id=product_id,
        quantity=quantity,
        unit_price=unit_price,
        location=location,
        reference_type=reference_type,
        reference_id=reference_id,
        notes=notes,
        journal_entry_id=journal_entry_id,
        created_by_id=created_by_id
    )
    
    db.session.add(transaction)
    db.session.commit()
    
    return transaction

def get_inventory_value():
    """Calculate the total value of inventory"""
    from sqlalchemy import func
    
    # Get all products
    products = db.session.query(Product).filter_by(is_active=True).all()
    
    total_value = 0
    
    for product in products:
        # Get current stock quantity
        current_stock = product.current_stock
        
        # Calculate value using cost price
        if current_stock > 0:
            total_value += float(current_stock) * float(product.cost_price)
    
    return total_value

def get_low_stock_products():
    """Get products that are below their reorder level"""
    # Get all active products
    products = db.session.query(Product).filter_by(is_active=True).all()
    
    low_stock = []
    
    for product in products:
        current_stock = product.current_stock
        
        if current_stock <= product.reorder_level:
            low_stock.append({
                'id': product.id,
                'sku': product.sku,
                'name': product.name,
                'current_stock': float(current_stock),
                'reorder_level': float(product.reorder_level),
                'uom': product.uom.abbreviation
            })
    
    return low_stock

def export_journal_entries_to_csv(start_date=None, end_date=None):
    """Export journal entries to a pandas DataFrame and then to CSV"""
    if not start_date:
        start_date = datetime.now().date().replace(day=1)  # First day of current month
    if not end_date:
        end_date = datetime.now().date()  # Current date
    
    # Query database for journal entries in date range
    entries = db.session.query(
        JournalEntry.id, 
        JournalEntry.entry_date, 
        JournalEntry.reference, 
        JournalEntry.description,
        JournalEntry.is_posted,
        User.username.label('created_by')
    ).join(
        User, JournalEntry.created_by_id == User.id
    ).filter(
        JournalEntry.entry_date.between(start_date, end_date)
    ).order_by(
        JournalEntry.entry_date.desc()
    ).all()
    
    # Convert to DataFrame
    entries_df = pd.DataFrame([
        {
            'id': entry.id,
            'entry_date': entry.entry_date,
            'reference': entry.reference,
            'description': entry.description,
            'status': 'Posted' if entry.is_posted else 'Draft',
            'created_by': entry.created_by
        } for entry in entries
    ])
    
    # Get items for each entry
    all_items = []
    for entry in entries:
        items = db.session.query(
            JournalItem.id,
            JournalItem.journal_entry_id,
            Account.code.label('account_code'),
            Account.name.label('account_name'),
            JournalItem.description,
            JournalItem.debit_amount,
            JournalItem.credit_amount
        ).join(
            Account, JournalItem.account_id == Account.id
        ).filter(
            JournalItem.journal_entry_id == entry.id
        ).all()
        
        for item in items:
            all_items.append({
                'journal_entry_id': item.journal_entry_id,
                'account_code': item.account_code,
                'account_name': item.account_name,
                'description': item.description,
                'debit_amount': item.debit_amount,
                'credit_amount': item.credit_amount
            })
    
    items_df = pd.DataFrame(all_items)
    
    return entries_df, items_df

def generate_asset_number():
    """Generate an asset number with format FA-YYYYMM-XXXX"""
    prefix = "FA"
    date_part = datetime.now().strftime("%Y%m")
    
    # Get the latest asset for current month
    latest_asset = db.session.query(FixedAsset).filter(
        FixedAsset.asset_number.like(f"{prefix}-{date_part}-%")
    ).order_by(
        FixedAsset.asset_number.desc()
    ).first()
    
    if latest_asset:
        # Extract the sequence number and increment
        seq_part = latest_asset.asset_number.split('-')[2]
        new_seq = int(seq_part) + 1
    else:
        new_seq = 1
    
    return f"{prefix}-{date_part}-{new_seq:04d}"

def format_currency(amount, symbol='$', decimal_places=2):
    """Format a number as currency with the specified symbol and decimal places"""
    if amount is None:
        return f"{symbol}0.00"
    
    try:
        formatted = f"{symbol}{float(amount):,.{decimal_places}f}"
        return formatted
    except (ValueError, TypeError):
        return f"{symbol}0.00"

def get_next_sequence(sequence_name, initial_value=1):
    """Get next sequence number for various document types"""
    # Check if Sequence model exists in the database
    from models import Sequence
    
    sequence = Sequence.query.filter_by(name=sequence_name).first()
    
    if not sequence:
        sequence = Sequence(name=sequence_name, value=initial_value)
        db.session.add(sequence)
        db.session.commit()
        return initial_value
    else:
        sequence.value += 1
        db.session.commit()
        return sequence.value

def month_name(month_number):
    """Get the name of a month from its number (1-12)"""
    import calendar
    return calendar.month_name[month_number]

def quarter_name(quarter_number, year=None):
    """Get the name of a quarter from its number (1-4)"""
    if year:
        return f"Q{quarter_number} {year}"
    return f"Q{quarter_number}"

def get_account_balance(account_id, start_date=None, end_date=None):
    """Get the balance of an account for a specific date range"""
    from models import Account, JournalItem, JournalEntry, AccountType
    from sqlalchemy import func
    from decimal import Decimal
    
    # Get the account
    account = Account.query.get(account_id)
    if not account:
        return Decimal('0.00')
    
    # Base query
    query = db.session.query(
        func.sum(JournalItem.debit_amount).label('total_debit'),
        func.sum(JournalItem.credit_amount).label('total_credit')
    ).join(
        JournalEntry, JournalItem.journal_entry_id == JournalEntry.id
    ).filter(
        JournalItem.account_id == account_id,
        JournalEntry.is_posted == True
    )
    
    # Apply date filters
    if start_date:
        query = query.filter(JournalEntry.entry_date >= start_date)
    if end_date:
        query = query.filter(JournalEntry.entry_date <= end_date)
    
    # Execute query
    result = query.first()
    
    # Calculate balance based on account type
    total_debit = result.total_debit or Decimal('0.00')
    total_credit = result.total_credit or Decimal('0.00')
    
    # For asset and expense accounts, debit increases the balance
    if account.account_type.name in [AccountType.ASSET, AccountType.EXPENSE]:
        balance = total_debit - total_credit
    # For liability, equity, and revenue accounts, credit increases the balance
    else:
        balance = total_credit - total_debit
    
    return balance

def generate_general_ledger(start_date=None, end_date=None, account_ids=None, account_type_ids=None, include_unposted=False):
    """Generate a general ledger report with optional filters"""
    from models import JournalEntry, JournalItem, Account, AccountType
    from datetime import datetime
    
    # Build the query with filtering
    query = db.session.query(
        JournalEntry.id.label('entry_id'),
        JournalEntry.entry_date,
        JournalEntry.reference,
        JournalEntry.description.label('entry_description'),
        JournalEntry.is_posted,
        Account.id.label('account_id'),
        Account.code.label('account_code'),
        Account.name.label('account_name'),
        AccountType.name.label('account_type'),
        JournalItem.description.label('item_description'),
        JournalItem.debit_amount,
        JournalItem.credit_amount
    ).join(
        JournalItem, JournalEntry.id == JournalItem.journal_entry_id
    ).join(
        Account, JournalItem.account_id == Account.id
    ).join(
        AccountType, Account.account_type_id == AccountType.id
    )
    
    # Apply date filters
    if start_date:
        query = query.filter(JournalEntry.entry_date >= start_date)
    if end_date:
        query = query.filter(JournalEntry.entry_date <= end_date)
    
    # Apply account filters
    if account_ids and any(account_ids):
        account_ids = [int(id) for id in account_ids]
        query = query.filter(Account.id.in_(account_ids))
    
    # Apply account type filters
    if account_type_ids and any(account_type_ids):
        account_type_ids = [int(id) for id in account_type_ids]
        query = query.filter(Account.account_type_id.in_(account_type_ids))
    
    # Apply posted status filter
    if not include_unposted:
        query = query.filter(JournalEntry.is_posted == True)
    
    # Order by date and entry ID
    query = query.order_by(JournalEntry.entry_date, JournalEntry.id, Account.code)
    
    # Execute the query
    results = query.all()
    
    # Organize results by account with running balance
    accounts = {}
    entries = []
    
    for row in results:
        entry = {
            'entry_id': row.entry_id,
            'entry_date': row.entry_date,
            'reference': row.reference,
            'entry_description': row.entry_description,
            'is_posted': row.is_posted,
            'account_id': row.account_id,
            'account_code': row.account_code,
            'account_name': row.account_name,
            'account_type': row.account_type,
            'item_description': row.item_description,
            'debit_amount': float(row.debit_amount) if row.debit_amount else 0,
            'credit_amount': float(row.credit_amount) if row.credit_amount else 0
        }
        
        entries.append(entry)
        
        # Track account balances
        if row.account_id not in accounts:
            accounts[row.account_id] = {
                'id': row.account_id,
                'code': row.account_code,
                'name': row.account_name,
                'type': row.account_type,
                'starting_balance': 0,  # Placeholder, will calculate running balances later
                'debit_total': 0,
                'credit_total': 0,
                'entries': []
            }
        
        accounts[row.account_id]['entries'].append(entry)
        accounts[row.account_id]['debit_total'] += float(row.debit_amount) if row.debit_amount else 0
        accounts[row.account_id]['credit_total'] += float(row.credit_amount) if row.credit_amount else 0
    
    # Calculate net movement and ending balance for each account
    for account_id, account in accounts.items():
        # Get the starting balance for this account (as of start_date - 1 day)
        if start_date:
            account['starting_balance'] = get_account_balance(account_id, end_date=start_date - timedelta(days=1))
        else:
            account['starting_balance'] = 0
        
        account_type = account['type']
        
        # Calculate balance based on account type
        if account_type in [AccountType.ASSET, AccountType.EXPENSE]:
            # Debit increases, credit decreases
            account['net_movement'] = account['debit_total'] - account['credit_total']
        else:
            # Credit increases, debit decreases
            account['net_movement'] = account['credit_total'] - account['debit_total']
        
        account['ending_balance'] = account['starting_balance'] + account['net_movement']
        
        # Calculate running balance for each entry
        running_balance = account['starting_balance']
        for entry in account['entries']:
            if account_type in [AccountType.ASSET, AccountType.EXPENSE]:
                # Debit increases, credit decreases
                running_balance = running_balance + entry['debit_amount'] - entry['credit_amount']
            else:
                # Credit increases, debit decreases
                running_balance = running_balance - entry['debit_amount'] + entry['credit_amount']
            
            entry['running_balance'] = running_balance
    
    # Build the final report data
    report_data = {
        'start_date': start_date.strftime('%Y-%m-%d') if start_date else None,
        'end_date': end_date.strftime('%Y-%m-%d') if end_date else None,
        'accounts': list(accounts.values()),
        'entries': entries,
        'totals': {
            'debit_total': sum(account['debit_total'] for account in accounts.values()),
            'credit_total': sum(account['credit_total'] for account in accounts.values())
        }
    }
    
    return report_data

def generate_balance_sheet(as_of_date=None):
    """Generate a balance sheet as of a specific date"""
    from models import Account, AccountType
    from decimal import Decimal
    from datetime import datetime
    
    # Use current date if not specified
    if not as_of_date:
        as_of_date = datetime.now().date()
    
    # Get all accounts
    asset_accounts = Account.query.join(AccountType).filter(AccountType.name == AccountType.ASSET).order_by(Account.code).all()
    liability_accounts = Account.query.join(AccountType).filter(AccountType.name == AccountType.LIABILITY).order_by(Account.code).all()
    equity_accounts = Account.query.join(AccountType).filter(AccountType.name == AccountType.EQUITY).order_by(Account.code).all()
    
    # Calculate account balances
    assets = []
    total_assets = Decimal('0.00')
    
    for account in asset_accounts:
        balance = get_account_balance(account.id, end_date=as_of_date)
        if balance != 0:
            assets.append({
                'account_code': account.code,
                'account_name': account.name,
                'balance': balance
            })
            total_assets += balance
    
    liabilities = []
    total_liabilities = Decimal('0.00')
    
    for account in liability_accounts:
        balance = get_account_balance(account.id, end_date=as_of_date)
        if balance != 0:
            liabilities.append({
                'account_code': account.code,
                'account_name': account.name,
                'balance': balance
            })
            total_liabilities += balance
    
    equity_items = []
    total_equity = Decimal('0.00')
    
    for account in equity_accounts:
        balance = get_account_balance(account.id, end_date=as_of_date)
        if balance != 0:
            equity_items.append({
                'account_code': account.code,
                'account_name': account.name,
                'balance': balance
            })
            total_equity += balance
    
    # Get revenue and expense accounts to calculate retained earnings
    revenue_accounts = Account.query.join(AccountType).filter(AccountType.name == AccountType.REVENUE).all()
    expense_accounts = Account.query.join(AccountType).filter(AccountType.name == AccountType.EXPENSE).all()
    
    # Calculate net income (for current period)
    total_revenue = sum(get_account_balance(account.id, end_date=as_of_date) for account in revenue_accounts)
    total_expenses = sum(get_account_balance(account.id, end_date=as_of_date) for account in expense_accounts)
    net_income = total_revenue - total_expenses
    
    # Add net income to equity if it's not zero
    if net_income != 0:
        equity_items.append({
            'account_code': '',
            'account_name': 'Current Period Net Income',
            'balance': net_income
        })
        total_equity += net_income
    
    # Build the report data structure
    report_data = {
        'as_of_date': as_of_date.strftime('%Y-%m-%d'),
        'assets': assets,
        'liabilities': liabilities,
        'equity': equity_items,
        'totals': {
            'assets': total_assets,
            'liabilities': total_liabilities,
            'equity': total_equity,
            'liabilities_and_equity': total_liabilities + total_equity
        }
    }
    
    return report_data

def generate_general_ledger(start_date=None, end_date=None, account_ids=None, account_type_ids=None, include_unposted=False):
    """Generate a general ledger report with optional filters"""
    from models import Account, AccountType, JournalEntry, JournalItem
    from datetime import datetime, timedelta
    from decimal import Decimal
    
    # Default dates if not provided
    if not start_date:
        start_date = datetime.now().date().replace(day=1)
    
    if not end_date:
        end_date = datetime.now().date()
    
    # Build account query
    accounts_query = Account.query.filter_by(is_active=True)
    
    # Apply account filters if provided
    if account_ids and len(account_ids) > 0:
        # Convert string IDs to integers
        account_ids = [int(id) for id in account_ids if id.isdigit()]
        if account_ids:
            accounts_query = accounts_query.filter(Account.id.in_(account_ids))
    
    # Apply account type filters if provided
    if account_type_ids and len(account_type_ids) > 0:
        # Convert string IDs to integers
        account_type_ids = [int(id) for id in account_type_ids if id.isdigit()]
        if account_type_ids:
            accounts_query = accounts_query.filter(Account.account_type_id.in_(account_type_ids))
    
    # Get accounts based on filters
    accounts = accounts_query.order_by(Account.code).all()
    
    # Build journal entries query for date range
    journal_query = JournalEntry.query.filter(
        JournalEntry.entry_date >= start_date,
        JournalEntry.entry_date <= end_date
    )
    
    # Apply posted filter unless including unposted entries
    if not include_unposted:
        journal_query = journal_query.filter_by(is_posted=True)
    
    # Get journal entries
    journal_entries = journal_query.order_by(JournalEntry.entry_date, JournalEntry.id).all()
    
    # Prepare report data
    report_data = {
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
        'accounts': [],
        'totals': {
            'debit_total': Decimal('0.00'),
            'credit_total': Decimal('0.00')
        }
    }
    
    # For each account, gather transactions
    for account in accounts:
        # Get starting balance (balance at start_date - 1 day)
        starting_balance = get_account_balance(
            account.id, 
            end_date=(start_date - timedelta(days=1))
        )
        
        # Initialize account data
        account_data = {
            'id': account.id,
            'code': account.code,
            'name': account.name,
            'starting_balance': starting_balance,
            'ending_balance': starting_balance,  # Will be updated as we process entries
            'entries': []
        }
        
        # Get all journal items for this account in the period
        journal_items = (
            JournalItem.query
            .join(JournalEntry)
            .filter(
                JournalItem.account_id == account.id,
                JournalEntry.entry_date >= start_date,
                JournalEntry.entry_date <= end_date
            )
        )
        
        # Apply posted filter unless including unposted entries
        if not include_unposted:
            journal_items = journal_items.filter(JournalEntry.is_posted == True)
        
        # Order by date and entry ID
        journal_items = (
            journal_items
            .order_by(JournalEntry.entry_date, JournalEntry.id)
            .all()
        )
        
        # Calculate running balance and prepare entries
        running_balance = starting_balance
        
        for item in journal_items:
            # Get parent journal entry
            entry = item.journal_entry
            
            # Calculate debit and credit amounts
            debit_amount = Decimal(item.debit_amount) if item.debit_amount else Decimal('0.00')
            credit_amount = Decimal(item.credit_amount) if item.credit_amount else Decimal('0.00')
            
            # Update running balance based on account type
            # For asset and expense accounts, debits increase, credits decrease
            # For liability, equity, and revenue accounts, credits increase, debits decrease
            if account.account_type.name in ['Asset', 'Expense']:
                running_balance += (debit_amount - credit_amount)
            else:
                running_balance += (credit_amount - debit_amount)
            
            # Add to report totals
            report_data['totals']['debit_total'] += debit_amount
            report_data['totals']['credit_total'] += credit_amount
            
            # Create entry data
            entry_data = {
                'entry_id': entry.id,
                'entry_date': entry.entry_date,
                'reference': entry.reference or f"JE-{entry.id}",
                'entry_description': entry.description,
                'account_code': account.code,
                'item_description': item.description,
                'debit_amount': debit_amount,
                'credit_amount': credit_amount,
                'running_balance': running_balance
            }
            
            account_data['entries'].append(entry_data)
        
        # Update ending balance
        account_data['ending_balance'] = running_balance
        
        # Only include account if it has entries or non-zero starting balance
        if account_data['entries'] or starting_balance != 0:
            report_data['accounts'].append(account_data)
    
    return report_data

def generate_report_data(data, periods, account_type):
    """Generate report data with the proper structure for budgeting"""
    from decimal import Decimal
    
    result = []
    for account_id, account_data in data.items():
        account_total = Decimal('0.00')
        period_values = []
        
        for period_info in periods:
            period = period_info['period']
            amount = account_data['periods'].get(period, Decimal('0.00'))
            period_values.append({
                'period': period, 
                'name': period_info['name'],
                'amount': amount
            })
            account_total += amount
        
        # Sort periods
        period_values.sort(key=lambda x: x['period'])
        
        # Only include accounts with values
        if account_total != 0:
            result.append({
                'account': account_data['account'],
                'periods': period_values,
                'total': account_total
            })
    
    # Sort by account code
    result.sort(key=lambda x: x['account'].code)
    
    return result
