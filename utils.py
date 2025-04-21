from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from models import *
from app import db

def get_financial_summary(start_date=None, end_date=None):
    """Get financial summary for dashboard"""
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
    """Get monthly income and expense trends for the last X months"""
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
