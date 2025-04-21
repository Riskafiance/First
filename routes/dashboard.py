from flask import Blueprint, render_template
from flask_login import login_required, current_user
from models import Role, Invoice, Expense, JournalEntry, JournalItem, Account, AccountType
from app import db
from sqlalchemy import func, desc
import datetime
from decimal import Decimal

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
@login_required
def index():
    """Dashboard index page"""
    permissions = current_user.get_permissions_list()
    
    # Get recent invoices (last 5)
    recent_invoices = Invoice.query.order_by(
        desc(Invoice.issue_date)
    ).limit(5).all()
    
    # Get recent expenses (last 5)
    recent_expenses = Expense.query.order_by(
        desc(Expense.expense_date)
    ).limit(5).all()
    
    # Get recent journal entries (last 5)
    recent_journals = JournalEntry.query.order_by(
        desc(JournalEntry.entry_date)
    ).limit(5).all()
    
    # Calculate monthly income and expenses for the chart (last 6 months)
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=180)  # roughly 6 months
    
    # Initialize income/expense data for the last 6 months
    months = []
    income_data = []
    expense_data = []
    
    # Get account types for income and expenses
    income_type = AccountType.query.filter_by(name=AccountType.REVENUE).first()
    expense_type = AccountType.query.filter_by(name=AccountType.EXPENSE).first()
    
    # Get all income and expense accounts
    income_accounts = []
    expense_accounts = []
    
    if income_type:
        income_accounts = [account.id for account in Account.query.filter_by(account_type_id=income_type.id).all()]
    
    if expense_type:
        expense_accounts = [account.id for account in Account.query.filter_by(account_type_id=expense_type.id).all()]
    
    # Get monthly totals for the last 6 months
    current_date = datetime.date.today()
    for i in range(5, -1, -1):  # Last 6 months (5 to 0)
        # Calculate the month start and end dates
        month_end = current_date.replace(day=1) - datetime.timedelta(days=1) if i > 0 else current_date
        if i > 0:
            month_end = month_end.replace(day=1) - datetime.timedelta(days=1)
        month_start = month_end.replace(day=1)
        
        # Format month name for display
        month_name = month_start.strftime('%b')
        months.append(month_name)
        
        # Sum income for this month from journal entries
        monthly_income = Decimal('0.00')
        if income_accounts:
            # Find entries within the date range
            income_entries = db.session.query(JournalEntry, JournalItem).join(
                JournalItem, JournalEntry.id == JournalItem.journal_entry_id
            ).filter(
                JournalEntry.entry_date >= month_start,
                JournalEntry.entry_date <= month_end,
                JournalItem.account_id.in_(income_accounts),
                JournalItem.credit_amount > 0
            ).all()
            
            # Sum up the credit amounts (income)
            for entry, item in income_entries:
                monthly_income += item.credit_amount
        
        # Sum expenses for this month from journal entries
        monthly_expense = Decimal('0.00')
        if expense_accounts:
            # Find entries within the date range
            expense_entries = db.session.query(JournalEntry, JournalItem).join(
                JournalItem, JournalEntry.id == JournalItem.journal_entry_id
            ).filter(
                JournalEntry.entry_date >= month_start,
                JournalEntry.entry_date <= month_end,
                JournalItem.account_id.in_(expense_accounts),
                JournalItem.debit_amount > 0
            ).all()
            
            # Sum up the debit amounts (expenses)
            for entry, item in expense_entries:
                monthly_expense += item.debit_amount
        
        # Add to data arrays
        income_data.append(float(monthly_income))
        expense_data.append(float(monthly_expense))
        
        # Move to the previous month
        current_date = month_start - datetime.timedelta(days=1)
    
    # Calculate total current month's income and expenses
    current_month_start = datetime.date.today().replace(day=1)
    current_month_income = sum(income_data[-1:]) if income_data else 0
    current_month_expense = sum(expense_data[-1:]) if expense_data else 0
    
    # Calculate YTD income and expenses
    current_year_start = datetime.date(datetime.date.today().year, 1, 1)
    ytd_income = sum(income_data) if income_data else 0
    ytd_expense = sum(expense_data) if expense_data else 0
    
    return render_template(
        'dashboard.html',
        permissions=permissions,
        recent_invoices=recent_invoices,
        recent_expenses=recent_expenses,
        recent_journals=recent_journals,
        months=months,
        income_data=income_data,
        expense_data=expense_data,
        current_month_income=current_month_income,
        current_month_expense=current_month_expense,
        ytd_income=ytd_income,
        ytd_expense=ytd_expense
    )