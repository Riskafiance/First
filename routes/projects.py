import os
from datetime import datetime, date
from decimal import Decimal
import logging

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from sqlalchemy import func, desc

from app import db
from models import (
    Project, ProjectStatus, JobTask, TimeEntry, ProjectExpense, 
    Entity, EntityType, Account, AccountType, User, Role,
    Invoice, InvoiceItem, InvoiceStatus, Expense
)
from core_utils import format_currency, generate_invoice_number

# Set up logging
logger = logging.getLogger(__name__)

# Blueprint configuration
projects_bp = Blueprint('projects', __name__)

# Helper function to create project code
def generate_project_code():
    """Generate a unique project code with format PRJ-YYYYMM-XXXX"""
    today = datetime.now()
    prefix = f"PRJ-{today.year}{today.month:02d}-"
    
    # Find the max project code with this prefix
    max_code = db.session.query(func.max(Project.project_code)).filter(
        Project.project_code.like(f"{prefix}%")
    ).scalar()
    
    if max_code:
        # Extract the numeric part and increment
        try:
            last_num = int(max_code.split('-')[-1])
            next_num = last_num + 1
        except (ValueError, IndexError):
            next_num = 1
    else:
        next_num = 1
    
    return f"{prefix}{next_num:04d}"

@projects_bp.route('/')
@login_required
def projects_list():
    """List all projects"""
    try:
        status_filter = request.args.get('status')
        client_filter = request.args.get('client')
        
        query = Project.query
        
        if status_filter:
            query = query.filter(Project.status_id == status_filter)
        
        if client_filter:
            query = query.filter(Project.entity_id == client_filter)
        
        projects = query.order_by(Project.created_at.desc()).all()
        
        # Get statuses for filter
        statuses = ProjectStatus.query.all()
        
        # Get clients for filter
        clients = Entity.query.join(
            Project, Project.entity_id == Entity.id
        ).distinct().all()
        
        return render_template(
            'projects/list.html',
            projects=projects,
            statuses=statuses,
            clients=clients,
            current_status=status_filter,
            current_client=client_filter
        )
    except Exception as e:
        logger.error(f"Error listing projects: {str(e)}")
        flash('There was an error retrieving the projects. Please try again.', 'danger')
        return render_template('projects/list.html', projects=[])

@projects_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_project():
    """Create a new project"""
    if not current_user.has_permission(Role.CAN_CREATE):
        flash('You do not have permission to create projects.', 'danger')
        return redirect(url_for('projects.projects_list'))
    
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            description = request.form.get('description')
            entity_id = request.form.get('entity_id')
            status_id = request.form.get('status_id')
            start_date = request.form.get('start_date')
            end_date = request.form.get('end_date')
            estimated_hours = request.form.get('estimated_hours')
            estimated_cost = request.form.get('estimated_cost')
            budget_amount = request.form.get('budget_amount')
            is_fixed_price = 'is_fixed_price' in request.form
            fixed_price_amount = request.form.get('fixed_price_amount')
            is_billable = 'is_billable' in request.form
            manager_id = request.form.get('manager_id')
            notes = request.form.get('notes')
            
            # Validate required fields
            if not name or not status_id or not start_date:
                flash('Please fill all required fields.', 'danger')
                return redirect(url_for('projects.create_project'))
            
            # Format numeric fields
            if estimated_hours:
                estimated_hours = Decimal(estimated_hours)
            else:
                estimated_hours = None
                
            if estimated_cost:
                estimated_cost = Decimal(estimated_cost)
            else:
                estimated_cost = None
                
            if budget_amount:
                budget_amount = Decimal(budget_amount)
            else:
                budget_amount = None
                
            if fixed_price_amount and is_fixed_price:
                fixed_price_amount = Decimal(fixed_price_amount)
            else:
                fixed_price_amount = None
            
            # Parse dates
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            if end_date:
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            else:
                end_date = None
                
            # Generate project code
            project_code = generate_project_code()
            
            # Create new project
            project = Project(
                project_code=project_code,
                name=name,
                description=description,
                entity_id=entity_id if entity_id else None,
                status_id=status_id,
                start_date=start_date,
                end_date=end_date,
                estimated_hours=estimated_hours,
                estimated_cost=estimated_cost,
                budget_amount=budget_amount,
                is_fixed_price=is_fixed_price,
                fixed_price_amount=fixed_price_amount,
                is_billable=is_billable,
                notes=notes,
                created_by_id=current_user.id,
                manager_id=manager_id if manager_id else None
            )
            
            db.session.add(project)
            db.session.commit()
            
            flash(f'Project {project.project_code} created successfully.', 'success')
            return redirect(url_for('projects.view_project', project_id=project.id))
        
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating project: {str(e)}")
            flash('There was an error creating the project. Please try again.', 'danger')
            
    # GET request
    try:
        # Get clients (entities that are customers)
        customers = Entity.query.join(
            EntityType, Entity.entity_type_id == EntityType.id
        ).filter(
            EntityType.name == EntityType.CUSTOMER
        ).order_by(Entity.name).all()
        
        # Get statuses
        statuses = ProjectStatus.query.all()
        if not statuses:
            # Create default statuses if none exist
            default_statuses = [
                ProjectStatus(name=ProjectStatus.PLANNED),
                ProjectStatus(name=ProjectStatus.IN_PROGRESS),
                ProjectStatus(name=ProjectStatus.ON_HOLD),
                ProjectStatus(name=ProjectStatus.COMPLETED),
                ProjectStatus(name=ProjectStatus.CANCELLED)
            ]
            db.session.add_all(default_statuses)
            db.session.commit()
            statuses = ProjectStatus.query.all()
        
        # Get potential project managers (users with manager role or higher)
        managers = User.query.join(
            Role, User.role_id == Role.id
        ).filter(
            Role.permissions.op('&')(Role.CAN_APPROVE) == Role.CAN_APPROVE
        ).order_by(User.username).all()
        
        return render_template(
            'projects/form.html',
            customers=customers,
            statuses=statuses,
            managers=managers,
            today=date.today()
        )
    except Exception as e:
        logger.error(f"Error loading project form: {str(e)}")
        flash('There was an error loading the form. Please try again.', 'danger')
        return redirect(url_for('projects.projects_list'))

