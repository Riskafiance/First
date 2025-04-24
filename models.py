from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from app import db
from flask_login import UserMixin
from datetime import datetime, date
from enum import Enum
from sqlalchemy.ext.hybrid import hybrid_property
from werkzeug.security import generate_password_hash, check_password_hash

# User roles and permissions
class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(255))
    
    # Define permissions as bit flags
    CAN_VIEW = 1
    CAN_CREATE = 2
    CAN_EDIT = 4
    CAN_DELETE = 8
    CAN_APPROVE = 16
    CAN_ADMIN = 32
    
    permissions = db.Column(db.Integer, default=CAN_VIEW)
    
    def __repr__(self):
        return f'<Role {self.name}>'
        
    @staticmethod
    def insert_roles():
        """Insert default roles"""
        roles = {
            'Viewer': Role.CAN_VIEW,
            'Creator': Role.CAN_VIEW | Role.CAN_CREATE,
            'Editor': Role.CAN_VIEW | Role.CAN_CREATE | Role.CAN_EDIT,
            'Manager': Role.CAN_VIEW | Role.CAN_CREATE | Role.CAN_EDIT | Role.CAN_DELETE | Role.CAN_APPROVE,
            'Admin': Role.CAN_VIEW | Role.CAN_CREATE | Role.CAN_EDIT | Role.CAN_DELETE | Role.CAN_APPROVE | Role.CAN_ADMIN
        }
        
        for role_name, permissions in roles.items():
            # Check if role exists
            role = Role.query.filter_by(name=role_name).first()
            if role is None:
                role = Role(name=role_name, permissions=permissions)
            else:
                role.permissions = permissions
            db.session.add(role)
        
        db.session.commit()

# User model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(64))
    last_name = db.Column(db.String(64))
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'))
    role = db.relationship('Role')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def has_permission(self, permission):
        if self.role:
            return (self.role.permissions & permission) == permission
        return False
        
    def get_permissions_list(self):
        """Returns a list of permission names the user has"""
        permissions = []
        
        if self.has_permission(Role.CAN_VIEW):
            permissions.append("View Records")
            
        if self.has_permission(Role.CAN_CREATE):
            permissions.append("Create Records")
            
        if self.has_permission(Role.CAN_EDIT):
            permissions.append("Edit Records")
            
        if self.has_permission(Role.CAN_DELETE):
            permissions.append("Delete Records")
            
        if self.has_permission(Role.CAN_APPROVE):
            permissions.append("Approve Records")
            
        if self.has_permission(Role.CAN_ADMIN):
            permissions.append("Administrator")
            
        return permissions
    
    def __repr__(self):
        return f'<User {self.username}>'

# Account Types
class AccountType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    
    # Constants for account types
    ASSET = 'Asset'
    LIABILITY = 'Liability'
    EQUITY = 'Equity'
    REVENUE = 'Revenue'
    EXPENSE = 'Expense'
    
    def __repr__(self):
        return f'<AccountType {self.name}>'

# Chart of Accounts
class Account(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255))
    account_type_id = db.Column(db.Integer, db.ForeignKey('account_type.id'), nullable=False)
    account_type = db.relationship('AccountType')
    parent_id = db.Column(db.Integer, db.ForeignKey('account.id'))
    parent = db.relationship('Account', remote_side=[id], backref='sub_accounts')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_by = db.relationship('User')
    
    def __repr__(self):
        return f'<Account {self.code} - {self.name}>'

# Journal Entries
class JournalEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    entry_date = db.Column(db.Date, nullable=False)
    reference = db.Column(db.String(50))
    description = db.Column(db.String(255))
    is_posted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_by = db.relationship('User')
    
    def __repr__(self):
        return f'<JournalEntry {self.id} - {self.entry_date}>'

# Journal Entry Line Items
class JournalItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    journal_entry_id = db.Column(db.Integer, db.ForeignKey('journal_entry.id'), nullable=False)
    journal_entry = db.relationship('JournalEntry', backref='items')
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    account = db.relationship('Account')
    description = db.Column(db.String(255))
    debit_amount = db.Column(db.Numeric(14, 2), default=0)
    credit_amount = db.Column(db.Numeric(14, 2), default=0)
    
    def __repr__(self):
        return f'<JournalItem {self.id} - {self.account.name}>'

# Entity Type (Customer or Vendor)
class EntityType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    
    # Constants
    CUSTOMER = 'Customer'
    VENDOR = 'Vendor'
    
    def __repr__(self):
        return f'<EntityType {self.name}>'

