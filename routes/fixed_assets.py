from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from datetime import datetime, date
from sqlalchemy import func, asc, desc
from sqlalchemy.exc import SQLAlchemyError
from decimal import Decimal
import json

from app import db
from models import (
    Account, AccountType, JournalEntry, JournalItem, Entity, EntityType,
    AssetCategory, AssetLocation, AssetStatus, AssetCondition, FixedAsset,
    AssetDepreciation, MaintenanceType, AssetMaintenance, AssetDisposal,
    AssetTransfer, AssetDocument
)
import utils

fixed_assets_bp = Blueprint('fixed_assets', __name__)

#
# Asset Categories Management
#
@fixed_assets_bp.route('/asset-categories')
@login_required
def asset_categories():
    """Display all asset categories"""
    categories = AssetCategory.query.all()
    return render_template('fixed_assets/categories.html', categories=categories)

@fixed_assets_bp.route('/asset-categories/add', methods=['GET', 'POST'])
@login_required
def add_category():
    """Add a new asset category"""
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        depreciation_method = request.form.get('depreciation_method')
        useful_life_years = request.form.get('useful_life_years')
        asset_account_id = request.form.get('asset_account_id')
        depreciation_account_id = request.form.get('depreciation_account_id')
        accumulated_depreciation_account_id = request.form.get('accumulated_depreciation_account_id')
        
        # Validate required fields
        if not name:
            flash('Category name is required', 'danger')
            return redirect(url_for('fixed_assets.add_category'))
        
        # Create new category
        try:
            category = AssetCategory(
                name=name,
                description=description,
                depreciation_method=depreciation_method,
                useful_life_years=useful_life_years if useful_life_years else None,
                asset_account_id=asset_account_id if asset_account_id else None,
                depreciation_account_id=depreciation_account_id if depreciation_account_id else None,
                accumulated_depreciation_account_id=accumulated_depreciation_account_id if accumulated_depreciation_account_id else None,
                created_by_id=current_user.id
            )
            db.session.add(category)
            db.session.commit()
            flash(f'Asset category "{name}" has been created successfully', 'success')
            return redirect(url_for('fixed_assets.asset_categories'))
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'danger')
    
    # Get accounts for selection
    asset_accounts = Account.query.join(AccountType).filter(AccountType.name == AccountType.ASSET).all()
    expense_accounts = Account.query.join(AccountType).filter(AccountType.name == AccountType.EXPENSE).all()
    
    return render_template('fixed_assets/category_form.html', 
                         category=None, 
                         asset_accounts=asset_accounts,
                         expense_accounts=expense_accounts)

@fixed_assets_bp.route('/asset-categories/<int:category_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_category(category_id):
    """Edit an existing asset category"""
    category = AssetCategory.query.get_or_404(category_id)
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        depreciation_method = request.form.get('depreciation_method')
        useful_life_years = request.form.get('useful_life_years')
        asset_account_id = request.form.get('asset_account_id')
        depreciation_account_id = request.form.get('depreciation_account_id')
        accumulated_depreciation_account_id = request.form.get('accumulated_depreciation_account_id')
        
        # Validate required fields
        if not name:
            flash('Category name is required', 'danger')
            return redirect(url_for('fixed_assets.edit_category', category_id=category_id))
        
        # Update category
        try:
            category.name = name
            category.description = description
            category.depreciation_method = depreciation_method
            category.useful_life_years = useful_life_years if useful_life_years else None
            category.asset_account_id = asset_account_id if asset_account_id else None
            category.depreciation_account_id = depreciation_account_id if depreciation_account_id else None
            category.accumulated_depreciation_account_id = accumulated_depreciation_account_id if accumulated_depreciation_account_id else None
            
            db.session.commit()
            flash(f'Asset category "{name}" has been updated successfully', 'success')
            return redirect(url_for('fixed_assets.asset_categories'))
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'danger')
    
    # Get accounts for selection
    asset_accounts = Account.query.join(AccountType).filter(AccountType.name == AccountType.ASSET).all()
    expense_accounts = Account.query.join(AccountType).filter(AccountType.name == AccountType.EXPENSE).all()
    
    return render_template('fixed_assets/category_form.html', 
                         category=category, 
                         asset_accounts=asset_accounts,
                         expense_accounts=expense_accounts)

#
# Asset Locations Management
#
@fixed_assets_bp.route('/asset-locations')
@login_required
def asset_locations():
    """Display all asset locations"""
    locations = AssetLocation.query.all()
    return render_template('fixed_assets/locations.html', locations=locations)

@fixed_assets_bp.route('/asset-locations/add', methods=['GET', 'POST'])
@login_required
def add_location():
    """Add a new asset location"""
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        address = request.form.get('address')
        
        # Validate required fields
        if not name:
            flash('Location name is required', 'danger')
            return redirect(url_for('fixed_assets.add_location'))
        
        # Create new location
        try:
            location = AssetLocation(
                name=name,
                description=description,
                address=address,
                created_by_id=current_user.id
            )
            db.session.add(location)
            db.session.commit()
            flash(f'Asset location "{name}" has been created successfully', 'success')
            return redirect(url_for('fixed_assets.asset_locations'))
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'danger')
    
    return render_template('fixed_assets/location_form.html', location=None)

