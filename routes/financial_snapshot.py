"""
Financial Snapshot Dashboard routes
"""
import datetime
from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from models import Role, Account, AccountType, JournalEntry, JournalItem, Invoice, Expense, Entity, FixedAsset, Product
from app import db
from core_utils import (
    get_financial_summary, 
    get_monthly_trends, 
    get_account_balance,
    get_inventory_value,
    get_low_stock_products
)
from sqlalchemy import func, desc, text, extract
from sqlalchemy.sql import label

snapshot = Blueprint('snapshot', __name__)

@snapshot.route('/financial-snapshot')
@login_required
def financial_snapshot():
    """One-Click Financial Snapshot Dashboard"""
    
    # Get date range parameters with defaults
    try:
        # Default to current month
        today = datetime.date.today()
        start_of_month = datetime.date(today.year, today.month, 1)
        
        # Get current financial summary for the month
        financial_summary = get_financial_summary(start_date=start_of_month)
        
        # Get trends for last 6 months
        trends = get_monthly_trends(months=6)
        
        # Calculate key financial ratios
        total_assets = db.session.query(func.sum(Account.balance)).join(AccountType).filter(
            AccountType.classification == 'Asset'
        ).scalar() or 0
        
        total_liabilities = db.session.query(func.sum(Account.balance)).join(AccountType).filter(
            AccountType.classification == 'Liability'
        ).scalar() or 0
        
        # Get total accounts receivable
        accounts_receivable = db.session.query(func.sum(Invoice.total_amount - Invoice.paid_amount)).filter(
            Invoice.paid_amount < Invoice.total_amount
        ).scalar() or 0
        
        # Get total accounts payable
        accounts_payable = db.session.query(func.sum(Expense.total_amount - Expense.paid_amount)).filter(
            Expense.paid_amount < Expense.total_amount
        ).scalar() or 0
        
        # Calculate recent revenue and expenses (last 30 days)
        thirty_days_ago = datetime.date.today() - datetime.timedelta(days=30)
        
        recent_revenue = db.session.query(func.sum(JournalItem.amount)).join(JournalEntry).join(Account).join(AccountType).filter(
            JournalEntry.entry_date >= thirty_days_ago,
            JournalEntry.is_posted == True,
            AccountType.classification == 'Revenue',
            JournalItem.amount > 0
        ).scalar() or 0
        
        recent_expenses = db.session.query(func.sum(JournalItem.amount)).join(JournalEntry).join(Account).join(AccountType).filter(
            JournalEntry.entry_date >= thirty_days_ago,
            JournalEntry.is_posted == True,
            AccountType.classification == 'Expense',
            JournalItem.amount > 0
        ).scalar() or 0
        
        # Get top 5 customers by revenue
        top_customers = db.session.query(
            Entity.id,
            Entity.name,
            label('total_revenue', func.sum(Invoice.total_amount))
        ).join(Invoice, Invoice.entity_id == Entity.id).filter(
            Entity.entity_type_id == 1  # Customer type ID
        ).group_by(Entity.id, Entity.name).order_by(
            desc('total_revenue')
        ).limit(5).all()
        
        # Get recent invoices (last 10)
        recent_invoices = db.session.query(Invoice).order_by(
            desc(Invoice.issue_date)
        ).limit(10).all()
        
        # Get recent expenses (last 10)
        recent_expenses_list = db.session.query(Expense).order_by(
            desc(Expense.expense_date)
        ).limit(10).all()
        
        # Get inventory value and low stock alerts
        inventory_value = get_inventory_value()
        low_stock_items = get_low_stock_products()
        
        # Calculate fixed assets total value
        fixed_assets_value = db.session.query(func.sum(FixedAsset.current_value)).scalar() or 0
        
        # Calculate liquidity ratios
        cash = db.session.query(func.sum(Account.balance)).join(AccountType).filter(
            AccountType.name == 'Cash'
        ).scalar() or 0
        
        current_assets = db.session.query(func.sum(Account.balance)).join(AccountType).filter(
            AccountType.classification == 'Asset',
            AccountType.is_current == True
        ).scalar() or 0
        
        current_liabilities = db.session.query(func.sum(Account.balance)).join(AccountType).filter(
            AccountType.classification == 'Liability',
            AccountType.is_current == True
        ).scalar() or 0
        
        # Calculate ratios
        if current_liabilities > 0:
            current_ratio = current_assets / current_liabilities
            quick_ratio = (cash + accounts_receivable) / current_liabilities
        else:
            current_ratio = 0
            quick_ratio = 0
            
        if total_assets > 0:
            debt_to_assets = total_liabilities / total_assets
        else:
            debt_to_assets = 0
        
        # Prepare data for charts
        income_expense_chart = []
        for month in trends['months']:
            income_expense_chart.append({
                'month': month,
                'income': trends['income'][month],
                'expense': trends['expenses'][month]
            })
        
        return render_template(
            'reports/financial_snapshot.html',
            financial_summary=financial_summary,
            trends=trends,
            income_expense_chart=income_expense_chart,
            total_assets=total_assets,
            total_liabilities=total_liabilities,
            accounts_receivable=accounts_receivable,
            accounts_payable=accounts_payable,
            recent_revenue=recent_revenue,
            recent_expenses=recent_expenses,
            top_customers=top_customers,
            recent_invoices=recent_invoices,
            recent_expenses_list=recent_expenses_list,
            inventory_value=inventory_value,
            low_stock_items=low_stock_items,
            fixed_assets_value=fixed_assets_value,
            current_ratio=current_ratio,
            quick_ratio=quick_ratio,
            debt_to_assets=debt_to_assets
        )
    except Exception as e:
        current_app.logger.error(f"Error in financial snapshot: {str(e)}")
        # If there's an error, return a simplified version of the dashboard
        return render_template(
            'reports/financial_snapshot.html',
            error=str(e)
        )

@snapshot.route('/api/financial-data')
@login_required
def get_financial_data():
    """API endpoint to get financial data for charts"""
    try:
        chart_type = request.args.get('type', 'income_expense')
        months = int(request.args.get('months', '6'))
        
        if chart_type == 'income_expense':
            trends = get_monthly_trends(months=months)
            chart_data = []
            for month in trends['months']:
                chart_data.append({
                    'month': month,
                    'income': trends['income'][month],
                    'expense': trends['expenses'][month]
                })
            return jsonify({'data': chart_data})
        
        elif chart_type == 'assets':
            # Get asset types distribution
            asset_types = db.session.query(
                AccountType.name,
                func.sum(Account.balance).label('total')
            ).join(Account).filter(
                AccountType.classification == 'Asset',
                Account.balance > 0
            ).group_by(AccountType.name).all()
            
            chart_data = [{'name': t.name, 'value': float(t.total)} for t in asset_types]
            return jsonify({'data': chart_data})
        
        elif chart_type == 'liabilities':
            # Get liability types distribution
            liability_types = db.session.query(
                AccountType.name,
                func.sum(Account.balance).label('total')
            ).join(Account).filter(
                AccountType.classification == 'Liability',
                Account.balance > 0
            ).group_by(AccountType.name).all()
            
            chart_data = [{'name': t.name, 'value': float(t.total)} for t in liability_types]
            return jsonify({'data': chart_data})
        
        return jsonify({'error': 'Invalid chart type'})
    
    except Exception as e:
        current_app.logger.error(f"Error in financial data API: {str(e)}")
        return jsonify({'error': str(e)})