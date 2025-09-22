#!/usr/bin/env python3
"""
Simple script to verify and initialize AlloyDB database
"""

import os
import sys
import json
import logging
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from google.cloud import secretmanager_v1
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
PROJECT_ID = "wise-karma-472219-r2"
ALLOYDB_IP = "10.36.0.2"
ALLOYDB_DATABASE = "products"
ALLOYDB_TABLE = "catalog_items"
GOOGLE_API_KEY = "AIzaSyCjvgLUncC4iVQlff_CwUXmAihYDvqEW74"

# Product data
PRODUCTS = [
    {"id": "OLJCESPC7Z", "name": "Sunglasses", "description": "Add a modern touch to your outfits with these sleek aviator sunglasses.", "categories": ["accessories"]},
    {"id": "66VCHSJNUP", "name": "Tank Top", "description": "Perfectly cropped cotton tank, with a scooped neckline.", "categories": ["clothing", "tops"]},
    {"id": "1YMWWN1N4O", "name": "Watch", "description": "This gold-tone stainless steel watch will work with most of your outfits.", "categories": ["accessories"]},
    {"id": "L9ECAV7KIM", "name": "Loafers", "description": "A neat addition to your summer wardrobe.", "categories": ["footwear"]},
    {"id": "2ZYFJ3GM2N", "name": "Hairdryer", "description": "This lightweight hairdryer has 3 heat and speed settings. It's perfect for travel.", "categories": ["hair", "beauty"]},
    {"id": "0PUK6V6EV0", "name": "Candle Holder", "description": "This small but intricate candle holder is an excellent gift.", "categories": ["decor", "home"]},
    {"id": "LS4PSXUNUM", "name": "Salt & Pepper Shakers", "description": "Add some flavor to your kitchen.", "categories": ["kitchen", "home"]},
    {"id": "9SIQT8TOJO", "name": "Vintage Typewriter", "description": "This typewriter looks good in your living room.", "categories": ["vintage", "decor", "home"]},
    {"id": "6E92ZMYYFZ", "name": "Film Camera", "description": "This camera looks like it's a few decades old but it's actually brand new.", "categories": ["photography", "vintage"]}
]

def get_embeddings(texts, api_key):
    """Generate embeddings using Gemini API."""
    logger.info(f"Generating embeddings for {len(texts)} texts...")
    
    embeddings = []
    for i, text in enumerate(texts):
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/embedding-001:embedContent?key={api_key}"
            headers = {"Content-Type": "application/json"}
            data = {
                "model": "models/embedding-001",
                "content": {"parts": [{"text": text}]}
            }
            
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            
            embedding = response.json()["embedding"]["values"]
            embeddings.append(embedding)
            logger.info(f"Generated embedding {i+1}/{len(texts)}")
            
        except Exception as e:
            logger.error(f"Failed to generate embedding for text {i}: {e}")
            raise
    
    return embeddings

def get_alloydb_password():
    """Get AlloyDB password from Secret Manager."""
    try:
        client = secretmanager_v1.SecretManagerServiceClient()
        secret_name = client.secret_version_path(
            project=PROJECT_ID, 
            secret="alloydb-secret", 
            secret_version="latest"
        )
        
        request = secretmanager_v1.AccessSecretVersionRequest(name=secret_name)
        response = client.access_secret_version(request=request)
        
        return response.payload.data.decode("UTF-8").strip()
    except Exception as e:
        logger.error(f"Failed to get password from Secret Manager: {e}")
        raise

