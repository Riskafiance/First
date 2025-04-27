"""
Utility functions for managing user-specific JSON data files
"""
import os
import json
from datetime import datetime, date, timedelta
from decimal import Decimal
from flask import g, current_app
from flask_login import current_user

# Path to user data directory
USER_DATA_DIR = 'user_data'

class JSONEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle dates and decimals"""
    def default(self, obj):
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        elif isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

def get_user_data_path(username):
    """Get the path to a user's data file"""
    # Ensure the username is sanitized to be safe as a filename
    sanitized_username = ''.join(c for c in username if c.isalnum() or c in '._-')
    return os.path.join(USER_DATA_DIR, f"{sanitized_username}_data.json")

def create_user_data_file(username):
    """Create a new, empty data file for a user"""
    # Ensure user data directory exists
    if not os.path.exists(USER_DATA_DIR):
        os.makedirs(USER_DATA_DIR)
    
    # Create an empty data structure
    data = {
        "created_at": datetime.now().isoformat(),
        "last_modified": datetime.now().isoformat(),
        "chart_of_accounts": {
            # Default chart of accounts structure
            "assets": [],
            "liabilities": [],
            "equity": [],
            "revenue": [],
            "expenses": []
        },
        "transactions": [],
        "journal_entries": [],
        "customers": [],
        "vendors": [],
        "invoices": [],
        "expenses": [],
        "products": [],
        "inventory": [],
        "fixed_assets": [],
        "projects": [],
        "budget_items": []
    }
    
    # Write to file
    file_path = get_user_data_path(username)
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)
    
    return file_path

def user_data_exists(username):
    """Check if data file exists for a user"""
    file_path = get_user_data_path(username)
    return os.path.exists(file_path)

def get_user_data(username):
    """Get user data from their JSON file"""
    file_path = get_user_data_path(username)
    
    # If file doesn't exist, create it
    if not os.path.exists(file_path):
        create_user_data_file(username)
    
    # Read and return the data
    with open(file_path, 'r') as f:
        return json.load(f)

def save_user_data(username, data):
    """Save user data to their JSON file"""
    # Update the last modified timestamp
    data["last_modified"] = datetime.now().isoformat()
    
    # Write to file
    file_path = get_user_data_path(username)
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)
    
    return True

def delete_user_data(username):
    """Delete a user's data file"""
    file_path = get_user_data_path(username)
    if os.path.exists(file_path):
        os.remove(file_path)
        return True
    return False

# Functions for working with specific sections of user data
def get_chart_of_accounts(username):
    """Get the chart of accounts for a user"""
    data = get_user_data(username)
    return data.get("chart_of_accounts", {})

def get_transactions(username):
    """Get transactions for a user"""
    data = get_user_data(username)
    return data.get("transactions", [])

def get_journal_entries(username):
    """Get journal entries for a user"""
    data = get_user_data(username)
    return data.get("journal_entries", [])

def get_customers(username):
    """Get customers for a user"""
    data = get_user_data(username)
    return data.get("customers", [])

def get_vendors(username):
    """Get vendors for a user"""
    data = get_user_data(username)
    return data.get("vendors", [])

def add_account(username, account_data):
    """Add a new account to the chart of accounts"""
    data = get_user_data(username)
    account_type = account_data.get("type", "").lower()
    
    # Ensure the account type exists
    if account_type not in data["chart_of_accounts"]:
        data["chart_of_accounts"][account_type] = []
    
    # Add a unique ID to the account
    account_data["id"] = len(data["chart_of_accounts"][account_type]) + 1
    account_data["created_at"] = datetime.now().isoformat()
    
    # Add the account
    data["chart_of_accounts"][account_type].append(account_data)
    
    # Save the data
    save_user_data(username, data)
    return account_data

def add_transaction(username, transaction_data):
    """Add a new transaction"""
    data = get_user_data(username)
    
    # Add a unique ID and timestamps
    transaction_data["id"] = len(data["transactions"]) + 1
    transaction_data["created_at"] = datetime.now().isoformat()
    
    # Add the transaction
    data["transactions"].append(transaction_data)
    
    # Save the data
    save_user_data(username, data)
    return transaction_data

def add_customer(username, customer_data):
    """Add a new customer"""
    data = get_user_data(username)
    
    # Add a unique ID and timestamps
    customer_data["id"] = len(data["customers"]) + 1
    customer_data["created_at"] = datetime.now().isoformat()
    
    # Add the customer
    data["customers"].append(customer_data)
    
    # Save the data
    save_user_data(username, data)
    return customer_data

def add_vendor(username, vendor_data):
    """Add a new vendor"""
    data = get_user_data(username)
    
    # Add a unique ID and timestamps
    vendor_data["id"] = len(data["vendors"]) + 1
    vendor_data["created_at"] = datetime.now().isoformat()
    
    # Add the vendor
    data["vendors"].append(vendor_data)
    
    # Save the data
    save_user_data(username, data)
    return vendor_data

def get_invoices(username):
    """Get invoices for a user"""
    data = get_user_data(username)
    return data.get("invoices", [])

def get_expenses(username):
    """Get expenses for a user"""
    data = get_user_data(username)
    return data.get("expenses", [])