@fixed_assets_bp.route('/asset-locations/<int:location_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_location(location_id):
    """Edit an existing asset location"""
    location = AssetLocation.query.get_or_404(location_id)
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        address = request.form.get('address')
        
        # Validate required fields
        if not name:
            flash('Location name is required', 'danger')
            return redirect(url_for('fixed_assets.edit_location', location_id=location_id))
        
        # Update location
        try:
            location.name = name
            location.description = description
            location.address = address
            
            db.session.commit()
            flash(f'Asset location "{name}" has been updated successfully', 'success')
            return redirect(url_for('fixed_assets.asset_locations'))
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'danger')
    
    return render_template('fixed_assets/location_form.html', location=location)

#
# Fixed Assets Dashboard
#
@fixed_assets_bp.route('/')
@login_required
def dashboard():
    """Fixed Assets Dashboard"""
    # Asset Summary
    total_assets = FixedAsset.query.count()
    total_categories = AssetCategory.query.count()
    total_locations = AssetLocation.query.count()
    
    # Active vs. Inactive Assets
    active_assets = FixedAsset.query.join(AssetStatus).filter(AssetStatus.name == AssetStatus.ACTIVE).count()
    disposed_assets = FixedAsset.query.join(AssetStatus).filter(AssetStatus.name.in_([AssetStatus.DISPOSED, AssetStatus.SOLD])).count()
    
    # Total Asset Value
    total_original_cost = db.session.query(func.sum(FixedAsset.purchase_cost)).scalar() or 0
    
    # Current Book Value (after depreciation)
    # This is a complex calculation in real-time, so we'll use the stored values
    total_book_value = db.session.query(func.sum(FixedAsset.current_value)).scalar() or 0
    
    # Assets by Category (for chart)
    assets_by_category = db.session.query(
        AssetCategory.name, 
        func.count(FixedAsset.id)
    ).join(
        FixedAsset, 
        FixedAsset.category_id == AssetCategory.id
    ).group_by(
        AssetCategory.name
    ).all()
    
    category_names = [item[0] for item in assets_by_category]
    category_counts = [item[1] for item in assets_by_category]
    
    # Assets by Location (for chart)
    assets_by_location = db.session.query(
        AssetLocation.name, 
        func.count(FixedAsset.id)
    ).join(
        FixedAsset, 
        FixedAsset.location_id == AssetLocation.id
    ).group_by(
        AssetLocation.name
    ).all()
    
    location_names = [item[0] for item in assets_by_location]
    location_counts = [item[1] for item in assets_by_location]
    
    # Assets by Condition
    assets_by_condition = db.session.query(
        AssetCondition.name, 
        func.count(FixedAsset.id)
    ).join(
        FixedAsset, 
        FixedAsset.condition_id == AssetCondition.id
    ).group_by(
        AssetCondition.name
    ).all()
    
    condition_names = [item[0] for item in assets_by_condition]
    condition_counts = [item[1] for item in assets_by_condition]
    
    # Recent assets
    recent_assets = FixedAsset.query.order_by(FixedAsset.created_at.desc()).limit(5).all()
    
    # Upcoming maintenance
    upcoming_maintenance = AssetMaintenance.query.filter(
        AssetMaintenance.next_maintenance_date >= date.today()
    ).order_by(
        AssetMaintenance.next_maintenance_date
    ).limit(5).all()
    
    # Depreciation Summary 
    total_depreciation = db.session.query(func.sum(AssetDepreciation.amount)).scalar() or 0
    
    return render_template('fixed_assets/dashboard.html',
                         total_assets=total_assets,
                         total_categories=total_categories,
                         total_locations=total_locations,
                         active_assets=active_assets,
                         disposed_assets=disposed_assets,
                         total_original_cost=total_original_cost,
                         total_book_value=total_book_value,
                         total_depreciation=total_depreciation,
                         category_names=json.dumps(category_names),
                         category_counts=json.dumps(category_counts),
                         location_names=json.dumps(location_names),
                         location_counts=json.dumps(location_counts),
                         condition_names=json.dumps(condition_names),
                         condition_counts=json.dumps(condition_counts),
                         recent_assets=recent_assets,
                         upcoming_maintenance=upcoming_maintenance,
                         format_currency=utils.format_currency)

#
# Fixed Assets List and Management
#
@fixed_assets_bp.route('/assets')
@login_required
def assets():
    """Display all fixed assets"""
    assets = FixedAsset.query.all()
    return render_template('fixed_assets/assets.html', assets=assets, format_currency=utils.format_currency)

