#!/usr/bin/env python3
"""
Simple Database Population Script

This script generates embeddings and populates the AlloyDB products database.

Usage:
    python populate_simple.py <password>
"""

import os
import json
import sys
import logging
from typing import List, Dict, Any

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from langchain_google_genai import GoogleGenerativeAIEmbeddings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
ALLOYDB_PRIMARY_IP = os.environ.get("ALLOYDB_PRIMARY_IP", "10.36.0.2")
PRODUCTS_FILE = "products.json"

def load_products() -> List[Dict[str, Any]]:
    """Load products from the products.json file."""
    try:
        logger.info(f"Loading products from {PRODUCTS_FILE}")
        
        if not os.path.exists(PRODUCTS_FILE):
            raise FileNotFoundError(f"Products file not found: {PRODUCTS_FILE}")
        
        with open(PRODUCTS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        products = data.get('products', [])
        logger.info(f"Loaded {len(products)} products")
        
        return products
        
    except Exception as e:
        logger.error(f"Failed to load products: {e}")
        raise

def create_embedding_text(product: Dict[str, Any]) -> str:
    """Create a comprehensive text representation of a product for embedding."""
    name = product.get('name', '')
    description = product.get('description', '')
    categories = product.get('categories', [])
    
    category_text = ', '.join(categories) if categories else ''
    
    embedding_text = f"{name}. {description}"
    if category_text:
        embedding_text += f" Categories: {category_text}."
    
    return embedding_text

def convert_price_to_decimal(price_usd: Dict[str, Any]) -> float:
    """Convert price from the nested format to a decimal value."""
    try:
        units = price_usd.get('units', 0)
        nanos = price_usd.get('nanos', 0)
        
        decimal_price = float(units) + (float(nanos) / 1_000_000_000)
        return round(decimal_price, 2)
        
    except Exception as e:
        logger.warning(f"Failed to convert price: {e}")
        return 0.0

def generate_embeddings(products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Generate embeddings for all products."""
    # Check for API key
    api_key = os.environ.get('GOOGLE_API_KEY')
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable is required")
    
    # Initialize embedding service
    logger.info("Initializing Gemini embedding service...")
    embedding_service = GoogleGenerativeAIEmbeddings(
        model="models/embedding-001",
        google_api_key=api_key
    )
    
    # Prepare texts for embedding
    texts = []
    for product in products:
        embedding_text = create_embedding_text(product)
        texts.append(embedding_text)
    
    # Generate embeddings
    logger.info(f"Generating embeddings for {len(texts)} products...")
    embeddings = embedding_service.embed_documents(texts)
    
    # Prepare results
    results = []
    for i, product in enumerate(products):
        price_decimal = convert_price_to_decimal(product.get('priceUsd', {}))
        
        result = {
            'id': product['id'],
            'name': product['name'],
            'description': product['description'],
            'categories': product.get('categories', []),
            'price_usd': price_decimal,
            'picture': product.get('picture', ''),
            'product_embedding': embeddings[i]
        }
        results.append(result)
    
    logger.info(f"Successfully generated embeddings for {len(results)} products")
    return results

def create_connection(password: str) -> psycopg2.extensions.connection:
    """Create connection to AlloyDB products database."""
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

def populate_database(password: str, embeddings_data: List[Dict[str, Any]]) -> None:
    """Populate the catalog_items table with product data and embeddings."""
    conn = create_connection(password)
    
    try:
        logger.info(f"Populating catalog_items table with {len(embeddings_data)} products...")
        
        # Clear existing data
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM catalog_items")
            logger.info("Cleared existing product data")
        
        # Insert products
        with conn.cursor() as cursor:
            insert_sql = """
                INSERT INTO catalog_items 
                (id, name, description, categories, price_usd, picture, product_embedding)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            
            for product in embeddings_data:
                cursor.execute(insert_sql, (
                    product['id'],
                    product['name'],
                    product['description'],
                    product['categories'],
                    product['price_usd'],
                    product['picture'],
                    product['product_embedding']
                ))
            
            logger.info(f"Successfully inserted {len(embeddings_data)} products")
        
        # Verify population
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM catalog_items")
            count = cursor.fetchone()[0]
            
            if count != len(embeddings_data):
                raise ValueError(f"Expected {len(embeddings_data)} products, but found {count}")
            
            logger.info(f"✓ Database verification passed: {count} products with embeddings")
        
        # Test vector search
        with conn.cursor() as cursor:
            cursor.execute("SELECT product_embedding FROM catalog_items LIMIT 1")
            sample_embedding = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT id, name, 1 - (product_embedding <=> %s) as similarity
                FROM catalog_items 
                ORDER BY product_embedding <=> %s
                LIMIT 3
            """, (sample_embedding, sample_embedding))
            
            results = cursor.fetchall()
            logger.info("Vector search test results:")
            for result in results:
                product_id, name, similarity = result
                logger.info(f"  {product_id}: {name} (similarity: {similarity:.3f})")
            
            logger.info("✓ Vector similarity search is working correctly")
        
    finally:
        conn.close()

def main():
    """Main function to populate the database with product embeddings."""
    if len(sys.argv) != 2:
        print("Usage: python populate_simple.py <password>")
        sys.exit(1)
    
    password = sys.argv[1]
    
    logger.info("Starting database population...")
    
    try:
        # Load products
        products = load_products()
        
        # Generate embeddings
        embeddings_data = generate_embeddings(products)
        
        # Populate database
        populate_database(password, embeddings_data)
        
        logger.info("Database population completed successfully!")
        logger.info(f"Populated {len(embeddings_data)} products with vector embeddings")
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. Build Shopping Assistant service: skaffold build")
        logger.info("2. Deploy the service to Kubernetes")
        
    except Exception as e:
        logger.error(f"Database population failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()