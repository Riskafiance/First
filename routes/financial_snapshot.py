"""
Financial Snapshot Dashboard routes
"""
import datetime
from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from models import Role, Account, AccountType, JournalEntry, JournalItem, Invoice, InvoiceStatus, Expense, ExpenseStatus, Entity, FixedAsset, Product
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
        # Get all asset accounts and sum their balances
        asset_accounts = Account.query.join(AccountType).filter(
            AccountType.name == AccountType.ASSET
        ).all()
        
        total_assets = sum(get_account_balance(account.id, end_date=today) for account in asset_accounts)
        
        # Get all liability accounts and sum their balances
        liability_accounts = Account.query.join(AccountType).filter(
            AccountType.name == AccountType.LIABILITY
        ).all()
        
        total_liabilities = sum(get_account_balance(account.id, end_date=today) for account in liability_accounts)
        
        # Get total accounts receivable - invoices that are not paid or cancelled
        accounts_receivable = db.session.query(func.sum(Invoice.total_amount)).join(
            InvoiceStatus, Invoice.status_id == InvoiceStatus.id
        ).filter(
            InvoiceStatus.name.in_([InvoiceStatus.DRAFT, InvoiceStatus.SENT, InvoiceStatus.OVERDUE])
        ).scalar() or 0
        
        # Get total accounts payable - expenses that are not paid or rejected
        accounts_payable = db.session.query(func.sum(Expense.total_amount)).join(
            ExpenseStatus, Expense.status_id == ExpenseStatus.id
        ).filter(
            ExpenseStatus.name.in_([ExpenseStatus.DRAFT, ExpenseStatus.PENDING, ExpenseStatus.APPROVED])
        ).scalar() or 0
        
        # Calculate recent revenue and expenses (last 30 days)
        thirty_days_ago = datetime.date.today() - datetime.timedelta(days=30)
        
        # Get recent revenue - Revenue accounts increase with credits
        revenue_query = db.session.query(
            func.sum(JournalItem.credit_amount)
        ).join(
            JournalEntry, JournalItem.journal_entry_id == JournalEntry.id
        ).join(
            Account, JournalItem.account_id == Account.id
        ).join(
            AccountType, Account.account_type_id == AccountType.id
        ).filter(
            JournalEntry.entry_date >= thirty_days_ago,
            JournalEntry.is_posted == True,
            AccountType.name == AccountType.REVENUE
        )
        
        recent_revenue = revenue_query.scalar() or 0
        
        # Get recent expenses - Expense accounts increase with debits
        expense_query = db.session.query(
            func.sum(JournalItem.debit_amount)
        ).join(
            JournalEntry, JournalItem.journal_entry_id == JournalEntry.id
        ).join(
            Account, JournalItem.account_id == Account.id
        ).join(
            AccountType, Account.account_type_id == AccountType.id
        ).filter(
            JournalEntry.entry_date >= thirty_days_ago,
            JournalEntry.is_posted == True,
            AccountType.name == AccountType.EXPENSE
        )
        
        recent_expenses = expense_query.scalar() or 0
        
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
        # Get cash accounts - Account type with code starting with 101 (assuming this is cash)
        cash_accounts = Account.query.filter(
            Account.code.startswith('101')  # Assuming 101 is the code for cash accounts
        ).all()
        
        cash = sum(get_account_balance(account.id, end_date=today) for account in cash_accounts)
        
        # Get all current asset accounts (usually 1xxx series except for fixed assets)
        current_asset_accounts = Account.query.join(AccountType).filter(
            AccountType.name == AccountType.ASSET,
            Account.code.startswith('1'),
            ~Account.code.startswith('15')  # Assuming 15xx are fixed assets
        ).all()
        
        current_assets = sum(get_account_balance(account.id, end_date=today) for account in current_asset_accounts)
        
        # Get current liability accounts (usually 2xxx series for short term liabilities)
        current_liability_accounts = Account.query.join(AccountType).filter(
            AccountType.name == AccountType.LIABILITY,
            Account.code.startswith('2'),
            ~Account.code.startswith('25')  # Assuming 25xx are long-term liabilities
        ).all()
        
        current_liabilities = sum(get_account_balance(account.id, end_date=today) for account in current_liability_accounts)
        
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
        # The get_monthly_trends function returns a list of dictionaries with month, income, and expenses
        income_expense_chart = []
        
        # Create a dictionary structure from the list for API endpoints
        structured_trends = {
            'months': [],
            'income': {},
            'expenses': {}
        }
        
        for item in trends:
            month = item['month']
            income = item['income']
            expense = item['expenses']
            
            # Build chart data directly
            income_expense_chart.append({
                'month': month,
                'income': income,
                'expense': expense
            })
            
            # Build structured format for API endpoints
            structured_trends['months'].append(month)
            structured_trends['income'][month] = income
            structured_trends['expenses'][month] = expense
            
        # Replace the list with the structured format for API endpoints
        trends = structured_trends
        
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
            trends_data = get_monthly_trends(months=months)
            chart_data = []
            
            # Direct conversion from the data returned by get_monthly_trends
            for item in trends_data:
                chart_data.append({
                    'month': item['month'],
                    'income': item['income'],
                    'expense': item['expenses']
                })
            return jsonify({'data': chart_data})
        
        elif chart_type == 'assets':
            # Get asset types distribution
            today = datetime.date.today()
            
            # Get a list of asset account types
            asset_types_query = db.session.query(AccountType).filter(
                AccountType.name == AccountType.ASSET
            ).all()
            
            # For each asset type, get the accounts and their balances
            chart_data = []
            for asset_type in asset_types_query:
                accounts = Account.query.filter_by(account_type_id=asset_type.id).all()
                total = sum(get_account_balance(account.id, end_date=today) for account in accounts)
                
                if total > 0:  # Only include asset types with positive balances
                    chart_data.append({
                        'name': asset_type.name,
                        'value': float(total)
                    })
            
            return jsonify({'data': chart_data})
        
        elif chart_type == 'liabilities':
            # Get liability types distribution
            today = datetime.date.today()
            
            # Get a list of liability account types
            liability_types_query = db.session.query(AccountType).filter(
                AccountType.name == AccountType.LIABILITY
            ).all()
            
            # For each liability type, get the accounts and their balances
            chart_data = []
            for liability_type in liability_types_query:
                accounts = Account.query.filter_by(account_type_id=liability_type.id).all()
                total = sum(get_account_balance(account.id, end_date=today) for account in accounts)
                
                if total > 0:  # Only include liability types with positive balances
                    chart_data.append({
                        'name': liability_type.name,
                        'value': float(total)
                    })
            
            return jsonify({'data': chart_data})
        
        return jsonify({'error': 'Invalid chart type'})
    
    except Exception as e:
        current_app.logger.error(f"Error in financial data API: {str(e)}")
        return jsonify({'error': str(e)})