@projects_bp.route('/<int:project_id>')
@login_required
def view_project(project_id):
    """View a project"""
    try:
        project = Project.query.get_or_404(project_id)
        
        # Get tasks
        tasks = JobTask.query.filter_by(
            project_id=project_id, 
            parent_task_id=None
        ).order_by(JobTask.start_date).all()
        
        # Get time entries summary
        time_summary = db.session.query(
            func.sum(TimeEntry.hours).label('total_hours'),
            func.sum(TimeEntry.cost_amount).label('total_cost'),
            func.sum(func.case((TimeEntry.is_billable, TimeEntry.billable_amount), else_=0)).label('total_billable')
        ).filter(
            TimeEntry.project_id == project_id
        ).first()
        
        # Get expense summary
        expense_summary = db.session.query(
            func.sum(ProjectExpense.amount).label('total_expense'),
            func.sum(func.case((ProjectExpense.is_billable, ProjectExpense.billable_amount), else_=0)).label('total_billable')
        ).filter(
            ProjectExpense.project_id == project_id
        ).first()
        
        # Get recent time entries
        recent_time = TimeEntry.query.filter_by(
            project_id=project_id
        ).order_by(
            TimeEntry.date.desc()
        ).limit(5).all()
        
        # Get recent expenses
        recent_expenses = ProjectExpense.query.filter_by(
            project_id=project_id
        ).order_by(
            ProjectExpense.date.desc()
        ).limit(5).all()
        
        return render_template(
            'projects/view.html',
            project=project,
            tasks=tasks,
            time_summary=time_summary,
            expense_summary=expense_summary,
            recent_time=recent_time,
            recent_expenses=recent_expenses,
            format_currency=format_currency
        )
    except Exception as e:
        logger.error(f"Error viewing project {project_id}: {str(e)}")
        flash('There was an error retrieving the project. Please try again.', 'danger')
        return redirect(url_for('projects.projects_list'))