def check_database_status():
    """Check if database and table exist."""
    try:
        password = get_alloydb_password()
        
        # Check if products database exists
        conn = psycopg2.connect(
            host=ALLOYDB_IP,
            port=5432,
            user="postgres",
            password=password,
            database="postgres",
            connect_timeout=30
        )
        
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (ALLOYDB_DATABASE,))
            db_exists = cursor.fetchone() is not None
        
        conn.close()
        
        if not db_exists:
            logger.info("❌ Products database does not exist")
            return False
        
        # Check if table exists and has data
        conn = psycopg2.connect(
            host=ALLOYDB_IP,
            port=5432,
            user="postgres",
            password=password,
            database=ALLOYDB_DATABASE,
            connect_timeout=30
        )
        
        with conn.cursor() as cursor:
            # Check if table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = %s
                )
            """, (ALLOYDB_TABLE,))
            table_exists = cursor.fetchone()[0]
            
            if not table_exists:
                logger.info("❌ catalog_items table does not exist")
                conn.close()
                return False
            
            # Check if vector extension is enabled
            cursor.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
            vector_exists = cursor.fetchone() is not None
            
            if not vector_exists:
                logger.info("❌ Vector extension is not enabled")
                conn.close()
                return False
            
            # Check if table has data
            cursor.execute(f"SELECT COUNT(*) FROM {ALLOYDB_TABLE}")
            count = cursor.fetchone()[0]
            
            if count == 0:
                logger.info("❌ catalog_items table is empty")
                conn.close()
                return False
            
            logger.info(f"✅ Database is properly initialized with {count} products")
            conn.close()
            return True
            
    except Exception as e:
        logger.error(f"Database check failed: {e}")
        return False

def init_database():
    """Initialize AlloyDB with products and embeddings."""
    logger.info("Starting AlloyDB initialization...")
    
    # Get password
    password = get_alloydb_password()
    
    # Connect to postgres database to create products database if needed
    conn = psycopg2.connect(
        host=ALLOYDB_IP,
        port=5432,
        user="postgres",
        password=password,
        database="postgres",
        connect_timeout=30
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    
    try:
        with conn.cursor() as cursor:
            # Check if products database exists
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (ALLOYDB_DATABASE,))
            if not cursor.fetchone():
                logger.info(f"Creating database: {ALLOYDB_DATABASE}")
                cursor.execute(f'CREATE DATABASE "{ALLOYDB_DATABASE}"')
            else:
                logger.info(f"Database {ALLOYDB_DATABASE} already exists")
    finally:
        conn.close()
    
    # Connect to products database
    conn = psycopg2.connect(
        host=ALLOYDB_IP,
        port=5432,
        user="postgres",
        password=password,
        database=ALLOYDB_DATABASE,
        connect_timeout=30
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    
    try:
        with conn.cursor() as cursor:
            # Enable vector extension
            logger.info("Enabling vector extension...")
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
            
            # Create table
            logger.info("Creating catalog_items table...")
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {ALLOYDB_TABLE} (
                    id VARCHAR PRIMARY KEY,
                    name VARCHAR NOT NULL,
                    description TEXT NOT NULL,
                    categories TEXT[],
                    price_usd DECIMAL(10,2),
                    picture VARCHAR,
                    product_embedding VECTOR(768)
                )
            """)
            
            # Create vector index
            logger.info("Creating vector similarity index...")
            cursor.execute(f"""
                CREATE INDEX IF NOT EXISTS {ALLOYDB_TABLE}_embedding_idx 
                ON {ALLOYDB_TABLE} USING hnsw (product_embedding vector_cosine_ops)
            """)
            
            # Generate embeddings
            texts = [product["description"] for product in PRODUCTS]
            embeddings = get_embeddings(texts, GOOGLE_API_KEY)
            
            # Insert products with embeddings
            logger.info("Inserting products with embeddings...")
            for product, embedding in zip(PRODUCTS, embeddings):
                cursor.execute(f"""
                    INSERT INTO {ALLOYDB_TABLE} 
                    (id, name, description, categories, product_embedding)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        name = EXCLUDED.name,
                        description = EXCLUDED.description,
                        categories = EXCLUDED.categories,
                        product_embedding = EXCLUDED.product_embedding
                """, (
                    product["id"],
                    product["name"],
                    product["description"],
                    product["categories"],
                    embedding
                ))
            
            # Verify insertion
            cursor.execute(f"SELECT COUNT(*) FROM {ALLOYDB_TABLE}")
            count = cursor.fetchone()[0]
            logger.info(f"✅ Successfully inserted {count} products")
            
            # Test vector search
            logger.info("Testing vector search...")
            test_embedding = get_embeddings(["stylish accessories"], GOOGLE_API_KEY)[0]
            cursor.execute(f"""
                SELECT id, name, description, 
                       product_embedding <=> %s as distance
                FROM {ALLOYDB_TABLE}
                ORDER BY distance
                LIMIT 3
            """, (test_embedding,))
            
            results = cursor.fetchall()
            logger.info("✅ Vector search test results:")
            for row in results:
                logger.info(f"  - {row[1]}: {row[2][:50]}... (distance: {row[3]:.4f})")
            
            logger.info("🎉 Database initialization completed successfully!")
    
    finally:
        conn.close()

if __name__ == "__main__":
    try:
        # First check if database is already initialized
        if check_database_status():
            logger.info("✅ Database is already properly initialized!")
            sys.exit(0)
        
        # Initialize if needed
        init_database()
        logger.info("SUCCESS: AlloyDB initialization complete")
    except Exception as e:
        logger.error(f"FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)