@fixed_assets_bp.route('/assets/add', methods=['GET', 'POST'])
@login_required
def add_asset():
    """Add a new fixed asset"""
    if request.method == 'POST':
        # Get form data
        name = request.form.get('name')
        description = request.form.get('description')
        category_id = request.form.get('category_id')
        acquisition_date = request.form.get('acquisition_date')
        purchase_cost = request.form.get('purchase_cost')
        salvage_value = request.form.get('salvage_value') or 0
        useful_life_years = request.form.get('useful_life_years')
        depreciation_method = request.form.get('depreciation_method')
        location_id = request.form.get('location_id')
        status_id = request.form.get('status_id')
        condition_id = request.form.get('condition_id')
        vendor_id = request.form.get('vendor_id')
        serial_number = request.form.get('serial_number')
        warranty_expiry_date = request.form.get('warranty_expiry_date')
        notes = request.form.get('notes')
        
        # Validate required fields
        if not all([name, category_id, acquisition_date, purchase_cost, useful_life_years, depreciation_method, status_id]):
            flash('Please fill in all required fields', 'danger')
            return redirect(url_for('fixed_assets.add_asset'))
        
        try:
            # Generate asset number
            asset_number = utils.generate_asset_number()
            
            # Convert date strings to date objects
            acquisition_date = datetime.strptime(acquisition_date, '%Y-%m-%d').date() if acquisition_date else None
            warranty_expiry_date = datetime.strptime(warranty_expiry_date, '%Y-%m-%d').date() if warranty_expiry_date else None
            
            # Create the fixed asset
            asset = FixedAsset(
                asset_number=asset_number,
                name=name,
                description=description,
                category_id=category_id,
                acquisition_date=acquisition_date,
                purchase_cost=purchase_cost,
                salvage_value=salvage_value,
                useful_life_years=useful_life_years,
                depreciation_method=depreciation_method,
                current_value=purchase_cost,  # Initially, current value equals purchase cost
                location_id=location_id,
                status_id=status_id,
                condition_id=condition_id,
                vendor_id=vendor_id,
                serial_number=serial_number,
                warranty_expiry_date=warranty_expiry_date,
                notes=notes,
                created_by_id=current_user.id
            )
            
            db.session.add(asset)
            
            # Create acquisition journal entry if appropriate accounts are set up
            category = AssetCategory.query.get(category_id)
            if category and category.asset_account_id:
                # Create journal entry
                journal_entry = JournalEntry(
                    entry_date=acquisition_date,
                    reference=f"ASSET-ACQ-{asset_number}",
                    description=f"Asset acquisition: {name}",
                    created_by_id=current_user.id
                )
                db.session.add(journal_entry)
                db.session.flush()  # Get the journal_entry.id
                
                # Add journal items
                # Debit the asset account
                debit_item = JournalItem(
                    journal_entry_id=journal_entry.id,
                    account_id=category.asset_account_id,
                    description=f"Asset acquisition: {name}",
                    debit_amount=purchase_cost,
                    credit_amount=0
                )
                db.session.add(debit_item)
                
                # Credit accounts payable or cash - simplified for now
                # In a real system, we might have more options or a proper purchase transaction
                default_liability_account = Account.query.join(AccountType).filter(
                    AccountType.name == AccountType.LIABILITY,
                    Account.name.like('%Payable%')
                ).first()
                
                if default_liability_account:
                    credit_item = JournalItem(
                        journal_entry_id=journal_entry.id,
                        account_id=default_liability_account.id,
                        description=f"Asset acquisition: {name}",
                        debit_amount=0,
                        credit_amount=purchase_cost
                    )
                    db.session.add(credit_item)
                    
                    # Post the journal entry
                    journal_entry.is_posted = True
                    
                    # Link the journal entry to the asset
                    asset.acquisition_journal_entry_id = journal_entry.id
            
            db.session.commit()
            flash(f'Fixed asset "{name}" has been created successfully', 'success')
            return redirect(url_for('fixed_assets.assets'))
            
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'danger')
    
    # Get data for form selects
    categories = AssetCategory.query.all()
    locations = AssetLocation.query.all()
    statuses = AssetStatus.query.all()
    conditions = AssetCondition.query.all()
    vendors = Entity.query.join(EntityType).filter(EntityType.name == EntityType.VENDOR).all()
    
    return render_template('fixed_assets/asset_form.html',
                         asset=None,
                         categories=categories,
                         locations=locations,
                         statuses=statuses,
                         conditions=conditions,
                         vendors=vendors)

