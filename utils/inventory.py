import random
import string
from datetime import datetime
from app import db
from models import (
    Product, InventoryTransaction, PurchaseOrder
)

def generate_product_sku():
    """Generate a unique product SKU"""
    # Format: PRD-XXXXXX where X is alphanumeric
    
    # Generate random part
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    sku = f"PRD-{random_part}"
    
    # Check if it exists already
    while db.session.query(Product).filter_by(sku=sku).first():
        random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        sku = f"PRD-{random_part}"
    
    return sku

def generate_po_number():
    """Generate a unique purchase order number"""
    # Format: PO-YYYYMMDD-XXX where XXX is a sequential number
    today = datetime.now().date()
    date_part = today.strftime("%Y%m%d")
    
    # Get the latest PO for today
    latest_po = db.session.query(PurchaseOrder).filter(
        PurchaseOrder.po_number.like(f"PO-{date_part}-%")
    ).order_by(
        PurchaseOrder.po_number.desc()
    ).first()
    
    if latest_po:
        # Extract the sequence number and increment
        seq_part = latest_po.po_number.split('-')[2]
        new_seq = int(seq_part) + 1
    else:
        new_seq = 1
    
    return f"PO-{date_part}-{new_seq:03d}"

def record_inventory_transaction(product_id, quantity, transaction_type, transaction_type_id=None, 
                                unit_price=None, location=None, reference_type=None, reference_id=None, 
                                notes=None, journal_entry_id=None, created_by_id=None):
    """Record an inventory transaction"""
    # Create inventory transaction
    transaction = InventoryTransaction(
        transaction_date=datetime.now(),
        transaction_type=transaction_type,  # 'IN' or 'OUT'
        transaction_type_id=transaction_type_id,
        product_id=product_id,
        quantity=quantity,
        unit_price=unit_price,
        location=location,
        reference_type=reference_type,
        reference_id=reference_id,
        notes=notes,
        journal_entry_id=journal_entry_id,
        created_by_id=created_by_id
    )
    
    db.session.add(transaction)
    db.session.commit()
    
    return transaction

def get_inventory_value():
    """Calculate the total value of inventory"""
    # Get all products
    products = db.session.query(Product).filter_by(is_active=True).all()
    
    total_value = 0
    
    for product in products:
        # Get current stock quantity
        current_stock = product.current_stock
        
        # Calculate value using cost price
        if current_stock > 0:
            total_value += float(current_stock) * float(product.cost_price)
    
    return total_value

def get_low_stock_products():
    """Get products that are below their reorder level"""
    # Get all active products
    products = db.session.query(Product).filter_by(is_active=True).all()
    
    low_stock = []
    
    for product in products:
        current_stock = product.current_stock
        
        if current_stock <= product.reorder_level:
            low_stock.append({
                'id': product.id,
                'sku': product.sku,
                'name': product.name,
                'current_stock': float(current_stock),
                'reorder_level': float(product.reorder_level),
                'uom': product.uom.abbreviation
            })
    
    return low_stock