# Customers and Vendors
class Entity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    entity_type_id = db.Column(db.Integer, db.ForeignKey('entity_type.id'), nullable=False)
    entity_type = db.relationship('EntityType')
    contact_name = db.Column(db.String(100))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    address = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_by = db.relationship('User')
    
    def __repr__(self):
        return f'<Entity {self.name} ({self.entity_type.name})>'

# Invoice Status
class InvoiceStatus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    
    # Constants
    DRAFT = 'Draft'
    SENT = 'Sent'
    PAID = 'Paid'
    OVERDUE = 'Overdue'
    CANCELLED = 'Cancelled'
    
    def __repr__(self):
        return f'<InvoiceStatus {self.name}>'

# Invoices
class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(20), unique=True, nullable=False)
    entity_id = db.Column(db.Integer, db.ForeignKey('entity.id'), nullable=False)
    entity = db.relationship('Entity')
    issue_date = db.Column(db.Date, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    status_id = db.Column(db.Integer, db.ForeignKey('invoice_status.id'), nullable=False)
    status = db.relationship('InvoiceStatus')
    total_amount = db.Column(db.Numeric(14, 2), default=0)
    notes = db.Column(db.Text)
    journal_entry_id = db.Column(db.Integer, db.ForeignKey('journal_entry.id'))
    journal_entry = db.relationship('JournalEntry')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_by = db.relationship('User')
    
    def __repr__(self):
        return f'<Invoice {self.invoice_number}>'

# Invoice Line Items
class InvoiceItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)
    invoice = db.relationship('Invoice', backref='items')
    description = db.Column(db.String(255), nullable=False)
    quantity = db.Column(db.Numeric(10, 2), default=1)
    unit_price = db.Column(db.Numeric(14, 2), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    account = db.relationship('Account')
    
    @property
    def line_total(self):
        return self.quantity * self.unit_price
    
    def __repr__(self):
        return f'<InvoiceItem {self.id} - {self.description}>'

# Expense Status
class ExpenseStatus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    
    # Constants
    DRAFT = 'Draft'
    PENDING = 'Pending'
    APPROVED = 'Approved'
    PAID = 'Paid'
    REJECTED = 'Rejected'
    
    def __repr__(self):
        return f'<ExpenseStatus {self.name}>'

# Expenses
class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    expense_number = db.Column(db.String(20), unique=True, nullable=False)
    entity_id = db.Column(db.Integer, db.ForeignKey('entity.id'), nullable=False)
    entity = db.relationship('Entity')
    expense_date = db.Column(db.Date, nullable=False)
    payment_due_date = db.Column(db.Date, nullable=False)
    status_id = db.Column(db.Integer, db.ForeignKey('expense_status.id'), nullable=False)
    status = db.relationship('ExpenseStatus')
    total_amount = db.Column(db.Numeric(14, 2), default=0)
    notes = db.Column(db.Text)
    journal_entry_id = db.Column(db.Integer, db.ForeignKey('journal_entry.id'))
    journal_entry = db.relationship('JournalEntry')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_by = db.relationship('User')
    
    def __repr__(self):
        return f'<Expense {self.expense_number}>'

# Expense Line Items
class ExpenseItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    expense_id = db.Column(db.Integer, db.ForeignKey('expense.id'), nullable=False)
    expense = db.relationship('Expense', backref='items')
    description = db.Column(db.String(255), nullable=False)
    quantity = db.Column(db.Numeric(10, 2), default=1)
    unit_price = db.Column(db.Numeric(14, 2), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    account = db.relationship('Account')
    
    @property
    def line_total(self):
        return self.quantity * self.unit_price
    
    def __repr__(self):
        return f'<ExpenseItem {self.id} - {self.description}>'

# Budget Period Types
class BudgetPeriodType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    
    # Constants
    MONTHLY = 'Monthly'
    QUARTERLY = 'Quarterly'
    ANNUAL = 'Annual'
    CUSTOM = 'Custom'
    
    def __repr__(self):
        return f'<BudgetPeriodType {self.name}>'

# Budget
class Budget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    year = db.Column(db.Integer, nullable=False)
    period_type_id = db.Column(db.Integer, db.ForeignKey('budget_period_type.id'), nullable=False)
    period_type = db.relationship('BudgetPeriodType')
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_by = db.relationship('User')
    
    def __repr__(self):
        return f'<Budget {self.name} ({self.year})>'

# Budget Line Items
class BudgetItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    budget_id = db.Column(db.Integer, db.ForeignKey('budget.id'), nullable=False)
    budget = db.relationship('Budget', backref='items')
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    account = db.relationship('Account')
    period = db.Column(db.Integer, nullable=False)  # Month (1-12), Quarter (1-4), or custom period number
    amount = db.Column(db.Numeric(14, 2), nullable=False)
    notes = db.Column(db.Text)
    
    def __repr__(self):
        return f'<BudgetItem {self.id} - {self.account.name} - Period {self.period}>'

# Budget Versions (for revision tracking)
class BudgetVersion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    budget_id = db.Column(db.Integer, db.ForeignKey('budget.id'), nullable=False)
    budget = db.relationship('Budget')
    version_number = db.Column(db.Integer, nullable=False)
    version_name = db.Column(db.String(100), nullable=False)
    is_active = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_by = db.relationship('User')
    notes = db.Column(db.Text)
    
    def __repr__(self):
        return f'<BudgetVersion {self.version_number} - {self.budget.name}>'

# Financial Forecasts
class Forecast(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    period_type_id = db.Column(db.Integer, db.ForeignKey('budget_period_type.id'), nullable=False)
    period_type = db.relationship('BudgetPeriodType')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_by = db.relationship('User')
    
    def __repr__(self):
        return f'<Forecast {self.name}>'

# Forecast Items
class ForecastItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    forecast_id = db.Column(db.Integer, db.ForeignKey('forecast.id'), nullable=False)
    forecast = db.relationship('Forecast', backref='items')
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    account = db.relationship('Account')
    period = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Numeric(14, 2), nullable=False)
    growth_factor = db.Column(db.Numeric(10, 4), default=0)  # For percentage-based forecasting
    notes = db.Column(db.Text)
    
    def __repr__(self):
        return f'<ForecastItem {self.id} - {self.account.name} - Period {self.period}>'

# Product Category
class ProductCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_by = db.relationship('User')
    
    def __repr__(self):
        return f'<ProductCategory {self.name}>'

# UOM - Unit of Measure
class UnitOfMeasure(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    abbreviation = db.Column(db.String(10), nullable=False, unique=True)
    
    def __repr__(self):
        return f'<UnitOfMeasure {self.abbreviation}>'

# Products/Inventory Items
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    category_id = db.Column(db.Integer, db.ForeignKey('product_category.id'))
    category = db.relationship('ProductCategory')
    uom_id = db.Column(db.Integer, db.ForeignKey('unit_of_measure.id'), nullable=False)
    uom = db.relationship('UnitOfMeasure')
    cost_price = db.Column(db.Numeric(14, 2), default=0)
    sales_price = db.Column(db.Numeric(14, 2), default=0)
    reorder_level = db.Column(db.Numeric(10, 2), default=0)
    preferred_vendor_id = db.Column(db.Integer, db.ForeignKey('entity.id'))
    preferred_vendor = db.relationship('Entity')
    asset_account_id = db.Column(db.Integer, db.ForeignKey('account.id'))
    asset_account = db.relationship('Account', foreign_keys=[asset_account_id])
    expense_account_id = db.Column(db.Integer, db.ForeignKey('account.id'))
    expense_account = db.relationship('Account', foreign_keys=[expense_account_id])
    revenue_account_id = db.Column(db.Integer, db.ForeignKey('account.id'))
    revenue_account = db.relationship('Account', foreign_keys=[revenue_account_id])
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_by = db.relationship('User')
    
    @property
    def current_stock(self):
        """Get current stock quantity from inventory transactions"""
        from sqlalchemy import func
        
        # Calculate total quantity from transactions
        in_quantity = db.session.query(
            func.sum(InventoryTransaction.quantity)
        ).filter(
            InventoryTransaction.product_id == self.id,
            InventoryTransaction.transaction_type == 'IN'
        ).scalar() or 0
        
        out_quantity = db.session.query(
            func.sum(InventoryTransaction.quantity)
        ).filter(
            InventoryTransaction.product_id == self.id,
            InventoryTransaction.transaction_type == 'OUT'
        ).scalar() or 0
        
        return in_quantity - out_quantity
    
    def __repr__(self):
        return f'<Product {self.sku} - {self.name}>'

# Inventory Transaction Types
class InventoryTransactionType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    
    # Constants
    PURCHASE = 'Purchase'
    SALE = 'Sale'
    ADJUSTMENT = 'Adjustment'
    RETURN_IN = 'Return In'
    RETURN_OUT = 'Return Out'
    TRANSFER = 'Transfer'
    
    def __repr__(self):
        return f'<InventoryTransactionType {self.name}>'

# Inventory Transactions
class InventoryTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    transaction_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    transaction_type = db.Column(db.String(5), nullable=False)  # IN or OUT
    transaction_type_id = db.Column(db.Integer, db.ForeignKey('inventory_transaction_type.id'))
    transaction_type_obj = db.relationship('InventoryTransactionType')
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    product = db.relationship('Product')
    quantity = db.Column(db.Numeric(10, 2), nullable=False)
    unit_price = db.Column(db.Numeric(14, 2))
    location = db.Column(db.String(100))
    reference_type = db.Column(db.String(50))  # Invoice, PO, Adjustment, etc.
    reference_id = db.Column(db.Integer)  # ID of the reference document
    notes = db.Column(db.Text)
    journal_entry_id = db.Column(db.Integer, db.ForeignKey('journal_entry.id'))
    journal_entry = db.relationship('JournalEntry')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_by = db.relationship('User')
    
    def __repr__(self):
        return f'<InventoryTransaction {self.id} - {self.product.name} ({self.quantity})>'

#
# Fixed Asset Management Models
#

# Asset Category
class AssetCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.String(255))
    depreciation_method = db.Column(db.String(50))  # straight-line, declining-balance, etc.
    useful_life_years = db.Column(db.Integer)  # Default useful life in years for this category
    asset_account_id = db.Column(db.Integer, db.ForeignKey('account.id'))
    asset_account = db.relationship('Account', foreign_keys=[asset_account_id])
    depreciation_account_id = db.Column(db.Integer, db.ForeignKey('account.id'))
    depreciation_account = db.relationship('Account', foreign_keys=[depreciation_account_id])
    accumulated_depreciation_account_id = db.Column(db.Integer, db.ForeignKey('account.id'))
    accumulated_depreciation_account = db.relationship('Account', foreign_keys=[accumulated_depreciation_account_id])
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_by = db.relationship('User')
    
    def __repr__(self):
        return f'<AssetCategory {self.name}>'

# Asset Location
class AssetLocation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.String(255))
    address = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_by = db.relationship('User')
    
    def __repr__(self):
        return f'<AssetLocation {self.name}>'

# Asset Status
class AssetStatus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    
    # Constants
    ACTIVE = 'Active'
    DISPOSED = 'Disposed'
    SOLD = 'Sold'
    UNDER_MAINTENANCE = 'Under Maintenance'
    EXPIRED = 'Expired'
    
    def __repr__(self):
        return f'<AssetStatus {self.name}>'

# Asset Condition
class AssetCondition(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(255))
    
    # Constants
    EXCELLENT = 'Excellent'
    GOOD = 'Good'
    FAIR = 'Fair'
    POOR = 'Poor'
    
    def __repr__(self):
        return f'<AssetCondition {self.name}>'

# Fixed Asset
class FixedAsset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    asset_number = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    category_id = db.Column(db.Integer, db.ForeignKey('asset_category.id'), nullable=False)
    category = db.relationship('AssetCategory')
    acquisition_date = db.Column(db.Date, nullable=False)
    purchase_cost = db.Column(db.Numeric(14, 2), nullable=False)
    salvage_value = db.Column(db.Numeric(14, 2), default=0)
    useful_life_years = db.Column(db.Integer, nullable=False)  # In years
    depreciation_method = db.Column(db.String(50), nullable=False)  # straight-line, declining-balance, etc.
    last_depreciation_date = db.Column(db.Date)
    current_value = db.Column(db.Numeric(14, 2))  # Book value after depreciation
    location_id = db.Column(db.Integer, db.ForeignKey('asset_location.id'))
    location = db.relationship('AssetLocation')
    status_id = db.Column(db.Integer, db.ForeignKey('asset_status.id'), nullable=False)
    status = db.relationship('AssetStatus')
    condition_id = db.Column(db.Integer, db.ForeignKey('asset_condition.id'))
    condition = db.relationship('AssetCondition')
    vendor_id = db.Column(db.Integer, db.ForeignKey('entity.id'))
    vendor = db.relationship('Entity')
    serial_number = db.Column(db.String(100))
    warranty_expiry_date = db.Column(db.Date)
    notes = db.Column(db.Text)
    is_fully_depreciated = db.Column(db.Boolean, default=False)
    image_url = db.Column(db.String(255))
    acquisition_journal_entry_id = db.Column(db.Integer, db.ForeignKey('journal_entry.id'))
    acquisition_journal_entry = db.relationship('JournalEntry', foreign_keys=[acquisition_journal_entry_id])
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_by = db.relationship('User')
    
    # Relationships
    depreciation_entries = db.relationship('AssetDepreciation', back_populates='asset')
    maintenance_records = db.relationship('AssetMaintenance', back_populates='asset')
    
    def calculate_monthly_depreciation(self):
        """Calculate the monthly depreciation amount"""
        depreciable_cost = float(self.purchase_cost) - float(self.salvage_value)
        
        if self.depreciation_method == 'straight-line':
            # Straight-line depreciation
            total_months = self.useful_life_years * 12
            return depreciable_cost / total_months if total_months > 0 else 0
        
        elif self.depreciation_method == 'declining-balance':
            # Double declining balance depreciation
            annual_rate = 2 / self.useful_life_years if self.useful_life_years > 0 else 0
            monthly_rate = annual_rate / 12
            
            # Get remaining book value from most recent depreciation
            book_value = float(self.current_value or self.purchase_cost)
            return book_value * monthly_rate
        
        return 0
    
    def calculate_depreciation_to_date(self, target_date=None):
        """Calculate the total depreciation up to a given date"""
        if not target_date:
            target_date = date.today()
        
        # If asset is not acquired yet or already fully depreciated
        if not self.acquisition_date or self.is_fully_depreciated:
            return 0
        
        # Calculate months in service
        start_date = self.acquisition_date
        months_in_service = (
            (target_date.year - start_date.year) * 12 + 
            (target_date.month - start_date.month)
        )
        
        # Calculate total depreciation
        depreciable_cost = float(self.purchase_cost) - float(self.salvage_value)
        
        if self.depreciation_method == 'straight-line':
            # Straight-line depreciation
            total_months = self.useful_life_years * 12
            monthly_depreciation = depreciable_cost / total_months if total_months > 0 else 0
            
            # Cap at total depreciable amount
            total_depreciation = min(monthly_depreciation * months_in_service, depreciable_cost)
            return total_depreciation
        
        elif self.depreciation_method == 'declining-balance':
            # This is more complex and requires iterative calculation
            # Get all recorded depreciation entries
            recorded_depreciation = sum(float(entry.amount) for entry in self.depreciation_entries)
            return recorded_depreciation
        
        return 0
    
    def get_current_book_value(self):
        """Calculate the current book value of the asset"""
        total_depreciation = self.calculate_depreciation_to_date()
        return float(self.purchase_cost) - total_depreciation
    
    def get_remaining_useful_life(self):
        """Calculate the remaining useful life in months"""
        if not self.acquisition_date or self.is_fully_depreciated:
            return 0
        
        total_months = self.useful_life_years * 12
        months_used = (
            (date.today().year - self.acquisition_date.year) * 12 + 
            (date.today().month - self.acquisition_date.month)
        )
        
        remaining = total_months - months_used
        return max(0, remaining)
    
    def __repr__(self):
        return f'<FixedAsset {self.asset_number} - {self.name}>'

# Asset Depreciation Records
class AssetDepreciation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('fixed_asset.id'), nullable=False)
    asset = db.relationship('FixedAsset', back_populates='depreciation_entries')
    date = db.Column(db.Date, nullable=False)
    amount = db.Column(db.Numeric(14, 2), nullable=False)
    period_start = db.Column(db.Date, nullable=False)
    period_end = db.Column(db.Date, nullable=False)
    book_value_before = db.Column(db.Numeric(14, 2), nullable=False)
    book_value_after = db.Column(db.Numeric(14, 2), nullable=False)
    journal_entry_id = db.Column(db.Integer, db.ForeignKey('journal_entry.id'))
    journal_entry = db.relationship('JournalEntry')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_by = db.relationship('User')
    
    def __repr__(self):
        return f'<AssetDepreciation {self.asset.name} - {self.date} - ${self.amount}>'

