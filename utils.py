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
