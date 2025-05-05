from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from models import Role, BankAccount, BankStatement, BankTransaction, ReconciliationRule, Account, JournalEntry, JournalItem, AccountType
from app import db
from sqlalchemy import desc, func
import datetime
from decimal import Decimal
import csv
import io
from werkzeug.utils import secure_filename
import os
import pandas as pd

# Create blueprint
bank_reconciliation_bp = Blueprint('bank_reconciliation', __name__)


@bank_reconciliation_bp.route('/bank-accounts')
@login_required
def bank_accounts():
    """List all bank accounts"""
    # Check permission
    if not current_user.has_permission(Role.CAN_VIEW):
        flash('You do not have permission to view bank accounts.', 'danger')
        return redirect(url_for('dashboard.index'))

    # Get all bank accounts
    accounts = BankAccount.query.filter_by(is_active=True).all()
    
    return render_template('bank_reconciliation/bank_accounts.html', accounts=accounts)


@bank_reconciliation_bp.route('/bank-accounts/add', methods=['GET', 'POST'])
@login_required
def add_bank_account():
    """Add a new bank account"""
    # Check permission
    if not current_user.has_permission(Role.CAN_CREATE):
        flash('You do not have permission to add bank accounts.', 'danger')
        return redirect(url_for('bank_reconciliation.bank_accounts'))

    # Get all GL accounts that can be linked to bank accounts
    # Typically these would be asset accounts of type "Bank"
    asset_type = AccountType.query.filter_by(name=AccountType.ASSET).first()
    if asset_type:
        gl_accounts = Account.query.filter_by(account_type_id=asset_type.id).all()
    else:
        gl_accounts = []

    if request.method == 'POST':
        # Get form data
        name = request.form.get('name')
        account_number = request.form.get('account_number')
        description = request.form.get('description')
        gl_account_id = request.form.get('gl_account_id')
        currency = request.form.get('currency', 'USD')
        
        # Validate required fields
        if not name or not account_number or not gl_account_id:
            flash('Please fill in all required fields.', 'danger')
            return render_template('bank_reconciliation/add_bank_account.html', gl_accounts=gl_accounts)
        
        # Create new bank account
        bank_account = BankAccount(
            name=name,
            account_number=account_number,
            description=description,
            gl_account_id=gl_account_id,
            currency=currency,
            is_active=True
        )
        
        # Save to database
        db.session.add(bank_account)
        try:
            db.session.commit()
            flash(f'Bank account {name} has been added successfully.', 'success')
            return redirect(url_for('bank_reconciliation.bank_accounts'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding bank account: {str(e)}', 'danger')
    
    return render_template('bank_reconciliation/add_bank_account.html', gl_accounts=gl_accounts)


@bank_reconciliation_bp.route('/bank-accounts/<int:account_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_bank_account(account_id):
    """Edit a bank account"""
    # Check permission
    if not current_user.has_permission(Role.CAN_EDIT):
        flash('You do not have permission to edit bank accounts.', 'danger')
        return redirect(url_for('bank_reconciliation.bank_accounts'))

    # Get the bank account
    bank_account = BankAccount.query.get_or_404(account_id)
    
    # Get all GL accounts that can be linked to bank accounts
    asset_type = AccountType.query.filter_by(name=AccountType.ASSET).first()
    if asset_type:
        gl_accounts = Account.query.filter_by(account_type_id=asset_type.id).all()
    else:
        gl_accounts = []

    if request.method == 'POST':
        # Get form data
        name = request.form.get('name')
        account_number = request.form.get('account_number')
        description = request.form.get('description')
        gl_account_id = request.form.get('gl_account_id')
        currency = request.form.get('currency', 'USD')
        is_active = 'is_active' in request.form
        
        # Validate required fields
        if not name or not account_number or not gl_account_id:
            flash('Please fill in all required fields.', 'danger')
            return render_template('bank_reconciliation/edit_bank_account.html', 
                                account=bank_account, gl_accounts=gl_accounts)
        
        # Update bank account
        bank_account.name = name
        bank_account.account_number = account_number
        bank_account.description = description
        bank_account.gl_account_id = gl_account_id
        bank_account.currency = currency
        bank_account.is_active = is_active
        
        # Save to database
        try:
            db.session.commit()
            flash(f'Bank account {name} has been updated successfully.', 'success')
            return redirect(url_for('bank_reconciliation.bank_accounts'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating bank account: {str(e)}', 'danger')
    
    return render_template('bank_reconciliation/edit_bank_account.html', 
                        account=bank_account, gl_accounts=gl_accounts)


@bank_reconciliation_bp.route('/bank-accounts/<int:account_id>/statements')
@login_required
def statements(account_id):
    """List all statements for a bank account"""
    # Check permission
    if not current_user.has_permission(Role.CAN_VIEW):
        flash('You do not have permission to view bank statements.', 'danger')
        return redirect(url_for('bank_reconciliation.bank_accounts'))

    # Get the bank account
    bank_account = BankAccount.query.get_or_404(account_id)
    
    # Get all statements for this account
    statements = BankStatement.query.filter_by(bank_account_id=account_id).order_by(
        desc(BankStatement.statement_date)
    ).all()
    
    return render_template('bank_reconciliation/statements.html', 
                        account=bank_account, statements=statements)


@bank_reconciliation_bp.route('/bank-accounts/<int:account_id>/statements/add', methods=['GET', 'POST'])
@login_required
def add_statement(account_id):
    """Add a new bank statement"""
    # Check permission
    if not current_user.has_permission(Role.CAN_CREATE):
        flash('You do not have permission to add bank statements.', 'danger')
        return redirect(url_for('bank_reconciliation.statements', account_id=account_id))

    # Get the bank account
    bank_account = BankAccount.query.get_or_404(account_id)
    
    if request.method == 'POST':
        # Get form data
        statement_date = request.form.get('statement_date')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        beginning_balance = request.form.get('beginning_balance')
        ending_balance = request.form.get('ending_balance')
        notes = request.form.get('notes')
        
        # Validate required fields
        if not statement_date or not start_date or not end_date or beginning_balance is None or ending_balance is None:
            flash('Please fill in all required fields.', 'danger')
            return render_template('bank_reconciliation/add_statement.html', account=bank_account)
        
        # Convert dates from string to date objects
        try:
            statement_date = datetime.datetime.strptime(statement_date, '%Y-%m-%d').date()
            start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format. Please use YYYY-MM-DD format.', 'danger')
            return render_template('bank_reconciliation/add_statement.html', account=bank_account)
        
        # Convert balances to Decimal
        try:
            beginning_balance = Decimal(beginning_balance)
            ending_balance = Decimal(ending_balance)
        except:
            flash('Invalid balance format. Please enter a valid number.', 'danger')
            return render_template('bank_reconciliation/add_statement.html', account=bank_account)
        
        # Create new bank statement
        statement = BankStatement(
            bank_account_id=account_id,
            statement_date=statement_date,
            start_date=start_date,
            end_date=end_date,
            beginning_balance=beginning_balance,
            ending_balance=ending_balance,
            notes=notes,
            is_reconciled=False
        )
        
        # Save to database
        db.session.add(statement)
        try:
            db.session.commit()
            flash(f'Bank statement dated {statement_date} has been added successfully.', 'success')
            return redirect(url_for('bank_reconciliation.statements', account_id=account_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding bank statement: {str(e)}', 'danger')
    
    return render_template('bank_reconciliation/add_statement.html', account=bank_account)


@bank_reconciliation_bp.route('/statements/<int:statement_id>/transactions')
@login_required
def transactions(statement_id):
    """List all transactions for a bank statement"""
    # Check permission
    if not current_user.has_permission(Role.CAN_VIEW):
        flash('You do not have permission to view bank transactions.', 'danger')
        return redirect(url_for('dashboard.index'))

    # Get the bank statement
    statement = BankStatement.query.get_or_404(statement_id)
    
    # Get all transactions for this statement
    transactions = BankTransaction.query.filter_by(statement_id=statement_id).order_by(
        BankTransaction.transaction_date
    ).all()
    
    # Calculate the reconciliation status
    reconciled_count = sum(1 for t in transactions if t.is_reconciled)
    total_count = len(transactions)
    
    return render_template('bank_reconciliation/transactions.html', 
                        statement=statement, 
                        transactions=transactions,
                        reconciled_count=reconciled_count,
                        total_count=total_count)


@bank_reconciliation_bp.route('/statements/<int:statement_id>/import-transactions', methods=['GET', 'POST'])
@login_required
def import_transactions(statement_id):
    """Import transactions from a CSV file"""
    # Check permission
    if not current_user.has_permission(Role.CAN_CREATE):
        flash('You do not have permission to import bank transactions.', 'danger')
        return redirect(url_for('bank_reconciliation.transactions', statement_id=statement_id))

    # Get the bank statement
    statement = BankStatement.query.get_or_404(statement_id)
    
    if request.method == 'POST':
        # Check if a file was uploaded
        if 'transaction_file' not in request.files:
            flash('No file selected.', 'danger')
            return redirect(request.url)
            
        file = request.files['transaction_file']
        
        # If user doesn't select a file
        if file.filename == '':
            flash('No file selected.', 'danger')
            return redirect(request.url)
            
        # Get form data for column mapping
        date_col = request.form.get('date_column')
        description_col = request.form.get('description_column')
        amount_col = request.form.get('amount_column')
        reference_col = request.form.get('reference_column')
        
        # Validate required fields
        if not date_col or not description_col or not amount_col:
            flash('Please map all required columns.', 'danger')
            return render_template('bank_reconciliation/import_transactions.html', statement=statement)
        
        # Try to parse the CSV file
        try:
            # Read the file contents
            file_content = file.read()
            
            # Try to decode with UTF-8 first
            try:
                file_content = file_content.decode('utf-8')
            except UnicodeDecodeError:
                # If UTF-8 fails, try other common encodings
                try:
                    file_content = file_content.decode('latin-1')
                except UnicodeDecodeError:
                    try:
                        file_content = file_content.decode('cp1252')
                    except UnicodeDecodeError:
                        flash('Unable to decode the CSV file. Please ensure it is properly encoded.', 'danger')
                        return render_template('bank_reconciliation/import_transactions.html', statement=statement)
            
            csv_file = io.StringIO(file_content)
            
            # Check if the file has content
            if len(file_content.strip()) == 0:
                flash('The uploaded file appears to be empty.', 'danger')
                return render_template('bank_reconciliation/import_transactions.html', statement=statement)
            
            # Try to detect the CSV delimiter
            dialect = csv.Sniffer().sniff(csv_file.read(1024))
            csv_file.seek(0)
            
            # Use pandas to read the CSV file which is more flexible with different formats
            try:
                # Try with auto-detected delimiter
                df = pd.read_csv(csv_file, dialect=dialect)
            except:
                # If that fails, reset and try with comma delimiter
                csv_file.seek(0)
                try:
                    df = pd.read_csv(csv_file)
                except Exception as e:
                    flash(f'Error parsing CSV: {str(e)}. Please check the file format.', 'danger')
                    return render_template('bank_reconciliation/import_transactions.html', statement=statement)
            
            # Get column names for debugging
            column_names = list(df.columns)
            
            # Convert column references to actual column names or indices
            try:
                # Map columns - try to handle both column names and indices
                if date_col.isdigit():
                    date_col_idx = int(date_col) - 1  # Convert to 0-based index
                    if date_col_idx >= len(column_names):
                        flash(f'Date column index {date_col} is out of range. File has {len(column_names)} columns.', 'danger')
                        return render_template('bank_reconciliation/import_transactions.html', statement=statement)
                    date_col = column_names[date_col_idx]
                elif date_col not in df.columns:
                    flash(f'Date column "{date_col}" not found in CSV. Available columns: {", ".join(column_names)}', 'danger')
                    return render_template('bank_reconciliation/import_transactions.html', statement=statement)
                
                if description_col.isdigit():
                    desc_col_idx = int(description_col) - 1
                    if desc_col_idx >= len(column_names):
                        flash(f'Description column index {description_col} is out of range. File has {len(column_names)} columns.', 'danger')
                        return render_template('bank_reconciliation/import_transactions.html', statement=statement)
                    description_col = column_names[desc_col_idx]
                elif description_col not in df.columns:
                    flash(f'Description column "{description_col}" not found in CSV. Available columns: {", ".join(column_names)}', 'danger')
                    return render_template('bank_reconciliation/import_transactions.html', statement=statement)
                
                if amount_col.isdigit():
                    amount_col_idx = int(amount_col) - 1
                    if amount_col_idx >= len(column_names):
                        flash(f'Amount column index {amount_col} is out of range. File has {len(column_names)} columns.', 'danger')
                        return render_template('bank_reconciliation/import_transactions.html', statement=statement)
                    amount_col = column_names[amount_col_idx]
                elif amount_col not in df.columns:
                    flash(f'Amount column "{amount_col}" not found in CSV. Available columns: {", ".join(column_names)}', 'danger')
                    return render_template('bank_reconciliation/import_transactions.html', statement=statement)
                
                if reference_col:
                    if reference_col.isdigit():
                        ref_col_idx = int(reference_col) - 1
                        if ref_col_idx >= len(column_names):
                            flash(f'Reference column index {reference_col} is out of range. File has {len(column_names)} columns.', 'danger')
                            return render_template('bank_reconciliation/import_transactions.html', statement=statement)
                        reference_col = column_names[ref_col_idx]
                    elif reference_col not in df.columns:
                        flash(f'Reference column "{reference_col}" not found in CSV. Available columns: {", ".join(column_names)}', 'danger')
                        return render_template('bank_reconciliation/import_transactions.html', statement=statement)
            except Exception as e:
                flash(f'Error mapping columns: {str(e)}', 'danger')
                return render_template('bank_reconciliation/import_transactions.html', statement=statement)
            
            # Process each row
            transaction_count = 0
            skipped_rows = 0
            errors = []
            
            for index, row in df.iterrows():
                try:
                    # Get values from the row based on column mapping
                    # Use .get method to avoid KeyErrors
                    transaction_date_str = str(row.get(date_col, '')).strip()
                    description = str(row.get(description_col, '')).strip()
                    amount_str = str(row.get(amount_col, '')).strip()
                    reference = str(row.get(reference_col, '')) if reference_col else ''
                    
                    # Skip rows with missing required values
                    if not transaction_date_str or not description or not amount_str:
                        skipped_rows += 1
                        continue
                    
                    # Convert date string to date object
                    # Try different date formats
                    transaction_date = None
                    date_formats = [
                        '%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%m-%d-%Y', '%d-%m-%Y',
                        '%Y/%m/%d', '%m.%d.%Y', '%d.%m.%Y', '%b %d, %Y', '%d %b %Y',
                        '%d-%b-%Y', '%d/%b/%Y', '%B %d, %Y', '%d %B %Y'
                    ]
                    
                    for date_format in date_formats:
                        try:
                            transaction_date = datetime.datetime.strptime(transaction_date_str, date_format).date()
                            break
                        except ValueError:
                            continue
                    
                    if transaction_date is None:
                        # If none of the formats worked, skip this row
                        skipped_rows += 1
                        errors.append(f"Row {index+1}: Unable to parse date format '{transaction_date_str}'")
                        continue
                    
                    # Convert amount string to decimal
                    try:
                        # Remove any currency symbols, commas, parentheses, and handle negative signs
                        # Handle parentheses notation for negative numbers (e.g., $(123.45) -> -123.45)
                        if '(' in amount_str and ')' in amount_str:
                            amount_str = amount_str.replace('(', '-').replace(')', '')
                            
                        amount_str = amount_str.replace('$', '').replace(',', '').replace(' ', '')
                        amount = Decimal(amount_str)
                        
                        # Determine transaction type (debit/credit)
                        transaction_type = 'debit' if amount < 0 else 'credit'
                        
                        # Make amount positive for storage
                        amount = abs(amount)
                    except Exception as e:
                        skipped_rows += 1
                        errors.append(f"Row {index+1}: Invalid amount format '{amount_str}': {str(e)}")
                        continue
                    
                    # Create a new bank transaction
                    transaction = BankTransaction(
                        statement_id=statement_id,
                        transaction_date=transaction_date,
                        description=description,
                        reference=reference,
                        amount=amount,
                        transaction_type=transaction_type,
                        is_reconciled=False
                    )
                    
                    db.session.add(transaction)
                    transaction_count += 1
                except Exception as e:
                    skipped_rows += 1
                    errors.append(f"Row {index+1}: {str(e)}")
            
            # Commit all transactions to the database
            if transaction_count > 0:
                try:
                    db.session.commit()
                    message = f'Successfully imported {transaction_count} transactions.'
                    if skipped_rows > 0:
                        message += f' Skipped {skipped_rows} rows.'
                    flash(message, 'success')
                    
                    # Report any errors in a separate flash message
                    if errors:
                        error_details = '<br>'.join(errors[:5])  # Show first 5 errors
                        if len(errors) > 5:
                            error_details += f'<br>... and {len(errors) - 5} more errors'
                        flash(f'Some rows had errors:<br>{error_details}', 'warning')
                    
                    return redirect(url_for('bank_reconciliation.transactions', statement_id=statement_id))
                except Exception as e:
                    db.session.rollback()
                    flash(f'Error importing transactions: {str(e)}', 'danger')
            else:
                if skipped_rows > 0:
                    flash(f'No valid transactions found. Skipped {skipped_rows} rows due to errors.', 'danger')
                    if errors:
                        error_details = '<br>'.join(errors[:5])  # Show first 5 errors
                        if len(errors) > 5:
                            error_details += f'<br>... and {len(errors) - 5} more errors'
                        flash(f'Error details:<br>{error_details}', 'warning')
                else:
                    flash('No transactions found in the file.', 'warning')
        
        except Exception as e:
            flash(f'Error reading CSV file: {str(e)}', 'danger')
    
    return render_template('bank_reconciliation/import_transactions.html', statement=statement)


@bank_reconciliation_bp.route('/statements/<int:statement_id>/reconcile')
@login_required
def reconcile(statement_id):
    """Reconcile bank statement with GL entries"""
    # Check permission
    if not current_user.has_permission(Role.CAN_EDIT):
        flash('You do not have permission to reconcile bank statements.', 'danger')
        return redirect(url_for('bank_reconciliation.transactions', statement_id=statement_id))

    # Get the bank statement
    statement = BankStatement.query.get_or_404(statement_id)
    
    # Get all unreconciled transactions for this statement
    transactions = BankTransaction.query.filter_by(
        statement_id=statement_id, 
        is_reconciled=False
    ).order_by(BankTransaction.transaction_date).all()
    
    # Get potential matching journal entries
    # We'll look for journal entries that:
    # 1. Are within the statement period
    # 2. Involve the associated GL account
    # 3. Are not already reconciled with other bank transactions
    
    # Get the GL account associated with this bank account
    gl_account_id = statement.bank_account.gl_account_id
    
    # Get journal entries within the date range that involve this GL account
    # We need to join with JournalItem since that's where the account_id is stored
    journal_entries = JournalEntry.query.join(
        JournalItem, JournalEntry.id == JournalItem.journal_entry_id
    ).filter(
        JournalEntry.entry_date >= statement.start_date,
        JournalEntry.entry_date <= statement.end_date,
        JournalItem.account_id == gl_account_id
    ).filter(
        ~JournalEntry.id.in_(
            db.session.query(BankTransaction.gl_entry_id).filter(
                BankTransaction.gl_entry_id.isnot(None)
            )
        )
    ).distinct().all()
    
    return render_template('bank_reconciliation/reconcile.html', 
                        statement=statement, 
                        transactions=transactions,
                        journal_entries=journal_entries)


@bank_reconciliation_bp.route('/transactions/<int:transaction_id>/match/<int:entry_id>', methods=['POST'])
@login_required
def match_transaction(transaction_id, entry_id):
    """Match a bank transaction with a journal entry"""
    # Check permission
    if not current_user.has_permission(Role.CAN_EDIT):
        return jsonify({'success': False, 'message': 'Permission denied'})

    # Get the transaction and journal entry
    transaction = BankTransaction.query.get_or_404(transaction_id)
    journal_entry = JournalEntry.query.get_or_404(entry_id)
    
    # Match the transaction with the journal entry
    transaction.gl_entry_id = entry_id
    transaction.is_reconciled = True
    transaction.reconciled_date = datetime.date.today()
    
    # Save to database
    try:
        db.session.commit()
        return jsonify({
            'success': True, 
            'message': 'Transaction matched successfully.',
            'transaction_id': transaction_id
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error matching transaction: {str(e)}'})


@bank_reconciliation_bp.route('/transactions/<int:transaction_id>/unmatch', methods=['POST'])
@login_required
def unmatch_transaction(transaction_id):
    """Unmatch a bank transaction from a journal entry"""
    # Check permission
    if not current_user.has_permission(Role.CAN_EDIT):
        return jsonify({'success': False, 'message': 'Permission denied'})

    # Get the transaction
    transaction = BankTransaction.query.get_or_404(transaction_id)
    
    # Unmatch the transaction
    transaction.gl_entry_id = None
    transaction.is_reconciled = False
    transaction.reconciled_date = None
    
    # Save to database
    try:
        db.session.commit()
        return jsonify({
            'success': True, 
            'message': 'Transaction unmatched successfully.',
            'transaction_id': transaction_id
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error unmatching transaction: {str(e)}'})


@bank_reconciliation_bp.route('/statements/<int:statement_id>/complete', methods=['POST'])
@login_required
def complete_reconciliation(statement_id):
    """Mark a bank statement as reconciled"""
    # Check permission
    if not current_user.has_permission(Role.CAN_APPROVE):
        flash('You do not have permission to complete reconciliation.', 'danger')
        return redirect(url_for('bank_reconciliation.reconcile', statement_id=statement_id))

    # Get the bank statement
    statement = BankStatement.query.get_or_404(statement_id)
    
    # Check if all transactions are reconciled
    unreconciled_count = BankTransaction.query.filter_by(
        statement_id=statement_id, 
        is_reconciled=False
    ).count()
    
    if unreconciled_count > 0:
        flash(f'Cannot complete reconciliation. There are still {unreconciled_count} unreconciled transactions.', 'danger')
        return redirect(url_for('bank_reconciliation.reconcile', statement_id=statement_id))
    
    # Mark the statement as reconciled
    statement.is_reconciled = True
    statement.reconciled_date = datetime.date.today()
    
    # Save to database
    try:
        db.session.commit()
        flash('Bank statement has been successfully reconciled.', 'success')
        return redirect(url_for('bank_reconciliation.statements', account_id=statement.bank_account_id))
    except Exception as e:
        db.session.rollback()
        flash(f'Error completing reconciliation: {str(e)}', 'danger')
        return redirect(url_for('bank_reconciliation.reconcile', statement_id=statement_id))


@bank_reconciliation_bp.route('/rules')
@login_required
def reconciliation_rules():
    """List all reconciliation rules"""
    # Check permission
    if not current_user.has_permission(Role.CAN_VIEW):
        flash('You do not have permission to view reconciliation rules.', 'danger')
        return redirect(url_for('dashboard.index'))

    # Get all reconciliation rules
    rules = ReconciliationRule.query.filter_by(is_active=True).all()
    
    return render_template('bank_reconciliation/rules.html', rules=rules)


@bank_reconciliation_bp.route('/rules/add', methods=['GET', 'POST'])
@login_required
def add_rule():
    """Add a new reconciliation rule"""
    # Check permission
    if not current_user.has_permission(Role.CAN_CREATE):
        flash('You do not have permission to add reconciliation rules.', 'danger')
        return redirect(url_for('bank_reconciliation.reconciliation_rules'))

    # Get all bank accounts
    bank_accounts = BankAccount.query.filter_by(is_active=True).all()
    
    # Get all GL accounts
    gl_accounts = Account.query.all()
    
    if request.method == 'POST':
        # Get form data
        name = request.form.get('name')
        bank_account_id = request.form.get('bank_account_id')
        match_pattern = request.form.get('match_pattern')
        gl_account_id = request.form.get('gl_account_id')
        
        # Validate required fields
        if not name or not bank_account_id or not match_pattern or not gl_account_id:
            flash('Please fill in all required fields.', 'danger')
            return render_template('bank_reconciliation/add_rule.html', 
                                bank_accounts=bank_accounts, gl_accounts=gl_accounts)
        
        # Create new reconciliation rule
        rule = ReconciliationRule(
            name=name,
            bank_account_id=bank_account_id,
            match_pattern=match_pattern,
            gl_account_id=gl_account_id,
            is_active=True
        )
        
        # Save to database
        db.session.add(rule)
        try:
            db.session.commit()
            flash(f'Reconciliation rule {name} has been added successfully.', 'success')
            return redirect(url_for('bank_reconciliation.reconciliation_rules'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding reconciliation rule: {str(e)}', 'danger')
    
    return render_template('bank_reconciliation/add_rule.html', 
                        bank_accounts=bank_accounts, gl_accounts=gl_accounts)


@bank_reconciliation_bp.route('/rules/<int:rule_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_rule(rule_id):
    """Edit a reconciliation rule"""
    # Check permission
    if not current_user.has_permission(Role.CAN_EDIT):
        flash('You do not have permission to edit reconciliation rules.', 'danger')
        return redirect(url_for('bank_reconciliation.reconciliation_rules'))

    # Get the reconciliation rule
    rule = ReconciliationRule.query.get_or_404(rule_id)
    
    # Get all bank accounts
    bank_accounts = BankAccount.query.filter_by(is_active=True).all()
    
    # Get all GL accounts
    gl_accounts = Account.query.all()
    
    if request.method == 'POST':
        # Get form data
        name = request.form.get('name')
        bank_account_id = request.form.get('bank_account_id')
        match_pattern = request.form.get('match_pattern')
        gl_account_id = request.form.get('gl_account_id')
        is_active = 'is_active' in request.form
        
        # Validate required fields
        if not name or not bank_account_id or not match_pattern or not gl_account_id:
            flash('Please fill in all required fields.', 'danger')
            return render_template('bank_reconciliation/edit_rule.html', 
                                rule=rule, bank_accounts=bank_accounts, gl_accounts=gl_accounts)
        
        # Update reconciliation rule
        rule.name = name
        rule.bank_account_id = bank_account_id
        rule.match_pattern = match_pattern
        rule.gl_account_id = gl_account_id
        rule.is_active = is_active
        
        # Save to database
        try:
            db.session.commit()
            flash(f'Reconciliation rule {name} has been updated successfully.', 'success')
            return redirect(url_for('bank_reconciliation.reconciliation_rules'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating reconciliation rule: {str(e)}', 'danger')
    
    return render_template('bank_reconciliation/edit_rule.html', 
                        rule=rule, bank_accounts=bank_accounts, gl_accounts=gl_accounts)


@bank_reconciliation_bp.route('/apply-rules/<int:statement_id>', methods=['POST'])
@login_required
def apply_rules(statement_id):
    """Apply reconciliation rules to a bank statement"""
    # Check permission
    if not current_user.has_permission(Role.CAN_EDIT):
        flash('You do not have permission to apply reconciliation rules.', 'danger')
        return redirect(url_for('bank_reconciliation.reconcile', statement_id=statement_id))

    # Get the bank statement
    statement = BankStatement.query.get_or_404(statement_id)
    
    # Get unreconciled transactions for this statement
    transactions = BankTransaction.query.filter_by(
        statement_id=statement_id,
        is_reconciled=False
    ).all()
    
    # Get active rules for this bank account
    rules = ReconciliationRule.query.filter_by(
        bank_account_id=statement.bank_account_id,
        is_active=True
    ).all()
    
    # Apply rules to transactions
    matched_count = 0
    for transaction in transactions:
        for rule in rules:
            # Check if transaction description matches the rule pattern
            if rule.match_pattern.lower() in transaction.description.lower():
                # For matching transactions, create a new journal entry
                journal_entry = JournalEntry(
                    entry_date=transaction.transaction_date,
                    reference=f"Auto-matched: {transaction.reference or transaction.description[:20]}",
                    description=transaction.description,
                    amount=transaction.amount
                )
                
                # Add journal entry to the database
                db.session.add(journal_entry)
                db.session.flush()  # This assigns an ID to the journal entry
                
                # Create journal items (line items) for the entry
                if transaction.transaction_type == 'credit':
                    # Money coming in - credit the bank account, debit the matched account
                    # Create the credit item (bank account)
                    credit_item = JournalItem(
                        journal_entry_id=journal_entry.id,
                        account_id=statement.bank_account.gl_account_id,
                        description=f"Bank deposit: {transaction.description[:30]}",
                        credit_amount=transaction.amount,
                        debit_amount=0
                    )
                    db.session.add(credit_item)
                    
                    # Create the debit item (income account from rule)
                    debit_item = JournalItem(
                        journal_entry_id=journal_entry.id,
                        account_id=rule.gl_account_id,
                        description=f"Income matched by rule: {rule.name}",
                        debit_amount=transaction.amount,
                        credit_amount=0
                    )
                    db.session.add(debit_item)
                else:
                    # Money going out - debit the bank account, credit the matched account
                    # Create the debit item (bank account)
                    debit_item = JournalItem(
                        journal_entry_id=journal_entry.id,
                        account_id=statement.bank_account.gl_account_id,
                        description=f"Bank withdrawal: {transaction.description[:30]}",
                        debit_amount=transaction.amount,
                        credit_amount=0
                    )
                    db.session.add(debit_item)
                    
                    # Create the credit item (expense account from rule)
                    credit_item = JournalItem(
                        journal_entry_id=journal_entry.id,
                        account_id=rule.gl_account_id,
                        description=f"Expense matched by rule: {rule.name}",
                        credit_amount=transaction.amount,
                        debit_amount=0
                    )
                    db.session.add(credit_item)
                
                # Link the journal entry to the transaction
                transaction.gl_entry_id = journal_entry.id
                transaction.is_reconciled = True
                transaction.reconciled_date = datetime.date.today()
                
                matched_count += 1
                break  # Stop after first matching rule
    
    # Save all changes to the database
    try:
        db.session.commit()
        flash(f'Successfully matched {matched_count} transactions using reconciliation rules.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error applying reconciliation rules: {str(e)}', 'danger')
    
    return redirect(url_for('bank_reconciliation.reconcile', statement_id=statement_id))