# Asset Maintenance Type
class MaintenanceType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.String(255))
    
    # Constants
    PREVENTIVE = 'Preventive'
    CORRECTIVE = 'Corrective'
    INSPECTION = 'Inspection'
    UPGRADE = 'Upgrade'
    
    def __repr__(self):
        return f'<MaintenanceType {self.name}>'

# Asset Maintenance Records
class AssetMaintenance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('fixed_asset.id'), nullable=False)
    asset = db.relationship('FixedAsset', back_populates='maintenance_records')
    maintenance_type_id = db.Column(db.Integer, db.ForeignKey('maintenance_type.id'), nullable=False)
    maintenance_type = db.relationship('MaintenanceType')
    date = db.Column(db.Date, nullable=False)
    cost = db.Column(db.Numeric(14, 2), nullable=False)
    provider = db.Column(db.String(100))
    description = db.Column(db.Text, nullable=False)
    maintenance_notes = db.Column(db.Text)
    next_maintenance_date = db.Column(db.Date)
    expense_account_id = db.Column(db.Integer, db.ForeignKey('account.id'))
    expense_account = db.relationship('Account')
    journal_entry_id = db.Column(db.Integer, db.ForeignKey('journal_entry.id'))
    journal_entry = db.relationship('JournalEntry')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_by = db.relationship('User')
    
    def __repr__(self):
        return f'<AssetMaintenance {self.asset.name} - {self.date}>'

