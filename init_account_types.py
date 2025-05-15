from app import app, db
from models import AccountType

def initialize_account_types():
    """Create account types if they don't exist"""
    print("Initializing account types...")
    
    # Define the required account types
    types = [
        AccountType.ASSET,
        AccountType.LIABILITY,
        AccountType.EQUITY,
        AccountType.REVENUE,
        AccountType.EXPENSE
    ]
    
    # Check if account types already exist
    existing_types = AccountType.query.all()
    existing_names = [t.name for t in existing_types]
    
    print(f"Found {len(existing_types)} existing account types: {', '.join(existing_names)}")
    
    # Add any missing account types
    for type_name in types:
        if type_name not in existing_names:
            print(f"Adding account type: {type_name}")
            account_type = AccountType(name=type_name)
            db.session.add(account_type)
    
    # Commit changes if any were made
    try:
        db.session.commit()
        print("Account types initialization complete.")
    except Exception as e:
        db.session.rollback()
        print(f"Error initializing account types: {str(e)}")

# Run within app context
with app.app_context():
    initialize_account_types()
    
    # Print all account types for verification
    all_types = AccountType.query.all()
    print("\nCurrent account types:")
    for t in all_types:
        print(f"- ID: {t.id}, Name: {t.name}")