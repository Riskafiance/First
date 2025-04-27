"""
Financial Snapshot Dashboard routes
"""
import datetime
from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from models import Role
from app import db
from core_utils import (
    get_financial_summary, 
    get_monthly_trends, 
    get_account_balance,
    get_inventory_value,
    get_low_stock_products
)
from utils.user_data import (
    get_model_adapter,
    get_invoices,
    get_expenses,
    get_user_data
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
        
        # Get user data
        username = current_user.username
        user_data = get_user_data(username)
        
        # Get account balances from user data
        total_assets = 0
        total_liabilities = 0
        cash = 0
        
        if 'chart_of_accounts' in user_data:
            chart = user_data.get('chart_of_accounts', {})
            # Calculate totals for asset accounts
            for account in chart.get('asset', []):
                total_assets += account.get('balance', 0)
                if account.get('name', '').lower() == 'cash':
                    cash = account.get('balance', 0)
            
            # Calculate totals for liability accounts
            for account in chart.get('liability', []):
                total_liabilities += account.get('balance', 0)
        
        # Get total accounts receivable from invoices
        accounts_receivable = 0
        for invoice in user_data.get('invoices', []):
            total = invoice.get('total_amount', 0)
            paid = invoice.get('paid_amount', 0)
            if paid < total:
                accounts_receivable += (total - paid)
        
        # Get total accounts payable from expenses
        accounts_payable = 0
        for expense in user_data.get('expenses', []):
            total = expense.get('total_amount', 0)
            paid = expense.get('paid_amount', 0)
            if paid < total:
                accounts_payable += (total - paid)
        
        # Calculate recent revenue and expenses (last 30 days)
        thirty_days_ago = datetime.date.today() - datetime.timedelta(days=30)
        thirty_days_ago_str = thirty_days_ago.isoformat()
        
        recent_revenue = 0
        recent_expenses = 0
        
        for entry in user_data.get('journal_entries', []):
            entry_date = entry.get('entry_date', '')
            if entry_date >= thirty_days_ago_str and entry.get('is_posted', False):
                for item in entry.get('items', []):
                    if item.get('account_type') == 'revenue':
                        recent_revenue += item.get('credit_amount', 0) - item.get('debit_amount', 0)
                    elif item.get('account_type') == 'expense':
                        recent_expenses += item.get('debit_amount', 0) - item.get('credit_amount', 0)
        
        # Get top 5 customers by revenue
        customers = user_data.get('customers', [])
        customer_revenue = {}
        
        for invoice in user_data.get('invoices', []):
            customer_id = invoice.get('entity_id')
            if customer_id:
                if customer_id not in customer_revenue:
                    customer_revenue[customer_id] = 0
                customer_revenue[customer_id] += invoice.get('total_amount', 0)
        
        top_customers = []
        for customer in customers:
            if customer.get('id') in customer_revenue:
                top_customers.append({
                    'id': customer.get('id'),
                    'name': customer.get('name'),
                    'total_revenue': customer_revenue[customer.get('id')]
                })
        
        # Sort and limit to top 5
        top_customers = sorted(top_customers, key=lambda x: x.get('total_revenue', 0), reverse=True)[:5]
        
        # Get recent invoices (last 10)
        all_invoices = get_invoices(username)
        sorted_invoices = sorted(all_invoices, key=lambda x: x.get('issue_date', ''), reverse=True)
        recent_invoices = sorted_invoices[:10] if sorted_invoices else []
        
        # Get recent expenses (last 10)
        all_expenses = get_expenses(username)
        sorted_expenses = sorted(all_expenses, key=lambda x: x.get('expense_date', ''), reverse=True)
        recent_expenses_list = sorted_expenses[:10] if sorted_expenses else []
        
        # Get inventory value and low stock alerts
        inventory_value = 0
        low_stock_items = []
        
        # Calculate from products in user data
        for product in user_data.get('products', []):
            current_stock = product.get('current_stock', 0)
            cost_price = product.get('cost_price', 0)
            if current_stock and cost_price:
                inventory_value += current_stock * cost_price
            
            # Check for low stock items
            reorder_level = product.get('reorder_level', 0)
            if current_stock <= reorder_level:
                low_stock_items.append({
                    'id': product.get('id'),
                    'sku': product.get('sku'),
                    'name': product.get('name'),
                    'current_stock': current_stock,
                    'reorder_level': reorder_level
                })
        
        # Calculate fixed assets total value
        fixed_assets_value = 0
        for asset in user_data.get('fixed_assets', []):
            fixed_assets_value += asset.get('current_value', 0)
        
        # We already have cash from above
        # Determine current assets (assets that are marked as current)
        current_assets = 0
        current_liabilities = 0
        
        if 'chart_of_accounts' in user_data:
            chart = user_data.get('chart_of_accounts', {})
            # Calculate current asset accounts
            for account in chart.get('asset', []):
                if account.get('is_current', False):
                    current_assets += account.get('balance', 0)
            
            # Calculate current liability accounts
            for account in chart.get('liability', []):
                if account.get('is_current', False):
                    current_liabilities += account.get('balance', 0)
        
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
            # Get user data
            username = current_user.username
            user_data = get_user_data(username)
            
            # Get asset types distribution from user data
            asset_types = {}
            if 'chart_of_accounts' in user_data:
                chart = user_data.get('chart_of_accounts', {})
                for account in chart.get('asset', []):
                    account_type = account.get('account_type_name', 'Other')
                    balance = account.get('balance', 0)
                    
                    if balance > 0:  # Only include positive balances
                        if account_type not in asset_types:
                            asset_types[account_type] = 0
                        asset_types[account_type] += balance
            
            # Convert to chart data format
            chart_data = [{'name': name, 'value': float(value)} for name, value in asset_types.items()]
            return jsonify({'data': chart_data})
        
        elif chart_type == 'liabilities':
            # Get user data
            username = current_user.username
            user_data = get_user_data(username)
            
            # Get liability types distribution from user data
            liability_types = {}
            if 'chart_of_accounts' in user_data:
                chart = user_data.get('chart_of_accounts', {})
                for account in chart.get('liability', []):
                    account_type = account.get('account_type_name', 'Other')
                    balance = account.get('balance', 0)
                    
                    if balance > 0:  # Only include positive balances
                        if account_type not in liability_types:
                            liability_types[account_type] = 0
                        liability_types[account_type] += balance
            
            # Convert to chart data format
            chart_data = [{'name': name, 'value': float(value)} for name, value in liability_types.items()]
            return jsonify({'data': chart_data})
        
        return jsonify({'error': 'Invalid chart type'})
    
    except Exception as e:
        current_app.logger.error(f"Error in financial data API: {str(e)}")
        return jsonify({'error': str(e)})