@fixed_assets_bp.route('/assets/<int:asset_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_asset(asset_id):
    """Edit an existing fixed asset"""
    asset = FixedAsset.query.get_or_404(asset_id)
    
    if request.method == 'POST':
        # Get form data
        name = request.form.get('name')
        description = request.form.get('description')
        category_id = request.form.get('category_id')
        salvage_value = request.form.get('salvage_value') or 0
        useful_life_years = request.form.get('useful_life_years')
        depreciation_method = request.form.get('depreciation_method')
        location_id = request.form.get('location_id')
        status_id = request.form.get('status_id')
        condition_id = request.form.get('condition_id')
        vendor_id = request.form.get('vendor_id')
        serial_number = request.form.get('serial_number')
        warranty_expiry_date = request.form.get('warranty_expiry_date')
        notes = request.form.get('notes')
        
        # Validate required fields
        if not all([name, category_id, useful_life_years, depreciation_method, status_id]):
            flash('Please fill in all required fields', 'danger')
            return redirect(url_for('fixed_assets.edit_asset', asset_id=asset_id))
        
        try:
            # Convert date strings to date objects
            warranty_expiry_date = datetime.strptime(warranty_expiry_date, '%Y-%m-%d').date() if warranty_expiry_date else None
            
            # Update the fixed asset
            asset.name = name
            asset.description = description
            asset.category_id = category_id
            asset.salvage_value = salvage_value
            asset.useful_life_years = useful_life_years
            asset.depreciation_method = depreciation_method
            asset.location_id = location_id
            asset.status_id = status_id
            asset.condition_id = condition_id
            asset.vendor_id = vendor_id
            asset.serial_number = serial_number
            asset.warranty_expiry_date = warranty_expiry_date
            asset.notes = notes
            
            db.session.commit()
            flash(f'Fixed asset "{name}" has been updated successfully', 'success')
            return redirect(url_for('fixed_assets.assets'))
            
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'danger')
    
    # Get data for form selects
    categories = AssetCategory.query.all()
    locations = AssetLocation.query.all()
    statuses = AssetStatus.query.all()
    conditions = AssetCondition.query.all()
    vendors = Entity.query.join(EntityType).filter(EntityType.name == EntityType.VENDOR).all()
    
    return render_template('fixed_assets/asset_form.html',
                         asset=asset,
                         categories=categories,
                         locations=locations,
                         statuses=statuses,
                         conditions=conditions,
                         vendors=vendors,
                         format_currency=utils.format_currency)

@fixed_assets_bp.route('/assets/<int:asset_id>')
@login_required
def asset_detail(asset_id):
    """Display detailed information about a fixed asset"""
    asset = FixedAsset.query.get_or_404(asset_id)
    
    # Get depreciation history
    depreciation_entries = AssetDepreciation.query.filter_by(asset_id=asset_id).order_by(AssetDepreciation.date.desc()).all()
    
    # Get maintenance history
    maintenance_records = AssetMaintenance.query.filter_by(asset_id=asset_id).order_by(AssetMaintenance.date.desc()).all()
    
    # Calculate current book value and depreciation amounts
    current_book_value = asset.get_current_book_value()
    total_depreciation = asset.calculate_depreciation_to_date()
    monthly_depreciation = asset.calculate_monthly_depreciation()
    remaining_useful_life = asset.get_remaining_useful_life()
    
    return render_template('fixed_assets/asset_detail.html',
                         asset=asset,
                         depreciation_entries=depreciation_entries,
                         maintenance_records=maintenance_records,
                         current_book_value=current_book_value,
                         total_depreciation=total_depreciation,
                         monthly_depreciation=monthly_depreciation,
                         remaining_useful_life=remaining_useful_life,
                         format_currency=utils.format_currency)

