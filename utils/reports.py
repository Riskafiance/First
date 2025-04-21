from datetime import datetime, timedelta
import pandas as pd
from app import db
from models import Account, AccountType, JournalEntry, JournalItem
from sqlalchemy import func, and_, or_

def generate_pl_report(start_date=None, end_date=None):
    """Generate a profit and loss report"""
    
    # Set default dates if not provided
    if not end_date:
        end_date = datetime.now().date()
    if not start_date:
        # Default to beginning of current month
        start_date = datetime(end_date.year, end_date.month, 1).date()
    
    # Convert date strings to date objects if needed
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
    
    # Get revenue and expense accounts
    revenue_type = db.session.query(AccountType).filter_by(name='Revenue').first()
    expense_type = db.session.query(AccountType).filter_by(name='Expense').first()
    
    if not revenue_type or not expense_type:
        return {
            'start_date': start_date,
            'end_date': end_date,
            'revenue': [],
            'expenses': [],
            'total_revenue': 0,
            'total_expenses': 0,
            'net_income': 0
        }
    
    # Query revenue accounts and their balances
    revenue_accounts = db.session.query(Account).filter_by(
        account_type_id=revenue_type.id, 
        is_active=True
    ).all()
    
    # Query expense accounts and their balances
    expense_accounts = db.session.query(Account).filter_by(
        account_type_id=expense_type.id,
        is_active=True
    ).all()
    
    revenue_data = []
    total_revenue = 0
    
    for account in revenue_accounts:
        # Calculate balance for the period
        balance = _get_account_balance_for_period(account.id, start_date, end_date)
        
        if balance != 0:  # Only include accounts with activity
            revenue_data.append({
                'id': account.id,
                'code': account.code,
                'name': account.name,
                'balance': float(abs(balance))  # Revenue is normally a credit balance
            })
            total_revenue += float(abs(balance))
    
    expense_data = []
    total_expenses = 0
    
    for account in expense_accounts:
        # Calculate balance for the period
        balance = _get_account_balance_for_period(account.id, start_date, end_date)
        
        if balance != 0:  # Only include accounts with activity
            expense_data.append({
                'id': account.id,
                'code': account.code,
                'name': account.name,
                'balance': float(abs(balance))  # Expenses is normally a debit balance
            })
            total_expenses += float(abs(balance))
    
    net_income = total_revenue - total_expenses
    
    # Sort by account code
    revenue_data.sort(key=lambda x: x['code'])
    expense_data.sort(key=lambda x: x['code'])
    
    return {
        'start_date': start_date,
        'end_date': end_date,
        'revenue': revenue_data,
        'expenses': expense_data,
        'total_revenue': total_revenue,
        'total_expenses': total_expenses,
        'net_income': net_income
    }

def generate_balance_sheet(as_of_date=None):
    """Generate a balance sheet report"""
    
    # Set default date if not provided
    if not as_of_date:
        as_of_date = datetime.now().date()
    
    # Convert date string to date object if needed
    if isinstance(as_of_date, str):
        as_of_date = datetime.strptime(as_of_date, "%Y-%m-%d").date()
    
    # Get account types
    asset_type = db.session.query(AccountType).filter_by(name='Asset').first()
    liability_type = db.session.query(AccountType).filter_by(name='Liability').first()
    equity_type = db.session.query(AccountType).filter_by(name='Equity').first()
    
    if not asset_type or not liability_type or not equity_type:
        return {
            'as_of_date': as_of_date,
            'assets': [],
            'liabilities': [],
            'equity': [],
            'total_assets': 0,
            'total_liabilities': 0,
            'total_equity': 0
        }
    
    # Query accounts and their balances
    asset_accounts = db.session.query(Account).filter_by(
        account_type_id=asset_type.id, 
        is_active=True
    ).all()
    
    liability_accounts = db.session.query(Account).filter_by(
        account_type_id=liability_type.id,
        is_active=True
    ).all()
    
    equity_accounts = db.session.query(Account).filter_by(
        account_type_id=equity_type.id,
        is_active=True
    ).all()
    
    # Calculate total asset balances
    asset_data = []
    total_assets = 0
    
    for account in asset_accounts:
        # Calculate balance up to the as_of_date
        balance = _get_account_balance_as_of(account.id, as_of_date)
        
        if balance != 0:  # Only include accounts with balances
            asset_data.append({
                'id': account.id,
                'code': account.code,
                'name': account.name,
                'balance': float(balance)
            })
            total_assets += float(balance)
    
    # Calculate liability balances
    liability_data = []
    total_liabilities = 0
    
    for account in liability_accounts:
        # Calculate balance up to the as_of_date
        balance = _get_account_balance_as_of(account.id, as_of_date)
        
        if balance != 0:  # Only include accounts with balances
            liability_data.append({
                'id': account.id,
                'code': account.code,
                'name': account.name,
                'balance': float(abs(balance))  # Liabilities typically have credit balances
            })
            total_liabilities += float(abs(balance))
    
    # Calculate equity balances
    equity_data = []
    total_equity = 0
    
    for account in equity_accounts:
        # Calculate balance up to the as_of_date
        balance = _get_account_balance_as_of(account.id, as_of_date)
        
        if balance != 0:  # Only include accounts with balances
            equity_data.append({
                'id': account.id,
                'code': account.code,
                'name': account.name,
                'balance': float(abs(balance))  # Equity typically has credit balances
            })
            total_equity += float(abs(balance))
    
    # Sort by account code
    asset_data.sort(key=lambda x: x['code'])
    liability_data.sort(key=lambda x: x['code'])
    equity_data.sort(key=lambda x: x['code'])
    
    # Calculate retained earnings/current year earnings
    # This is a simplified approach - in a real system, you'd calculate this properly from revenue/expense accounts
    total_liabilities_and_equity = total_liabilities + total_equity
    difference = total_assets - total_liabilities_and_equity
    
    if abs(difference) > 0.001:  # If there's a material difference
        # Add current year earnings/retained earnings to equity
        equity_data.append({
            'id': None,
            'code': '3999',
            'name': 'Current Year Earnings',
            'balance': float(abs(difference))
        })
        total_equity += float(abs(difference))
    
    return {
        'as_of_date': as_of_date,
        'assets': asset_data,
        'liabilities': liability_data,
        'equity': equity_data,
        'total_assets': total_assets,
        'total_liabilities': total_liabilities,
        'total_equity': total_equity
    }

