from flask import Blueprint, render_template, request
from datetime import datetime, timedelta
from flask_login import login_required
from app import db
from models import JournalEntry, Invoice, InvoiceStatus
from utils import get_financial_summary, get_monthly_trends

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@login_required
def index():
    """Dashboard home page with financial overview"""
    # Get period from query parameters
    period = request.args.get('period', 'month')
    
    # Set date range based on period
    today = datetime.now().date()
    if period == 'today':
        start_date = today
        end_date = today
    elif period == 'week':
        start_date = today - timedelta(days=today.weekday())
        end_date = today
    elif period == 'month':
        start_date = today.replace(day=1)
        end_date = today
    elif period == 'quarter':
        current_month = today.month
        current_quarter = (current_month - 1) // 3 + 1
        quarter_start_month = (current_quarter - 1) * 3 + 1
        start_date = today.replace(month=quarter_start_month, day=1)
        end_date = today
    elif period == 'year':
        start_date = today.replace(month=1, day=1)
        end_date = today
    else:
        # Default to current month
        start_date = today.replace(day=1)
        end_date = today
    
    # Get financial summary
    summary = get_financial_summary(start_date, end_date)
    
    # Get monthly trends
    monthly_trends = get_monthly_trends(6)
    
    # Get recent invoices
    recent_invoices = Invoice.query.order_by(Invoice.issue_date.desc()).limit(5).all()
    
    # Get recent journal entries
    recent_journals = JournalEntry.query.order_by(JournalEntry.entry_date.desc()).limit(5).all()
    
    return render_template(
        'dashboard.html',
        summary=summary,
        monthly_trends=monthly_trends,
        recent_invoices=recent_invoices,
        recent_journals=recent_journals,
        period=period
    )
