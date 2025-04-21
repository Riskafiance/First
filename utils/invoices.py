from datetime import datetime
from app import db
from models import Invoice

def generate_invoice_number():
    """Generate a unique invoice number"""
    # Format: INV-YYYYMMDD-XXX where XXX is a sequential number
    today = datetime.now().date()
    date_part = today.strftime("%Y%m%d")
    
    # Get the latest invoice for today
    latest_invoice = db.session.query(Invoice).filter(
        Invoice.invoice_number.like(f"INV-{date_part}-%")
    ).order_by(
        Invoice.invoice_number.desc()
    ).first()
    
    if latest_invoice:
        # Extract the sequence number and increment
        seq_part = latest_invoice.invoice_number.split('-')[2]
        new_seq = int(seq_part) + 1
    else:
        new_seq = 1
    
    return f"INV-{date_part}-{new_seq:03d}"