#
# Asset Depreciation
#
@fixed_assets_bp.route('/assets/<int:asset_id>/record-depreciation', methods=['GET', 'POST'])
@login_required
def record_depreciation(asset_id):
    """Record a depreciation entry for a fixed asset"""
    asset = FixedAsset.query.get_or_404(asset_id)
    
    # Check if asset is already fully depreciated
    if asset.is_fully_depreciated:
        flash('This asset is already fully depreciated', 'warning')
        return redirect(url_for('fixed_assets.asset_detail', asset_id=asset_id))
    
    if request.method == 'POST':
        # Get form data
        depreciation_date = request.form.get('depreciation_date')
        period_start = request.form.get('period_start')
        period_end = request.form.get('period_end')
        amount = request.form.get('amount')
        
        # Validate required fields
        if not all([depreciation_date, period_start, period_end, amount]):
            flash('Please fill in all required fields', 'danger')
            return redirect(url_for('fixed_assets.record_depreciation', asset_id=asset_id))
        
        try:
            # Convert date strings to date objects
            depreciation_date = datetime.strptime(depreciation_date, '%Y-%m-%d').date()
            period_start = datetime.strptime(period_start, '%Y-%m-%d').date()
            period_end = datetime.strptime(period_end, '%Y-%m-%d').date()
            
            # Validate dates
            if period_start > period_end:
                flash('Period start date must be before or equal to period end date', 'danger')
                return redirect(url_for('fixed_assets.record_depreciation', asset_id=asset_id))
            
            # Calculate book values
            current_book_value = asset.get_current_book_value()
            book_value_after = current_book_value - Decimal(amount)
            
            # Check if this depreciation would exceed the total depreciable amount
            if book_value_after < Decimal(asset.salvage_value):
                flash('Depreciation amount would exceed the depreciable cost of the asset', 'danger')
                return redirect(url_for('fixed_assets.record_depreciation', asset_id=asset_id))
            
            # Create the depreciation entry
            depreciation = AssetDepreciation(
                asset_id=asset_id,
                date=depreciation_date,
                amount=amount,
                period_start=period_start,
                period_end=period_end,
                book_value_before=current_book_value,
                book_value_after=book_value_after,
                created_by_id=current_user.id
            )
            
            db.session.add(depreciation)
            
            # Update the asset
            asset.last_depreciation_date = depreciation_date
            asset.current_value = book_value_after
            
            # Check if asset is now fully depreciated
            if book_value_after <= Decimal(asset.salvage_value):
                asset.is_fully_depreciated = True
            
            # Create a journal entry for the depreciation
            category = asset.category
            if category and category.depreciation_account_id and category.accumulated_depreciation_account_id:
                # Create journal entry
                journal_entry = JournalEntry(
                    entry_date=depreciation_date,
                    reference=f"ASSET-DEP-{asset.asset_number}-{depreciation_date}",
                    description=f"Asset depreciation: {asset.name} for period {period_start} to {period_end}",
                    created_by_id=current_user.id
                )
                db.session.add(journal_entry)
                db.session.flush()  # Get the journal_entry.id
                
                # Add journal items
                # Debit the depreciation expense account
                debit_item = JournalItem(
                    journal_entry_id=journal_entry.id,
                    account_id=category.depreciation_account_id,
                    description=f"Depreciation expense: {asset.name}",
                    debit_amount=amount,
                    credit_amount=0
                )
                db.session.add(debit_item)
                
                # Credit the accumulated depreciation account
                credit_item = JournalItem(
                    journal_entry_id=journal_entry.id,
                    account_id=category.accumulated_depreciation_account_id,
                    description=f"Accumulated depreciation: {asset.name}",
                    debit_amount=0,
                    credit_amount=amount
                )
                db.session.add(credit_item)
                
                # Post the journal entry
                journal_entry.is_posted = True
                
                # Link the journal entry to the depreciation record
                depreciation.journal_entry_id = journal_entry.id
            
            db.session.commit()
            flash(f'Depreciation for "{asset.name}" has been recorded successfully', 'success')
            return redirect(url_for('fixed_assets.asset_detail', asset_id=asset_id))
            
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'danger')
    
    # For GET request, prepare form data
    suggested_amount = asset.calculate_monthly_depreciation()
    
    return render_template('fixed_assets/depreciation_form.html',
                         asset=asset,
                         suggested_amount=suggested_amount,
                         current_date=date.today().strftime('%Y-%m-%d'),
                         current_book_value=asset.get_current_book_value(),
                         format_currency=utils.format_currency)

#
# Asset Maintenance
#
@fixed_assets_bp.route('/maintenance')
@login_required
def maintenance_list():
    """Display all maintenance records"""
    maintenance_records = AssetMaintenance.query.order_by(AssetMaintenance.date.desc()).all()
    return render_template('fixed_assets/maintenance_list.html', 
                         maintenance_records=maintenance_records,
                         format_currency=utils.format_currency)

