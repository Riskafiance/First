"""
Test PostgreSQL database connection
"""
import os
import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_postgres_connection():
    """Test PostgreSQL database connection"""
    try:
        # Get database URL from environment
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            logger.error("DATABASE_URL environment variable not set")
            return False
        
        logger.info("Connecting to PostgreSQL database...")
        
        # Connect to the database
        conn = psycopg2.connect(database_url)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        
        # Create a cursor
        cur = conn.cursor()
        
        # Get PostgreSQL version info
        logger.info("Getting PostgreSQL version info...")
        cur.execute("SELECT version();")
        version = cur.fetchone()
        logger.info("PostgreSQL version: %s", version)
        
        # List tables in the database
        logger.info("Listing tables in the database...")
        cur.execute(sql.SQL("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';"))
        tables = cur.fetchall()
        logger.info("Tables in database:")
        for table in tables:
            logger.info("  - %s", table[0])
        
        # Close cursor and connection
        cur.close()
        conn.close()
        
        logger.info("PostgreSQL connection test successful!")
        return True
    
    except Exception as e:
        logger.error("Error connecting to PostgreSQL database: %s", e)
        return False

if __name__ == "__main__":
    test_postgres_connection()