# Asset Disposal Records
class AssetDisposal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('fixed_asset.id'), nullable=False)
    asset = db.relationship('FixedAsset')
    disposal_date = db.Column(db.Date, nullable=False)
    disposal_type = db.Column(db.String(50), nullable=False)  # Sold, Scrapped, Donated, etc.
    disposal_amount = db.Column(db.Numeric(14, 2), default=0)  # Sale amount if sold
    buyer_id = db.Column(db.Integer, db.ForeignKey('entity.id'))
    buyer = db.relationship('Entity')
    book_value_at_disposal = db.Column(db.Numeric(14, 2), nullable=False)
    gain_loss_amount = db.Column(db.Numeric(14, 2), nullable=False)
    reason = db.Column(db.Text)
    notes = db.Column(db.Text)
    journal_entry_id = db.Column(db.Integer, db.ForeignKey('journal_entry.id'))
    journal_entry = db.relationship('JournalEntry')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_by = db.relationship('User')
    
    def __repr__(self):
        return f'<AssetDisposal {self.asset.name} - {self.disposal_date}>'

# Asset Transfer Records
class AssetTransfer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('fixed_asset.id'), nullable=False)
    asset = db.relationship('FixedAsset')
    transfer_date = db.Column(db.Date, nullable=False)
    from_location_id = db.Column(db.Integer, db.ForeignKey('asset_location.id'), nullable=False)
    from_location = db.relationship('AssetLocation', foreign_keys=[from_location_id])
    to_location_id = db.Column(db.Integer, db.ForeignKey('asset_location.id'), nullable=False)
    to_location = db.relationship('AssetLocation', foreign_keys=[to_location_id])
    reason = db.Column(db.Text)
    transfer_notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_by = db.relationship('User')
    
    def __repr__(self):
        return f'<AssetTransfer {self.asset.name} - {self.transfer_date}>'