@fixed_assets_bp.route('/assets/<int:asset_id>/add-maintenance', methods=['GET', 'POST'])
@login_required
def add_maintenance(asset_id):
    from datetime import date
    """Add a maintenance record for a fixed asset"""
    asset = FixedAsset.query.get_or_404(asset_id)
    
    if request.method == 'POST':
        # Get form data
        maintenance_type_id = request.form.get('maintenance_type_id')
        date = request.form.get('maintenance_date')
        cost = request.form.get('cost')
        provider = request.form.get('provider')
        description = request.form.get('description')
        maintenance_notes = request.form.get('maintenance_notes')
        next_maintenance_date = request.form.get('next_maintenance_date')
        expense_account_id = request.form.get('expense_account_id')
        
        # Validate required fields
        if not all([maintenance_type_id, date, cost, description]):
            flash('Please fill in all required fields', 'danger')
            return redirect(url_for('fixed_assets.add_maintenance', asset_id=asset_id))
        
        try:
            # Convert date strings to date objects
            maintenance_date = datetime.strptime(date, '%Y-%m-%d').date()
            next_maintenance_date = datetime.strptime(next_maintenance_date, '%Y-%m-%d').date() if next_maintenance_date else None
            
            # Create the maintenance record
            maintenance = AssetMaintenance(
                asset_id=asset_id,
                maintenance_type_id=maintenance_type_id,
                date=maintenance_date,
                cost=cost,
                provider=provider,
                description=description,
                maintenance_notes=maintenance_notes,
                next_maintenance_date=next_maintenance_date,
                expense_account_id=expense_account_id if expense_account_id else None,
                created_by_id=current_user.id
            )
            
            db.session.add(maintenance)
            
            # Create a journal entry for the maintenance expense if account is specified
            if expense_account_id:
                # Create journal entry
                journal_entry = JournalEntry(
                    entry_date=maintenance_date,
                    reference=f"ASSET-MAINT-{asset.asset_number}-{maintenance_date}",
                    description=f"Asset maintenance: {asset.name} - {description}",
                    created_by_id=current_user.id
                )
                db.session.add(journal_entry)
                db.session.flush()  # Get the journal_entry.id
                
                # Add journal items
                # Debit the maintenance expense account
                debit_item = JournalItem(
                    journal_entry_id=journal_entry.id,
                    account_id=expense_account_id,
                    description=f"Maintenance expense: {asset.name}",
                    debit_amount=cost,
                    credit_amount=0
                )
                db.session.add(debit_item)
                
                # Credit accounts payable or cash - simplified for now
                default_liability_account = Account.query.join(AccountType).filter(
                    AccountType.name == AccountType.LIABILITY,
                    Account.name.like('%Payable%')
                ).first()
                
                if default_liability_account:
                    credit_item = JournalItem(
                        journal_entry_id=journal_entry.id,
                        account_id=default_liability_account.id,
                        description=f"Maintenance expense: {asset.name}",
                        debit_amount=0,
                        credit_amount=cost
                    )
                    db.session.add(credit_item)
                    
                    # Post the journal entry
                    journal_entry.is_posted = True
                    
                    # Link the journal entry to the maintenance record
                    maintenance.journal_entry_id = journal_entry.id
            
            # Update asset condition based on maintenance
            if request.form.get('update_condition') and request.form.get('new_condition_id'):
                asset.condition_id = request.form.get('new_condition_id')
            
            # Update asset status if needed
            if request.form.get('update_status'):
                # Get the "Under Maintenance" status
                under_maintenance_status = AssetStatus.query.filter_by(name=AssetStatus.UNDER_MAINTENANCE).first()
                active_status = AssetStatus.query.filter_by(name=AssetStatus.ACTIVE).first()
                
                if request.form.get('set_maintenance_status') and under_maintenance_status:
                    asset.status_id = under_maintenance_status.id
                elif request.form.get('set_active_status') and active_status:
                    asset.status_id = active_status.id
            
            db.session.commit()
            flash(f'Maintenance record for "{asset.name}" has been added successfully', 'success')
            return redirect(url_for('fixed_assets.asset_detail', asset_id=asset_id))
            
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'danger')
    
    # Get data for form selects
    maintenance_types = MaintenanceType.query.all()
    expense_accounts = Account.query.join(AccountType).filter(AccountType.name == AccountType.EXPENSE).all()
    conditions = AssetCondition.query.all()
    
    return render_template('fixed_assets/maintenance_form.html',
                         asset=asset,
                         maintenance=None,
                         maintenance_types=maintenance_types,
                         expense_accounts=expense_accounts,
                         conditions=conditions,
                         current_date=date.today().strftime('%Y-%m-%d'),
                         format_currency=utils.format_currency)

