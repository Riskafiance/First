from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from models import (
    Product, ProductCategory, UnitOfMeasure, InventoryTransaction, 
    InventoryTransactionType, Warehouse, PurchaseOrder, PurchaseOrderStatus,
    PurchaseOrderItem, Entity, EntityType, Account, AccountType, Role,
    JournalEntry, JournalItem
)
import utils
import core_utils
from datetime import datetime, timedelta
from sqlalchemy import func

inventory_bp = Blueprint('inventory', __name__)

@inventory_bp.route('/')
@login_required
def dashboard():
    """Inventory dashboard"""
    # Get inventory overview
    inventory_value = utils.get_inventory_value()
    
    # Get product categories
    categories = ProductCategory.query.order_by(ProductCategory.name).all()
    
    # Count products by category
    category_counts = []
    for category in categories:
        count = Product.query.filter_by(
            category_id=category.id, 
            is_active=True
        ).count()
        if count > 0:
            category_counts.append((category.name, count))
    
    # Add uncategorized products
    uncategorized_count = Product.query.filter_by(
        category_id=None, 
        is_active=True
    ).count()
    if uncategorized_count > 0:
        category_counts.append(('Uncategorized', uncategorized_count))
    
    # Sort by count (descending)
    category_counts = sorted(category_counts, key=lambda x: x[1], reverse=True)
    
    # Get low stock products
    low_stock = utils.get_low_stock_products()
    
    # Get purchase order status counts
    statuses = PurchaseOrderStatus.query.all()
    po_status_data = {}
    for status in statuses:
        count = PurchaseOrder.query.filter_by(status_id=status.id).count()
        po_status_data[status.name] = count
    
    # Get recent inventory transactions
    recent_transactions = InventoryTransaction.query.order_by(
        InventoryTransaction.transaction_date.desc()
    ).limit(10).all()
    
    return render_template(
        'inventory/dashboard.html',
        inventory_value=inventory_value,
        category_counts=category_counts,
        low_stock=low_stock,
        po_status_data=po_status_data,
        recent_transactions=recent_transactions
    )

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
        description = request.form.get('description')
        
        uom = UnitOfMeasure(
            name=name,
            abbreviation=abbreviation,
            description=description,
            created_by_id=current_user.id
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
        uom.name = request.form.get('name')
        uom.abbreviation = request.form.get('abbreviation')
        uom.description = request.form.get('description')
        
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
        flash(f'Cannot delete UOM. It is used by {products} products.', 'danger')
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
        location = request.form.get('location')
        description = request.form.get('description')
        is_active = 'is_active' in request.form
        
        warehouse = Warehouse(
            name=name,
            location=location,
            description=description,
            is_active=is_active,
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
        warehouse.name = request.form.get('name')
        warehouse.location = request.form.get('location')
        warehouse.description = request.form.get('description')
        warehouse.is_active = 'is_active' in request.form
        
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
    search = request.args.get('search')
    category = request.args.get('category')
    status = request.args.get('status')
    sort = request.args.get('sort', 'name')
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # Base query
    query = Product.query
    
    # Apply filters
    if search:
        query = query.filter(Product.name.ilike(f'%{search}%') | Product.sku.ilike(f'%{search}%'))
    
    if category:
        query = query.filter_by(category_id=category)
    
    if status == 'active':
        query = query.filter_by(is_active=True)
    elif status == 'inactive':
        query = query.filter_by(is_active=False)
    
    # Apply sorting
    if sort == 'name':
        query = query.order_by(Product.name)
    elif sort == 'sku':
        query = query.order_by(Product.sku)
    elif sort == 'stock_low':
        # This assumes current_stock is a property or hybrid property
        # For simplicity, we'll just sort by ID here
        query = query.order_by(Product.id)
    elif sort == 'stock_high':
        # Similar to above
        query = query.order_by(Product.id.desc())
    elif sort == 'price_low':
        query = query.order_by(Product.sales_price)
    elif sort == 'price_high':
        query = query.order_by(Product.sales_price.desc())
    
    # Paginate
    pagination = query.paginate(page=page, per_page=per_page)
    products = pagination.items
    
    # Get categories for filter dropdown
    categories = ProductCategory.query.order_by(ProductCategory.name).all()
    
    return render_template(
        'inventory/products.html',
        products=products,
        categories=categories,
        pagination=pagination
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
        
        # Generate SKU if not provided
        if not sku:
            sku = utils.generate_product_sku(name, category_id)
        
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
            is_active=is_active,
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
        asset_accounts = Account.query.filter_by(
            account_type_id=asset_type.id
        ).order_by(Account.code).all()
    
    expense_accounts = []
    if expense_type:
        expense_accounts = Account.query.filter_by(
            account_type_id=expense_type.id
        ).order_by(Account.code).all()
    
    revenue_accounts = []
    if revenue_type:
        revenue_accounts = Account.query.filter_by(
            account_type_id=revenue_type.id
        ).order_by(Account.code).all()
    
    return render_template(
        'inventory/product_form.html',
        categories=categories,
        uoms=uoms,
        vendors=vendors,
        asset_accounts=asset_accounts,
        expense_accounts=expense_accounts,
        revenue_accounts=revenue_accounts
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
        asset_accounts = Account.query.filter_by(
            account_type_id=asset_type.id
        ).order_by(Account.code).all()
    
    expense_accounts = []
    if expense_type:
        expense_accounts = Account.query.filter_by(
            account_type_id=expense_type.id
        ).order_by(Account.code).all()
    
    revenue_accounts = []
    if revenue_type:
        revenue_accounts = Account.query.filter_by(
            account_type_id=revenue_type.id
        ).order_by(Account.code).all()
    
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
        utils.record_inventory_transaction(
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

@inventory_bp.route('/reports/stock-valuation')
@login_required
def stock_valuation_report():
    """Stock valuation report"""
    # Get filters
    warehouse_id = request.args.get('warehouse_id')
    category_id = request.args.get('category_id')
    search = request.args.get('search')
    sort = request.args.get('sort', 'name')
    
    # Create a simple version that doesn't rely on complex SQLAlchemy case statements
    # Get all products
    products = Product.query.filter_by(is_active=True).all()
    
    # Calculate current stock and values manually
    stock_items_data = []
    total_value = 0
    category_totals = {}
    warehouse_totals = {}
    
    for product in products:
        # Get current stock for product
        current_stock = 0
        transactions = InventoryTransaction.query.filter_by(product_id=product.id).all()
        
        for tx in transactions:
            if tx.transaction_type == 'IN':
                current_stock += tx.quantity
            elif tx.transaction_type == 'OUT':
                current_stock -= tx.quantity
        
        # Skip if no stock
        if current_stock <= 0:
            continue
            
        # Calculate value
        item_value = current_stock * product.cost_price
        total_value += item_value
        
        # Add to stock items
        stock_items_data.append({
            'product': product,
            'quantity': current_stock,
            'value': item_value,
            'warehouse': {'name': 'Main Warehouse'}  # Default warehouse
        })
        
        # Calculate category totals
        category_name = product.category.name if product.category else 'Uncategorized'
        if category_name not in category_totals:
            category_totals[category_name] = 0
        category_totals[category_name] += item_value
        
        # Calculate warehouse totals
        warehouse_name = 'Main Warehouse'  # Default for now
        if warehouse_name not in warehouse_totals:
            warehouse_totals[warehouse_name] = 0
        warehouse_totals[warehouse_name] += item_value
    
    # Apply filters for our simplified version
    filtered_stock_items = []
    
    for item in stock_items_data:
        # Apply category filter
        if category_id and item['product'].category_id != int(category_id):
            continue
            
        # Apply search filter
        if search and search.lower() not in item['product'].name.lower() and search.lower() not in item['product'].sku.lower():
            continue
            
        filtered_stock_items.append(item)
    
    # Apply sorting
    if sort == 'name':
        filtered_stock_items.sort(key=lambda x: x['product'].name)
    elif sort == 'value_high':
        filtered_stock_items.sort(key=lambda x: x['value'], reverse=True)
    elif sort == 'value_low':
        filtered_stock_items.sort(key=lambda x: x['value'])
    elif sort == 'quantity_high':
        filtered_stock_items.sort(key=lambda x: x['quantity'], reverse=True)
    elif sort == 'quantity_low':
        filtered_stock_items.sort(key=lambda x: x['quantity'])
    
    # Our simplified version already built all the data we need
    stock_items = filtered_stock_items
    
    # Get categories and warehouses for filter dropdowns
    categories = ProductCategory.query.order_by(ProductCategory.name).all()
    warehouses = Warehouse.query.filter_by(is_active=True).order_by(Warehouse.name).all()
    
    # Sort category and warehouse totals
    category_totals = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)
    warehouse_totals = sorted(warehouse_totals.items(), key=lambda x: x[1], reverse=True)
    
    return render_template(
        'inventory/stock_valuation_report.html',
        stock_items=stock_items,
        total_value=total_value,
        categories=categories,
        warehouses=warehouses,
        category_totals=category_totals,
        warehouse_totals=warehouse_totals,
        show_by_category=True,
        show_by_warehouse=True,
        datetime_now=datetime.now()
    )

@inventory_bp.route('/reports/stock-valuation/export')
@login_required
def export_stock_valuation():
    """Export stock valuation report to Excel"""
    # Similar logic as stock_valuation_report but exports to Excel
    flash('Export feature coming soon.', 'info')
    return redirect(url_for('inventory.stock_valuation_report'))

@inventory_bp.route('/reports/low-stock')
@login_required
def low_stock_report():
    """Low stock report"""
    # Get low stock products
    low_stock = utils.get_low_stock_products()
    
    # Get warehouses for filter
    warehouses = Warehouse.query.filter_by(is_active=True).order_by(Warehouse.name).all()
    
    # Get categories for filter
    categories = ProductCategory.query.order_by(ProductCategory.name).all()
    
    return render_template(
        'inventory/low_stock_report.html',
        low_stock=low_stock,
        warehouses=warehouses,
        categories=categories,
        datetime_now=datetime.now()
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
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        query = query.filter(PurchaseOrder.order_date >= start_date)
    
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        query = query.filter(PurchaseOrder.order_date <= end_date)
    
    # Get POs ordered by date
    purchase_orders = query.order_by(PurchaseOrder.order_date.desc()).all()
    
    # Get statuses for filter dropdown
    statuses = PurchaseOrderStatus.query.all()
    
    # Get vendors for filter dropdown
    vendor_type = EntityType.query.filter_by(name=EntityType.VENDOR).first()
    vendors = []
    if vendor_type:
        vendors = Entity.query.filter_by(entity_type_id=vendor_type.id).order_by(Entity.name).all()
    
    # Get status counts for dashboard
    po_status_data = {}
    for status in statuses:
        count = PurchaseOrder.query.filter_by(status_id=status.id).count()
        po_status_data[status.name] = count
    
    return render_template(
        'inventory/purchase_orders.html',
        purchase_orders=purchase_orders,
        statuses=statuses,
        vendors=vendors,
        po_status_data=po_status_data,
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
        warehouse_id = request.form.get('warehouse_id') or None
        notes = request.form.get('notes')
        action = request.form.get('action', 'save_draft')
        
        # Validate required fields
        if not vendor_id or not order_date:
            flash('Vendor and order date are required.', 'danger')
            return redirect(url_for('inventory.create_purchase_order'))
        
        # Parse dates
        order_date = datetime.strptime(order_date, '%Y-%m-%d').date()
        if expected_delivery_date:
            expected_delivery_date = datetime.strptime(expected_delivery_date, '%Y-%m-%d').date()
        
        # Get product IDs from form
        product_ids = request.form.getlist('product_id[]')
        quantities = request.form.getlist('quantity[]')
        unit_prices = request.form.getlist('unit_price[]')
        
        # Validate line items
        if not product_ids:
            flash('At least one line item is required.', 'danger')
            return redirect(url_for('inventory.create_purchase_order'))
        
        # Calculate total amount
        total_amount = 0
        for i in range(len(product_ids)):
            if i < len(quantities) and i < len(unit_prices) and product_ids[i]:
                try:
                    qty = float(quantities[i])
                    price = float(unit_prices[i])
                    total_amount += qty * price
                except (ValueError, TypeError):
                    pass
        
        # Get draft status
        draft_status = PurchaseOrderStatus.query.filter_by(name=PurchaseOrderStatus.DRAFT).first()
        submitted_status = PurchaseOrderStatus.query.filter_by(name=PurchaseOrderStatus.SUBMITTED).first()
        
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
        po_number = utils.generate_po_number()
        
        # Create purchase order
        purchase_order = PurchaseOrder(
            po_number=po_number,
            vendor_id=vendor_id,
            order_date=order_date,
            expected_delivery_date=expected_delivery_date,
            status_id=submitted_status.id if action == 'submit' else draft_status.id,
            warehouse_id=warehouse_id,
            total_amount=total_amount,
            notes=notes,
            created_by_id=current_user.id
        )
        
        db.session.add(purchase_order)
        db.session.flush()  # Get ID without committing
        
        # Process line items
        items = []
        
        for i in range(len(product_ids)):
            if not product_ids[i]:
                continue
                
            product_id = product_ids[i]
            
            # Get product for description
            product = Product.query.get(product_id)
            if not product:
                continue
                
            description = product.name
            
            try:
                quantity = float(quantities[i]) if i < len(quantities) else 0
                unit_price = float(unit_prices[i]) if i < len(unit_prices) else 0
                tax_rate = 0  # Default to 0 for now
            except (ValueError, TypeError):
                continue
            
            # Skip empty items
            if quantity <= 0:
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
    
    # Get vendors (entities of type Vendor)
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
    
    # Get items
    items = PurchaseOrderItem.query.filter_by(po_id=po_id).all()
    
    # Get vendor
    vendor = Entity.query.get(purchase_order.vendor_id) if purchase_order.vendor_id else None
    
    # Get warehouse
    warehouse = Warehouse.query.get(purchase_order.warehouse_id) if purchase_order.warehouse_id else None
    
    # Get status
    status = PurchaseOrderStatus.query.get(purchase_order.status_id) if purchase_order.status_id else None
    
    return render_template(
        'inventory/purchase_order_view.html',
        po=purchase_order,
        items=items,
        vendor=vendor,
        warehouse=warehouse,
        status=status
    )