# Asset Document/Attachment Records
class AssetDocument(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('fixed_asset.id'), nullable=False)
    asset = db.relationship('FixedAsset')
    document_type = db.Column(db.String(50), nullable=False)  # Invoice, Warranty, Manual, etc.
    file_name = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer)  # In bytes
    upload_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    description = db.Column(db.String(255))
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_by = db.relationship('User')
    
    def __repr__(self):
        return f'<AssetDocument {self.asset.name} - {self.document_type}>'

# Warehouse Locations
class Warehouse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    address = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_by = db.relationship('User')
    
    def __repr__(self):
        return f'<Warehouse {self.code} - {self.name}>'

# Sequence table for generating sequential numbers
class Sequence(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.Integer, default=0)
    
    def __repr__(self):
        return f'<Sequence {self.name}: {self.value}>'

# Purchase Order Status
class PurchaseOrderStatus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    
    # Constants
    DRAFT = 'Draft'
    SUBMITTED = 'Submitted'
    APPROVED = 'Approved'
    PARTIALLY_RECEIVED = 'Partially Received'
    RECEIVED = 'Received'
    CANCELLED = 'Cancelled'
    
    def __repr__(self):
        return f'<PurchaseOrderStatus {self.name}>'

# Purchase Orders
class PurchaseOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    po_number = db.Column(db.String(20), unique=True, nullable=False)
    vendor_id = db.Column(db.Integer, db.ForeignKey('entity.id'), nullable=False)
    vendor = db.relationship('Entity')
    order_date = db.Column(db.Date, nullable=False)
    expected_delivery_date = db.Column(db.Date)
    status_id = db.Column(db.Integer, db.ForeignKey('purchase_order_status.id'), nullable=False)
    status = db.relationship('PurchaseOrderStatus')
    shipping_address = db.Column(db.String(255))
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouse.id'))
    warehouse = db.relationship('Warehouse')
    total_amount = db.Column(db.Numeric(14, 2), default=0)
    notes = db.Column(db.Text)
    journal_entry_id = db.Column(db.Integer, db.ForeignKey('journal_entry.id'))
    journal_entry = db.relationship('JournalEntry')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_by = db.relationship('User')
    
    def __repr__(self):
        return f'<PurchaseOrder {self.po_number}>'

