#!/usr/bin/env python3
"""
Simple AlloyDB Database Initialization Script

This script initializes the AlloyDB databases and tables required for the
Online Boutique Shopping Assistant service without using Secret Manager.

Usage:
    python init_alloydb_simple.py <password>
"""

import os
import sys
import time
import logging
from typing import Optional

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration from environment variables
PROJECT_ID = os.environ.get("PROJECT_ID", "wise-karma-472219-r2")
ALLOYDB_PRIMARY_IP = os.environ.get("ALLOYDB_PRIMARY_IP", "10.36.0.2")

def create_connection(password: str, database: Optional[str] = None, retries: int = 3) -> psycopg2.extensions.connection:
    """Create connection to AlloyDB with retry logic."""
    connection_params = {
        'host': ALLOYDB_PRIMARY_IP,
        'port': 5432,
        'user': 'postgres',
        'password': password,
        'connect_timeout': 30
    }
    
    if database:
        connection_params['database'] = database
    
    for attempt in range(retries):
        try:
            logger.info(f"Attempting to connect to AlloyDB (attempt {attempt + 1}/{retries})")
            if database:
                logger.info(f"Connecting to database: {database}")
            
            conn = psycopg2.connect(**connection_params)
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            
            logger.info("Successfully connected to AlloyDB")
            return conn
            
        except psycopg2.Error as e:
            logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
            if attempt < retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                logger.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                logger.error("All connection attempts failed")
                raise

def database_exists(conn: psycopg2.extensions.connection, database_name: str) -> bool:
    """Check if a database exists."""
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (database_name,)
            )
            return cursor.fetchone() is not None
    except psycopg2.Error as e:
        logger.error(f"Error checking if database {database_name} exists: {e}")
        return False

def create_database(conn: psycopg2.extensions.connection, database_name: str) -> None:
    """Create a database if it doesn't exist."""
    try:
        if database_exists(conn, database_name):
            logger.info(f"Database '{database_name}' already exists")
            return
        
        with conn.cursor() as cursor:
            # Create database
            cursor.execute(f'CREATE DATABASE "{database_name}"')
            logger.info(f"Successfully created database: {database_name}")
            
    except psycopg2.Error as e:
        logger.error(f"Failed to create database {database_name}: {e}")
        raise

def setup_products_database(password: str) -> None:
    """Set up the products database with vector extension and catalog_items table."""
    logger.info("Setting up products database...")
    
    # Connect to products database
    conn = create_connection(password, 'products')
    
    try:
        with conn.cursor() as cursor:
            # Enable vector extension
            logger.info("Enabling vector extension...")
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
            
            # Create catalog_items table
            logger.info("Creating catalog_items table...")
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS catalog_items (
                id VARCHAR PRIMARY KEY,
                name VARCHAR NOT NULL,
                description TEXT NOT NULL,
                categories TEXT[],
                price_usd DECIMAL(10,2),
                picture VARCHAR,
                product_embedding VECTOR(768)
            )
            """
            cursor.execute(create_table_sql)
            
            # Create vector similarity index for efficient search
            logger.info("Creating vector similarity index...")
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS catalog_items_embedding_idx 
                ON catalog_items USING hnsw (product_embedding vector_cosine_ops)
            """)
            
            logger.info("Products database setup completed successfully")
            
    except psycopg2.Error as e:
        logger.error(f"Failed to setup products database: {e}")
        raise
    finally:
        conn.close()

def setup_carts_database(password: str) -> None:
    """Set up the carts database with cart_items table."""
    logger.info("Setting up carts database...")
    
    # Connect to carts database
    conn = create_connection(password, 'carts')
    
    try:
        with conn.cursor() as cursor:
            # Create cart_items table
            logger.info("Creating cart_items table...")
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS cart_items (
                user_id VARCHAR NOT NULL,
                product_id VARCHAR NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, product_id)
            )
            """
            cursor.execute(create_table_sql)
            
            # Create index for efficient cart lookups
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS cart_items_user_id_idx 
                ON cart_items (user_id)
            """)
            
            logger.info("Carts database setup completed successfully")
            
    except psycopg2.Error as e:
        logger.error(f"Failed to setup carts database: {e}")
        raise
    finally:
        conn.close()

def verify_setup(password: str) -> None:
    """Verify that databases and tables were created successfully."""
    logger.info("Verifying database setup...")
    
    try:
        # Verify products database
        conn = create_connection(password, 'products')
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'catalog_items'")
            if cursor.fetchone()[0] == 1:
                logger.info("✓ catalog_items table exists in products database")
            else:
                raise Exception("catalog_items table not found")
        conn.close()
        
        # Verify carts database
        conn = create_connection(password, 'carts')
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'cart_items'")
            if cursor.fetchone()[0] == 1:
                logger.info("✓ cart_items table exists in carts database")
            else:
                raise Exception("cart_items table not found")
        conn.close()
        
        logger.info("Database verification completed successfully")
        
    except Exception as e:
        logger.error(f"Database verification failed: {e}")
        raise

def main():
    """Main function to initialize AlloyDB databases."""
    if len(sys.argv) != 2:
        print("Usage: python init_alloydb_simple.py <password>")
        sys.exit(1)
    
    password = sys.argv[1]
    
    logger.info("Starting AlloyDB initialization...")
    
    try:
        # Connect to default postgres database to create new databases
        logger.info("Connecting to AlloyDB...")
        conn = create_connection(password)
        
        # Create databases
        logger.info("Creating databases...")
        create_database(conn, 'products')
        create_database(conn, 'carts')
        conn.close()
        
        # Setup database schemas
        setup_products_database(password)
        setup_carts_database(password)
        
        # Verify setup
        verify_setup(password)
        
        logger.info("AlloyDB initialization completed successfully!")
        logger.info("Next steps:")
        logger.info("1. Run the product embedding generation script")
        logger.info("2. Build and deploy the Shopping Assistant service")
        
    except Exception as e:
        logger.error(f"AlloyDB initialization failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()