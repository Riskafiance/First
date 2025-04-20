from datetime import datetime
from app import db
from flask_login import UserMixin
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
