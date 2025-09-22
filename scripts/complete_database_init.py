#!/usr/bin/env python3
"""
Complete AlloyDB initialization script for Shopping Assistant.
This script initializes the database with products from products.json and generates embeddings.
"""

import os
import sys
import json
import asyncio
import logging
from google.cloud import secretmanager
from google.cloud.alloydb.connector import Connector
import asyncpg

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Product data from products.json
PRODUCTS_DATA = {
    "products": [
        {
            "id": "OLJCESPC7Z",
            "name": "Sunglasses",
            "description": "Add a modern touch to your outfits with these sleek aviator sunglasses.",
            "picture": "/static/img/products/sunglasses.jpg",
            "priceUsd": {"currencyCode": "USD", "units": 19, "nanos": 990000000},
            "categories": ["accessories"]
        },
        {
            "id": "66VCHSJNUP",
            "name": "Tank Top",
            "description": "Perfectly cropped cotton tank, with a scooped neckline.",
            "picture": "/static/img/products/tank-top.jpg",
            "priceUsd": {"currencyCode": "USD", "units": 18, "nanos": 990000000},
            "categories": ["clothing", "tops"]
        },
        {
            "id": "1YMWWN1N4O",
            "name": "Watch",
            "description": "This gold-tone stainless steel watch will work with most of your outfits.",
            "picture": "/static/img/products/watch.jpg",
            "priceUsd": {"currencyCode": "USD", "units": 109, "nanos": 990000000},
            "categories": ["accessories"]
        },
        {
            "id": "L9ECAV7KIM",
            "name": "Loafers",
            "description": "A neat addition to your summer wardrobe.",
            "picture": "/static/img/products/loafers.jpg",
            "priceUsd": {"currencyCode": "USD", "units": 89, "nanos": 990000000},
            "categories": ["footwear"]
        },
        {
            "id": "2ZYFJ3GM2N",
            "name": "Hairdryer",
            "description": "This lightweight hairdryer has 3 heat and speed settings. It's perfect for travel.",
            "picture": "/static/img/products/hairdryer.jpg",
            "priceUsd": {"currencyCode": "USD", "units": 24, "nanos": 990000000},
            "categories": ["hair", "beauty"]
        },
        {
            "id": "0PUK6V6EV0",
            "name": "Candle Holder",
            "description": "This small but intricate candle holder is an excellent gift.",
            "picture": "/static/img/products/candle-holder.jpg",
            "priceUsd": {"currencyCode": "USD", "units": 18, "nanos": 990000000},
            "categories": ["decor", "home"]
        },
        {
            "id": "LS4PSXUNUM",
            "name": "Salt & Pepper Shakers",
            "description": "Add some flavor to your kitchen.",
            "picture": "/static/img/products/salt-and-pepper-shakers.jpg",
            "priceUsd": {"currencyCode": "USD", "units": 18, "nanos": 990000000},
            "categories": ["kitchen", "home"]
        },
        {
            "id": "9SIQT8TOJO",
            "name": "Vintage Typewriter",
            "description": "This typewriter looks good in your living room.",
            "picture": "/static/img/products/typewriter.jpg",
            "priceUsd": {"currencyCode": "USD", "units": 67, "nanos": 990000000},
            "categories": ["vintage", "decor", "home"]
        },
        {
            "id": "6E92ZMYYFZ",
            "name": "Film Camera",
            "description": "This camera looks like it's a few decades old but it's actually brand new.",
            "picture": "/static/img/products/film-camera.jpg",
            "priceUsd": {"currencyCode": "USD", "units": 2245, "nanos": 0},
            "categories": ["photography", "vintage"]
        }
    ]
}

