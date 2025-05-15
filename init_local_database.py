"""
This script initializes the database with required default values.
Run this once after setting up your database to ensure all required data is present.
"""
from app import app, db
from models import Role, AccountType, EntityType, InvoiceStatus, ExpenseStatus, BudgetPeriodType
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def init_account_types():
    """Initialize account types"""
    logger.info("Initializing account types...")
    types = [
        {"id": 1, "name": "Asset"},
        {"id": 2, "name": "Liability"},
        {"id": 3, "name": "Equity"},
        {"id": 4, "name": "Revenue"},
        {"id": 5, "name": "Expense"}
    ]
    
    count = 0
    for type_data in types:
        account_type = AccountType.query.filter_by(id=type_data["id"]).first()
        if not account_type:
            account_type = AccountType(id=type_data["id"], name=type_data["name"])
            db.session.add(account_type)
            count += 1
    
    if count > 0:
        logger.info(f"Added {count} account types")
    else:
        logger.info("All account types already exist")

def init_entity_types():
    """Initialize entity types"""
    logger.info("Initializing entity types...")
    types = [
        {"id": 1, "name": EntityType.CUSTOMER},
        {"id": 2, "name": EntityType.VENDOR}
    ]
    
    count = 0
    for type_data in types:
        entity_type = EntityType.query.filter_by(id=type_data["id"]).first()
        if not entity_type:
            entity_type = EntityType(id=type_data["id"], name=type_data["name"])
            db.session.add(entity_type)
            count += 1
    
    if count > 0:
        logger.info(f"Added {count} entity types")
    else:
        logger.info("All entity types already exist")

def init_invoice_statuses():
    """Initialize invoice statuses"""
    logger.info("Initializing invoice statuses...")
    statuses = [
        {"id": 1, "name": InvoiceStatus.DRAFT},
        {"id": 2, "name": InvoiceStatus.SENT},
        {"id": 3, "name": InvoiceStatus.PAID},
        {"id": 4, "name": InvoiceStatus.OVERDUE},
        {"id": 5, "name": InvoiceStatus.CANCELLED}
    ]
    
    count = 0
    for status_data in statuses:
        invoice_status = InvoiceStatus.query.filter_by(id=status_data["id"]).first()
        if not invoice_status:
            invoice_status = InvoiceStatus(id=status_data["id"], name=status_data["name"])
            db.session.add(invoice_status)
            count += 1
    
    if count > 0:
        logger.info(f"Added {count} invoice statuses")
    else:
        logger.info("All invoice statuses already exist")

def init_expense_statuses():
    """Initialize expense statuses"""
    logger.info("Initializing expense statuses...")
    statuses = [
        {"id": 1, "name": ExpenseStatus.DRAFT},
        {"id": 2, "name": ExpenseStatus.PENDING},
        {"id": 3, "name": ExpenseStatus.APPROVED},
        {"id": 4, "name": ExpenseStatus.PAID},
        {"id": 5, "name": ExpenseStatus.REJECTED}
    ]
    
    count = 0
    for status_data in statuses:
        expense_status = ExpenseStatus.query.filter_by(id=status_data["id"]).first()
        if not expense_status:
            expense_status = ExpenseStatus(id=status_data["id"], name=status_data["name"])
            db.session.add(expense_status)
            count += 1
    
    if count > 0:
        logger.info(f"Added {count} expense statuses")
    else:
        logger.info("All expense statuses already exist")

def init_budget_period_types():
    """Initialize budget period types"""
    logger.info("Initializing budget period types...")
    types = [
        {"id": 1, "name": BudgetPeriodType.MONTHLY},
        {"id": 2, "name": BudgetPeriodType.QUARTERLY},
        {"id": 3, "name": BudgetPeriodType.ANNUAL},
        {"id": 4, "name": BudgetPeriodType.CUSTOM}
    ]
    
    count = 0
    for type_data in types:
        period_type = BudgetPeriodType.query.filter_by(id=type_data["id"]).first()
        if not period_type:
            period_type = BudgetPeriodType(id=type_data["id"], name=type_data["name"])
            db.session.add(period_type)
            count += 1
    
    if count > 0:
        logger.info(f"Added {count} budget period types")
    else:
        logger.info("All budget period types already exist")

def init_roles():
    """Initialize user roles"""
    logger.info("Initializing roles...")
    Role.insert_roles()
    logger.info("Roles initialized")

def initialize_database():
    """Initialize the database with required default values"""
    logger.info("Starting database initialization...")
    
    try:
        # Initialize all required data
        init_roles()
        init_account_types()
        init_entity_types()
        init_invoice_statuses()
        init_expense_statuses()
        init_budget_period_types()
        
        # Commit all changes
        db.session.commit()
        logger.info("Database initialization completed successfully!")
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error initializing database: {str(e)}")
        raise

if __name__ == "__main__":
    with app.app_context():
        initialize_database()