from datetime import datetime
from app import db
from models import Expense

def generate_expense_number():
    """Generate a unique expense number"""
    # Format: EXP-YYYYMMDD-XXX where XXX is a sequential number
    today = datetime.now().date()
    date_part = today.strftime("%Y%m%d")
    
    # Get the latest expense for today
    latest_expense = db.session.query(Expense).filter(
        Expense.expense_number.like(f"EXP-{date_part}-%")
    ).order_by(
        Expense.expense_number.desc()
    ).first()
    
    if latest_expense:
        # Extract the sequence number and increment
        seq_part = latest_expense.expense_number.split('-')[2]
        new_seq = int(seq_part) + 1
    else:
        new_seq = 1
    
    return f"EXP-{date_part}-{new_seq:03d}"