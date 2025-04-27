"""
Utility functions for initializing new user accounts
"""
from app import db
from models import Role, User, AccountType, Account

def initialize_new_user_account(user):
    """
    Initialize a new user's account with basic structure but no transactions
    Creates:
    1. Basic account structure (chart of accounts)
    2. Assumes the user is isolated - no data from other users will be visible
    
    Args:
        user (User): The newly created user object
    """
    # Create basic chart of accounts for the new user
    # This provides the structure without any transactions
    create_default_account_types()
    create_default_chart_of_accounts(user.id)

def create_default_account_types():
    """
    Create default account types if they don't exist
    These are global and shared across all users
    """
    account_types = [
        # Asset accounts
        {'code': '1000', 'name': 'Assets', 'classification': 'Asset', 'description': 'Resources owned by the business'},
        {'code': '1100', 'name': 'Current Assets', 'classification': 'Asset', 'description': 'Assets expected to be converted to cash within one year'},
        {'code': '1200', 'name': 'Fixed Assets', 'classification': 'Asset', 'description': 'Long-term assets used in the operation of business'},
        
        # Liability accounts
        {'code': '2000', 'name': 'Liabilities', 'classification': 'Liability', 'description': 'Obligations of the business'},
        {'code': '2100', 'name': 'Current Liabilities', 'classification': 'Liability', 'description': 'Obligations due within one year'},
        {'code': '2200', 'name': 'Long-term Liabilities', 'classification': 'Liability', 'description': 'Obligations due after one year'},
        
        # Equity accounts
        {'code': '3000', 'name': 'Equity', 'classification': 'Equity', 'description': 'Owners claim to business assets'},
        
        # Revenue accounts
        {'code': '4000', 'name': 'Revenue', 'classification': 'Revenue', 'description': 'Income from business operations'},
        
        # Expense accounts
        {'code': '5000', 'name': 'Expenses', 'classification': 'Expense', 'description': 'Costs incurred in business operations'},
        {'code': '5100', 'name': 'Operating Expenses', 'classification': 'Expense', 'description': 'Day-to-day business costs'},
    ]
    
    for account_type_data in account_types:
        # Check if account type already exists
        account_type = AccountType.query.filter_by(code=account_type_data['code']).first()
        if not account_type:
            account_type = AccountType(**account_type_data)
            db.session.add(account_type)
    
    db.session.commit()

def create_default_chart_of_accounts(user_id):
    """
    Create a default chart of accounts for a new user
    All accounts start with zero balance

    Args:
        user_id (int): The user ID to associate with these accounts
    """
    accounts = [
        # Current Assets
        {'code': '1110', 'name': 'Cash', 'account_type': '1100', 'user_id': user_id, 'balance': 0, 
         'description': 'Cash on hand and in bank accounts'},
        {'code': '1120', 'name': 'Accounts Receivable', 'account_type': '1100', 'user_id': user_id, 'balance': 0, 
         'description': 'Amounts owed to the business by customers'},
        {'code': '1130', 'name': 'Inventory', 'account_type': '1100', 'user_id': user_id, 'balance': 0, 
         'description': 'Goods available for sale to customers'},
        
        # Fixed Assets
        {'code': '1210', 'name': 'Equipment', 'account_type': '1200', 'user_id': user_id, 'balance': 0, 
         'description': 'Business equipment and machinery'},
        {'code': '1220', 'name': 'Furniture and Fixtures', 'account_type': '1200', 'user_id': user_id, 'balance': 0, 
         'description': 'Office furniture and fixtures'},
        {'code': '1230', 'name': 'Accumulated Depreciation', 'account_type': '1200', 'user_id': user_id, 'balance': 0, 
         'description': 'Accumulated depreciation of fixed assets', 'is_contra': True},
        
        # Current Liabilities
        {'code': '2110', 'name': 'Accounts Payable', 'account_type': '2100', 'user_id': user_id, 'balance': 0, 
         'description': 'Amounts owed by the business to vendors'},
        {'code': '2120', 'name': 'Accrued Expenses', 'account_type': '2100', 'user_id': user_id, 'balance': 0, 
         'description': 'Expenses incurred but not yet paid'},
        
        # Long-term Liabilities
        {'code': '2210', 'name': 'Long-term Loans', 'account_type': '2200', 'user_id': user_id, 'balance': 0, 
         'description': 'Loans due after one year'},
        
        # Equity
        {'code': '3010', 'name': 'Owner\'s Capital', 'account_type': '3000', 'user_id': user_id, 'balance': 0, 
         'description': 'Owner\'s investment in the business'},
        {'code': '3020', 'name': 'Retained Earnings', 'account_type': '3000', 'user_id': user_id, 'balance': 0, 
         'description': 'Accumulated earnings retained in the business'},
        
        # Revenue
        {'code': '4010', 'name': 'Sales Revenue', 'account_type': '4000', 'user_id': user_id, 'balance': 0, 
         'description': 'Income from sales of goods or services'},
        {'code': '4020', 'name': 'Service Revenue', 'account_type': '4000', 'user_id': user_id, 'balance': 0, 
         'description': 'Income from providing services'},
        
        # Expenses
        {'code': '5110', 'name': 'Rent Expense', 'account_type': '5100', 'user_id': user_id, 'balance': 0, 
         'description': 'Cost of renting business premises'},
        {'code': '5120', 'name': 'Utilities Expense', 'account_type': '5100', 'user_id': user_id, 'balance': 0, 
         'description': 'Cost of utilities like electricity, water, internet'},
        {'code': '5130', 'name': 'Salaries and Wages', 'account_type': '5100', 'user_id': user_id, 'balance': 0, 
         'description': 'Employee compensation'},
        {'code': '5140', 'name': 'Depreciation Expense', 'account_type': '5100', 'user_id': user_id, 'balance': 0, 
         'description': 'Allocation of asset costs over their useful life'},
    ]
    
    for account_data in accounts:
        # Get the account type
        account_type_code = account_data.pop('account_type')
        account_type = AccountType.query.filter_by(code=account_type_code).first()
        
        if account_type:
            # Create the account with the account type
            account = Account(account_type_id=account_type.id, **account_data)
            db.session.add(account)
    
    db.session.commit()