#
# Asset Disposal
#
@fixed_assets_bp.route('/assets/<int:asset_id>/dispose', methods=['GET', 'POST'])
@login_required
def dispose_asset(asset_id):
    """Record disposal of a fixed asset"""
    asset = FixedAsset.query.get_or_404(asset_id)
    
    # Check if asset is already disposed
    disposed_status = AssetStatus.query.filter(AssetStatus.name.in_([AssetStatus.DISPOSED, AssetStatus.SOLD])).all()
    disposed_status_ids = [status.id for status in disposed_status]
    
    if asset.status_id in disposed_status_ids:
        flash('This asset has already been disposed', 'warning')
        return redirect(url_for('fixed_assets.asset_detail', asset_id=asset_id))
    
    if request.method == 'POST':
        # Get form data
        disposal_date = request.form.get('disposal_date')
        disposal_type = request.form.get('disposal_type')
        disposal_amount = request.form.get('disposal_amount') or 0
        buyer_id = request.form.get('buyer_id')
        reason = request.form.get('reason')
        notes = request.form.get('notes')
        
        # Validate required fields
        if not all([disposal_date, disposal_type]):
            flash('Please fill in all required fields', 'danger')
            return redirect(url_for('fixed_assets.dispose_asset', asset_id=asset_id))
        
        try:
            # Convert date strings to date objects
            disposal_date = datetime.strptime(disposal_date, '%Y-%m-%d').date()
            
            # Calculate current book value
            book_value = asset.get_current_book_value()
            
            # Calculate gain/loss
            disposal_amount = Decimal(disposal_amount)
            gain_loss = disposal_amount - book_value
            
            # Create the disposal record
            disposal = AssetDisposal(
                asset_id=asset_id,
                disposal_date=disposal_date,
                disposal_type=disposal_type,
                disposal_amount=disposal_amount,
                buyer_id=buyer_id if buyer_id else None,
                book_value_at_disposal=book_value,
                gain_loss_amount=gain_loss,
                reason=reason,
                notes=notes,
                created_by_id=current_user.id
            )
            
            db.session.add(disposal)
            
            # Update asset status
            if disposal_type == 'Sold':
                sold_status = AssetStatus.query.filter_by(name=AssetStatus.SOLD).first()
                if sold_status:
                    asset.status_id = sold_status.id
            else:
                disposed_status = AssetStatus.query.filter_by(name=AssetStatus.DISPOSED).first()
                if disposed_status:
                    asset.status_id = disposed_status.id
            
            # Create a journal entry for the disposal
            category = asset.category
            if category and category.asset_account_id and category.accumulated_depreciation_account_id:
                # Create journal entry
                journal_entry = JournalEntry(
                    entry_date=disposal_date,
                    reference=f"ASSET-DISP-{asset.asset_number}",
                    description=f"Asset disposal: {asset.name}",
                    created_by_id=current_user.id
                )
                db.session.add(journal_entry)
                db.session.flush()  # Get the journal_entry.id
                
                # Calculate the accumulated depreciation
                accumulated_depreciation = asset.purchase_cost - book_value
                
                # Add journal items based on disposal type
                if disposal_type == 'Sold':
                    # Debit Cash or Accounts Receivable for the sale amount
                    cash_account = Account.query.join(AccountType).filter(
                        AccountType.name == AccountType.ASSET,
                        Account.name.like('%Cash%')
                    ).first()
                    
                    if cash_account:
                        cash_debit = JournalItem(
                            journal_entry_id=journal_entry.id,
                            account_id=cash_account.id,
                            description=f"Cash received for sale of asset: {asset.name}",
                            debit_amount=disposal_amount,
                            credit_amount=0
                        )
                        db.session.add(cash_debit)
                    
                    # Debit Accumulated Depreciation
                    acc_dep_debit = JournalItem(
                        journal_entry_id=journal_entry.id,
                        account_id=category.accumulated_depreciation_account_id,
                        description=f"Remove accumulated depreciation for: {asset.name}",
                        debit_amount=accumulated_depreciation,
                        credit_amount=0
                    )
                    db.session.add(acc_dep_debit)
                    
                    # Credit Asset account for original cost
                    asset_credit = JournalItem(
                        journal_entry_id=journal_entry.id,
                        account_id=category.asset_account_id,
                        description=f"Remove asset from books: {asset.name}",
                        debit_amount=0,
                        credit_amount=asset.purchase_cost
                    )
                    db.session.add(asset_credit)
                    
                    # If there's a gain/loss, record it
                    if gain_loss != 0:
                        # Find or create a gain/loss account
                        gain_loss_account = None
                        if gain_loss > 0:
                            # Gain on disposal - Revenue account
                            gain_loss_account = Account.query.join(AccountType).filter(
                                AccountType.name == AccountType.REVENUE,
                                Account.name.like('%Gain%')
                            ).first()
                        else:
                            # Loss on disposal - Expense account
                            gain_loss_account = Account.query.join(AccountType).filter(
                                AccountType.name == AccountType.EXPENSE,
                                Account.name.like('%Loss%')
                            ).first()
                        
                        if gain_loss_account:
                            if gain_loss > 0:
                                # Credit Gain account
                                gain_credit = JournalItem(
                                    journal_entry_id=journal_entry.id,
                                    account_id=gain_loss_account.id,
                                    description=f"Gain on disposal of asset: {asset.name}",
                                    debit_amount=0,
                                    credit_amount=abs(gain_loss)
                                )
                                db.session.add(gain_credit)
                            else:
                                # Debit Loss account
                                loss_debit = JournalItem(
                                    journal_entry_id=journal_entry.id,
                                    account_id=gain_loss_account.id,
                                    description=f"Loss on disposal of asset: {asset.name}",
                                    debit_amount=abs(gain_loss),
                                    credit_amount=0
                                )
                                db.session.add(loss_debit)
                else:
                    # For non-sale disposals (e.g., scrapped)
                    # Debit Accumulated Depreciation
                    acc_dep_debit = JournalItem(
                        journal_entry_id=journal_entry.id,
                        account_id=category.accumulated_depreciation_account_id,
                        description=f"Remove accumulated depreciation for: {asset.name}",
                        debit_amount=accumulated_depreciation,
                        credit_amount=0
                    )
                    db.session.add(acc_dep_debit)
                    
                    # Credit Asset account for original cost
                    asset_credit = JournalItem(
                        journal_entry_id=journal_entry.id,
                        account_id=category.asset_account_id,
                        description=f"Remove asset from books: {asset.name}",
                        debit_amount=0,
                        credit_amount=asset.purchase_cost
                    )
                    db.session.add(asset_credit)
                    
                    # If book value is non-zero, record a loss
                    if book_value > 0:
                        loss_account = Account.query.join(AccountType).filter(
                            AccountType.name == AccountType.EXPENSE,
                            Account.name.like('%Loss%')
                        ).first()
                        
                        if loss_account:
                            loss_debit = JournalItem(
                                journal_entry_id=journal_entry.id,
                                account_id=loss_account.id,
                                description=f"Loss on disposal of asset: {asset.name}",
                                debit_amount=book_value,
                                credit_amount=0
                            )
                            db.session.add(loss_debit)
                
                # Post the journal entry
                journal_entry.is_posted = True
                
                # Link the journal entry to the disposal record
                disposal.journal_entry_id = journal_entry.id
            
            db.session.commit()
            flash(f'Asset "{asset.name}" has been disposed successfully', 'success')
            return redirect(url_for('fixed_assets.asset_detail', asset_id=asset_id))
            
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'danger')
    
    # Get customers for buyer selection in case of sale
    customers = Entity.query.join(EntityType).filter(EntityType.name == EntityType.CUSTOMER).all()
    
    return render_template('fixed_assets/disposal_form.html',
                         asset=asset,
                         customers=customers,
                         current_date=date.today().strftime('%Y-%m-%d'),
                         current_book_value=asset.get_current_book_value(),
                         format_currency=utils.format_currency)

