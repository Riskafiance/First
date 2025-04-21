"""
PostgreSQL database utilities
"""
import os
import logging
from sqlalchemy import text
from app import db

logger = logging.getLogger(__name__)

def is_using_postgresql():
    """Check if PostgreSQL is being used"""
    database_url = os.environ.get("DATABASE_URL", "")
    return database_url.startswith(("postgres://", "postgresql://"))

def create_index(table_name, column_name, index_name=None, unique=False):
    """Create an index on a table column"""
    if not is_using_postgresql():
        logger.warning("Not using PostgreSQL, skipping index creation")
        return
    
    if index_name is None:
        index_name = f"idx_{table_name}_{column_name}"
    
    unique_clause = "UNIQUE" if unique else ""
    
    try:
        with db.engine.connect() as conn:
            # Check if index already exists
            result = conn.execute(text(
                "SELECT 1 FROM pg_indexes WHERE indexname = :index_name"
            ), {"index_name": index_name})
            
            if result.fetchone():
                logger.info(f"Index {index_name} already exists")
                return
            
            # Create the index
            conn.execute(text(
                f"CREATE {unique_clause} INDEX {index_name} ON {table_name} ({column_name})"
            ))
            
            logger.info(f"Created index {index_name} on {table_name}.{column_name}")
    except Exception as e:
        logger.error(f"Error creating index {index_name}: {e}")

def create_search_index(table_name, column_name, index_name=None):
    """Create a full-text search index on a text column"""
    if not is_using_postgresql():
        logger.warning("Not using PostgreSQL, skipping search index creation")
        return
    
    if index_name is None:
        index_name = f"idx_search_{table_name}_{column_name}"
    
    try:
        with db.engine.connect() as conn:
            # Check if index already exists
            result = conn.execute(text(
                "SELECT 1 FROM pg_indexes WHERE indexname = :index_name"
            ), {"index_name": index_name})
            
            if result.fetchone():
                logger.info(f"Index {index_name} already exists")
                return
            
            # Create the GIN index for full-text search
            conn.execute(text(
                f"CREATE INDEX {index_name} ON {table_name} USING gin(to_tsvector('english', {column_name}))"
            ))
            
            logger.info(f"Created full-text search index {index_name} on {table_name}.{column_name}")
    except Exception as e:
        logger.error(f"Error creating search index {index_name}: {e}")

def perform_full_text_search(table_name, column_name, search_term, limit=10):
    """Perform a full-text search on a column"""
    if not is_using_postgresql():
        logger.warning("Not using PostgreSQL, falling back to LIKE search")
        return []
    
    try:
        with db.engine.connect() as conn:
            result = conn.execute(text(
                f"SELECT * FROM {table_name} "
                f"WHERE to_tsvector('english', {column_name}) @@ plainto_tsquery('english', :search_term) "
                f"ORDER BY ts_rank(to_tsvector('english', {column_name}), plainto_tsquery('english', :search_term)) DESC "
                f"LIMIT :limit"
            ), {"search_term": search_term, "limit": limit})
            
            return result.fetchall()
    except Exception as e:
        logger.error(f"Error performing full-text search: {e}")
        return []

def analyze_table(table_name):
    """Analyze a table to update statistics for the query planner"""
    if not is_using_postgresql():
        logger.warning("Not using PostgreSQL, skipping table analysis")
        return
    
    try:
        # Handle PostgreSQL reserved keywords like 'user' by quoting the table name
        quoted_table_name = f'"{table_name}"' if table_name.lower() in ('user', 'order', 'group', 'table') else table_name
        
        with db.engine.connect() as conn:
            conn.execute(text(f"ANALYZE {quoted_table_name}"))
            logger.info(f"Analyzed table {table_name}")
    except Exception as e:
        logger.error(f"Error analyzing table {table_name}: {e}")

def optimize_queries():
    """Create indexes on commonly queried columns to optimize performance"""
    if not is_using_postgresql():
        return
    
    # Create indexes for commonly queried columns
    create_index("invoice", "entity_id")
    create_index("invoice", "status_id")
    create_index("invoice", "issue_date")
    create_index("invoice", "invoice_number", unique=True)
    
    create_index("journal_entry", "entry_date")
    create_index("journal_entry", "is_posted")
    
    create_index("journal_item", "journal_entry_id")
    create_index("journal_item", "account_id")
    
    create_index("account", "account_type_id")
    create_index("account", "code", unique=True)
    
    create_index("entity", "entity_type_id")
    create_index("entity", "name")
    
    create_index("expense", "entity_id")
    create_index("expense", "status_id")
    create_index("expense", "expense_date")
    
    create_index("product", "category_id")
    create_index("product", "sku", unique=True)
    
    create_index("fixed_asset", "category_id")
    create_index("fixed_asset", "asset_number", unique=True)
    
    # Create full-text search indexes
    create_search_index("entity", "name")
    create_search_index("product", "name")
    create_search_index("product", "description")
    create_search_index("invoice", "notes")
    create_search_index("expense", "notes")
    create_search_index("fixed_asset", "description")
    
    # Analyze tables to update statistics
    for table in [
        "user", "role", "account", "account_type", "journal_entry", "journal_item",
        "entity", "entity_type", "invoice", "invoice_status", "invoice_item",
        "expense", "expense_status", "expense_item", "product", "product_category",
        "fixed_asset", "asset_category", "asset_depreciation", "budget", "budget_item"
    ]:
        analyze_table(table)