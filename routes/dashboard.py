from flask import Blueprint, render_template
from flask_login import login_required, current_user
from models import Role
import datetime
from decimal import Decimal
import os, sys
from datetime import date

# Import functions from user_data.py for user-specific JSON data
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
sys.path.insert(0, root_dir)
from utils.user_data import get_invoices, get_expenses, get_journal_entries, get_financial_summary, get_monthly_trends

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
@login_required
def index():
    """Dashboard index page"""
    permissions = current_user.get_permissions_list()
    username = current_user.username
    
    # Get user data from their JSON file
    # Get recent invoices (last 5) from user's JSON data
    all_invoices = get_invoices(username)
    # Sort by issue_date (descending) and take the first 5
    sorted_invoices = sorted(all_invoices, key=lambda x: x.get('issue_date', ''), reverse=True)
    recent_invoices = sorted_invoices[:5] if sorted_invoices else []
    
    # Get recent expenses (last 5) from user's JSON data
    all_expenses = get_expenses(username)
    # Sort by expense_date (descending) and take the first 5
    sorted_expenses = sorted(all_expenses, key=lambda x: x.get('expense_date', ''), reverse=True)
    recent_expenses = sorted_expenses[:5] if sorted_expenses else []
    
    # Get recent journal entries (last 5) from user's JSON data
    all_journals = get_journal_entries(username)
    # Sort by entry_date (descending) and take the first 5
    sorted_journals = sorted(all_journals, key=lambda x: x.get('entry_date', ''), reverse=True)
    recent_journals = sorted_journals[:5] if sorted_journals else []
    
    # Get current month's financial summary
    today = date.today()
    current_month_start = today.replace(day=1)
    current_month_summary = get_financial_summary(username, current_month_start, today)
    
    # Get financial summaries for YTD
    current_year_start = date(today.year, 1, 1)
    ytd_summary = get_financial_summary(username, current_year_start, today)
    
    # Get monthly trends data for the past 6 months
    monthly_trends = get_monthly_trends(username, 6)
    
    # Extract data for the chart - use absolute values to avoid minus signs
    months = [month_data['month'].split()[0] for month_data in monthly_trends]  # Just show the month name, not the year
    income_data = [abs(month_data['income']) for month_data in monthly_trends]
    expense_data = [abs(month_data['expenses']) for month_data in monthly_trends]
    
    # Ensure we have real data in the dashboard financials
    current_month_income = current_month_summary.get('income', 0)
    current_month_expense = current_month_summary.get('expenses', 0)
    ytd_income = ytd_summary.get('income', 0)
    ytd_expense = ytd_summary.get('expenses', 0)
    
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