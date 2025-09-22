#!/bin/bash
# Cloud Shell initialization script for AlloyDB and Shopping Assistant
# This script should be run from Google Cloud Shell

set -e

echo "🚀 Starting AlloyDB initialization from Cloud Shell..."

# Set project and region
PROJECT_ID="wise-karma-472219-r2"
REGION="us-central1"
CLUSTER_NAME="onlineboutique-cluster"
INSTANCE_NAME="onlineboutique-instance"

echo "📋 Configuration:"
echo "  Project: $PROJECT_ID"
echo "  Region: $REGION"
echo "  Cluster: $CLUSTER_NAME"
echo "  Instance: $INSTANCE_NAME"

# Set the project
gcloud config set project $PROJECT_ID

# Get the AlloyDB password
echo "🔐 Getting AlloyDB password from Secret Manager..."
DB_PASSWORD=$(gcloud secrets versions access latest --secret="alloydb-secret")
echo "✅ Password retrieved"

# Install required Python packages
echo "📦 Installing required Python packages..."
pip3 install --user google-cloud-secret-manager google-cloud-alloydb-connector[asyncpg] langchain-google-genai asyncpg psycopg[binary] langchain-google-alloydb-pg

# Create the initialization script
cat > /tmp/init_alloydb_complete.py << 'EOF'
#!/usr/bin/env python3
import os
import sys
import json
import asyncio
import logging
from google.cloud import secretmanager
from google.cloud.alloydb.connector import Connector
import asyncpg
from langchain_google_genai import GoogleGenerativeAIEmbeddings

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def init_database():
    """Initialize AlloyDB with products and embeddings"""
    
    # Configuration
    project_id = "wise-karma-472219-r2"
    region = "us-central1"
    cluster_name = "onlineboutique-cluster"
    instance_name = "onlineboutique-instance"
    database_name = "products"
    table_name = "catalog_items"
    
    # Get password
    password = sys.argv[1] if len(sys.argv) > 1 else None
    if not password:
        logger.error("Password required as first argument")
        return False
    
    logger.info("Starting AlloyDB initialization...")
    
    try:
        # Create connector
        connector = Connector()
        instance_connection_string = f"projects/{project_id}/locations/{region}/clusters/{cluster_name}/instances/{instance_name}"
        
        # Connect to postgres database first to create our database
        logger.info("Connecting to postgres database...")
        conn = await connector.connect_async(
            instance_connection_string,
            "asyncpg",
            user="postgres",
            password=password,
            db="postgres"
        )
        
        # Create products database if it doesn't exist
        logger.info("Creating products database...")
        try:
            await conn.execute("CREATE DATABASE products")
            logger.info("✅ Products database created")
        except Exception as e:
            if "already exists" in str(e):
                logger.info("✅ Products database already exists")
            else:
                raise e
        
        await conn.close()
        
        # Connect to products database
        logger.info("Connecting to products database...")
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
            logger.warning(f"Index creation warning: {e}")
        
        # Load products data
        products_data = {
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
        
        # Initialize embeddings
        logger.info("Initializing Gemini embeddings...")
        embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
        
        # Process each product
        logger.info("Processing products and generating embeddings...")
        for i, product in enumerate(products_data["products"]):
            logger.info(f"Processing product {i+1}/{len(products_data['products'])}: {product['name']}")
            
            # Generate embedding for product description
            embedding = await asyncio.to_thread(embeddings.embed_query, product["description"])
            
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
        
        # Verify data
        count = await conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")
        logger.info(f"✅ Database initialized with {count} products")
        
        # Test vector search
        logger.info("Testing vector search...")
        test_embedding = await asyncio.to_thread(embeddings.embed_query, "stylish accessories")
        results = await conn.fetch(
            f"SELECT id, name, description FROM {table_name} ORDER BY product_embedding <=> $1 LIMIT 3",
            test_embedding
        )
        
        logger.info("✅ Vector search test results:")
        for result in results:
            logger.info(f"  - {result['name']}: {result['description'][:50]}...")
        
        await conn.close()
        await connector.close_async()
        
        logger.info("🎉 AlloyDB initialization completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Initialization failed: {e}")
        if 'connector' in locals():
            await connector.close_async()
        return False

if __name__ == "__main__":
    result = asyncio.run(init_database())
    sys.exit(0 if result else 1)
EOF

# Run the initialization script
echo "🔄 Running database initialization..."
python3 /tmp/init_alloydb_complete.py "$DB_PASSWORD"

if [ $? -eq 0 ]; then
    echo "✅ Database initialization completed successfully!"
    
    # Test the Shopping Assistant service
    echo "🧪 Testing Shopping Assistant service restart..."
    kubectl delete pod -l app=shoppingassistantservice
    
    echo "⏳ Waiting for service to restart..."
    sleep 30
    
    kubectl get pods -l app=shoppingassistantservice
    
    echo "🎉 AlloyDB initialization complete!"
    echo "The Shopping Assistant service should now start successfully."
else
    echo "❌ Database initialization failed!"
    exit 1
fi