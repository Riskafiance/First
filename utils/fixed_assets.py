from datetime import datetime
from decimal import Decimal
from app import db
from models import FixedAsset

def format_currency(amount, symbol='$'):
    """Format a decimal value as currency"""
    if amount is None:
        return f"{symbol}0.00"
    
    if not isinstance(amount, Decimal):
        try:
            amount = Decimal(str(amount))
        except:
            return f"{symbol}0.00"
    
    return f"{symbol}{amount:,.2f}"

def generate_asset_number():
    """Generate a unique asset number"""
    # Format: FA-YYYYMMDD-XXX where XXX is a sequential number
    today = datetime.now().date()
    date_part = today.strftime("%Y%m%d")
    
    # Get the latest asset for today
    latest_asset = db.session.query(FixedAsset).filter(
        FixedAsset.asset_number.like(f"FA-{date_part}-%")
    ).order_by(
        FixedAsset.asset_number.desc()
    ).first()
    
    if latest_asset:
        # Extract the sequence number and increment
        seq_part = latest_asset.asset_number.split('-')[2]
        new_seq = int(seq_part) + 1
    else:
        new_seq = 1
    
    return f"FA-{date_part}-{new_seq:03d}"

def get_next_sequence(prefix, field_name, model_class):
    """Get the next sequence number for a given prefix and model"""
    # Format: PREFIX-XXX where XXX is a sequential number
    
    # Get the latest record with this prefix
    query = db.session.query(model_class).filter(
        getattr(model_class, field_name).like(f"{prefix}-%")
    ).order_by(
        getattr(model_class, field_name).desc()
    )
    
    latest = query.first()
    
    if latest:
        # Extract the sequence number and increment
        field_value = getattr(latest, field_name)
        seq_part = field_value.split('-')[1]
        new_seq = int(seq_part) + 1
    else:
        new_seq = 1
    
    return f"{prefix}-{new_seq:03d}"