def generate_general_ledger(start_date=None, end_date=None, account_ids=None, account_type_ids=None, include_unposted=False):
    """Generate general ledger report"""
    
    # Set default dates if not provided
    if not end_date:
        end_date = datetime.now().date()
    if not start_date:
        # Default to beginning of current month
        start_date = datetime(end_date.year, end_date.month, 1).date()
    
    # Convert date strings to date objects if needed
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
    
    # Build query filters
    filters = [
        JournalEntry.entry_date >= start_date,
        JournalEntry.entry_date <= end_date
    ]
    
    if not include_unposted:
        filters.append(JournalEntry.is_posted == True)
    
    # Execute query to get all journal entries
    journal_entries = db.session.query(JournalEntry).filter(
        *filters
    ).order_by(
        JournalEntry.entry_date, 
        JournalEntry.id
    ).all()
    
    # Generate report data
    data = []
    
    for entry in journal_entries:
        for item in entry.items:
            # Check if we need to filter by account_ids or account_type_ids
            account = item.account
            
            if account_ids and account.id not in account_ids:
                continue
                
            if account_type_ids and account.account_type_id not in account_type_ids:
                continue
            
            data.append({
                'entry_id': entry.id,
                'entry_date': entry.entry_date,
                'entry_number': entry.entry_number,
                'posted': entry.is_posted,
                'description': entry.description,
                'account_id': account.id,
                'account_code': account.code,
                'account_name': account.name,
                'debit': float(item.debit) if item.debit else 0,
                'credit': float(item.credit) if item.credit else 0,
                'entry_created_at': entry.created_at,
                'memo': item.memo
            })
    
    return data

def _get_account_balance_for_period(account_id, start_date, end_date):
    """Helper function to get account balance for a specific period"""
    # Get sum of debits for the period
    debits = db.session.query(func.sum(JournalItem.debit)).join(
        JournalEntry, JournalItem.journal_entry_id == JournalEntry.id
    ).filter(
        JournalItem.account_id == account_id,
        JournalEntry.is_posted == True,
        JournalEntry.entry_date >= start_date,
        JournalEntry.entry_date <= end_date
    ).scalar() or 0
    
    # Get sum of credits for the period
    credits = db.session.query(func.sum(JournalItem.credit)).join(
        JournalEntry, JournalItem.journal_entry_id == JournalEntry.id
    ).filter(
        JournalItem.account_id == account_id,
        JournalEntry.is_posted == True,
        JournalEntry.entry_date >= start_date,
        JournalEntry.entry_date <= end_date
    ).scalar() or 0
    
    # Return the net balance (debits - credits)
    # For revenue accounts, subtract credits from debits
    # For expense accounts, subtract debits from credits
    return float(debits) - float(credits)

def _get_account_balance_as_of(account_id, as_of_date):
    """Helper function to get account balance as of a specific date"""
    # Get sum of debits
    debits = db.session.query(func.sum(JournalItem.debit)).join(
        JournalEntry, JournalItem.journal_entry_id == JournalEntry.id
    ).filter(
        JournalItem.account_id == account_id,
        JournalEntry.is_posted == True,
        JournalEntry.entry_date <= as_of_date
    ).scalar() or 0
    
    # Get sum of credits
    credits = db.session.query(func.sum(JournalItem.credit)).join(
        JournalEntry, JournalItem.journal_entry_id == JournalEntry.id
    ).filter(
        JournalItem.account_id == account_id,
        JournalEntry.is_posted == True,
        JournalEntry.entry_date <= as_of_date
    ).scalar() or 0
    
    # Calculate balance based on account type
    account = db.session.query(Account).get(account_id)
    
    if not account:
        return 0
    
    # For asset and expense accounts, balance = debits - credits
    # For liability, equity, and revenue accounts, balance = credits - debits
    account_type = account.account_type
    
    if account_type.name in ['Asset', 'Expense']:
        balance = float(debits) - float(credits)
    else:
        balance = float(credits) - float(debits)
    
    return balance