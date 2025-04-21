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
    
    # Get current month's financial summary
    today = date.today()
    current_month_start = today.replace(day=1)
    current_month_summary = get_financial_summary(current_month_start, today)
    
    # Get financial summaries for YTD
    current_year_start = date(today.year, 1, 1)
    ytd_summary = get_financial_summary(current_year_start, today)
    
    # Get monthly trends data for the past 6 months
    monthly_trends = get_monthly_trends(6)
    
    # Extract data for the chart
    months = [month_data['month'].split()[0] for month_data in monthly_trends]  # Just show the month name, not the year
    income_data = [month_data['income'] for month_data in monthly_trends]
    expense_data = [month_data['expenses'] for month_data in monthly_trends]
    
    # Ensure we have real data in the dashboard financials
    current_month_income = current_month_summary['income']
    current_month_expense = current_month_summary['expenses']
    ytd_income = ytd_summary['income']
    ytd_expense = ytd_summary['expenses']
    
    # Ensure we have arrays, even if empty
    if not months:
        months = [''] * 6  # Empty months for chart if no data
    if not income_data:
        income_data = [0] * 6  # Zero income for chart if no data
    if not expense_data:
        expense_data = [0] * 6  # Zero expenses for chart if no data
    
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