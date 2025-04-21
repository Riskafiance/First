import calendar
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from app import db
from models import JournalEntry, JournalItem, Account
from sqlalchemy import func

def month_name(month_number):
    """Return the name of the month based on its number (1-12)"""
    if month_number < 1 or month_number > 12:
        return ""
    return calendar.month_name[month_number]

def quarter_name(quarter_number):
    """Return the formatted quarter name (e.g., Q1, Q2, etc.)"""
    if quarter_number < 1 or quarter_number > 4:
        return ""
    return f"Q{quarter_number}"

def get_account_balance(account_id, start_date, end_date, is_posted_only=True):
    """Get the balance for an account during a specific period"""
    # Convert date strings to date objects if needed
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
    
    # Get account to check its account type
    account = db.session.query(Account).get(account_id)
    if not account:
        return 0
    
    # Build the filters for the query
    filters = [
        JournalItem.account_id == account_id,
        JournalEntry.entry_date >= start_date,
        JournalEntry.entry_date <= end_date
    ]
    
    if is_posted_only:
        filters.append(JournalEntry.is_posted == True)
    
    # Get debits sum
    debits = db.session.query(func.sum(JournalItem.debit)).join(
        JournalEntry, JournalItem.journal_entry_id == JournalEntry.id
    ).filter(
        *filters
    ).scalar() or 0
    
    # Get credits sum
    credits = db.session.query(func.sum(JournalItem.credit)).join(
        JournalEntry, JournalItem.journal_entry_id == JournalEntry.id
    ).filter(
        *filters
    ).scalar() or 0
    
    # Calculate balance based on account type
    account_type = account.account_type.name
    
    if account_type in ['Asset', 'Expense']:
        # Debit accounts - positive balance is debit
        balance = float(debits) - float(credits)
    else:
        # Credit accounts - positive balance is credit
        balance = float(credits) - float(debits)
    
    return balance

def generate_report_data(report_type, year, period_type='monthly'):
    """Generate report data structure for budgeting and forecast reports"""
    
    # Initialize the report data structure
    report_data = {
        'year': year,
        'report_type': report_type,
        'period_type': period_type,
        'periods': []
    }
    
    # Generate periods based on period_type
    if period_type == 'monthly':
        for month in range(1, 13):
            # For each month in the year
            first_day = date(year, month, 1)
            last_day = date(year, month, calendar.monthrange(year, month)[1])
            
            report_data['periods'].append({
                'number': month,
                'name': month_name(month),
                'start_date': first_day,
                'end_date': last_day
            })
    
    elif period_type == 'quarterly':
        for quarter in range(1, 5):
            # For each quarter
            month_start = (quarter - 1) * 3 + 1
            month_end = quarter * 3
            
            first_day = date(year, month_start, 1)
            last_day = date(year, month_end, calendar.monthrange(year, month_end)[1])
            
            report_data['periods'].append({
                'number': quarter,
                'name': quarter_name(quarter),
                'start_date': first_day,
                'end_date': last_day
            })
    
    elif period_type == 'annual':
        # Just one period for the whole year
        first_day = date(year, 1, 1)
        last_day = date(year, 12, 31)
        
        report_data['periods'].append({
            'number': 1,
            'name': str(year),
            'start_date': first_day,
            'end_date': last_day
        })
    
    return report_data