from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from models import Entity, EntityType, Invoice, Role

entities_bp = Blueprint('entities', __name__)

@entities_bp.route('/customers')
@login_required
def customers():
    """Show list of customers"""
    # Get the customer entity type
    customer_type = EntityType.query.filter_by(name=EntityType.CUSTOMER).first()
    
    if not customer_type:
        # Create entity types if they don't exist
        customer_type = EntityType(name=EntityType.CUSTOMER)
        vendor_type = EntityType(name=EntityType.VENDOR)
        
        db.session.add_all([customer_type, vendor_type])
        db.session.commit()
    
    # Get customers
    customers = Entity.query.filter_by(entity_type_id=customer_type.id).order_by(Entity.name).all()
    
    return render_template('customers.html', customers=customers)

@entities_bp.route('/vendors')
@login_required
def vendors():
    """Show list of vendors"""
    # Get the vendor entity type
    vendor_type = EntityType.query.filter_by(name=EntityType.VENDOR).first()
    
    if not vendor_type:
        # Create entity types if they don't exist
        customer_type = EntityType(name=EntityType.CUSTOMER)
        vendor_type = EntityType(name=EntityType.VENDOR)
        
        db.session.add_all([customer_type, vendor_type])
        db.session.commit()
    
    # Get vendors
    vendors = Entity.query.filter_by(entity_type_id=vendor_type.id).order_by(Entity.name).all()
    
    return render_template('vendors.html', vendors=vendors)

@entities_bp.route('/customers/create', methods=['GET', 'POST'])
@login_required
def create_customer():
    """Create a new customer"""
    # Check permission
    if not current_user.has_permission(Role.CAN_CREATE):
        flash('You do not have permission to create customers.', 'danger')
        return redirect(url_for('entities.customers'))
    
    if request.method == 'POST':
        # Get form data
        name = request.form.get('name')
        contact_name = request.form.get('contact_name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        address = request.form.get('address')
        
        # Get the customer entity type
        customer_type = EntityType.query.filter_by(name=EntityType.CUSTOMER).first()
        
        if not customer_type:
            # Create entity types if they don't exist
            customer_type = EntityType(name=EntityType.CUSTOMER)
            vendor_type = EntityType(name=EntityType.VENDOR)
            
            db.session.add_all([customer_type, vendor_type])
            db.session.commit()
        
        # Create customer
        customer = Entity(
            name=name,
            entity_type_id=customer_type.id,
            contact_name=contact_name,
            email=email,
            phone=phone,
            address=address,
            created_by_id=current_user.id
        )
        
        db.session.add(customer)
        db.session.commit()
        
        flash('Customer created successfully.', 'success')
        return redirect(url_for('entities.customers'))
    
    return render_template('entity_form.html', entity_type='customer')

@entities_bp.route('/vendors/create', methods=['GET', 'POST'])
@login_required
def create_vendor():
    """Create a new vendor"""
    # Check permission
    if not current_user.has_permission(Role.CAN_CREATE):
        flash('You do not have permission to create vendors.', 'danger')
        return redirect(url_for('entities.vendors'))
    
    if request.method == 'POST':
        # Get form data
        name = request.form.get('name')
        contact_name = request.form.get('contact_name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        address = request.form.get('address')
        
        # Get the vendor entity type
        vendor_type = EntityType.query.filter_by(name=EntityType.VENDOR).first()
        
        if not vendor_type:
            # Create entity types if they don't exist
            customer_type = EntityType(name=EntityType.CUSTOMER)
            vendor_type = EntityType(name=EntityType.VENDOR)
            
            db.session.add_all([customer_type, vendor_type])
            db.session.commit()
        
        # Create vendor
        vendor = Entity(
            name=name,
            entity_type_id=vendor_type.id,
            contact_name=contact_name,
            email=email,
            phone=phone,
            address=address,
            created_by_id=current_user.id
        )
        
        db.session.add(vendor)
        db.session.commit()
        
        flash('Vendor created successfully.', 'success')
        return redirect(url_for('entities.vendors'))
    
    return render_template('entity_form.html', entity_type='vendor')

@entities_bp.route('/entities/<int:entity_id>')
@login_required
def view(entity_id):
    """View an entity (customer or vendor)"""
    entity = Entity.query.get_or_404(entity_id)
    
    # Get recent invoices for this entity
    recent_invoices = Invoice.query.filter_by(entity_id=entity_id).order_by(Invoice.issue_date.desc()).limit(10).all()
    
    # Determine if it's a customer or vendor
    entity_type = 'customer' if entity.entity_type.name == EntityType.CUSTOMER else 'vendor'
    
    return render_template(
        'entity_form.html',
        entity=entity,
        entity_type=entity_type,
        viewing=True,
        recent_invoices=recent_invoices
    )

@entities_bp.route('/entities/<int:entity_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(entity_id):
    """Edit an entity (customer or vendor)"""
    # Check permission
    if not current_user.has_permission(Role.CAN_EDIT):
        flash('You do not have permission to edit entities.', 'danger')
        return redirect(url_for('entities.view', entity_id=entity_id))
    
    entity = Entity.query.get_or_404(entity_id)
    
    # Determine if it's a customer or vendor
    entity_type = 'customer' if entity.entity_type.name == EntityType.CUSTOMER else 'vendor'
    
    if request.method == 'POST':
        # Update entity
        entity.name = request.form.get('name')
        entity.contact_name = request.form.get('contact_name')
        entity.email = request.form.get('email')
        entity.phone = request.form.get('phone')
        entity.address = request.form.get('address')
        
        db.session.commit()
        
        flash(f'{entity_type.capitalize()} updated successfully.', 'success')
        return redirect(url_for('entities.view', entity_id=entity_id))
    
    return render_template(
        'entity_form.html',
        entity=entity,
        entity_type=entity_type,
        editing=True
    )

@entities_bp.route('/entities/<int:entity_id>/delete', methods=['POST'])
@login_required
def delete(entity_id):
    """Delete an entity (customer or vendor)"""
    # Check permission
    if not current_user.has_permission(Role.CAN_DELETE):
        flash('You do not have permission to delete entities.', 'danger')
        return redirect(url_for('entities.view', entity_id=entity_id))
    
    entity = Entity.query.get_or_404(entity_id)
    
    # Check if entity has invoices
    has_invoices = Invoice.query.filter_by(entity_id=entity_id).first() is not None
    
    if has_invoices:
        flash('Cannot delete an entity with existing invoices.', 'danger')
        return redirect(url_for('entities.view', entity_id=entity_id))
    
    # Determine redirect based on entity type
    entity_type = entity.entity_type.name
    
    # Delete entity
    db.session.delete(entity)
    db.session.commit()
    
    flash('Entity deleted successfully.', 'success')
    
    if entity_type == EntityType.CUSTOMER:
        return redirect(url_for('entities.customers'))
    else:
        return redirect(url_for('entities.vendors'))
