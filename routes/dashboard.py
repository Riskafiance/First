from flask import Blueprint, render_template
from flask_login import login_required, current_user
from models import Role, Invoice, Expense, JournalEntry, JournalItem, Account, AccountType
from app import db
from sqlalchemy import func, desc
import datetime
from decimal import Decimal
import os, sys
from datetime import date

# Import functions from core_utils.py
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
sys.path.insert(0, root_dir)
from core_utils import get_financial_summary, get_monthly_trends

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
@login_required
def index():
    """Dashboard index page"""
    permissions = current_user.get_permissions_list()
    
    # Check if this is a new user
    # A user is considered new if they don't have any associated data
    # Check for journal entries, invoices, or expenses linked to this user
    
    # Count transactions associated with this user
    invoice_count = Invoice.query.filter_by(created_by_id=current_user.id).count()
    expense_count = Expense.query.filter_by(created_by_id=current_user.id).count()
    journal_count = JournalEntry.query.filter_by(created_by_id=current_user.id).count()
    
    # If there are no transactions, consider this a new user with an empty dashboard
    is_new_user = (invoice_count == 0 and expense_count == 0 and journal_count == 0)
    
    # Get recent invoices (last 5)
    recent_invoices = []
    if not is_new_user:
        recent_invoices = Invoice.query.order_by(
            desc(Invoice.issue_date)
        ).limit(5).all()
    
    # Get recent expenses (last 5)
    recent_expenses = []
    if not is_new_user:
        recent_expenses = Expense.query.order_by(
            desc(Expense.expense_date)
        ).limit(5).all()
    
    # Get recent journal entries (last 5)
    recent_journals = []
    if not is_new_user:
        recent_journals = JournalEntry.query.order_by(
            desc(JournalEntry.entry_date)
        ).limit(5).all()
    
    # Prepare empty data for new users or get actual data for existing users
    today = date.today()
    current_month_start = today.replace(day=1)
    current_year_start = date(today.year, 1, 1)
    
    # Initialize with empty data
    current_month_income = 0
    current_month_expense = 0
    ytd_income = 0
    ytd_expense = 0
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']  # Default month names
    income_data = [0] * 6  # Zero income for chart
    expense_data = [0] * 6  # Zero expenses for chart
    
    # Get actual data if not a new user
    if not is_new_user:
        # Get current month's financial summary
        current_month_summary = get_financial_summary(current_month_start, today)
        current_month_income = current_month_summary['income']
        current_month_expense = current_month_summary['expenses']
        
        # Get financial summaries for YTD
        ytd_summary = get_financial_summary(current_year_start, today)
        ytd_income = ytd_summary['income']
        ytd_expense = ytd_summary['expenses']
        
        # Get monthly trends data for the past 6 months
        monthly_trends = get_monthly_trends(6)
        
        # Extract data for the chart if we have any trends
        if monthly_trends:
            months = [month_data['month'].split()[0] for month_data in monthly_trends]
            income_data = [abs(month_data['income']) for month_data in monthly_trends]
            expense_data = [abs(month_data['expenses']) for month_data in monthly_trends]
    
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