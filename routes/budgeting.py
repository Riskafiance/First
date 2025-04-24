from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from models import (
    Budget, BudgetItem, BudgetPeriodType, BudgetVersion,
    Forecast, ForecastItem, Account, AccountType, Role,
    JournalEntry, JournalItem
)
import utils
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import calendar
from sqlalchemy import func, text, case
from decimal import Decimal
import json

budgeting_bp = Blueprint('budgeting', __name__)

# Helper functions
def get_period_months(period_type):
    """Return the number of months per period for the given period type"""
    if period_type == BudgetPeriodType.MONTHLY:
        return 1
    elif period_type == BudgetPeriodType.QUARTERLY:
        return 3
    elif period_type == BudgetPeriodType.ANNUAL:
        return 12
    else:
        return 1  # Default to monthly for custom periods

def generate_budget_periods(period_type, year):
    """Generate period labels based on period type"""
    periods = []
    
    if period_type == BudgetPeriodType.MONTHLY:
        for month in range(1, 13):
            periods.append({
                'period': month,
                'name': utils.month_name(month),
                'start_date': date(year, month, 1),
                'end_date': date(year, month, calendar.monthrange(year, month)[1])
            })
    elif period_type == BudgetPeriodType.QUARTERLY:
        for quarter in range(1, 5):
            start_month = (quarter - 1) * 3 + 1
            end_month = quarter * 3
            start_date = date(year, start_month, 1)
            end_date = date(year, end_month, calendar.monthrange(year, end_month)[1])
            periods.append({
                'period': quarter,
                'name': f"Q{quarter} {year}",
                'start_date': start_date,
                'end_date': end_date
            })
    elif period_type == BudgetPeriodType.ANNUAL:
        periods.append({
            'period': 1,
            'name': str(year),
            'start_date': date(year, 1, 1),
            'end_date': date(year, 12, 31)
        })
    
    return periods

