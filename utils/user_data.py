"""
Utility functions for managing user-specific JSON data files
"""
import os
import json
from datetime import datetime

# Path to user data directory
USER_DATA_DIR = 'user_data'

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

def initialize_empty_account(username):
    """
    Initialize a completely empty account for a new user
    Creates an empty data file with basic structure but no data
    """
    return create_user_data_file(username)