#
# Asset Transfer
#
@fixed_assets_bp.route('/assets/<int:asset_id>/transfer', methods=['GET', 'POST'])
@login_required
def transfer_asset(asset_id):
    """Transfer a fixed asset to a different location"""
    asset = FixedAsset.query.get_or_404(asset_id)
    
    if not asset.location_id:
        flash('This asset does not have a current location assigned', 'warning')
        return redirect(url_for('fixed_assets.asset_detail', asset_id=asset_id))
    
    if request.method == 'POST':
        # Get form data
        transfer_date = request.form.get('transfer_date')
        to_location_id = request.form.get('to_location_id')
        reason = request.form.get('reason')
        transfer_notes = request.form.get('transfer_notes')
        
        # Validate required fields
        if not all([transfer_date, to_location_id]):
            flash('Please fill in all required fields', 'danger')
            return redirect(url_for('fixed_assets.transfer_asset', asset_id=asset_id))
        
        # Check if target location is the same as current location
        if int(to_location_id) == asset.location_id:
            flash('The target location is the same as the current location', 'warning')
            return redirect(url_for('fixed_assets.transfer_asset', asset_id=asset_id))
        
        try:
            # Convert date strings to date objects
            transfer_date = datetime.strptime(transfer_date, '%Y-%m-%d').date()
            
            # Create the transfer record
            transfer = AssetTransfer(
                asset_id=asset_id,
                transfer_date=transfer_date,
                from_location_id=asset.location_id,
                to_location_id=to_location_id,
                reason=reason,
                transfer_notes=transfer_notes,
                created_by_id=current_user.id
            )
            
            db.session.add(transfer)
            
            # Update asset location
            asset.location_id = to_location_id
            
            db.session.commit()
            flash(f'Asset "{asset.name}" has been transferred successfully', 'success')
            return redirect(url_for('fixed_assets.asset_detail', asset_id=asset_id))
            
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'danger')
    
    # Get all locations except the current one
    locations = AssetLocation.query.filter(AssetLocation.id != asset.location_id).all()
    current_location = AssetLocation.query.get(asset.location_id)
    
    return render_template('fixed_assets/transfer_form.html',
                         asset=asset,
                         current_location=current_location,
                         locations=locations,
                         current_date=date.today().strftime('%Y-%m-%d'),
                         format_currency=utils.format_currency)

# Set up blueprints and routes
def setup_assets_blueprint(app):
    app.register_blueprint(fixed_assets_bp, url_prefix='/fixed-assets')
    
    # Initialize reference data
    with app.app_context():
        # Initialize Asset Statuses
        status_names = [
            AssetStatus.ACTIVE,
            AssetStatus.DISPOSED,
            AssetStatus.SOLD,
            AssetStatus.UNDER_MAINTENANCE,
            AssetStatus.EXPIRED
        ]
        for status_name in status_names:
            if not AssetStatus.query.filter_by(name=status_name).first():
                db.session.add(AssetStatus(name=status_name))
                
        # Initialize Asset Conditions
        condition_names = [
            AssetCondition.EXCELLENT,
            AssetCondition.GOOD,
            AssetCondition.FAIR,
            'Poor',
            'Unusable'
        ]
        for condition_name in condition_names:
            if not AssetCondition.query.filter_by(name=condition_name).first():
                db.session.add(AssetCondition(name=condition_name))
        
        # Initialize Asset Locations if none exist
        if AssetLocation.query.count() == 0:
            default_locations = [
                {"name": "Main Office", "description": "Main office location", "address": "123 Main St"},
                {"name": "Warehouse", "description": "Primary storage warehouse", "address": "456 Storage Ave"},
                {"name": "Branch Office", "description": "Secondary office location", "address": "789 Branch Rd"}
            ]
            for loc in default_locations:
                db.session.add(AssetLocation(
                    name=loc["name"],
                    description=loc["description"],
                    address=loc["address"]
                ))
        
        # Commit all changes
        db.session.commit()