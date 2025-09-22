#!/usr/bin/env python3
"""
Database Population Script

This script populates the AlloyDB products database with product data and embeddings.
It can either generate embeddings on-the-fly or use pre-generated embeddings from
the generate_embeddings.py script.

Usage:
    python populate_database.py [--use-saved-embeddings]
"""

import os
import json
import sys
import argparse
import logging
from typing import List, Dict, Any, Optional

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from google.cloud import secretmanager_v1

# Import our embedding generation functions
from generate_embeddings import generate_all_embeddings, load_products

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration from environment variables
PROJECT_ID = os.environ.get("PROJECT_ID", "wise-karma-472219-r2")
ALLOYDB_SECRET_NAME = os.environ.get("ALLOYDB_SECRET_NAME", "alloydb-secret")
ALLOYDB_PRIMARY_IP = os.environ.get("ALLOYDB_PRIMARY_IP", "10.36.0.2")
EMBEDDINGS_FILE = "scripts/product_embeddings.json"

def get_database_password() -> str:
    """Retrieve database password from Google Secret Manager."""
    try:
        client = secretmanager_v1.SecretManagerServiceClient()
        secret_name = client.secret_version_path(
            project=PROJECT_ID, 
            secret=ALLOYDB_SECRET_NAME, 
            secret_version="latest"
        )
        
        request = secretmanager_v1.AccessSecretVersionRequest(name=secret_name)
        response = client.access_secret_version(request=request)
        password = response.payload.data.decode("UTF-8").strip()
        
        return password
        
    except Exception as e:
        logger.error(f"Failed to retrieve password from Secret Manager: {e}")
        raise