# Purchase Order Items
class PurchaseOrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    po_id = db.Column(db.Integer, db.ForeignKey('purchase_order.id'), nullable=False)
    po = db.relationship('PurchaseOrder', backref='items')
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    product = db.relationship('Product')
    description = db.Column(db.String(255))
    quantity_ordered = db.Column(db.Numeric(10, 2), nullable=False)
    quantity_received = db.Column(db.Numeric(10, 2), default=0)
    unit_price = db.Column(db.Numeric(14, 2), nullable=False)
    tax_rate = db.Column(db.Numeric(5, 2), default=0)
    
    @property
    def line_total(self):
        return self.quantity_ordered * self.unit_price
    
    def __repr__(self):
        return f'<PurchaseOrderItem {self.id} - {self.product.name}>'

# Bank Reconciliation Models
class BankAccount(db.Model):
    """Model for bank accounts that can be reconciled"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    account_number = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(255))
    gl_account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    currency = db.Column(db.String(3), default="USD")
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    gl_account = db.relationship('Account', backref='bank_accounts')
    statements = db.relationship('BankStatement', backref='bank_account', lazy=True, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<BankAccount {self.name}>"

class BankStatement(db.Model):
    """Model for bank statements"""
    id = db.Column(db.Integer, primary_key=True)
    bank_account_id = db.Column(db.Integer, db.ForeignKey('bank_account.id'), nullable=False)
    statement_date = db.Column(db.Date, nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    beginning_balance = db.Column(db.Numeric(precision=15, scale=2), nullable=False)
    ending_balance = db.Column(db.Numeric(precision=15, scale=2), nullable=False)
    is_reconciled = db.Column(db.Boolean, default=False)
    reconciled_date = db.Column(db.Date)
    notes = db.Column(db.Text)
    
    # Relationships
    transactions = db.relationship('BankTransaction', backref='statement', lazy=True, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<BankStatement {self.statement_date}>"

class BankTransaction(db.Model):
    """Model for individual bank transactions from a statement"""
    id = db.Column(db.Integer, primary_key=True)
    statement_id = db.Column(db.Integer, db.ForeignKey('bank_statement.id'), nullable=False)
    transaction_date = db.Column(db.Date, nullable=False)
    description = db.Column(db.String(255), nullable=False)
    reference = db.Column(db.String(100))
    amount = db.Column(db.Numeric(precision=15, scale=2), nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)  # 'debit' or 'credit'
    is_reconciled = db.Column(db.Boolean, default=False)
    reconciled_date = db.Column(db.Date)
    gl_entry_id = db.Column(db.Integer, db.ForeignKey('journal_entry.id'))
    
    # Relationships
    gl_entry = db.relationship('JournalEntry', backref='bank_transactions')
    
    def __repr__(self):
        return f"<BankTransaction {self.description} {self.amount}>"

class ReconciliationRule(db.Model):
    """Model for automatic reconciliation rules"""
    id = db.Column(db.Integer, primary_key=True)
    bank_account_id = db.Column(db.Integer, db.ForeignKey('bank_account.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    match_pattern = db.Column(db.String(255), nullable=False)
    gl_account_id = db.Column(db.Integer, db.ForeignKey('account.id'))
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    bank_account = db.relationship('BankAccount', backref='rules')
    gl_account = db.relationship('Account', backref='reconciliation_rules')
    
    def __repr__(self):
        return f"<ReconciliationRule {self.name}>"

# Project Status
class ProjectStatus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    
    # Constants
    PLANNED = 'Planned'
    IN_PROGRESS = 'In Progress'
    ON_HOLD = 'On Hold'
    COMPLETED = 'Completed'
    CANCELLED = 'Cancelled'
    
    def __repr__(self):
        return f'<ProjectStatus {self.name}>'

# Project
class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    entity_id = db.Column(db.Integer, db.ForeignKey('entity.id'))  # Client/Customer
    entity = db.relationship('Entity')
    status_id = db.Column(db.Integer, db.ForeignKey('project_status.id'), nullable=False)
    status = db.relationship('ProjectStatus')
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date)
    estimated_hours = db.Column(db.Numeric(10, 2))
    estimated_cost = db.Column(db.Numeric(14, 2))
    budget_amount = db.Column(db.Numeric(14, 2))
    is_fixed_price = db.Column(db.Boolean, default=False)
    fixed_price_amount = db.Column(db.Numeric(14, 2))
    is_billable = db.Column(db.Boolean, default=True)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    manager_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    manager = db.relationship('User', foreign_keys=[manager_id])
    
    @hybrid_property
    def actual_hours(self):
        """Calculate the total hours logged to the project"""
        from sqlalchemy import func
        hours = db.session.query(func.sum(TimeEntry.hours)).filter(
            TimeEntry.project_id == self.id,
            TimeEntry.is_approved == True
        ).scalar() or 0
        return hours
    
    @hybrid_property
    def actual_cost(self):
        """Calculate the total cost of the project"""
        from sqlalchemy import func
        # Cost from time entries
        time_cost = db.session.query(func.sum(TimeEntry.cost_amount)).filter(
            TimeEntry.project_id == self.id,
            TimeEntry.is_approved == True
        ).scalar() or Decimal('0.00')
        
        # Cost from expenses
        expense_cost = db.session.query(func.sum(ProjectExpense.amount)).filter(
            ProjectExpense.project_id == self.id,
            ProjectExpense.is_approved == True
        ).scalar() or Decimal('0.00')
        
        return time_cost + expense_cost
    
    @hybrid_property
    def budget_variance(self):
        """Calculate the variance between budget and actual cost"""
        if not self.budget_amount:
            return None
        return self.budget_amount - self.actual_cost
    
    @hybrid_property
    def budget_variance_percentage(self):
        """Calculate the percentage variance between budget and actual cost"""
        if not self.budget_amount or self.budget_amount == 0:
            return None
        return (self.budget_variance / self.budget_amount) * 100
    
    @hybrid_property
    def completion_percentage(self):
        """Calculate the completion percentage based on task status"""
        if not self.tasks:
            return 0
        
        completed_tasks = sum(1 for task in self.tasks if task.is_completed)
        return (completed_tasks / len(self.tasks)) * 100
    
    def __repr__(self):
        return f'<Project {self.project_code} - {self.name}>'

# Job Task
class JobTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    project = db.relationship('Project', backref='tasks')
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    estimated_hours = db.Column(db.Numeric(10, 2))
    estimated_cost = db.Column(db.Numeric(14, 2))
    is_billable = db.Column(db.Boolean, default=True)
    billing_rate = db.Column(db.Numeric(14, 2))
    is_completed = db.Column(db.Boolean, default=False)
    completion_date = db.Column(db.Date)
    parent_task_id = db.Column(db.Integer, db.ForeignKey('job_task.id'))
    parent_task = db.relationship('JobTask', remote_side=[id], backref='subtasks')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    assignee_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    assignee = db.relationship('User', foreign_keys=[assignee_id])
    
    @hybrid_property
    def actual_hours(self):
        """Calculate the total hours logged to the task"""
        from sqlalchemy import func
        hours = db.session.query(func.sum(TimeEntry.hours)).filter(
            TimeEntry.task_id == self.id,
            TimeEntry.is_approved == True
        ).scalar() or 0
        return hours
    
    def __repr__(self):
        return f'<JobTask {self.id} - {self.name}>'

# Time Entry
class TimeEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    project = db.relationship('Project', backref='time_entries')
    task_id = db.Column(db.Integer, db.ForeignKey('job_task.id'))
    task = db.relationship('JobTask', backref='time_entries')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', foreign_keys=[user_id])
    date = db.Column(db.Date, nullable=False)
    hours = db.Column(db.Numeric(5, 2), nullable=False)
    description = db.Column(db.Text)
    is_billable = db.Column(db.Boolean, default=True)
    billing_rate = db.Column(db.Numeric(14, 2))
    cost_rate = db.Column(db.Numeric(14, 2))
    cost_amount = db.Column(db.Numeric(14, 2))
    invoice_item_id = db.Column(db.Integer, db.ForeignKey('invoice_item.id'))
    invoice_item = db.relationship('InvoiceItem')
    is_approved = db.Column(db.Boolean, default=False)
    approved_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    approved_by = db.relationship('User', foreign_keys=[approved_by_id])
    approved_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    @hybrid_property
    def billable_amount(self):
        """Calculate the billable amount for this time entry"""
        if not self.is_billable or not self.billing_rate:
            return Decimal('0.00')
        return self.hours * self.billing_rate
    
    def __repr__(self):
        return f'<TimeEntry {self.id} - {self.user.username} - {self.date}>'

# Project Expense
class ProjectExpense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    project = db.relationship('Project', backref='expenses')
    task_id = db.Column(db.Integer, db.ForeignKey('job_task.id'))
    task = db.relationship('JobTask', backref='expenses')
    expense_id = db.Column(db.Integer, db.ForeignKey('expense.id'))
    expense = db.relationship('Expense')
    date = db.Column(db.Date, nullable=False)
    description = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Numeric(14, 2), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    account = db.relationship('Account')
    is_billable = db.Column(db.Boolean, default=True)
    markup_percentage = db.Column(db.Numeric(5, 2), default=0)
    invoice_item_id = db.Column(db.Integer, db.ForeignKey('invoice_item.id'))
    invoice_item = db.relationship('InvoiceItem')
    is_approved = db.Column(db.Boolean, default=False)
    approved_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    approved_by = db.relationship('User', foreign_keys=[approved_by_id])
    approved_at = db.Column(db.DateTime)
    receipt_file = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    
    @hybrid_property
    def billable_amount(self):
        """Calculate the billable amount including markup"""
        if not self.is_billable:
            return Decimal('0.00')
        markup = Decimal('1.00') + (self.markup_percentage or Decimal('0.00')) / 100
        return self.amount * markup
    
    def __repr__(self):
        return f'<ProjectExpense {self.id} - {self.description}>'
