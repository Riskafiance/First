from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from models import (
    Product, ProductCategory, UnitOfMeasure, InventoryTransaction, 
    InventoryTransactionType, Warehouse, PurchaseOrder, PurchaseOrderStatus,
    PurchaseOrderItem, Entity, EntityType, Account, AccountType, Role,
    JournalEntry, JournalItem
)
from utils import (
    generate_product_sku, generate_po_number, record_inventory_transaction,
    get_inventory_value, get_low_stock_products
)
from datetime import datetime, timedelta
from sqlalchemy import func

inventory_bp = Blueprint('inventory', __name__)

# Product Categories
@inventory_bp.route('/categories')
@login_required
def categories():
    """List product categories"""
    categories = ProductCategory.query.all()
    return render_template('inventory/categories.html', categories=categories)

@inventory_bp.route('/categories/create', methods=['GET', 'POST'])
@login_required
def create_category():
    """Create a new product category"""
    if not current_user.has_permission(Role.CAN_CREATE):
        flash('You do not have permission to create categories.', 'danger')
        return redirect(url_for('inventory.categories'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        
        category = ProductCategory(
            name=name,
            description=description,
            created_by_id=current_user.id
        )
        
        db.session.add(category)
        db.session.commit()
        
        flash('Category created successfully.', 'success')
        return redirect(url_for('inventory.categories'))
    
    return render_template('inventory/category_form.html')

@inventory_bp.route('/categories/<int:category_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_category(category_id):
    """Edit a product category"""
    if not current_user.has_permission(Role.CAN_EDIT):
        flash('You do not have permission to edit categories.', 'danger')
        return redirect(url_for('inventory.categories'))
    
    category = ProductCategory.query.get_or_404(category_id)
    
    if request.method == 'POST':
        category.name = request.form.get('name')
        category.description = request.form.get('description')
        
        db.session.commit()
        
        flash('Category updated successfully.', 'success')
        return redirect(url_for('inventory.categories'))
    
    return render_template('inventory/category_form.html', category=category)

@inventory_bp.route('/categories/<int:category_id>/delete', methods=['POST'])
@login_required
def delete_category(category_id):
    """Delete a product category"""
    if not current_user.has_permission(Role.CAN_DELETE):
        flash('You do not have permission to delete categories.', 'danger')
        return redirect(url_for('inventory.categories'))
    
    category = ProductCategory.query.get_or_404(category_id)
    
    # Check if there are products using this category
    products = Product.query.filter_by(category_id=category_id).count()
    if products > 0:
        flash(f'Cannot delete category. It is used by {products} products.', 'danger')
        return redirect(url_for('inventory.categories'))
    
    db.session.delete(category)
    db.session.commit()
    
    flash('Category deleted successfully.', 'success')
    return redirect(url_for('inventory.categories'))

# Units of Measure
@inventory_bp.route('/uoms')
@login_required
def uoms():
    """List units of measure"""
    uoms = UnitOfMeasure.query.all()
    return render_template('inventory/uoms.html', uoms=uoms)

@inventory_bp.route('/uoms/create', methods=['GET', 'POST'])
@login_required
def create_uom():
    """Create a new unit of measure"""
    if not current_user.has_permission(Role.CAN_CREATE):
        flash('You do not have permission to create units of measure.', 'danger')
        return redirect(url_for('inventory.uoms'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        abbreviation = request.form.get('abbreviation')
        
        # Check if UOM already exists
        existing_uom = UnitOfMeasure.query.filter(
            (UnitOfMeasure.name == name) | (UnitOfMeasure.abbreviation == abbreviation)
        ).first()
        
        if existing_uom:
            flash('A unit of measure with that name or abbreviation already exists.', 'danger')
            return render_template('inventory/uom_form.html')
        
        uom = UnitOfMeasure(
            name=name,
            abbreviation=abbreviation
        )
        
        db.session.add(uom)
        db.session.commit()
        
        flash('Unit of measure created successfully.', 'success')
        return redirect(url_for('inventory.uoms'))
    
    return render_template('inventory/uom_form.html')

@inventory_bp.route('/uoms/<int:uom_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_uom(uom_id):
    """Edit a unit of measure"""
    if not current_user.has_permission(Role.CAN_EDIT):
        flash('You do not have permission to edit units of measure.', 'danger')
        return redirect(url_for('inventory.uoms'))
    
    uom = UnitOfMeasure.query.get_or_404(uom_id)
    
    if request.method == 'POST':
        name = request.form.get('name')
        abbreviation = request.form.get('abbreviation')
        
        # Check if changes would conflict with existing UOM
        existing_uom = UnitOfMeasure.query.filter(
            ((UnitOfMeasure.name == name) | (UnitOfMeasure.abbreviation == abbreviation)) &
            (UnitOfMeasure.id != uom_id)
        ).first()
        
        if existing_uom:
            flash('A unit of measure with that name or abbreviation already exists.', 'danger')
            return render_template('inventory/uom_form.html', uom=uom)
        
        uom.name = name
        uom.abbreviation = abbreviation
        
        db.session.commit()
        
        flash('Unit of measure updated successfully.', 'success')
        return redirect(url_for('inventory.uoms'))
    
    return render_template('inventory/uom_form.html', uom=uom)

@inventory_bp.route('/uoms/<int:uom_id>/delete', methods=['POST'])
@login_required
def delete_uom(uom_id):
    """Delete a unit of measure"""
    if not current_user.has_permission(Role.CAN_DELETE):
        flash('You do not have permission to delete units of measure.', 'danger')
        return redirect(url_for('inventory.uoms'))
    
    uom = UnitOfMeasure.query.get_or_404(uom_id)
    
    # Check if there are products using this UOM
    products = Product.query.filter_by(uom_id=uom_id).count()
    if products > 0:
        flash(f'Cannot delete unit of measure. It is used by {products} products.', 'danger')
        return redirect(url_for('inventory.uoms'))
    
    db.session.delete(uom)
    db.session.commit()
    
    flash('Unit of measure deleted successfully.', 'success')
    return redirect(url_for('inventory.uoms'))

# Warehouses
@inventory_bp.route('/warehouses')
@login_required
def warehouses():
    """List warehouses"""
    warehouses = Warehouse.query.all()
    return render_template('inventory/warehouses.html', warehouses=warehouses)

@inventory_bp.route('/warehouses/create', methods=['GET', 'POST'])
@login_required
def create_warehouse():
    """Create a new warehouse"""
    if not current_user.has_permission(Role.CAN_CREATE):
        flash('You do not have permission to create warehouses.', 'danger')
        return redirect(url_for('inventory.warehouses'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        code = request.form.get('code')
        address = request.form.get('address')
        
        # Check if warehouse code already exists
        existing_warehouse = Warehouse.query.filter_by(code=code).first()
        if existing_warehouse:
            flash('A warehouse with that code already exists.', 'danger')
            return render_template('inventory/warehouse_form.html')
        
        warehouse = Warehouse(
            name=name,
            code=code,
            address=address,
            is_active=True,
            created_by_id=current_user.id
        )
        
        db.session.add(warehouse)
        db.session.commit()
        
        flash('Warehouse created successfully.', 'success')
        return redirect(url_for('inventory.warehouses'))
    
    return render_template('inventory/warehouse_form.html')

@inventory_bp.route('/warehouses/<int:warehouse_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_warehouse(warehouse_id):
    """Edit a warehouse"""
    if not current_user.has_permission(Role.CAN_EDIT):
        flash('You do not have permission to edit warehouses.', 'danger')
        return redirect(url_for('inventory.warehouses'))
    
    warehouse = Warehouse.query.get_or_404(warehouse_id)
    
    if request.method == 'POST':
        name = request.form.get('name')
        code = request.form.get('code')
        address = request.form.get('address')
        is_active = 'is_active' in request.form
        
        # Check if code change would conflict with existing warehouse
        if code != warehouse.code:
            existing_warehouse = Warehouse.query.filter_by(code=code).first()
            if existing_warehouse:
                flash('A warehouse with that code already exists.', 'danger')
                return render_template('inventory/warehouse_form.html', warehouse=warehouse)
        
        warehouse.name = name
        warehouse.code = code
        warehouse.address = address
        warehouse.is_active = is_active
        
        db.session.commit()
        
        flash('Warehouse updated successfully.', 'success')
        return redirect(url_for('inventory.warehouses'))
    
    return render_template('inventory/warehouse_form.html', warehouse=warehouse)

@inventory_bp.route('/warehouses/<int:warehouse_id>/delete', methods=['POST'])
@login_required
def delete_warehouse(warehouse_id):
    """Delete a warehouse"""
    if not current_user.has_permission(Role.CAN_DELETE):
        flash('You do not have permission to delete warehouses.', 'danger')
        return redirect(url_for('inventory.warehouses'))
    
    warehouse = Warehouse.query.get_or_404(warehouse_id)
    
    # Check if there are POs using this warehouse
    purchase_orders = PurchaseOrder.query.filter_by(warehouse_id=warehouse_id).count()
    if purchase_orders > 0:
        flash(f'Cannot delete warehouse. It is used by {purchase_orders} purchase orders.', 'danger')
        return redirect(url_for('inventory.warehouses'))
    
    db.session.delete(warehouse)
    db.session.commit()
    
    flash('Warehouse deleted successfully.', 'success')
    return redirect(url_for('inventory.warehouses'))

# Products
@inventory_bp.route('/products')
@login_required
def products():
    """List products"""
    # Get filters
    category_id = request.args.get('category_id')
    search_query = request.args.get('search')
    show_inactive = 'show_inactive' in request.args
    
    # Base query
    query = Product.query
    
    # Apply filters
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    if search_query:
        query = query.filter(
            (Product.name.ilike(f'%{search_query}%')) |
            (Product.sku.ilike(f'%{search_query}%')) |
            (Product.description.ilike(f'%{search_query}%'))
        )
    
    if not show_inactive:
        query = query.filter_by(is_active=True)
    
    # Order by name
    products = query.order_by(Product.name).all()
    
    # Get categories for filter dropdown
    categories = ProductCategory.query.order_by(ProductCategory.name).all()
    
    return render_template(
        'inventory/products.html',
        products=products,
        categories=categories,
        selected_category=category_id,
        search_query=search_query,
        show_inactive=show_inactive
    )

@inventory_bp.route('/products/create', methods=['GET', 'POST'])
@login_required
def create_product():
    """Create a new product"""
    if not current_user.has_permission(Role.CAN_CREATE):
        flash('You do not have permission to create products.', 'danger')
        return redirect(url_for('inventory.products'))
    
    if request.method == 'POST':
        # Get form data
        name = request.form.get('name')
        sku = request.form.get('sku') or generate_product_sku()
        description = request.form.get('description')
        category_id = request.form.get('category_id') or None
        uom_id = request.form.get('uom_id')
        cost_price = request.form.get('cost_price', 0)
        sales_price = request.form.get('sales_price', 0)
        reorder_level = request.form.get('reorder_level', 0)
        preferred_vendor_id = request.form.get('preferred_vendor_id') or None
        asset_account_id = request.form.get('asset_account_id') or None
        expense_account_id = request.form.get('expense_account_id') or None
        revenue_account_id = request.form.get('revenue_account_id') or None
        
        # Validate SKU uniqueness
        existing_product = Product.query.filter_by(sku=sku).first()
        if existing_product:
            flash('A product with that SKU already exists.', 'danger')
            return redirect(url_for('inventory.create_product'))
        
        # Create product
        product = Product(
            name=name,
            sku=sku,
            description=description,
            category_id=category_id,
            uom_id=uom_id,
            cost_price=cost_price,
            sales_price=sales_price,
            reorder_level=reorder_level,
            preferred_vendor_id=preferred_vendor_id,
            asset_account_id=asset_account_id,
            expense_account_id=expense_account_id,
            revenue_account_id=revenue_account_id,
            is_active=True,
            created_by_id=current_user.id
        )
        
        db.session.add(product)
        db.session.commit()
        
        flash('Product created successfully.', 'success')
        return redirect(url_for('inventory.view_product', product_id=product.id))
    
    # Get data for dropdowns
    categories = ProductCategory.query.order_by(ProductCategory.name).all()
    uoms = UnitOfMeasure.query.order_by(UnitOfMeasure.name).all()
    
    # Get vendors (entities of type Vendor)
    vendor_type = EntityType.query.filter_by(name=EntityType.VENDOR).first()
    if vendor_type:
        vendors = Entity.query.filter_by(entity_type_id=vendor_type.id).order_by(Entity.name).all()
    else:
        vendors = []
    
    # Get accounts by type
    asset_type = AccountType.query.filter_by(name=AccountType.ASSET).first()
    expense_type = AccountType.query.filter_by(name=AccountType.EXPENSE).first()
    revenue_type = AccountType.query.filter_by(name=AccountType.REVENUE).first()
    
    asset_accounts = []
    if asset_type:
        asset_accounts = Account.query.filter_by(account_type_id=asset_type.id, is_active=True).order_by(Account.code).all()
    
    expense_accounts = []
    if expense_type:
        expense_accounts = Account.query.filter_by(account_type_id=expense_type.id, is_active=True).order_by(Account.code).all()
    
    revenue_accounts = []
    if revenue_type:
        revenue_accounts = Account.query.filter_by(account_type_id=revenue_type.id, is_active=True).order_by(Account.code).all()
    
    return render_template(
        'inventory/product_form.html',
        categories=categories,
        uoms=uoms,
        vendors=vendors,
        asset_accounts=asset_accounts,
        expense_accounts=expense_accounts,
        revenue_accounts=revenue_accounts,
        new_sku=generate_product_sku()
    )

@inventory_bp.route('/products/<int:product_id>')
@login_required
def view_product(product_id):
    """View a product"""
    product = Product.query.get_or_404(product_id)
    
    # Get recent transactions
    recent_transactions = InventoryTransaction.query.filter_by(
        product_id=product_id
    ).order_by(
        InventoryTransaction.transaction_date.desc()
    ).limit(10).all()
    
    return render_template(
        'inventory/product_view.html',
        product=product,
        recent_transactions=recent_transactions
    )

@inventory_bp.route('/products/<int:product_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    """Edit a product"""
    if not current_user.has_permission(Role.CAN_EDIT):
        flash('You do not have permission to edit products.', 'danger')
        return redirect(url_for('inventory.products'))
    
    product = Product.query.get_or_404(product_id)
    
    if request.method == 'POST':
        # Get form data
        name = request.form.get('name')
        sku = request.form.get('sku')
        description = request.form.get('description')
        category_id = request.form.get('category_id') or None
        uom_id = request.form.get('uom_id')
        cost_price = request.form.get('cost_price', 0)
        sales_price = request.form.get('sales_price', 0)
        reorder_level = request.form.get('reorder_level', 0)
        preferred_vendor_id = request.form.get('preferred_vendor_id') or None
        asset_account_id = request.form.get('asset_account_id') or None
        expense_account_id = request.form.get('expense_account_id') or None
        revenue_account_id = request.form.get('revenue_account_id') or None
        is_active = 'is_active' in request.form
        
        # Validate SKU uniqueness if changed
        if sku != product.sku:
            existing_product = Product.query.filter_by(sku=sku).first()
            if existing_product:
                flash('A product with that SKU already exists.', 'danger')
                return redirect(url_for('inventory.edit_product', product_id=product_id))
        
        # Update product
        product.name = name
        product.sku = sku
        product.description = description
        product.category_id = category_id
        product.uom_id = uom_id
        product.cost_price = cost_price
        product.sales_price = sales_price
        product.reorder_level = reorder_level
        product.preferred_vendor_id = preferred_vendor_id
        product.asset_account_id = asset_account_id
        product.expense_account_id = expense_account_id
        product.revenue_account_id = revenue_account_id
        product.is_active = is_active
        
        db.session.commit()
        
        flash('Product updated successfully.', 'success')
        return redirect(url_for('inventory.view_product', product_id=product.id))
    
    # Get data for dropdowns
    categories = ProductCategory.query.order_by(ProductCategory.name).all()
    uoms = UnitOfMeasure.query.order_by(UnitOfMeasure.name).all()
    
    # Get vendors (entities of type Vendor)
    vendor_type = EntityType.query.filter_by(name=EntityType.VENDOR).first()
    if vendor_type:
        vendors = Entity.query.filter_by(entity_type_id=vendor_type.id).order_by(Entity.name).all()
    else:
        vendors = []
    
    # Get accounts by type
    asset_type = AccountType.query.filter_by(name=AccountType.ASSET).first()
    expense_type = AccountType.query.filter_by(name=AccountType.EXPENSE).first()
    revenue_type = AccountType.query.filter_by(name=AccountType.REVENUE).first()
    
    asset_accounts = []
    if asset_type:
        asset_accounts = Account.query.filter_by(account_type_id=asset_type.id, is_active=True).order_by(Account.code).all()
    
    expense_accounts = []
    if expense_type:
        expense_accounts = Account.query.filter_by(account_type_id=expense_type.id, is_active=True).order_by(Account.code).all()
    
    revenue_accounts = []
    if revenue_type:
        revenue_accounts = Account.query.filter_by(account_type_id=revenue_type.id, is_active=True).order_by(Account.code).all()
    
    return render_template(
        'inventory/product_form.html',
        product=product,
        categories=categories,
        uoms=uoms,
        vendors=vendors,
        asset_accounts=asset_accounts,
        expense_accounts=expense_accounts,
        revenue_accounts=revenue_accounts
    )

@inventory_bp.route('/products/<int:product_id>/delete', methods=['POST'])
@login_required
def delete_product(product_id):
    """Delete a product"""
    if not current_user.has_permission(Role.CAN_DELETE):
        flash('You do not have permission to delete products.', 'danger')
        return redirect(url_for('inventory.products'))
    
    product = Product.query.get_or_404(product_id)
    
    # Check if there are inventory transactions using this product
    transactions = InventoryTransaction.query.filter_by(product_id=product_id).count()
    if transactions > 0:
        flash(f'Cannot delete product. It has {transactions} inventory transactions.', 'danger')
        return redirect(url_for('inventory.products'))
    
    db.session.delete(product)
    db.session.commit()
    
    flash('Product deleted successfully.', 'success')
    return redirect(url_for('inventory.products'))

@inventory_bp.route('/products/<int:product_id>/adjust', methods=['GET', 'POST'])
@login_required
def adjust_inventory(product_id):
    """Adjust inventory for a product"""
    if not current_user.has_permission(Role.CAN_EDIT):
        flash('You do not have permission to adjust inventory.', 'danger')
        return redirect(url_for('inventory.products'))
    
    product = Product.query.get_or_404(product_id)
    
    if request.method == 'POST':
        # Get form data
        adjustment_type = request.form.get('adjustment_type')  # 'increase' or 'decrease'
        quantity = float(request.form.get('quantity', 0))
        reason = request.form.get('reason')
        location = request.form.get('location')
        unit_price = float(request.form.get('unit_price', 0)) if 'unit_price' in request.form else None
        
        if quantity <= 0:
            flash('Quantity must be greater than zero.', 'danger')
            return redirect(url_for('inventory.adjust_inventory', product_id=product_id))
        
        # Determine transaction type
        transaction_type = 'IN' if adjustment_type == 'increase' else 'OUT'
        
        # Get adjustment transaction type
        adjustment_type_obj = InventoryTransactionType.query.filter_by(name=InventoryTransactionType.ADJUSTMENT).first()
        if not adjustment_type_obj:
            adjustment_type_obj = InventoryTransactionType(name=InventoryTransactionType.ADJUSTMENT)
            db.session.add(adjustment_type_obj)
            db.session.flush()
        
        # Create journal entry if needed (only for material adjustments)
        journal_entry = None
        if unit_price and product.asset_account_id:
            # Create journal entry
            journal_entry = JournalEntry(
                entry_date=datetime.now().date(),
                reference=f"ADJ-{product.sku}",
                description=f"Inventory adjustment for {product.name}",
                is_posted=True,
                created_by_id=current_user.id
            )
            
            db.session.add(journal_entry)
            db.session.flush()
            
            # Add journal items
            journal_items = []
            
            # Calculate total amount
            total_amount = quantity * unit_price
            
            # Get inventory account
            inventory_account_id = product.asset_account_id
            
            # Get adjustment account (expense or income)
            asset_type = AccountType.query.filter_by(name=AccountType.ASSET).first()
            expense_type = AccountType.query.filter_by(name=AccountType.EXPENSE).first()
            revenue_type = AccountType.query.filter_by(name=AccountType.REVENUE).first()
            
            # Default adjustment account (should be configured by admin)
            adjustment_account = None
            
            if adjustment_type == 'increase':
                # Credit an expense or debit an asset
                if expense_type:
                    # Find a suitable expense account
                    adjustment_account = Account.query.filter(
                        Account.account_type_id == expense_type.id,
                        Account.name.ilike('%inventory adjustment%')
                    ).first()
                
                if not adjustment_account and product.expense_account_id:
                    adjustment_account = Account.query.get(product.expense_account_id)
                
                if not adjustment_account and asset_type:
                    # Create a default adjustment account if needed
                    adjustment_account = Account.query.filter(
                        Account.account_type_id == expense_type.id,
                        Account.name.ilike('%inventory adjustment%')
                    ).first()
                    
                    if not adjustment_account:
                        adjustment_account = Account(
                            code='5500',
                            name='Inventory Adjustment',
                            account_type_id=expense_type.id,
                            is_active=True,
                            created_by_id=current_user.id
                        )
                        db.session.add(adjustment_account)
                        db.session.flush()
            else:
                # Debit an expense or credit a revenue
                if revenue_type:
                    # Find a suitable revenue account
                    adjustment_account = Account.query.filter(
                        Account.account_type_id == revenue_type.id,
                        Account.name.ilike('%inventory adjustment%')
                    ).first()
                
                if not adjustment_account and product.revenue_account_id:
                    adjustment_account = Account.query.get(product.revenue_account_id)
                
                if not adjustment_account and revenue_type:
                    # Create a default adjustment account if needed
                    adjustment_account = Account.query.filter(
                        Account.account_type_id == revenue_type.id,
                        Account.name.ilike('%inventory adjustment%')
                    ).first()
                    
                    if not adjustment_account:
                        adjustment_account = Account(
                            code='4900',
                            name='Inventory Adjustment',
                            account_type_id=revenue_type.id,
                            is_active=True,
                            created_by_id=current_user.id
                        )
                        db.session.add(adjustment_account)
                        db.session.flush()
            
            if adjustment_type == 'increase':
                # Debit inventory (increase asset)
                inventory_item = JournalItem(
                    journal_entry_id=journal_entry.id,
                    account_id=inventory_account_id,
                    description=f"Inventory adjustment increase for {product.name}",
                    debit_amount=total_amount,
                    credit_amount=0
                )
                journal_items.append(inventory_item)
                
                # Credit adjustment account
                adjustment_item = JournalItem(
                    journal_entry_id=journal_entry.id,
                    account_id=adjustment_account.id,
                    description=f"Inventory adjustment increase for {product.name}",
                    debit_amount=0,
                    credit_amount=total_amount
                )
                journal_items.append(adjustment_item)
            else:
                # Credit inventory (decrease asset)
                inventory_item = JournalItem(
                    journal_entry_id=journal_entry.id,
                    account_id=inventory_account_id,
                    description=f"Inventory adjustment decrease for {product.name}",
                    debit_amount=0,
                    credit_amount=total_amount
                )
                journal_items.append(inventory_item)
                
                # Debit adjustment account
                adjustment_item = JournalItem(
                    journal_entry_id=journal_entry.id,
                    account_id=adjustment_account.id,
                    description=f"Inventory adjustment decrease for {product.name}",
                    debit_amount=total_amount,
                    credit_amount=0
                )
                journal_items.append(adjustment_item)
            
            db.session.add_all(journal_items)
        
        # Record inventory transaction
        record_inventory_transaction(
            product_id=product.id,
            quantity=quantity,
            transaction_type=transaction_type,
            transaction_type_id=adjustment_type_obj.id,
            unit_price=unit_price,
            location=location,
            reference_type='Adjustment',
            notes=reason,
            journal_entry_id=journal_entry.id if journal_entry else None,
            created_by_id=current_user.id
        )
        
        flash('Inventory adjustment recorded successfully.', 'success')
        return redirect(url_for('inventory.view_product', product_id=product_id))
    
    # Get locations (warehouses)
    warehouses = Warehouse.query.filter_by(is_active=True).order_by(Warehouse.name).all()
    
    return render_template(
        'inventory/adjust_inventory.html',
        product=product,
        warehouses=warehouses,
        current_stock=product.current_stock
    )

@inventory_bp.route('/products/<int:product_id>/transactions')
@login_required
def product_transactions(product_id):
    """View all transactions for a product"""
    product = Product.query.get_or_404(product_id)
    
    # Get filters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    transaction_type = request.args.get('transaction_type')
    
    # Parse dates
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    else:
        start_date = (datetime.now() - timedelta(days=30)).date()
    
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    else:
        end_date = datetime.now().date()
    
    # Base query
    query = InventoryTransaction.query.filter_by(product_id=product_id)
    
    # Apply date filters
    query = query.filter(
        func.date(InventoryTransaction.transaction_date) >= start_date,
        func.date(InventoryTransaction.transaction_date) <= end_date
    )
    
    # Apply transaction type filter
    if transaction_type:
        query = query.filter_by(transaction_type=transaction_type)
    
    # Get transactions ordered by date
    transactions = query.order_by(InventoryTransaction.transaction_date.desc()).all()
    
    return render_template(
        'inventory/product_transactions.html',
        product=product,
        transactions=transactions,
        start_date=start_date,
        end_date=end_date,
        transaction_type=transaction_type
    )

# Purchase Orders
@inventory_bp.route('/purchase-orders')
@login_required
def purchase_orders():
    """List purchase orders"""
    # Get filters
    status = request.args.get('status')
    vendor_id = request.args.get('vendor_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Base query
    query = PurchaseOrder.query
    
    # Apply filters
    if status:
        query = query.join(PurchaseOrderStatus).filter(PurchaseOrderStatus.name == status)
    
    if vendor_id:
        query = query.filter_by(vendor_id=vendor_id)
    
    if start_date:
        query = query.filter(PurchaseOrder.order_date >= datetime.strptime(start_date, '%Y-%m-%d').date())
    
    if end_date:
        query = query.filter(PurchaseOrder.order_date <= datetime.strptime(end_date, '%Y-%m-%d').date())
    
    # Get POs ordered by date
    purchase_orders = query.order_by(PurchaseOrder.order_date.desc()).all()
    
    # Get data for filter dropdowns
    statuses = PurchaseOrderStatus.query.all()
    
    # Get vendors
    vendor_type = EntityType.query.filter_by(name=EntityType.VENDOR).first()
    vendors = []
    if vendor_type:
        vendors = Entity.query.filter_by(entity_type_id=vendor_type.id).order_by(Entity.name).all()
    
    return render_template(
        'inventory/purchase_orders.html',
        purchase_orders=purchase_orders,
        statuses=statuses,
        vendors=vendors,
        selected_status=status,
        selected_vendor=vendor_id,
        start_date=start_date,
        end_date=end_date
    )

@inventory_bp.route('/purchase-orders/create', methods=['GET', 'POST'])
@login_required
def create_purchase_order():
    """Create a new purchase order"""
    if not current_user.has_permission(Role.CAN_CREATE):
        flash('You do not have permission to create purchase orders.', 'danger')
        return redirect(url_for('inventory.purchase_orders'))
    
    if request.method == 'POST':
        # Get form data
        vendor_id = request.form.get('vendor_id')
        order_date = request.form.get('order_date')
        expected_delivery_date = request.form.get('expected_delivery_date') or None
        shipping_address = request.form.get('shipping_address')
        warehouse_id = request.form.get('warehouse_id') or None
        notes = request.form.get('notes')
        total_amount = float(request.form.get('total_amount', 0))
        
        # Validate required fields
        if not vendor_id or not order_date:
            flash('Vendor and order date are required.', 'danger')
            return redirect(url_for('inventory.create_purchase_order'))
        
        # Parse dates
        order_date = datetime.strptime(order_date, '%Y-%m-%d').date()
        if expected_delivery_date:
            expected_delivery_date = datetime.strptime(expected_delivery_date, '%Y-%m-%d').date()
        
        # Get draft status
        draft_status = PurchaseOrderStatus.query.filter_by(name=PurchaseOrderStatus.DRAFT).first()
        if not draft_status:
            # Create statuses if they don't exist
            draft_status = PurchaseOrderStatus(name=PurchaseOrderStatus.DRAFT)
            submitted_status = PurchaseOrderStatus(name=PurchaseOrderStatus.SUBMITTED)
            approved_status = PurchaseOrderStatus(name=PurchaseOrderStatus.APPROVED)
            partially_received_status = PurchaseOrderStatus(name=PurchaseOrderStatus.PARTIALLY_RECEIVED)
            received_status = PurchaseOrderStatus(name=PurchaseOrderStatus.RECEIVED)
            cancelled_status = PurchaseOrderStatus(name=PurchaseOrderStatus.CANCELLED)
            
            db.session.add_all([draft_status, submitted_status, approved_status, 
                                partially_received_status, received_status, cancelled_status])
            db.session.commit()
        
        # Generate PO number
        po_number = generate_po_number()
        
        # Create purchase order
        purchase_order = PurchaseOrder(
            po_number=po_number,
            vendor_id=vendor_id,
            order_date=order_date,
            expected_delivery_date=expected_delivery_date,
            status_id=draft_status.id,
            shipping_address=shipping_address,
            warehouse_id=warehouse_id,
            total_amount=total_amount,
            notes=notes,
            created_by_id=current_user.id
        )
        
        db.session.add(purchase_order)
        db.session.flush()  # Get ID without committing
        
        # Process line items
        items = []
        
        for key, value in request.form.items():
            if key.startswith('items[') and key.endswith('[product_id]'):
                # Extract the index from the key
                index = key.split('[')[1].split(']')[0]
                
                product_id = value
                description = request.form.get(f'items[{index}][description]', '')
                quantity = float(request.form.get(f'items[{index}][quantity]', 0))
                unit_price = float(request.form.get(f'items[{index}][unit_price]', 0))
                tax_rate = float(request.form.get(f'items[{index}][tax_rate]', 0))
                
                # Skip empty items
                if not product_id or quantity <= 0:
                    continue
                
                # Create purchase order item
                item = PurchaseOrderItem(
                    po_id=purchase_order.id,
                    product_id=product_id,
                    description=description,
                    quantity_ordered=quantity,
                    quantity_received=0,
                    unit_price=unit_price,
                    tax_rate=tax_rate
                )
                
                items.append(item)
        
        if not items:
            db.session.rollback()
            flash('Purchase order must have at least one item.', 'danger')
            return redirect(url_for('inventory.create_purchase_order'))
        
        # Add all items
        db.session.add_all(items)
        db.session.commit()
        
        flash('Purchase order created successfully.', 'success')
        return redirect(url_for('inventory.view_purchase_order', po_id=purchase_order.id))
    
    # Get data for form
    # Get vendors
    vendor_type = EntityType.query.filter_by(name=EntityType.VENDOR).first()
    vendors = []
    if vendor_type:
        vendors = Entity.query.filter_by(entity_type_id=vendor_type.id).order_by(Entity.name).all()
    
    # Get warehouses
    warehouses = Warehouse.query.filter_by(is_active=True).order_by(Warehouse.name).all()
    
    # Get products
    products = Product.query.filter_by(is_active=True).order_by(Product.name).all()
    
    return render_template(
        'inventory/purchase_order_form.html',
        vendors=vendors,
        warehouses=warehouses,
        products=products,
        today=datetime.now().strftime('%Y-%m-%d')
    )

@inventory_bp.route('/purchase-orders/<int:po_id>')
@login_required
def view_purchase_order(po_id):
    """View a purchase order"""
    purchase_order = PurchaseOrder.query.get_or_404(po_id)
    
    return render_template(
        'inventory/purchase_order_view.html',
        purchase_order=purchase_order
    )

@inventory_bp.route('/purchase-orders/<int:po_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_purchase_order(po_id):
    """Edit a purchase order"""
    if not current_user.has_permission(Role.CAN_EDIT):
        flash('You do not have permission to edit purchase orders.', 'danger')
        return redirect(url_for('inventory.purchase_orders'))
    
    purchase_order = PurchaseOrder.query.get_or_404(po_id)
    
    # Can only edit draft POs
    if purchase_order.status.name != PurchaseOrderStatus.DRAFT:
        flash('Cannot edit a purchase order that is not in draft status.', 'danger')
        return redirect(url_for('inventory.view_purchase_order', po_id=po_id))
    
    if request.method == 'POST':
        # Get form data
        vendor_id = request.form.get('vendor_id')
        order_date = request.form.get('order_date')
        expected_delivery_date = request.form.get('expected_delivery_date') or None
        shipping_address = request.form.get('shipping_address')
        warehouse_id = request.form.get('warehouse_id') or None
        notes = request.form.get('notes')
        total_amount = float(request.form.get('total_amount', 0))
        
        # Validate required fields
        if not vendor_id or not order_date:
            flash('Vendor and order date are required.', 'danger')
            return redirect(url_for('inventory.edit_purchase_order', po_id=po_id))
        
        # Parse dates
        order_date = datetime.strptime(order_date, '%Y-%m-%d').date()
        if expected_delivery_date:
            expected_delivery_date = datetime.strptime(expected_delivery_date, '%Y-%m-%d').date()
        
        # Update purchase order
        purchase_order.vendor_id = vendor_id
        purchase_order.order_date = order_date
        purchase_order.expected_delivery_date = expected_delivery_date
        purchase_order.shipping_address = shipping_address
        purchase_order.warehouse_id = warehouse_id
        purchase_order.notes = notes
        purchase_order.total_amount = total_amount
        
        # Delete existing items
        for item in purchase_order.items:
            db.session.delete(item)
        
        # Process line items
        items = []
        
        for key, value in request.form.items():
            if key.startswith('items[') and key.endswith('[product_id]'):
                # Extract the index from the key
                index = key.split('[')[1].split(']')[0]
                
                product_id = value
                description = request.form.get(f'items[{index}][description]', '')
                quantity = float(request.form.get(f'items[{index}][quantity]', 0))
                unit_price = float(request.form.get(f'items[{index}][unit_price]', 0))
                tax_rate = float(request.form.get(f'items[{index}][tax_rate]', 0))
                
                # Skip empty items
                if not product_id or quantity <= 0:
                    continue
                
                # Create purchase order item
                item = PurchaseOrderItem(
                    po_id=purchase_order.id,
                    product_id=product_id,
                    description=description,
                    quantity_ordered=quantity,
                    quantity_received=0,
                    unit_price=unit_price,
                    tax_rate=tax_rate
                )
                
                items.append(item)
        
        if not items:
            flash('Purchase order must have at least one item.', 'danger')
            return redirect(url_for('inventory.edit_purchase_order', po_id=po_id))
        
        # Add all items
        db.session.add_all(items)
        db.session.commit()
        
        flash('Purchase order updated successfully.', 'success')
        return redirect(url_for('inventory.view_purchase_order', po_id=po_id))
    
    # Get data for form
    # Get vendors
    vendor_type = EntityType.query.filter_by(name=EntityType.VENDOR).first()
    vendors = []
    if vendor_type:
        vendors = Entity.query.filter_by(entity_type_id=vendor_type.id).order_by(Entity.name).all()
    
    # Get warehouses
    warehouses = Warehouse.query.filter_by(is_active=True).order_by(Warehouse.name).all()
    
    # Get products
    products = Product.query.filter_by(is_active=True).order_by(Product.name).all()
    
    return render_template(
        'inventory/purchase_order_form.html',
        purchase_order=purchase_order,
        vendors=vendors,
        warehouses=warehouses,
        products=products
    )

@inventory_bp.route('/purchase-orders/<int:po_id>/submit', methods=['POST'])
@login_required
def submit_purchase_order(po_id):
    """Submit a purchase order"""
    if not current_user.has_permission(Role.CAN_EDIT):
        flash('You do not have permission to submit purchase orders.', 'danger')
        return redirect(url_for('inventory.purchase_orders'))
    
    purchase_order = PurchaseOrder.query.get_or_404(po_id)
    
    # Can only submit draft POs
    if purchase_order.status.name != PurchaseOrderStatus.DRAFT:
        flash('Cannot submit a purchase order that is not in draft status.', 'danger')
        return redirect(url_for('inventory.view_purchase_order', po_id=po_id))
    
    # Get submitted status
    submitted_status = PurchaseOrderStatus.query.filter_by(name=PurchaseOrderStatus.SUBMITTED).first()
    
    # Update status
    purchase_order.status_id = submitted_status.id
    db.session.commit()
    
    flash('Purchase order submitted for approval.', 'success')
    return redirect(url_for('inventory.view_purchase_order', po_id=po_id))

@inventory_bp.route('/purchase-orders/<int:po_id>/approve', methods=['POST'])
@login_required
def approve_purchase_order(po_id):
    """Approve a purchase order"""
    if not current_user.has_permission(Role.CAN_APPROVE):
        flash('You do not have permission to approve purchase orders.', 'danger')
        return redirect(url_for('inventory.purchase_orders'))
    
    purchase_order = PurchaseOrder.query.get_or_404(po_id)
    
    # Can only approve submitted POs
    if purchase_order.status.name != PurchaseOrderStatus.SUBMITTED:
        flash('Cannot approve a purchase order that is not submitted.', 'danger')
        return redirect(url_for('inventory.view_purchase_order', po_id=po_id))
    
    # Get approved status
    approved_status = PurchaseOrderStatus.query.filter_by(name=PurchaseOrderStatus.APPROVED).first()
    
    # Update status
    purchase_order.status_id = approved_status.id
    db.session.commit()
    
    flash('Purchase order approved.', 'success')
    return redirect(url_for('inventory.view_purchase_order', po_id=po_id))

@inventory_bp.route('/purchase-orders/<int:po_id>/cancel', methods=['POST'])
@login_required
def cancel_purchase_order(po_id):
    """Cancel a purchase order"""
    if not current_user.has_permission(Role.CAN_APPROVE):
        flash('You do not have permission to cancel purchase orders.', 'danger')
        return redirect(url_for('inventory.purchase_orders'))
    
    purchase_order = PurchaseOrder.query.get_or_404(po_id)
    
    # Cannot cancel POs that are partially received or fully received
    if purchase_order.status.name in [PurchaseOrderStatus.PARTIALLY_RECEIVED, PurchaseOrderStatus.RECEIVED]:
        flash('Cannot cancel a purchase order that has already been received.', 'danger')
        return redirect(url_for('inventory.view_purchase_order', po_id=po_id))
    
    # Get cancelled status
    cancelled_status = PurchaseOrderStatus.query.filter_by(name=PurchaseOrderStatus.CANCELLED).first()
    
    # Update status
    purchase_order.status_id = cancelled_status.id
    db.session.commit()
    
    flash('Purchase order cancelled.', 'danger')
    return redirect(url_for('inventory.view_purchase_order', po_id=po_id))

@inventory_bp.route('/purchase-orders/<int:po_id>/receive', methods=['GET', 'POST'])
@login_required
def receive_purchase_order(po_id):
    """Receive inventory against a purchase order"""
    if not current_user.has_permission(Role.CAN_EDIT):
        flash('You do not have permission to receive inventory.', 'danger')
        return redirect(url_for('inventory.purchase_orders'))
    
    purchase_order = PurchaseOrder.query.get_or_404(po_id)
    
    # Can only receive approved or partially received POs
    if purchase_order.status.name not in [PurchaseOrderStatus.APPROVED, PurchaseOrderStatus.PARTIALLY_RECEIVED]:
        flash('Cannot receive inventory for a purchase order that is not approved or partially received.', 'danger')
        return redirect(url_for('inventory.view_purchase_order', po_id=po_id))
    
    if request.method == 'POST':
        # Get form data
        receive_date = request.form.get('receive_date')
        location = request.form.get('location')
        notes = request.form.get('notes')
        
        # Validate required fields
        if not receive_date:
            flash('Receive date is required.', 'danger')
            return redirect(url_for('inventory.receive_purchase_order', po_id=po_id))
        
        # Parse date
        receive_date = datetime.strptime(receive_date, '%Y-%m-%d').date()
        
        # Get transaction type for purchases
        purchase_type = InventoryTransactionType.query.filter_by(name=InventoryTransactionType.PURCHASE).first()
        if not purchase_type:
            purchase_type = InventoryTransactionType(name=InventoryTransactionType.PURCHASE)
            db.session.add(purchase_type)
            db.session.flush()
        
        # Create journal entry
        asset_type = AccountType.query.filter_by(name=AccountType.ASSET).first()
        liability_type = AccountType.query.filter_by(name=AccountType.LIABILITY).first()
        
        # Get accounts payable account
        ap_account = None
        if liability_type:
            ap_account = Account.query.filter(
                Account.account_type_id == liability_type.id,
                Account.name.like('%Accounts Payable%')
            ).first()
        
        if not ap_account and liability_type:
            ap_account = Account(
                code='2000',
                name='Accounts Payable',
                account_type_id=liability_type.id,
                is_active=True,
                created_by_id=current_user.id
            )
            db.session.add(ap_account)
            db.session.flush()
        
        # Create journal entry
        journal_entry = JournalEntry(
            entry_date=receive_date,
            reference=purchase_order.po_number,
            description=f"Inventory receipt for PO #{purchase_order.po_number} from {purchase_order.vendor.name}",
            is_posted=True,
            created_by_id=current_user.id
        )
        
        db.session.add(journal_entry)
        db.session.flush()
        
        # Add journal items and record inventory transactions
        journal_items = []
        total_received_value = 0
        all_items_received = True
        
        for key, value in request.form.items():
            if key.startswith('receive_quantity_') and value:
                # Extract the item ID from the key
                item_id = int(key.replace('receive_quantity_', ''))
                quantity_to_receive = float(value)
                
                # Skip items with zero quantity
                if quantity_to_receive <= 0:
                    continue
                
                # Get the PO item
                po_item = PurchaseOrderItem.query.get(item_id)
                if not po_item or po_item.po_id != purchase_order.id:
                    continue
                
                # Validate the quantity doesn't exceed what's remaining to be received
                remaining_to_receive = float(po_item.quantity_ordered) - float(po_item.quantity_received)
                if quantity_to_receive > remaining_to_receive:
                    quantity_to_receive = remaining_to_receive
                
                # Update the received quantity
                po_item.quantity_received = float(po_item.quantity_received) + quantity_to_receive
                
                # Check if all items are fully received
                if float(po_item.quantity_received) < float(po_item.quantity_ordered):
                    all_items_received = False
                
                # Calculate the value of the received items
                line_value = quantity_to_receive * float(po_item.unit_price)
                total_received_value += line_value
                
                # Record inventory transaction
                record_inventory_transaction(
                    product_id=po_item.product_id,
                    quantity=quantity_to_receive,
                    transaction_type='IN',
                    transaction_type_id=purchase_type.id,
                    unit_price=po_item.unit_price,
                    location=location,
                    reference_type='PurchaseOrder',
                    reference_id=purchase_order.id,
                    notes=notes,
                    journal_entry_id=journal_entry.id,
                    created_by_id=current_user.id
                )
                
                # Get the product's inventory account
                product = Product.query.get(po_item.product_id)
                if product and product.asset_account_id:
                    # Debit inventory account
                    inventory_item = JournalItem(
                        journal_entry_id=journal_entry.id,
                        account_id=product.asset_account_id,
                        description=f"Inventory receipt: {quantity_to_receive} x {product.name}",
                        debit_amount=line_value,
                        credit_amount=0
                    )
                    journal_items.append(inventory_item)
        
        if not journal_items:
            db.session.rollback()
            flash('No items were received.', 'warning')
            return redirect(url_for('inventory.receive_purchase_order', po_id=po_id))
        
        # Credit accounts payable for the total value
        ap_item = JournalItem(
            journal_entry_id=journal_entry.id,
            account_id=ap_account.id,
            description=f"Accounts payable for PO #{purchase_order.po_number}",
            debit_amount=0,
            credit_amount=total_received_value
        )
        journal_items.append(ap_item)
        
        # Add journal items
        db.session.add_all(journal_items)
        
        # Update purchase order status
        if all_items_received:
            received_status = PurchaseOrderStatus.query.filter_by(name=PurchaseOrderStatus.RECEIVED).first()
            purchase_order.status_id = received_status.id
        else:
            partially_received_status = PurchaseOrderStatus.query.filter_by(name=PurchaseOrderStatus.PARTIALLY_RECEIVED).first()
            purchase_order.status_id = partially_received_status.id
        
        # Link journal entry to purchase order if not already linked
        if not purchase_order.journal_entry_id:
            purchase_order.journal_entry_id = journal_entry.id
        
        db.session.commit()
        
        flash('Inventory received successfully.', 'success')
        return redirect(url_for('inventory.view_purchase_order', po_id=po_id))
    
    # Get warehouses for location dropdown
    warehouses = Warehouse.query.filter_by(is_active=True).order_by(Warehouse.name).all()
    
    return render_template(
        'inventory/receive_inventory.html',
        purchase_order=purchase_order,
        warehouses=warehouses,
        today=datetime.now().strftime('%Y-%m-%d')
    )

# Dashboard and reports
@inventory_bp.route('/')
@login_required
def dashboard():
    """Inventory dashboard"""
    # Get inventory value
    inventory_value = get_inventory_value()
    
    # Get low stock products
    low_stock = get_low_stock_products()
    
    # Get recent transactions
    recent_transactions = InventoryTransaction.query.order_by(
        InventoryTransaction.transaction_date.desc()
    ).limit(10).all()
    
    # Get POs by status
    po_status_counts = db.session.query(
        PurchaseOrderStatus.name, 
        func.count(PurchaseOrder.id)
    ).join(
        PurchaseOrder, PurchaseOrder.status_id == PurchaseOrderStatus.id
    ).group_by(
        PurchaseOrderStatus.name
    ).all()
    
    po_status_data = {name: count for name, count in po_status_counts}
    
    # Get inventory counts by category
    category_counts = db.session.query(
        ProductCategory.name,
        func.count(Product.id)
    ).join(
        Product, Product.category_id == ProductCategory.id
    ).filter(
        Product.is_active == True
    ).group_by(
        ProductCategory.name
    ).all()
    
    return render_template(
        'inventory/dashboard.html',
        inventory_value=inventory_value,
        low_stock=low_stock,
        recent_transactions=recent_transactions,
        po_status_data=po_status_data,
        category_counts=category_counts
    )

@inventory_bp.route('/reports/stock-valuation')
@login_required
def stock_valuation_report():
    """Stock valuation report"""
    # Get all active products
    products = Product.query.filter_by(is_active=True).order_by(Product.name).all()
    
    # Calculate valuation for each product
    valuation = []
    total_value = 0
    
    for product in products:
        stock = product.current_stock
        value = float(stock) * float(product.cost_price)
        
        if stock > 0:
            valuation.append({
                'id': product.id,
                'sku': product.sku,
                'name': product.name,
                'category': product.category.name if product.category else 'Uncategorized',
                'stock': stock,
                'uom': product.uom.abbreviation,
                'cost_price': float(product.cost_price),
                'value': value
            })
            
            total_value += value
    
    # Sort by value (descending)
    valuation.sort(key=lambda x: x['value'], reverse=True)
    
    return render_template(
        'inventory/stock_valuation_report.html',
        valuation=valuation,
        total_value=total_value
    )

@inventory_bp.route('/reports/low-stock')
@login_required
def low_stock_report():
    """Low stock report"""
    low_stock = get_low_stock_products()
    
    # Add more details to each item
    for item in low_stock:
        product = Product.query.get(item['id'])
        item['category'] = product.category.name if product.category else 'Uncategorized'
        item['preferred_vendor'] = product.preferred_vendor.name if product.preferred_vendor else 'None'
    
    return render_template(
        'inventory/low_stock_report.html',
        low_stock=low_stock
    )

# API endpoints for AJAX
@inventory_bp.route('/api/products/<int:product_id>/json')
@login_required
def get_product_json(product_id):
    """Get product details as JSON"""
    product = Product.query.get_or_404(product_id)
    
    return jsonify({
        'id': product.id,
        'sku': product.sku,
        'name': product.name,
        'description': product.description,
        'uom': product.uom.abbreviation,
        'cost_price': float(product.cost_price),
        'sales_price': float(product.sales_price),
        'current_stock': float(product.current_stock)
    })