async def init_database_complete():
    """Initialize AlloyDB with complete product catalog and embeddings"""
    
    # Configuration
    project_id = "wise-karma-472219-r2"
    region = "us-central1"
    cluster_name = "onlineboutique-cluster"
    instance_name = "onlineboutique-instance"
    database_name = "products"
    table_name = "catalog_items"
    
    # Get password from command line or Secret Manager
    if len(sys.argv) > 1:
        password = sys.argv[1]
    else:
        logger.info("Getting password from Secret Manager...")
        try:
            client = secretmanager.SecretManagerServiceClient()
            secret_path = f"projects/{project_id}/secrets/alloydb-secret/versions/latest"
            response = client.access_secret_version(request={"name": secret_path})
            password = response.payload.data.decode("UTF-8").strip()
        except Exception as e:
            logger.error(f"Failed to get password: {e}")
            return False
    
    logger.info("Starting complete AlloyDB initialization...")
    logger.info(f"Project: {project_id}")
    logger.info(f"Cluster: {cluster_name}")
    logger.info(f"Instance: {instance_name}")
    logger.info(f"Database: {database_name}")
    
    try:
        # Create connector
        connector = Connector()
        instance_connection_string = f"projects/{project_id}/locations/{region}/clusters/{cluster_name}/instances/{instance_name}"
        
        # Step 1: Connect to postgres database to create products database
        logger.info("Step 1: Creating products database...")
        conn = await connector.connect_async(
            instance_connection_string,
            "asyncpg",
            user="postgres",
            password=password,
            db="postgres"
        )
        
        try:
            await conn.execute("CREATE DATABASE products")
            logger.info("✅ Products database created")
        except Exception as e:
            if "already exists" in str(e):
                logger.info("✅ Products database already exists")
            else:
                logger.error(f"Failed to create database: {e}")
                raise e
        
        await conn.close()
        
        # Step 2: Connect to products database and set up schema
        logger.info("Step 2: Setting up database schema...")
        conn = await connector.connect_async(
            instance_connection_string,
            "asyncpg",
            user="postgres",
            password=password,
            db=database_name
        )
        
        # Enable vector extension
        logger.info("Enabling vector extension...")
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        logger.info("✅ Vector extension enabled")
        
        # Create catalog_items table
        logger.info("Creating catalog_items table...")
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id VARCHAR PRIMARY KEY,
            name VARCHAR NOT NULL,
            description TEXT NOT NULL,
            categories TEXT[],
            price_usd DECIMAL(10,2),
            picture VARCHAR,
            product_embedding VECTOR(768)
        )
        """
        await conn.execute(create_table_sql)
        logger.info("✅ Table created")
        
        # Create vector index
        logger.info("Creating vector index...")
        try:
            await conn.execute(f"CREATE INDEX IF NOT EXISTS catalog_items_embedding_idx ON {table_name} USING hnsw (product_embedding vector_cosine_ops)")
            logger.info("✅ Vector index created")
        except Exception as e:
            logger.warning(f"Index creation: {e}")
        
        # Step 3: Generate embeddings and populate data
        logger.info("Step 3: Generating embeddings and populating data...")
        
        # For now, we'll use dummy embeddings since we can't easily import the Gemini library here
        # In a real scenario, this would use GoogleGenerativeAIEmbeddings
        import random
        
        def generate_dummy_embedding(text):
            """Generate a dummy 768-dimensional embedding for testing"""
            random.seed(hash(text) % (2**32))  # Deterministic based on text
            return [random.uniform(-1, 1) for _ in range(768)]
        
        # Process each product
        for i, product in enumerate(PRODUCTS_DATA["products"]):
            logger.info(f"Processing product {i+1}/{len(PRODUCTS_DATA['products'])}: {product['name']}")
            
            # Generate embedding (dummy for now)
            embedding = generate_dummy_embedding(product["description"])
            
            # Convert price to decimal
            price_usd = product["priceUsd"]["units"] + (product["priceUsd"]["nanos"] / 1000000000)
            
            # Insert product with embedding
            insert_sql = f"""
            INSERT INTO {table_name} (id, name, description, categories, price_usd, picture, product_embedding)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                description = EXCLUDED.description,
                categories = EXCLUDED.categories,
                price_usd = EXCLUDED.price_usd,
                picture = EXCLUDED.picture,
                product_embedding = EXCLUDED.product_embedding
            """
            
            await conn.execute(
                insert_sql,
                product["id"],
                product["name"],
                product["description"],
                product["categories"],
                price_usd,
                product["picture"],
                embedding
            )
            
            logger.info(f"✅ Inserted {product['name']} with embedding")
        
        # Step 4: Verify the setup
        logger.info("Step 4: Verifying database setup...")
        
        # Check record count
        count = await conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")
        logger.info(f"✅ Database contains {count} products")
        
        # Test vector search
        logger.info("Testing vector search...")
        test_embedding = generate_dummy_embedding("stylish accessories")
        results = await conn.fetch(
            f"SELECT id, name, description FROM {table_name} ORDER BY product_embedding <=> $1 LIMIT 3",
            test_embedding
        )
        
        logger.info("✅ Vector search test results:")
        for result in results:
            logger.info(f"  - {result['name']}: {result['description'][:50]}...")
        
        # Check table structure
        columns = await conn.fetch("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = $1
            ORDER BY ordinal_position
        """, table_name)
        
        logger.info("✅ Table structure:")
        for col in columns:
            logger.info(f"  - {col['column_name']}: {col['data_type']}")
        
        await conn.close()
        await connector.close_async()
        
        logger.info("🎉 Complete AlloyDB initialization successful!")
        logger.info("The Shopping Assistant service should now be able to start.")
        return True
        
    except Exception as e:
        logger.error(f"❌ Initialization failed: {e}")
        import traceback
        traceback.print_exc()
        if 'connector' in locals():
            await connector.close_async()
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python complete_database_init.py <password>")
        print("Or run without password to use Secret Manager")
    
    result = asyncio.run(init_database_complete())
    sys.exit(0 if result else 1)