def get_actual_vs_budget(budget_id, start_date, end_date):
    """
    Get actual vs budget data for the given budget and date range
    Returns a dictionary with account data and summary info
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.debug(f"Starting get_actual_vs_budget for budget_id: {budget_id}, start_date: {start_date}, end_date: {end_date}")
    
    # Get the budget
    budget = Budget.query.get_or_404(budget_id)
    logger.debug(f"Found budget: {budget.name}")
    
    # Get budget items
    budget_items = BudgetItem.query.filter_by(budget_id=budget_id).all()
    logger.debug(f"Found {len(budget_items)} budget items")
    
    # Get all accounts with budget items
    account_ids = set(item.account_id for item in budget_items)
    logger.debug(f"Account IDs found: {account_ids}")
    
    # Handle case where there are no budget items yet
    if not account_ids:
        logger.debug("No account IDs found, returning empty data")
        return {
            'budget': budget,
            'accounts': [],
            'summary': {
                'budget_total': Decimal('0.00'),
                'actual_total': Decimal('0.00'),
                'variance_total': Decimal('0.00'),
                'variance_percent': 0
            }
        }
    
    accounts = Account.query.filter(Account.id.in_(account_ids)).all()
    logger.debug(f"Found {len(accounts)} accounts")
    
    # Create a lookup for budget amounts
    budget_amounts = {}
    for item in budget_items:
        if item.account_id not in budget_amounts:
            budget_amounts[item.account_id] = {}
        budget_amounts[item.account_id][item.period] = item.amount
    
    # Get actual data from journal entries
    actuals = {}
    
    for account in accounts:
        actuals[account.id] = {}
        
        # Create a mapping of period to date range
        try:
            periods = generate_budget_periods(budget.period_type.name, budget.year)
            logger.debug(f"Generated {len(periods)} periods for account {account.id}")
        except Exception as e:
            logger.error(f"Error generating periods: {str(e)}")
            periods = []
        
        for period_info in periods:
            period = period_info['period']
            period_start = period_info['start_date']
            period_end = period_info['end_date']
            
            # Only get data for periods in our date range
            if period_end < start_date or period_start > end_date:
                continue
            
            # Get actual amounts from journal entries
            try:
                logger.debug(f"Getting balance for account {account.id} from {period_start} to {period_end}")
                actual_amount = utils.get_account_balance(
                    account.id, 
                    period_start, 
                    period_end
                )
                logger.debug(f"Got actual amount: {actual_amount}")
                actuals[account.id][period] = actual_amount
            except Exception as e:
                logger.error(f"Error getting account balance: {str(e)}")
                actuals[account.id][period] = Decimal('0.00')
    
    # Prepare result
    result = {
        'budget': budget,
        'accounts': [],
        'summary': {
            'budget_total': Decimal('0.00'),
            'actual_total': Decimal('0.00'),
            'variance_total': Decimal('0.00'),
            'variance_percent': 0
        }
    }
    
    try:
        logger.debug("Processing account data")
        # Process each account
        for account in accounts:
            try:
                account_data = {
                    'account': account,
                    'periods': [],
                    'budget_total': Decimal('0.00'),
                    'actual_total': Decimal('0.00'),
                    'variance_total': Decimal('0.00'),
                    'variance_percent': 0
                }
                
                # Get periods again to ensure we have them for each account
                try:
                    account_periods = generate_budget_periods(budget.period_type.name, budget.year)
                except Exception as e:
                    logger.error(f"Error regenerating periods for account {account.id}: {str(e)}")
                    account_periods = []
                
                # Get data for each period
                for period_info in account_periods:
                    try:
                        period = period_info['period']
                        
                        # Only include periods in our date range
                        if period_info['end_date'] < start_date or period_info['start_date'] > end_date:
                            continue
                        
                        # Get budget amount
                        try:
                            budget_amount = budget_amounts.get(account.id, {}).get(period, Decimal('0.00'))
                            if not isinstance(budget_amount, Decimal):
                                budget_amount = Decimal(str(budget_amount))
                        except Exception as e:
                            logger.error(f"Error getting budget amount for account {account.id}, period {period}: {str(e)}")
                            budget_amount = Decimal('0.00')
                        
                        # Get actual amount
                        try:
                            actual_amount = actuals.get(account.id, {}).get(period, Decimal('0.00'))
                            if not isinstance(actual_amount, Decimal):
                                actual_amount = Decimal(str(actual_amount))
                        except Exception as e:
                            logger.error(f"Error getting actual amount for account {account.id}, period {period}: {str(e)}")
                            actual_amount = Decimal('0.00')
                        
                        # Calculate variance
                        try:
                            variance = actual_amount - budget_amount
                            variance_percent = 0
                            if budget_amount != 0:
                                variance_percent = (variance / budget_amount) * 100
                        except Exception as e:
                            logger.error(f"Error calculating variance for account {account.id}, period {period}: {str(e)}")
                            variance = Decimal('0.00')
                            variance_percent = 0
                        
                        # Create period data
                        period_data = {
                            'period': period,
                            'name': period_info['name'],
                            'budget': budget_amount,
                            'actual': actual_amount,
                            'variance': variance,
                            'variance_percent': variance_percent
                        }
                        
                        # Update account totals
                        account_data['periods'].append(period_data)
                        account_data['budget_total'] += budget_amount
                        account_data['actual_total'] += actual_amount
                    except Exception as e:
                        logger.error(f"Error processing period {period} for account {account.id}: {str(e)}")
                        continue
                
                # Calculate account totals
                try:
                    account_data['variance_total'] = account_data['actual_total'] - account_data['budget_total']
                    if account_data['budget_total'] != 0:
                        account_data['variance_percent'] = (account_data['variance_total'] / account_data['budget_total']) * 100
                except Exception as e:
                    logger.error(f"Error calculating totals for account {account.id}: {str(e)}")
                    account_data['variance_total'] = Decimal('0.00')
                    account_data['variance_percent'] = 0
                
                # Add to result
                result['accounts'].append(account_data)
                
                # Update summary totals
                result['summary']['budget_total'] += account_data['budget_total']
                result['summary']['actual_total'] += account_data['actual_total']
            except Exception as e:
                logger.error(f"Error processing account {account.id}: {str(e)}")
                continue
        
        # Calculate summary variance
        try:
            result['summary']['variance_total'] = result['summary']['actual_total'] - result['summary']['budget_total']
            if result['summary']['budget_total'] != 0:
                result['summary']['variance_percent'] = (result['summary']['variance_total'] / result['summary']['budget_total']) * 100
        except Exception as e:
            logger.error(f"Error calculating summary variance: {str(e)}")
            result['summary']['variance_total'] = Decimal('0.00')
            result['summary']['variance_percent'] = 0
        
        logger.debug("Completed get_actual_vs_budget successfully")
    except Exception as e:
        logger.error(f"Error in get_actual_vs_budget result processing: {str(e)}")
    
    return result

# Routes
@budgeting_bp.route('/dashboard')
@login_required
def dashboard():
    """Budgeting and forecasting dashboard"""
    # Get active budgets
    active_budgets = Budget.query.filter_by(is_active=True).all()
    
    # Get counts
    budget_count = Budget.query.count()
    forecast_count = Forecast.query.count()
    
    # Get latest variance report for summary
    latest_variance = None
    if active_budgets:
        current_budget = active_budgets[0]
        latest_variance = get_actual_vs_budget(
            current_budget.id,
            current_budget.start_date,
            datetime.now().date()
        )
    
    return render_template(
        'budgeting/dashboard.html',
        active_budgets=active_budgets,
        budget_count=budget_count,
        forecast_count=forecast_count,
        latest_variance=latest_variance
    )

# Budget Routes
@budgeting_bp.route('/budgets')
@login_required
def budgets():
    """List all budgets"""
    # Get filters
    year = request.args.get('year', datetime.now().year, type=int)
    is_active = request.args.get('is_active')
    
    # Base query
    query = Budget.query
    
    # Apply filters
    if year:
        query = query.filter_by(year=year)
    
    if is_active:
        if is_active == 'active':
            query = query.filter_by(is_active=True)
        elif is_active == 'inactive':
            query = query.filter_by(is_active=False)
    
    # Get budgets
    budgets = query.order_by(Budget.year.desc(), Budget.name).all()
    
    # Get list of years for filter
    years = db.session.query(Budget.year).distinct().order_by(Budget.year.desc()).all()
    years = [y[0] for y in years]
    
    return render_template(
        'budgeting/budgets.html',
        budgets=budgets,
        years=years,
        current_year=year
    )

@budgeting_bp.route('/budgets/create', methods=['GET', 'POST'])
@login_required
def create_budget():
    """Create a new budget"""
    if not current_user.has_permission(Role.CAN_CREATE):
        flash('You do not have permission to create budgets.', 'danger')
        return redirect(url_for('budgeting.budgets'))
    
    if request.method == 'POST':
        # Get form data
        name = request.form.get('name')
        description = request.form.get('description')
        year = request.form.get('year', type=int)
        period_type_id = request.form.get('period_type_id', type=int)
        
        # Validate
        if not name or not year or not period_type_id:
            flash('Please fill in all required fields.', 'danger')
            return redirect(url_for('budgeting.create_budget'))
        
        # Get period type
        period_type = BudgetPeriodType.query.get(period_type_id)
        if not period_type:
            flash('Invalid period type.', 'danger')
            return redirect(url_for('budgeting.create_budget'))
        
        # Set date range based on year and period type
        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)
        
        # Create budget
        budget = Budget(
            name=name,
            description=description,
            year=year,
            period_type_id=period_type_id,
            start_date=start_date,
            end_date=end_date,
            is_active=True,
            created_by_id=current_user.id
        )
        
        # Create initial version
        version = BudgetVersion(
            budget=budget,
            version_number=1,
            version_name='Initial Version',
            is_active=True,
            created_by_id=current_user.id,
            notes='Initial budget creation'
        )
        
        db.session.add_all([budget, version])
        db.session.commit()
        
        flash('Budget created successfully.', 'success')
        return redirect(url_for('budgeting.edit_budget', budget_id=budget.id))
    
    # Get period types
    period_types = BudgetPeriodType.query.all()
    if not period_types:
        # Create default period types if they don't exist
        monthly = BudgetPeriodType(name=BudgetPeriodType.MONTHLY)
        quarterly = BudgetPeriodType(name=BudgetPeriodType.QUARTERLY)
        annual = BudgetPeriodType(name=BudgetPeriodType.ANNUAL)
        custom = BudgetPeriodType(name=BudgetPeriodType.CUSTOM)
        
        db.session.add_all([monthly, quarterly, annual, custom])
        db.session.commit()
        
        period_types = BudgetPeriodType.query.all()
    
    # Get current year for default value
    current_year = datetime.now().year
    
    return render_template(
        'budgeting/budget_form.html',
        period_types=period_types,
        current_year=current_year
    )

@budgeting_bp.route('/budgets/<int:budget_id>')
@login_required
def view_budget(budget_id):
    """View a budget"""
    import logging
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)
    
    try:
        logger.debug(f"Starting view_budget for budget_id: {budget_id}")
        budget = Budget.query.get_or_404(budget_id)
        logger.debug(f"Found budget: {budget.name}, year: {budget.year}")
        
        # Get budget items
        budget_items = BudgetItem.query.filter_by(budget_id=budget_id).all()
        logger.debug(f"Found {len(budget_items)} budget items")
        
        # Get period info
        periods = generate_budget_periods(budget.period_type.name, budget.year)
        logger.debug(f"Generated {len(periods)} periods")
        
        # Get all accounts with budget items
        account_ids = set(item.account_id for item in budget_items)
        logger.debug(f"Account IDs: {account_ids}")
        
        accounts = []
        if account_ids:
            accounts = Account.query.filter(Account.id.in_(account_ids)).order_by(Account.code).all()
        logger.debug(f"Found {len(accounts)} accounts")
        
        # Create a lookup for budget amounts
        budget_data = {}
        for account in accounts:
            budget_data[account.id] = {
                'account': account,
                'periods': {}
            }
        
        for item in budget_items:
            if item.account_id in budget_data:
                budget_data[item.account_id]['periods'][item.period] = item.amount
        
        logger.debug(f"Created budget_data with {len(budget_data)} entries")
        
        # Get actual vs budget data
        try:
            variance_data = get_actual_vs_budget(
                budget_id, 
                budget.start_date, 
                min(budget.end_date, datetime.now().date())
            )
            logger.debug("Successfully got variance data")
        except Exception as e:
            logger.error(f"Error getting variance data: {str(e)}")
            variance_data = None
        
        # Get budget versions
        versions = BudgetVersion.query.filter_by(budget_id=budget_id).order_by(BudgetVersion.version_number.desc()).all()
        logger.debug(f"Found {len(versions)} budget versions")
        
        # Render the template
        logger.debug("Rendering budget_view.html template with data")
        return render_template(
            'budgeting/budget_view.html',
            budget=budget,
            budget_data=budget_data,
            accounts=accounts,
            periods=periods,
            variance_data=variance_data,
            versions=versions
        )
        
    except Exception as e:
        logger.error(f"Error in view_budget: {str(e)}")
        # Return a simple error page instead of a blank page
        return f"""
        <html>
        <head><title>Error</title></head>
        <body>
            <h1>Error Viewing Budget</h1>
            <p>There was an error loading the budget: {str(e)}</p>
            <a href="{url_for('budgeting.budgets')}">Back to Budgets</a>
        </body>
        </html>
        """

@budgeting_bp.route('/budgets/<int:budget_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_budget(budget_id):
    """Edit a budget"""
    if not current_user.has_permission(Role.CAN_EDIT):
        flash('You do not have permission to edit budgets.', 'danger')
        return redirect(url_for('budgeting.view_budget', budget_id=budget_id))
    
    budget = Budget.query.get_or_404(budget_id)
    
    if request.method == 'POST':
        # Check the action
        action = request.form.get('action', 'save')
        
        if action == 'save':
            # Update budget details
            budget.name = request.form.get('name')
            budget.description = request.form.get('description')
            budget.is_active = 'is_active' in request.form
            
            db.session.commit()
            flash('Budget updated successfully.', 'success')
            return redirect(url_for('budgeting.view_budget', budget_id=budget.id))
        
        elif action == 'save_items':
            # Process budget items
            for key, value in request.form.items():
                if key.startswith('budget_amount_'):
                    # Extract account_id and period from the key
                    parts = key.split('_')
                    if len(parts) >= 3:
                        account_id = int(parts[2])
                        period = int(parts[3])
                        
                        try:
                            amount = Decimal(value) if value else Decimal('0.00')
                        except (ValueError, TypeError):
                            amount = Decimal('0.00')
                        
                        # Find existing item or create new one
                        item = BudgetItem.query.filter_by(
                            budget_id=budget.id,
                            account_id=account_id,
                            period=period
                        ).first()
                        
                        if item:
                            item.amount = amount
                        else:
                            item = BudgetItem(
                                budget_id=budget.id,
                                account_id=account_id,
                                period=period,
                                amount=amount
                            )
                            db.session.add(item)
            
            # Create a new version
            version_name = request.form.get('version_name', 'Updated Version')
            version_notes = request.form.get('version_notes', '')
            
            # Get latest version number
            latest_version = BudgetVersion.query.filter_by(budget_id=budget.id).order_by(
                BudgetVersion.version_number.desc()
            ).first()
            
            new_version_number = 1
            if latest_version:
                new_version_number = latest_version.version_number + 1
            
            # Create new version
            new_version = BudgetVersion(
                budget_id=budget.id,
                version_number=new_version_number,
                version_name=version_name,
                is_active=True,
                created_by_id=current_user.id,
                notes=version_notes
            )
            
            # Set previous version as inactive
            if latest_version:
                latest_version.is_active = False
            
            db.session.add(new_version)
            db.session.commit()
            
            flash('Budget items updated successfully.', 'success')
            return redirect(url_for('budgeting.view_budget', budget_id=budget.id))
    
    # Get period info
    periods = generate_budget_periods(budget.period_type.name, budget.year)
    
    # Get budget items
    budget_items = BudgetItem.query.filter_by(budget_id=budget_id).all()
    
    # Create a lookup for budget amounts
    budget_data = {}
    for item in budget_items:
        if item.account_id not in budget_data:
            budget_data[item.account_id] = {}
        budget_data[item.account_id][item.period] = item.amount
    
    # Get accounts for budget
    accounts = []
    if budget_items:
        account_ids = set(item.account_id for item in budget_items)
        accounts = Account.query.filter(Account.id.in_(account_ids)).order_by(Account.code).all()
    
    # Get available accounts
    revenue_type = AccountType.query.filter_by(name=AccountType.REVENUE).first()
    expense_type = AccountType.query.filter_by(name=AccountType.EXPENSE).first()
    
    revenue_accounts = []
    expense_accounts = []
    
    if revenue_type:
        revenue_accounts = Account.query.filter_by(account_type_id=revenue_type.id, is_active=True).order_by(Account.code).all()
    
    if expense_type:
        expense_accounts = Account.query.filter_by(account_type_id=expense_type.id, is_active=True).order_by(Account.code).all()
    
    return render_template(
        'budgeting/budget_edit.html',
        budget=budget,
        periods=periods,
        accounts=accounts,
        budget_data=budget_data,
        revenue_accounts=revenue_accounts,
        expense_accounts=expense_accounts
    )

@budgeting_bp.route('/budgets/<int:budget_id>/add_account', methods=['POST'])
@login_required
def add_budget_account(budget_id):
    """Add an account to a budget"""
    if not current_user.has_permission(Role.CAN_EDIT):
        flash('You do not have permission to edit budgets.', 'danger')
        return redirect(url_for('budgeting.view_budget', budget_id=budget_id))
    
    budget = Budget.query.get_or_404(budget_id)
    
    # Get the account ID from the form
    account_id = request.form.get('account_id', type=int)
    if not account_id:
        flash('Please select an account.', 'danger')
        return redirect(url_for('budgeting.edit_budget', budget_id=budget_id))
    
    # Check if account exists
    account = Account.query.get(account_id)
    if not account:
        flash('Selected account does not exist.', 'danger')
        return redirect(url_for('budgeting.edit_budget', budget_id=budget_id))
    
    # Check if account is already in the budget
    existing_item = BudgetItem.query.filter_by(budget_id=budget_id, account_id=account_id).first()
    if existing_item:
        flash(f'Account {account.name} is already in this budget.', 'warning')
        return redirect(url_for('budgeting.edit_budget', budget_id=budget_id))
    
    # Get period info
    periods = generate_budget_periods(budget.period_type.name, budget.year)
    
    # Add account to budget with zero amounts
    items = []
    for period_info in periods:
        item = BudgetItem(
            budget_id=budget_id,
            account_id=account_id,
            period=period_info['period'],
            amount=0
        )
        items.append(item)
    
    db.session.add_all(items)
    db.session.commit()
    
    flash(f'Account {account.name} added to budget.', 'success')
    return redirect(url_for('budgeting.edit_budget', budget_id=budget_id))

@budgeting_bp.route('/budgets/<int:budget_id>/remove_account/<int:account_id>', methods=['POST'])
@login_required
def remove_budget_account(budget_id, account_id):
    """Remove an account from a budget"""
    if not current_user.has_permission(Role.CAN_EDIT):
        flash('You do not have permission to edit budgets.', 'danger')
        return redirect(url_for('budgeting.view_budget', budget_id=budget_id))
    
    # Check if account exists in the budget
    items = BudgetItem.query.filter_by(budget_id=budget_id, account_id=account_id).all()
    if not items:
        flash('Account not found in this budget.', 'warning')
        return redirect(url_for('budgeting.edit_budget', budget_id=budget_id))
    
    # Get account name for the message
    account = Account.query.get(account_id)
    account_name = account.name if account else 'Unknown'
    
    # Delete all items for this account
    for item in items:
        db.session.delete(item)
    
    db.session.commit()
    
    flash(f'Account {account_name} removed from budget.', 'success')
    return redirect(url_for('budgeting.edit_budget', budget_id=budget_id))

@budgeting_bp.route('/budgets/<int:budget_id>/delete', methods=['POST'])
@login_required
def delete_budget(budget_id):
    """Delete a budget"""
    if not current_user.has_permission(Role.CAN_DELETE):
        flash('You do not have permission to delete budgets.', 'danger')
        return redirect(url_for('budgeting.view_budget', budget_id=budget_id))
    
    budget = Budget.query.get_or_404(budget_id)
    
    # Delete all related items
    BudgetItem.query.filter_by(budget_id=budget_id).delete()
    
    # Delete all versions
    BudgetVersion.query.filter_by(budget_id=budget_id).delete()
    
    # Delete budget
    db.session.delete(budget)
    db.session.commit()
    
    flash('Budget deleted successfully.', 'success')
    return redirect(url_for('budgeting.budgets'))

# Budget vs Actual Report
@budgeting_bp.route('/reports/variance')
@login_required
def variance_report():
    """Budget vs Actual Variance Report"""
    # Get filters
    budget_id = request.args.get('budget_id', type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Get all active budgets for filter dropdown
    budgets = Budget.query.filter_by(is_active=True).all()
    
    # If no budget selected but we have budgets, use the first one
    if not budget_id and budgets:
        budget_id = budgets[0].id
    
    # If no budget, show empty report
    if not budget_id:
        return render_template(
            'budgeting/variance_report.html',
            budgets=budgets,
            variance_data=None
        )
    
    # Get the selected budget
    budget = Budget.query.get_or_404(budget_id)
    
    # Parse dates
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    else:
        start_date = budget.start_date
    
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    else:
        end_date = min(budget.end_date, datetime.now().date())
    
    # Get variance data
    variance_data = get_actual_vs_budget(budget_id, start_date, end_date)
    
    return render_template(
        'budgeting/variance_report.html',
        budgets=budgets,
        selected_budget=budget,
        variance_data=variance_data,
        start_date=start_date,
        end_date=end_date
    )

# Forecast Routes
@budgeting_bp.route('/forecasts')
@login_required
def forecasts():
    """List all forecasts"""
    forecasts = Forecast.query.order_by(Forecast.start_date.desc()).all()
    return render_template('budgeting/forecasts.html', forecasts=forecasts)

@budgeting_bp.route('/forecasts/create', methods=['GET', 'POST'])
@login_required
def create_forecast():
    """Create a new forecast"""
    if not current_user.has_permission(Role.CAN_CREATE):
        flash('You do not have permission to create forecasts.', 'danger')
        return redirect(url_for('budgeting.forecasts'))
    
    if request.method == 'POST':
        # Get form data
        name = request.form.get('name')
        description = request.form.get('description')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        period_type_id = request.form.get('period_type_id', type=int)
        
        # Validate
        if not name or not start_date or not end_date or not period_type_id:
            flash('Please fill in all required fields.', 'danger')
            return redirect(url_for('budgeting.create_forecast'))
        
        # Parse dates
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        # Create forecast
        forecast = Forecast(
            name=name,
            description=description,
            start_date=start_date,
            end_date=end_date,
            period_type_id=period_type_id,
            is_active=True,
            created_by_id=current_user.id
        )
        
        db.session.add(forecast)
        db.session.commit()
        
        flash('Forecast created successfully.', 'success')
        return redirect(url_for('budgeting.view_forecast', forecast_id=forecast.id))
    
    # Get period types
    period_types = BudgetPeriodType.query.all()
    if not period_types:
        # Create default period types if they don't exist
        monthly = BudgetPeriodType(name=BudgetPeriodType.MONTHLY)
        quarterly = BudgetPeriodType(name=BudgetPeriodType.QUARTERLY)
        annual = BudgetPeriodType(name=BudgetPeriodType.ANNUAL)
        custom = BudgetPeriodType(name=BudgetPeriodType.CUSTOM)
        
        db.session.add_all([monthly, quarterly, annual, custom])
        db.session.commit()
        
        period_types = BudgetPeriodType.query.all()
    
    # Default dates
    today = datetime.now().date()
    
    return render_template(
        'budgeting/forecast_form.html',
        period_types=period_types,
        today=today
    )

@budgeting_bp.route('/forecasts/<int:forecast_id>')
@login_required
def view_forecast(forecast_id):
    """View a forecast"""
    forecast = Forecast.query.get_or_404(forecast_id)
    
    # Get forecast items
    items = ForecastItem.query.filter_by(forecast_id=forecast_id).all()
    
    # Get all accounts with forecast items
    account_ids = set(item.account_id for item in items)
    accounts = Account.query.filter(Account.id.in_(account_ids)).order_by(Account.code).all()
    
    # Create a lookup for forecast amounts
    forecast_data = {}
    for account in accounts:
        forecast_data[account.id] = {
            'account': account,
            'periods': {}
        }
    
    for item in items:
        if item.account_id in forecast_data:
            forecast_data[item.account_id]['periods'][item.period] = {
                'amount': item.amount,
                'growth_factor': item.growth_factor
            }
    
    return render_template(
        'budgeting/forecast_view.html',
        forecast=forecast,
        forecast_data=forecast_data,
        accounts=accounts
    )

@budgeting_bp.route('/forecasts/<int:forecast_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_forecast(forecast_id):
    """Edit a forecast"""
    if not current_user.has_permission(Role.CAN_EDIT):
        flash('You do not have permission to edit forecasts.', 'danger')
        return redirect(url_for('budgeting.view_forecast', forecast_id=forecast_id))
    
    forecast = Forecast.query.get_or_404(forecast_id)
    
    if request.method == 'POST':
        # Update forecast details
        forecast.name = request.form.get('name')
        forecast.description = request.form.get('description')
        forecast.is_active = 'is_active' in request.form
        
        db.session.commit()
        flash('Forecast updated successfully.', 'success')
        return redirect(url_for('budgeting.view_forecast', forecast_id=forecast.id))
    
    return render_template(
        'budgeting/forecast_edit.html',
        forecast=forecast
    )

@budgeting_bp.route('/forecasts/<int:forecast_id>/delete', methods=['POST'])
@login_required
def delete_forecast(forecast_id):
    """Delete a forecast"""
    if not current_user.has_permission(Role.CAN_DELETE):
        flash('You do not have permission to delete forecasts.', 'danger')
        return redirect(url_for('budgeting.view_forecast', forecast_id=forecast_id))
    
    forecast = Forecast.query.get_or_404(forecast_id)
    
    # Delete all related items
    ForecastItem.query.filter_by(forecast_id=forecast_id).delete()
    
    # Delete forecast
    db.session.delete(forecast)
    db.session.commit()
    
    flash('Forecast deleted successfully.', 'success')
    return redirect(url_for('budgeting.forecasts'))