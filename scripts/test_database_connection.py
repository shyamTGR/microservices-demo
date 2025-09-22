#!/usr/bin/env python3
"""
Test database connectivity from within the Shopping Assistant service pod.
"""

import os
import sys
import asyncio
from google.cloud import secretmanager
from google.cloud.alloydb.connector import Connector
import asyncpg

async def test_database_connection():
    """Test database connection and basic operations"""
    
    # Get environment variables
    project_id = os.environ.get("PROJECT_ID", "wise-karma-472219-r2")
    region = os.environ.get("REGION", "us-central1")
    cluster_name = os.environ.get("ALLOYDB_CLUSTER_NAME", "onlineboutique-cluster")
    instance_name = os.environ.get("ALLOYDB_INSTANCE_NAME", "onlineboutique-instance")
    database_name = os.environ.get("ALLOYDB_DATABASE_NAME", "products")
    table_name = os.environ.get("ALLOYDB_TABLE_NAME", "catalog_items")
    secret_name = os.environ.get("ALLOYDB_SECRET_NAME", "alloydb-secret")
    
    print(f"Testing connection to AlloyDB:")
    print(f"  Project: {project_id}")
    print(f"  Region: {region}")
    print(f"  Cluster: {cluster_name}")
    print(f"  Instance: {instance_name}")
    print(f"  Database: {database_name}")
    print(f"  Table: {table_name}")
    
    try:
        # Get password from Secret Manager
        print("Getting password from Secret Manager...")
        client = secretmanager.SecretManagerServiceClient()
        secret_path = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
        response = client.access_secret_version(request={"name": secret_path})
        password = response.payload.data.decode("UTF-8")
        print("✅ Successfully retrieved password from Secret Manager")
        
        # Create connector
        print("Creating AlloyDB connector...")
        connector = Connector()
        
        # Connection string
        instance_connection_string = f"projects/{project_id}/locations/{region}/clusters/{cluster_name}/instances/{instance_name}"
        print(f"Connection string: {instance_connection_string}")
        
        # Test connection
        print("Testing database connection...")
        conn = await connector.connect_async(
            instance_connection_string,
            "asyncpg",
            user="postgres",
            password=password,
            db=database_name
        )
        print("✅ Successfully connected to AlloyDB")
        
        # Test basic query
        print("Testing basic query...")
        result = await conn.fetchval("SELECT 1")
        if result == 1:
            print("✅ Basic query successful")
        
        # Check if table exists
        print(f"Checking if table '{table_name}' exists...")
        table_exists = await conn.fetchval(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = $1)",
            table_name
        )
        
        if table_exists:
            print(f"✅ Table '{table_name}' exists")
            
            # Check table contents
            count = await conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")
            print(f"📊 Table '{table_name}' contains {count} rows")
            
            if count > 0:
                # Show sample data
                sample = await conn.fetchrow(f"SELECT id, name FROM {table_name} LIMIT 1")
                print(f"📝 Sample row: {dict(sample)}")
        else:
            print(f"❌ Table '{table_name}' does not exist")
        
        # Check vector extension
        print("Checking vector extension...")
        vector_ext = await conn.fetchval(
            "SELECT EXISTS (SELECT FROM pg_extension WHERE extname = 'vector')"
        )
        
        if vector_ext:
            print("✅ Vector extension is installed")
        else:
            print("❌ Vector extension is not installed")
        
        # Close connection
        await conn.close()
        await connector.close_async()
        
        print("\n🎉 Database connectivity test completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Database connectivity test failed: {e}")
        if 'connector' in locals():
            await connector.close_async()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_database_connection())
    sys.exit(0 if result else 1)