@projects_bp.route('/<int:project_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_project(project_id):
    """Edit a project"""
    if not current_user.has_permission(Role.CAN_EDIT):
        flash('You do not have permission to edit projects.', 'danger')
        return redirect(url_for('projects.view_project', project_id=project_id))
    
    try:
        project = Project.query.get_or_404(project_id)
        
        if request.method == 'POST':
            try:
                project.name = request.form.get('name')
                project.description = request.form.get('description')
                project.entity_id = request.form.get('entity_id') or None
                project.status_id = request.form.get('status_id')
                
                start_date = request.form.get('start_date')
                if start_date:
                    project.start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                
                end_date = request.form.get('end_date')
                if end_date:
                    project.end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                else:
                    project.end_date = None
                
                estimated_hours = request.form.get('estimated_hours')
                if estimated_hours:
                    project.estimated_hours = Decimal(estimated_hours)
                else:
                    project.estimated_hours = None
                
                estimated_cost = request.form.get('estimated_cost')
                if estimated_cost:
                    project.estimated_cost = Decimal(estimated_cost)
                else:
                    project.estimated_cost = None
                
                budget_amount = request.form.get('budget_amount')
                if budget_amount:
                    project.budget_amount = Decimal(budget_amount)
                else:
                    project.budget_amount = None
                
                project.is_fixed_price = 'is_fixed_price' in request.form
                
                fixed_price_amount = request.form.get('fixed_price_amount')
                if fixed_price_amount and project.is_fixed_price:
                    project.fixed_price_amount = Decimal(fixed_price_amount)
                else:
                    project.fixed_price_amount = None
                
                project.is_billable = 'is_billable' in request.form
                project.manager_id = request.form.get('manager_id') or None
                project.notes = request.form.get('notes')
                
                db.session.commit()
                flash('Project updated successfully.', 'success')
                return redirect(url_for('projects.view_project', project_id=project.id))
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error updating project: {str(e)}")
                flash('There was an error updating the project. Please try again.', 'danger')
        
        # GET request
        # Get clients (entities that are customers)
        customers = Entity.query.join(
            EntityType, Entity.entity_type_id == EntityType.id
        ).filter(
            EntityType.name == EntityType.CUSTOMER
        ).order_by(Entity.name).all()
        
        # Get statuses
        statuses = ProjectStatus.query.all()
        
        # Get potential project managers (users with manager role or higher)
        managers = User.query.join(
            Role, User.role_id == Role.id
        ).filter(
            Role.permissions.op('&')(Role.CAN_APPROVE) == Role.CAN_APPROVE
        ).order_by(User.username).all()
        
        return render_template(
            'projects/form.html',
            project=project,
            customers=customers,
            statuses=statuses,
            managers=managers,
            edit_mode=True
        )
    except Exception as e:
        logger.error(f"Error loading project edit form: {str(e)}")
        flash('There was an error loading the project. Please try again.', 'danger')
        return redirect(url_for('projects.projects_list'))

@projects_bp.route('/<int:project_id>/tasks')
@login_required
def project_tasks(project_id):
    """View project tasks"""
    try:
        project = Project.query.get_or_404(project_id)
        
        # Get all tasks for the project
        tasks = JobTask.query.filter_by(
            project_id=project_id
        ).order_by(JobTask.start_date).all()
        
        # Organize tasks into a hierarchy
        root_tasks = [task for task in tasks if task.parent_task_id is None]
        
        return render_template(
            'projects/tasks.html',
            project=project,
            root_tasks=root_tasks,
            all_tasks=tasks,
            format_currency=format_currency
        )
    except Exception as e:
        logger.error(f"Error viewing project tasks: {str(e)}")
        flash('There was an error retrieving the project tasks. Please try again.', 'danger')
        return redirect(url_for('projects.view_project', project_id=project_id))

@projects_bp.route('/<int:project_id>/tasks/create', methods=['GET', 'POST'])
@login_required
def create_task(project_id):
    """Create a new task for a project"""
    if not current_user.has_permission(Role.CAN_CREATE):
        flash('You do not have permission to create tasks.', 'danger')
        return redirect(url_for('projects.project_tasks', project_id=project_id))
    
    try:
        project = Project.query.get_or_404(project_id)
        
        if request.method == 'POST':
            try:
                name = request.form.get('name')
                description = request.form.get('description')
                parent_task_id = request.form.get('parent_task_id') or None
                start_date = request.form.get('start_date')
                end_date = request.form.get('end_date')
                estimated_hours = request.form.get('estimated_hours')
                estimated_cost = request.form.get('estimated_cost')
                is_billable = 'is_billable' in request.form
                billing_rate = request.form.get('billing_rate')
                assignee_id = request.form.get('assignee_id') or None
                
                # Validate required fields
                if not name:
                    flash('Task name is required.', 'danger')
                    return redirect(url_for('projects.create_task', project_id=project_id))
                
                # Format numeric fields
                if estimated_hours:
                    estimated_hours = Decimal(estimated_hours)
                else:
                    estimated_hours = None
                    
                if estimated_cost:
                    estimated_cost = Decimal(estimated_cost)
                else:
                    estimated_cost = None
                    
                if billing_rate and is_billable:
                    billing_rate = Decimal(billing_rate)
                else:
                    billing_rate = None
                
                # Parse dates
                if start_date:
                    start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                else:
                    start_date = None
                    
                if end_date:
                    end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                else:
                    end_date = None
                    
                # Create new task
                task = JobTask(
                    project_id=project_id,
                    name=name,
                    description=description,
                    parent_task_id=parent_task_id,
                    start_date=start_date,
                    end_date=end_date,
                    estimated_hours=estimated_hours,
                    estimated_cost=estimated_cost,
                    is_billable=is_billable,
                    billing_rate=billing_rate,
                    is_completed=False,
                    created_by_id=current_user.id,
                    assignee_id=assignee_id
                )
                
                db.session.add(task)
                db.session.commit()
                
                flash('Task created successfully.', 'success')
                return redirect(url_for('projects.project_tasks', project_id=project_id))
            
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error creating task: {str(e)}")
                flash('There was an error creating the task. Please try again.', 'danger')
        
        # GET request
        # Get potential parent tasks
        tasks = JobTask.query.filter_by(project_id=project_id).all()
        
        # Get potential assignees (all users)
        users = User.query.order_by(User.username).all()
        
        return render_template(
            'projects/task_form.html',
            project=project,
            tasks=tasks,
            users=users,
            today=date.today()
        )
    
    except Exception as e:
        logger.error(f"Error loading task form: {str(e)}")
        flash('There was an error loading the form. Please try again.', 'danger')
        return redirect(url_for('projects.project_tasks', project_id=project_id))

@projects_bp.route('/<int:project_id>/tasks/<int:task_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_task(project_id, task_id):
    """Edit a task"""
    if not current_user.has_permission(Role.CAN_EDIT):
        flash('You do not have permission to edit tasks.', 'danger')
        return redirect(url_for('projects.project_tasks', project_id=project_id))
    
    try:
        project = Project.query.get_or_404(project_id)
        task = JobTask.query.get_or_404(task_id)
        
        # Ensure task belongs to the project
        if task.project_id != project_id:
            flash('Task does not belong to this project.', 'danger')
            return redirect(url_for('projects.project_tasks', project_id=project_id))
        
        if request.method == 'POST':
            try:
                task.name = request.form.get('name')
                task.description = request.form.get('description')
                parent_task_id = request.form.get('parent_task_id')
                
                # Prevent circular references
                if parent_task_id and int(parent_task_id) == task.id:
                    flash('A task cannot be its own parent.', 'danger')
                else:
                    task.parent_task_id = parent_task_id or None
                
                start_date = request.form.get('start_date')
                if start_date:
                    task.start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                else:
                    task.start_date = None
                
                end_date = request.form.get('end_date')
                if end_date:
                    task.end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                else:
                    task.end_date = None
                
                estimated_hours = request.form.get('estimated_hours')
                if estimated_hours:
                    task.estimated_hours = Decimal(estimated_hours)
                else:
                    task.estimated_hours = None
                
                estimated_cost = request.form.get('estimated_cost')
                if estimated_cost:
                    task.estimated_cost = Decimal(estimated_cost)
                else:
                    task.estimated_cost = None
                
                task.is_billable = 'is_billable' in request.form
                
                billing_rate = request.form.get('billing_rate')
                if billing_rate and task.is_billable:
                    task.billing_rate = Decimal(billing_rate)
                else:
                    task.billing_rate = None
                
                task.assignee_id = request.form.get('assignee_id') or None
                
                # Handle task completion
                is_completed = 'is_completed' in request.form
                if is_completed and not task.is_completed:
                    task.is_completed = True
                    task.completion_date = date.today()
                elif not is_completed:
                    task.is_completed = False
                    task.completion_date = None
                
                db.session.commit()
                flash('Task updated successfully.', 'success')
                return redirect(url_for('projects.project_tasks', project_id=project_id))
            
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error updating task: {str(e)}")
                flash('There was an error updating the task. Please try again.', 'danger')
        
        # GET request
        # Get potential parent tasks (excluding this task and its subtasks)
        potential_parents = JobTask.query.filter(
            JobTask.project_id == project_id,
            JobTask.id != task_id
        ).all()
        
        # Remove any subtasks of this task from potential parents to prevent circular references
        def get_subtask_ids(task_id):
            subtasks = JobTask.query.filter_by(parent_task_id=task_id).all()
            subtask_ids = [subtask.id for subtask in subtasks]
            for subtask_id in subtask_ids:
                subtask_ids.extend(get_subtask_ids(subtask_id))
            return subtask_ids
            
        subtask_ids = get_subtask_ids(task.id)
        potential_parents = [p for p in potential_parents if p.id not in subtask_ids]
        
        # Get potential assignees (all users)
        users = User.query.order_by(User.username).all()
        
        return render_template(
            'projects/task_form.html',
            project=project,
            task=task,
            tasks=potential_parents,
            users=users,
            edit_mode=True
        )
    
    except Exception as e:
        logger.error(f"Error loading task edit form: {str(e)}")
        flash('There was an error loading the task. Please try again.', 'danger')
        return redirect(url_for('projects.project_tasks', project_id=project_id))

@projects_bp.route('/<int:project_id>/time')
@login_required
def project_time(project_id):
    """View time entries for a project"""
    try:
        project = Project.query.get_or_404(project_id)
        
        # Get filter parameters
        user_id = request.args.get('user_id', type=int)
        task_id = request.args.get('task_id', type=int)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        billable = request.args.get('billable')
        
        # Build query
        query = TimeEntry.query.filter_by(project_id=project_id)
        
        if user_id:
            query = query.filter_by(user_id=user_id)
        
        if task_id:
            query = query.filter_by(task_id=task_id)
        
        if start_date:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                query = query.filter(TimeEntry.date >= start_date)
            except ValueError:
                pass
        
        if end_date:
            try:
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                query = query.filter(TimeEntry.date <= end_date)
            except ValueError:
                pass
        
        if billable == 'yes':
            query = query.filter_by(is_billable=True)
        elif billable == 'no':
            query = query.filter_by(is_billable=False)
        
        # Execute query with sorting
        time_entries = query.order_by(TimeEntry.date.desc()).all()
        
        # Get tasks for this project for filter
        tasks = JobTask.query.filter_by(project_id=project_id).order_by(JobTask.name).all()
        
        # Get users who have time entries for filter
        users_with_entries = db.session.query(User).join(
            TimeEntry, TimeEntry.user_id == User.id
        ).filter(
            TimeEntry.project_id == project_id
        ).distinct().order_by(User.username).all()
        
        # Calculate summary
        total_hours = sum(entry.hours for entry in time_entries)
        total_billable = sum(entry.billable_amount for entry in time_entries if entry.is_billable)
        total_cost = sum(entry.cost_amount for entry in time_entries if entry.cost_amount)
        
        return render_template(
            'projects/time.html',
            project=project,
            time_entries=time_entries,
            tasks=tasks,
            users=users_with_entries,
            total_hours=total_hours,
            total_billable=total_billable,
            total_cost=total_cost,
            selected_user=user_id,
            selected_task=task_id,
            selected_start_date=start_date,
            selected_end_date=end_date,
            selected_billable=billable,
            format_currency=format_currency
        )
    
    except Exception as e:
        logger.error(f"Error viewing project time entries: {str(e)}")
        flash('There was an error retrieving the time entries. Please try again.', 'danger')
        return redirect(url_for('projects.view_project', project_id=project_id))

@projects_bp.route('/<int:project_id>/time/add', methods=['GET', 'POST'])
@login_required
def add_time_entry(project_id):
    """Add a time entry to a project"""
    try:
        project = Project.query.get_or_404(project_id)
        
        if request.method == 'POST':
            try:
                date_str = request.form.get('date')
                hours = request.form.get('hours')
                task_id = request.form.get('task_id') or None
                description = request.form.get('description')
                is_billable = 'is_billable' in request.form
                billing_rate = request.form.get('billing_rate')
                cost_rate = request.form.get('cost_rate')
                
                # Validate required fields
                if not date_str or not hours:
                    flash('Date and hours are required.', 'danger')
                    return redirect(url_for('projects.add_time_entry', project_id=project_id))
                
                # Parse date
                entry_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                
                # Convert to Decimal
                hours = Decimal(hours)
                
                # Optional fields
                if billing_rate and is_billable:
                    billing_rate = Decimal(billing_rate)
                else:
                    billing_rate = None
                    
                if cost_rate:
                    cost_rate = Decimal(cost_rate)
                    cost_amount = cost_rate * hours
                else:
                    cost_rate = None
                    cost_amount = None
                
                # Create time entry
                time_entry = TimeEntry(
                    project_id=project_id,
                    task_id=task_id,
                    user_id=current_user.id,
                    date=entry_date,
                    hours=hours,
                    description=description,
                    is_billable=is_billable,
                    billing_rate=billing_rate,
                    cost_rate=cost_rate,
                    cost_amount=cost_amount,
                    created_at=datetime.utcnow()
                )
                
                db.session.add(time_entry)
                db.session.commit()
                
                flash('Time entry added successfully.', 'success')
                return redirect(url_for('projects.project_time', project_id=project_id))
            
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error adding time entry: {str(e)}")
                flash('There was an error adding the time entry. Please try again.', 'danger')
        
        # GET request
        # Get tasks for this project
        tasks = JobTask.query.filter_by(project_id=project_id).order_by(JobTask.name).all()
        
        # Default to today's date
        today = date.today()
        
        # Get default billing rate if task is selected
        task_id = request.args.get('task_id')
        default_rate = None
        
        if task_id:
            task = JobTask.query.get(task_id)
            if task and task.is_billable:
                default_rate = task.billing_rate
        
        # Default cost rate for current user (could be stored in a user profile)
        default_cost_rate = None
        
        return render_template(
            'projects/time_form.html',
            project=project,
            tasks=tasks,
            today=today,
            default_task_id=task_id,
            default_rate=default_rate,
            default_cost_rate=default_cost_rate
        )
    
    except Exception as e:
        logger.error(f"Error loading time entry form: {str(e)}")
        flash('There was an error loading the form. Please try again.', 'danger')
        return redirect(url_for('projects.project_time', project_id=project_id))

@projects_bp.route('/<int:project_id>/expenses')
@login_required
def project_expenses(project_id):
    """View expenses for a project"""
    try:
        project = Project.query.get_or_404(project_id)
        
        # Get filter parameters
        task_id = request.args.get('task_id', type=int)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        billable = request.args.get('billable')
        account_id = request.args.get('account_id', type=int)
        
        # Build query
        query = ProjectExpense.query.filter_by(project_id=project_id)
        
        if task_id:
            query = query.filter_by(task_id=task_id)
        
        if start_date:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                query = query.filter(ProjectExpense.date >= start_date)
            except ValueError:
                pass
        
        if end_date:
            try:
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                query = query.filter(ProjectExpense.date <= end_date)
            except ValueError:
                pass
        
        if billable == 'yes':
            query = query.filter_by(is_billable=True)
        elif billable == 'no':
            query = query.filter_by(is_billable=False)
        
        if account_id:
            query = query.filter_by(account_id=account_id)
        
        # Execute query with sorting
        expenses = query.order_by(ProjectExpense.date.desc()).all()
        
        # Get tasks for this project for filter
        tasks = JobTask.query.filter_by(project_id=project_id).order_by(JobTask.name).all()
        
        # Get expense accounts for filter
        expense_accounts = Account.query.join(
            AccountType, Account.account_type_id == AccountType.id
        ).filter(
            AccountType.name == AccountType.EXPENSE
        ).order_by(Account.code).all()
        
        # Calculate summary
        total_amount = sum(expense.amount for expense in expenses)
        total_billable = sum(expense.billable_amount for expense in expenses if expense.is_billable)
        
        return render_template(
            'projects/expenses.html',
            project=project,
            expenses=expenses,
            tasks=tasks,
            accounts=expense_accounts,
            total_amount=total_amount,
            total_billable=total_billable,
            selected_task=task_id,
            selected_start_date=start_date,
            selected_end_date=end_date,
            selected_billable=billable,
            selected_account=account_id,
            format_currency=format_currency
        )
    
    except Exception as e:
        logger.error(f"Error viewing project expenses: {str(e)}")
        flash('There was an error retrieving the expenses. Please try again.', 'danger')
        return redirect(url_for('projects.view_project', project_id=project_id))

@projects_bp.route('/<int:project_id>/expenses/add', methods=['GET', 'POST'])
@login_required
def add_expense(project_id):
    """Add an expense to a project"""
    try:
        project = Project.query.get_or_404(project_id)
        
        if request.method == 'POST':
            try:
                date_str = request.form.get('date')
                description = request.form.get('description')
                amount = request.form.get('amount')
                account_id = request.form.get('account_id')
                task_id = request.form.get('task_id') or None
                is_billable = 'is_billable' in request.form
                markup_percentage = request.form.get('markup_percentage')
                
                # Validate required fields
                if not date_str or not description or not amount or not account_id:
                    flash('Date, description, amount, and account are required.', 'danger')
                    return redirect(url_for('projects.add_expense', project_id=project_id))
                
                # Parse date
                expense_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                
                # Convert to Decimal
                amount = Decimal(amount)
                
                # Optional fields
                if markup_percentage and is_billable:
                    markup_percentage = Decimal(markup_percentage)
                else:
                    markup_percentage = Decimal('0')
                
                # Create expense
                expense = ProjectExpense(
                    project_id=project_id,
                    task_id=task_id,
                    date=expense_date,
                    description=description,
                    amount=amount,
                    account_id=account_id,
                    is_billable=is_billable,
                    markup_percentage=markup_percentage,
                    created_at=datetime.utcnow(),
                    created_by_id=current_user.id
                )
                
                db.session.add(expense)
                db.session.commit()
                
                flash('Expense added successfully.', 'success')
                return redirect(url_for('projects.project_expenses', project_id=project_id))
            
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error adding expense: {str(e)}")
                flash('There was an error adding the expense. Please try again.', 'danger')
        
        # GET request
        # Get tasks for this project
        tasks = JobTask.query.filter_by(project_id=project_id).order_by(JobTask.name).all()
        
        # Get expense accounts
        expense_accounts = Account.query.join(
            AccountType, Account.account_type_id == AccountType.id
        ).filter(
            AccountType.name == AccountType.EXPENSE
        ).order_by(Account.code).all()
        
        # Default to today's date
        today = date.today()
        
        # Optional pre-selected task
        task_id = request.args.get('task_id')
        
        return render_template(
            'projects/expense_form.html',
            project=project,
            tasks=tasks,
            accounts=expense_accounts,
            today=today,
            default_task_id=task_id
        )
    
    except Exception as e:
        logger.error(f"Error loading expense form: {str(e)}")
        flash('There was an error loading the form. Please try again.', 'danger')
        return redirect(url_for('projects.project_expenses', project_id=project_id))

@projects_bp.route('/<int:project_id>/billing')
@login_required
def project_billing(project_id):
    """View billing information for a project"""
    try:
        project = Project.query.get_or_404(project_id)
        
        # Get unbilled time entries
        unbilled_time = TimeEntry.query.filter(
            TimeEntry.project_id == project_id,
            TimeEntry.is_billable == True,
            TimeEntry.invoice_item_id.is_(None)
        ).order_by(TimeEntry.date).all()
        
        # Get unbilled expenses
        unbilled_expenses = ProjectExpense.query.filter(
            ProjectExpense.project_id == project_id,
            ProjectExpense.is_billable == True,
            ProjectExpense.invoice_item_id.is_(None)
        ).order_by(ProjectExpense.date).all()
        
        # Get invoices related to this project
        invoices = Invoice.query.join(
            InvoiceItem, Invoice.id == InvoiceItem.invoice_id
        ).join(
            TimeEntry, TimeEntry.invoice_item_id == InvoiceItem.id
        ).filter(
            TimeEntry.project_id == project_id
        ).union(
            Invoice.query.join(
                InvoiceItem, Invoice.id == InvoiceItem.invoice_id
            ).join(
                ProjectExpense, ProjectExpense.invoice_item_id == InvoiceItem.id
            ).filter(
                ProjectExpense.project_id == project_id
            )
        ).order_by(Invoice.issue_date.desc()).all()
        
        # Calculate billing summaries
        total_billable_time = sum(entry.billable_amount for entry in unbilled_time)
        total_billable_expenses = sum(expense.billable_amount for expense in unbilled_expenses)
        total_unbilled = total_billable_time + total_billable_expenses
        
        # Calculate total billed
        total_billed = Decimal('0.00')
        for invoice in invoices:
            total_billed += invoice.total_amount
        
        return render_template(
            'projects/billing.html',
            project=project,
            unbilled_time=unbilled_time,
            unbilled_expenses=unbilled_expenses,
            invoices=invoices,
            total_billable_time=total_billable_time,
            total_billable_expenses=total_billable_expenses,
            total_unbilled=total_unbilled,
            total_billed=total_billed,
            format_currency=format_currency
        )
    
    except Exception as e:
        logger.error(f"Error viewing project billing: {str(e)}")
        flash('There was an error retrieving the billing information. Please try again.', 'danger')
        return redirect(url_for('projects.view_project', project_id=project_id))

@projects_bp.route('/<int:project_id>/billing/generate', methods=['POST'])
@login_required
def generate_invoice(project_id):
    """Generate an invoice from unbilled project items"""
    if not current_user.has_permission(Role.CAN_CREATE):
        flash('You do not have permission to generate invoices.', 'danger')
        return redirect(url_for('projects.project_billing', project_id=project_id))
    
    try:
        project = Project.query.get_or_404(project_id)
        
        # Check if client exists
        if not project.entity_id:
            flash('This project has no client assigned. Please edit the project to assign a client.', 'danger')
            return redirect(url_for('projects.project_billing', project_id=project_id))
        
        # Get selected time entries and expenses to bill
        time_entry_ids = request.form.getlist('time_entry_id', type=int)
        expense_ids = request.form.getlist('expense_id', type=int)
        
        if not time_entry_ids and not expense_ids:
            flash('Please select at least one time entry or expense to include in the invoice.', 'danger')
            return redirect(url_for('projects.project_billing', project_id=project_id))
        
        # Generate invoice
        invoice_number = generate_invoice_number()
        issue_date = date.today()
        due_date = issue_date.replace(day=issue_date.day + 30)  # Due in 30 days
        
        # Get draft status
        draft_status = InvoiceStatus.query.filter_by(name=InvoiceStatus.DRAFT).first()
        if not draft_status:
            draft_status = InvoiceStatus(name=InvoiceStatus.DRAFT)
            db.session.add(draft_status)
            db.session.commit()
        
        # Create invoice
        invoice = Invoice(
            invoice_number=invoice_number,
            entity_id=project.entity_id,
            issue_date=issue_date,
            due_date=due_date,
            status_id=draft_status.id,
            notes=f"Invoice for project: {project.name} ({project.project_code})",
            created_by_id=current_user.id
        )
        
        db.session.add(invoice)
        db.session.commit()
        
        # Create invoice items from time entries
        if time_entry_ids:
            time_entries = TimeEntry.query.filter(TimeEntry.id.in_(time_entry_ids)).all()
            
            # Group time entries by task
            task_groups = {}
            for entry in time_entries:
                task_name = entry.task.name if entry.task else "General Project Work"
                key = (task_name, entry.billing_rate)
                
                if key not in task_groups:
                    task_groups[key] = {
                        'task_name': task_name,
                        'entries': [],
                        'hours': Decimal('0.00'),
                        'rate': entry.billing_rate
                    }
                
                task_groups[key]['entries'].append(entry)
                task_groups[key]['hours'] += entry.hours
            
            # Create an invoice item for each task group
            for group_key, group_data in task_groups.items():
                # Find appropriate revenue account
                revenue_account = Account.query.join(
                    AccountType, Account.account_type_id == AccountType.id
                ).filter(
                    AccountType.name == AccountType.REVENUE
                ).first()
                
                if not revenue_account:
                    # Create a default revenue account if none exists
                    revenue_type = AccountType.query.filter_by(name=AccountType.REVENUE).first()
                    if not revenue_type:
                        revenue_type = AccountType(name=AccountType.REVENUE)
                        db.session.add(revenue_type)
                        db.session.commit()
                    
                    revenue_account = Account(
                        code="4000",
                        name="Service Revenue",
                        account_type_id=revenue_type.id,
                        is_active=True,
                        created_by_id=current_user.id
                    )
                    db.session.add(revenue_account)
                    db.session.commit()
                
                # Create invoice item for this task group
                task_name = group_data['task_name']
                hours = group_data['hours']
                rate = group_data['rate']
                amount = hours * rate
                
                invoice_item = InvoiceItem(
                    invoice_id=invoice.id,
                    description=f"Professional Services - {task_name}",
                    quantity=hours,
                    unit_price=rate,
                    account_id=revenue_account.id
                )
                
                db.session.add(invoice_item)
                db.session.commit()
                
                # Update time entries with the invoice item id
                for entry in group_data['entries']:
                    entry.invoice_item_id = invoice_item.id
                
                db.session.commit()
        
        # Create invoice items from expenses
        if expense_ids:
            expenses = ProjectExpense.query.filter(ProjectExpense.id.in_(expense_ids)).all()
            
            for expense in expenses:
                # Create invoice item for this expense
                markup = Decimal('1.00') + (expense.markup_percentage or Decimal('0.00')) / 100
                billable_amount = expense.amount * markup
                
                invoice_item = InvoiceItem(
                    invoice_id=invoice.id,
                    description=f"Expense - {expense.description}",
                    quantity=Decimal('1.00'),
                    unit_price=billable_amount,
                    account_id=expense.account_id
                )
                
                db.session.add(invoice_item)
                db.session.commit()
                
                # Update expense with the invoice item id
                expense.invoice_item_id = invoice_item.id
                db.session.commit()
        
        # Update invoice total
        invoice_items = InvoiceItem.query.filter_by(invoice_id=invoice.id).all()
        invoice.total_amount = sum(item.quantity * item.unit_price for item in invoice_items)
        db.session.commit()
        
        flash(f'Invoice {invoice.invoice_number} generated successfully.', 'success')
        return redirect(url_for('invoicing.view_invoice', invoice_id=invoice.id))
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error generating invoice: {str(e)}")
        flash('There was an error generating the invoice. Please try again.', 'danger')
        return redirect(url_for('projects.project_billing', project_id=project_id))

@projects_bp.route('/<int:project_id>/reports')
@login_required
def project_reports(project_id):
    """View reports for a project"""
    try:
        project = Project.query.get_or_404(project_id)
        
        # Get time summary by task
        task_time_summary = db.session.query(
            JobTask.id,
            JobTask.name,
            func.sum(TimeEntry.hours).label('total_hours'),
            func.sum(TimeEntry.cost_amount).label('total_cost'),
            func.sum(func.case((TimeEntry.is_billable, TimeEntry.billable_amount), else_=0)).label('total_billable')
        ).outerjoin(
            TimeEntry, TimeEntry.task_id == JobTask.id
        ).filter(
            JobTask.project_id == project_id
        ).group_by(
            JobTask.id, JobTask.name
        ).order_by(
            JobTask.name
        ).all()
        
        # Get time summary by user
        user_time_summary = db.session.query(
            User.id,
            User.username,
            func.sum(TimeEntry.hours).label('total_hours'),
            func.sum(TimeEntry.cost_amount).label('total_cost'),
            func.sum(func.case((TimeEntry.is_billable, TimeEntry.billable_amount), else_=0)).label('total_billable')
        ).join(
            TimeEntry, TimeEntry.user_id == User.id
        ).filter(
            TimeEntry.project_id == project_id
        ).group_by(
            User.id, User.username
        ).order_by(
            User.username
        ).all()
        
        # Get expense summary by category
        expense_summary = db.session.query(
            Account.id,
            Account.name,
            func.sum(ProjectExpense.amount).label('total_amount'),
            func.sum(func.case((ProjectExpense.is_billable, ProjectExpense.billable_amount), else_=0)).label('total_billable')
        ).join(
            ProjectExpense, ProjectExpense.account_id == Account.id
        ).filter(
            ProjectExpense.project_id == project_id
        ).group_by(
            Account.id, Account.name
        ).order_by(
            Account.name
        ).all()
        
        # Calculate project totals
        total_hours = sum(row.total_hours or 0 for row in task_time_summary)
        total_cost = sum(row.total_cost or 0 for row in task_time_summary)
        total_billable_time = sum(row.total_billable or 0 for row in task_time_summary)
        total_expenses = sum(row.total_amount or 0 for row in expense_summary)
        total_billable_expenses = sum(row.total_billable or 0 for row in expense_summary)
        total_revenue = total_billable_time + total_billable_expenses
        
        # Calculate profit/loss
        project_profit = total_revenue - total_cost - total_expenses
        profit_margin = (project_profit / total_revenue * 100) if total_revenue > 0 else 0
        
        return render_template(
            'projects/reports.html',
            project=project,
            task_time_summary=task_time_summary,
            user_time_summary=user_time_summary,
            expense_summary=expense_summary,
            total_hours=total_hours,
            total_cost=total_cost,
            total_billable_time=total_billable_time,
            total_expenses=total_expenses,
            total_billable_expenses=total_billable_expenses,
            total_revenue=total_revenue,
            project_profit=project_profit,
            profit_margin=profit_margin,
            format_currency=format_currency
        )
    
    except Exception as e:
        logger.error(f"Error viewing project reports: {str(e)}")
        flash('There was an error retrieving the project reports. Please try again.', 'danger')
        return redirect(url_for('projects.view_project', project_id=project_id))

# API endpoints for AJAX requests
@projects_bp.route('/api/tasks/<int:task_id>/info')
@login_required
def get_task_info(task_id):
    """Get information about a task for dynamic forms"""
    try:
        task = JobTask.query.get_or_404(task_id)
        
        return jsonify({
            'success': True,
            'is_billable': task.is_billable,
            'billing_rate': float(task.billing_rate) if task.billing_rate else None
        })
    
    except Exception as e:
        logger.error(f"Error getting task info: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get task information'
        }), 500