def create_connection() -> psycopg2.extensions.connection:
    """Create connection to AlloyDB products database."""
    password = get_database_password()
    
    try:
        logger.info("Connecting to AlloyDB products database...")
        conn = psycopg2.connect(
            host=ALLOYDB_PRIMARY_IP,
            port=5432,
            database='products',
            user='postgres',
            password=password,
            connect_timeout=30
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        
        logger.info("Successfully connected to products database")
        return conn
        
    except psycopg2.Error as e:
        logger.error(f"Failed to connect to products database: {e}")
        raise

def load_saved_embeddings() -> Optional[List[Dict[str, Any]]]:
    """Load pre-generated embeddings from file if available."""
    try:
        if not os.path.exists(EMBEDDINGS_FILE):
            logger.info(f"No saved embeddings found at {EMBEDDINGS_FILE}")
            return None
        
        logger.info(f"Loading saved embeddings from {EMBEDDINGS_FILE}")
        with open(EMBEDDINGS_FILE, 'r', encoding='utf-8') as f:
            embeddings_data = json.load(f)
        
        logger.info(f"Loaded {len(embeddings_data)} saved embeddings")
        return embeddings_data
        
    except Exception as e:
        logger.error(f"Failed to load saved embeddings: {e}")
        return None

def clear_existing_data(conn: psycopg2.extensions.connection) -> None:
    """Clear existing product data from the catalog_items table."""
    try:
        logger.info("Clearing existing product data...")
        
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM catalog_items")
            cursor.execute("SELECT COUNT(*) FROM catalog_items")
            count = cursor.fetchone()[0]
            
            if count == 0:
                logger.info("Successfully cleared existing product data")
            else:
                logger.warning(f"Warning: {count} items still remain in catalog_items table")
                
    except psycopg2.Error as e:
        logger.error(f"Failed to clear existing data: {e}")
        raise

def insert_products_batch(conn: psycopg2.extensions.connection, 
                         products_batch: List[Dict[str, Any]]) -> None:
    """Insert a batch of products into the catalog_items table."""
    try:
        with conn.cursor() as cursor:
            # Prepare the INSERT statement
            insert_sql = """
                INSERT INTO catalog_items 
                (id, name, description, categories, price_usd, picture, product_embedding)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    description = EXCLUDED.description,
                    categories = EXCLUDED.categories,
                    price_usd = EXCLUDED.price_usd,
                    picture = EXCLUDED.picture,
                    product_embedding = EXCLUDED.product_embedding
            """
            
            # Prepare batch data
            batch_data = []
            for product in products_batch:
                batch_data.append((
                    product['id'],
                    product['name'],
                    product['description'],
                    product['categories'],  # PostgreSQL array
                    product['price_usd'],
                    product['picture'],
                    product['product_embedding']  # Vector type
                ))
            
            # Execute batch insert
            cursor.executemany(insert_sql, batch_data)
            
            logger.info(f"Successfully inserted {len(batch_data)} products")
            
    except psycopg2.Error as e:
        logger.error(f"Failed to insert products batch: {e}")
        raise

def populate_products_table(conn: psycopg2.extensions.connection, 
                          embeddings_data: List[Dict[str, Any]]) -> None:
    """Populate the catalog_items table with product data and embeddings."""
    try:
        logger.info(f"Populating catalog_items table with {len(embeddings_data)} products...")
        
        # Clear existing data
        clear_existing_data(conn)
        
        # Insert products in batches
        batch_size = 10
        for i in range(0, len(embeddings_data), batch_size):
            batch = embeddings_data[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(embeddings_data) + batch_size - 1) // batch_size
            
            logger.info(f"Inserting batch {batch_num}/{total_batches} ({len(batch)} products)")
            insert_products_batch(conn, batch)
        
        logger.info("Successfully populated catalog_items table")
        
    except Exception as e:
        logger.error(f"Failed to populate products table: {e}")
        raise

def verify_population(conn: psycopg2.extensions.connection, 
                     expected_count: int) -> None:
    """Verify that the database was populated correctly."""
    try:
        logger.info("Verifying database population...")
        
        with conn.cursor() as cursor:
            # Check total count
            cursor.execute("SELECT COUNT(*) FROM catalog_items")
            actual_count = cursor.fetchone()[0]
            
            if actual_count != expected_count:
                raise ValueError(f"Expected {expected_count} products, but found {actual_count}")
            
            # Check that embeddings are present
            cursor.execute("SELECT COUNT(*) FROM catalog_items WHERE product_embedding IS NOT NULL")
            embedding_count = cursor.fetchone()[0]
            
            if embedding_count != expected_count:
                raise ValueError(f"Expected {expected_count} embeddings, but found {embedding_count}")
            
            # Sample a few products to verify data integrity
            cursor.execute("""
                SELECT id, name, description, array_length(categories, 1), price_usd, 
                       array_length(product_embedding, 1) as embedding_dim
                FROM catalog_items 
                LIMIT 3
            """)
            
            sample_products = cursor.fetchall()
            logger.info("Sample products:")
            for product in sample_products:
                product_id, name, description, cat_count, price, emb_dim = product
                logger.info(f"  {product_id}: {name} (${price}, {cat_count} categories, {emb_dim}D embedding)")
            
            logger.info(f"✓ Database verification passed: {actual_count} products with embeddings")
            
    except Exception as e:
        logger.error(f"Database verification failed: {e}")
        raise

def test_vector_search(conn: psycopg2.extensions.connection) -> None:
    """Test vector similarity search functionality."""
    try:
        logger.info("Testing vector similarity search...")
        
        with conn.cursor() as cursor:
            # Get a sample embedding for testing
            cursor.execute("SELECT product_embedding FROM catalog_items LIMIT 1")
            sample_embedding = cursor.fetchone()[0]
            
            # Perform similarity search
            cursor.execute("""
                SELECT id, name, description, 
                       1 - (product_embedding <=> %s) as similarity
                FROM catalog_items 
                ORDER BY product_embedding <=> %s
                LIMIT 3
            """, (sample_embedding, sample_embedding))
            
            results = cursor.fetchall()
            logger.info("Vector search test results:")
            for result in results:
                product_id, name, description, similarity = result
                logger.info(f"  {product_id}: {name} (similarity: {similarity:.3f})")
            
            logger.info("✓ Vector similarity search is working correctly")
            
    except Exception as e:
        logger.error(f"Vector search test failed: {e}")
        raise

def main():
    """Main function to populate the database with product embeddings."""
    parser = argparse.ArgumentParser(description='Populate AlloyDB with product embeddings')
    parser.add_argument('--use-saved-embeddings', action='store_true',
                       help='Use pre-generated embeddings from file instead of generating new ones')
    
    args = parser.parse_args()
    
    logger.info("Starting database population...")
    
    try:
        # Get embeddings data
        if args.use_saved_embeddings:
            embeddings_data = load_saved_embeddings()
            if embeddings_data is None:
                logger.info("No saved embeddings found, generating new ones...")
                embeddings_data = generate_all_embeddings()
        else:
            logger.info("Generating fresh embeddings...")
            embeddings_data = generate_all_embeddings()
        
        if not embeddings_data:
            raise ValueError("No embeddings data available")
        
        # Connect to database
        conn = create_connection()
        
        try:
            # Populate database
            populate_products_table(conn, embeddings_data)
            
            # Verify population
            verify_population(conn, len(embeddings_data))
            
            # Test vector search
            test_vector_search(conn)
            
            logger.info("Database population completed successfully!")
            logger.info(f"Populated {len(embeddings_data)} products with vector embeddings")
            logger.info("")
            logger.info("Next steps:")
            logger.info("1. Build Shopping Assistant service: skaffold build")
            logger.info("2. Deploy the service to Kubernetes")
            
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"Database population failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()