from datetime import datetime
import pandas as pd
from app import db
from models import JournalEntry, JournalItem, Account, User

def export_journal_entries_to_csv(start_date=None, end_date=None):
    """Export journal entries to a pandas DataFrame and then to CSV"""
    if not start_date:
        start_date = datetime.now().date().replace(day=1)  # First day of current month
    if not end_date:
        end_date = datetime.now().date()  # Current date
    
    # Query database for journal entries in date range
    entries = db.session.query(
        JournalEntry.id, 
        JournalEntry.entry_date, 
        JournalEntry.reference, 
        JournalEntry.description,
        JournalEntry.is_posted,
        User.username.label('created_by')
    ).join(
        User, JournalEntry.created_by_id == User.id
    ).filter(
        JournalEntry.entry_date.between(start_date, end_date)
    ).order_by(
        JournalEntry.entry_date.desc()
    ).all()
    
    # Convert to DataFrame
    entries_df = pd.DataFrame([
        {
            'id': entry.id,
            'entry_date': entry.entry_date,
            'reference': entry.reference,
            'description': entry.description,
            'status': 'Posted' if entry.is_posted else 'Draft',
            'created_by': entry.created_by
        } for entry in entries
    ])
    
    # Get items for each entry
    all_items = []
    for entry in entries:
        items = db.session.query(
            JournalItem.id,
            JournalItem.journal_entry_id,
            Account.code.label('account_code'),
            Account.name.label('account_name'),
            JournalItem.description,
            JournalItem.debit_amount,
            JournalItem.credit_amount
        ).join(
            Account, JournalItem.account_id == Account.id
        ).filter(
            JournalItem.journal_entry_id == entry.id
        ).all()
        
        for item in items:
            all_items.append({
                'journal_entry_id': item.journal_entry_id,
                'account_code': item.account_code,
                'account_name': item.account_name,
                'description': item.description,
                'debit_amount': item.debit_amount,
                'credit_amount': item.credit_amount
            })
    
    items_df = pd.DataFrame(all_items)
    
    return entries_df, items_df