def get_products(username):
    """Get products for a user"""
    data = get_user_data(username)
    return data.get("products", [])

def get_projects(username):
    """Get projects for a user"""
    data = get_user_data(username)
    return data.get("projects", [])

def add_journal_entry(username, entry_data):
    """Add a new journal entry"""
    data = get_user_data(username)
    
    # Add a unique ID and timestamps
    entry_data["id"] = len(data["journal_entries"]) + 1
    entry_data["created_at"] = datetime.now().isoformat()
    
    # Add the entry
    data["journal_entries"].append(entry_data)
    
    # Save the data
    save_user_data(username, data)
    return entry_data

def add_invoice(username, invoice_data):
    """Add a new invoice"""
    data = get_user_data(username)
    
    # Add a unique ID and timestamps
    invoice_data["id"] = len(data["invoices"]) + 1
    invoice_data["created_at"] = datetime.now().isoformat()
    
    # Add the invoice
    data["invoices"].append(invoice_data)
    
    # Save the data
    save_user_data(username, data)
    return invoice_data

def add_expense(username, expense_data):
    """Add a new expense"""
    data = get_user_data(username)
    
    # Add a unique ID and timestamps
    expense_data["id"] = len(data["expenses"]) + 1
    expense_data["created_at"] = datetime.now().isoformat()
    
    # Add the expense
    data["expenses"].append(expense_data)
    
    # Save the data
    save_user_data(username, data)
    return expense_data

def get_financial_summary(username, start_date=None, end_date=None):
    """Get financial summary for the dashboard"""
    if not start_date:
        start_date = datetime.now().date().replace(day=1)  # First day of current month
    if not end_date:
        end_date = datetime.now().date()  # Current date
        
    # Convert to strings for comparison if they're date objects
    if isinstance(start_date, date):
        start_date = start_date.isoformat()
    if isinstance(end_date, date):
        end_date = end_date.isoformat()
    
    # Get user data
    data = get_user_data(username)
    
    # Get revenue from journal entries
    income = 0
    for entry in data.get("journal_entries", []):
        entry_date = entry.get("entry_date")
        if entry_date and start_date <= entry_date <= end_date and entry.get("is_posted", True):
            for item in entry.get("items", []):
                if item.get("account_type") == "revenue":
                    income += item.get("credit_amount", 0) - item.get("debit_amount", 0)
    
    # Get expenses from journal entries
    expenses = 0
    for entry in data.get("journal_entries", []):
        entry_date = entry.get("entry_date")
        if entry_date and start_date <= entry_date <= end_date and entry.get("is_posted", True):
            for item in entry.get("items", []):
                if item.get("account_type") == "expense":
                    expenses += item.get("debit_amount", 0) - item.get("credit_amount", 0)
    
    # Get outstanding invoices
    accounts_receivable = 0
    for invoice in data.get("invoices", []):
        if invoice.get("status") in ["sent", "overdue"]:
            accounts_receivable += invoice.get("total_amount", 0)
    
    # Return financial summary
    return {
        "income": income,
        "expenses": expenses,
        "profit": income - expenses,
        "accounts_receivable": accounts_receivable
    }

def get_monthly_trends(username, months=6):
    """Get monthly trends for the last X months"""
    today = datetime.now().date()
    result = []
    
    # Get user data
    data = get_user_data(username)
    
    # Create empty monthly data for the past X months
    for i in range(months-1, -1, -1):  # Count backwards from months-1 to 0
        # Calculate month date
        month_date = today.replace(day=1)  # First day of current month
        # Go back i months
        for _ in range(i):
            # Go to first day of previous month
            if month_date.month == 1:
                month_date = month_date.replace(year=month_date.year-1, month=12)
            else:
                month_date = month_date.replace(month=month_date.month-1)
        
        # Calculate month end
        if month_date.month == 12:
            month_end = month_date.replace(year=month_date.year+1, month=1, day=1) - timedelta(days=1)
        else:
            month_end = month_date.replace(month=month_date.month+1, day=1) - timedelta(days=1)
        
        # Format month name
        month_name = f"{month_date.strftime('%b')} {month_date.year}"
        
        # Calculate income and expenses for this month
        income = 0
        expenses = 0
        
        # Convert to strings for comparison
        start_date = month_date.isoformat()
        end_date = month_end.isoformat()
        
        # Process journal entries
        for entry in data.get("journal_entries", []):
            entry_date = entry.get("entry_date")
            if entry_date and start_date <= entry_date <= end_date and entry.get("is_posted", True):
                for item in entry.get("items", []):
                    if item.get("account_type") == "revenue":
                        income += item.get("credit_amount", 0) - item.get("debit_amount", 0)
                    elif item.get("account_type") == "expense":
                        expenses += item.get("debit_amount", 0) - item.get("credit_amount", 0)
        
        # Add to result
        result.append({
            "month": month_name,
            "income": income,
            "expenses": expenses
        })
    
    return result

def initialize_empty_account(username):
    """
    Initialize a completely empty account for a new user
    Creates an empty data file with basic structure but no data
    """
    return create_user_data_file(username)