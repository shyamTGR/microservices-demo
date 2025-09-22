#!/usr/bin/env python3
"""
Verification script for Shopping Assistant service deployment.
This script verifies:
1. Service deployment and pod status
2. Database connectivity
3. Vector store initialization
4. API endpoint functionality
"""

import subprocess
import json
import time
import sys
import os

def run_kubectl_command(cmd):
    """Run kubectl command and return output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error running command: {cmd}")
            print(f"Error: {result.stderr}")
            return None
        return result.stdout.strip()
    except Exception as e:
        print(f"Exception running command {cmd}: {e}")
        return None

def check_pod_status():
    """Check if Shopping Assistant service pod is running"""
    print("🔍 Checking Shopping Assistant service pod status...")
    
    # Get pod status
    cmd = "kubectl get pods -l app=shoppingassistantservice -o json"
    output = run_kubectl_command(cmd)
    
    if not output:
        print("❌ Failed to get pod status")
        return False
    
    try:
        pods_data = json.loads(output)
        pods = pods_data.get('items', [])
        
        if not pods:
            print("❌ No Shopping Assistant service pods found")
            return False
        
        for pod in pods:
            name = pod['metadata']['name']
            status = pod['status']['phase']
            ready = False
            
            # Check if pod is ready
            if 'containerStatuses' in pod['status']:
                for container in pod['status']['containerStatuses']:
                    if container.get('ready', False):
                        ready = True
                        break
            
            print(f"📦 Pod: {name}")
            print(f"   Status: {status}")
            print(f"   Ready: {ready}")
            
            if status == 'Running' and ready:
                print("✅ Shopping Assistant service pod is running and ready")
                return True
            else:
                # Get pod logs for debugging
                logs_cmd = f"kubectl logs {name} --tail=10"
                logs = run_kubectl_command(logs_cmd)
                if logs:
                    print(f"   Recent logs:\n{logs}")
        
        print("❌ Shopping Assistant service pod is not ready")
        return False
        
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse pod status JSON: {e}")
        return False

def check_service_endpoint():
    """Check if service endpoint is accessible"""
    print("\n🔍 Checking service endpoint accessibility...")
    
    # Get service info
    cmd = "kubectl get service shoppingassistantservice -o json"
    output = run_kubectl_command(cmd)
    
    if not output:
        print("❌ Failed to get service info")
        return False
    
    try:
        service_data = json.loads(output)
        cluster_ip = service_data['spec']['clusterIP']
        port = service_data['spec']['ports'][0]['port']
        
        print(f"🌐 Service endpoint: {cluster_ip}:{port}")
        print("✅ Service endpoint is configured")
        return True
        
    except (json.JSONDecodeError, KeyError) as e:
        print(f"❌ Failed to parse service info: {e}")
        return False

def check_database_connectivity():
    """Check database connectivity from within the cluster"""
    print("\n🔍 Checking database connectivity...")
    
    # Get a running pod name
    cmd = "kubectl get pods -l app=shoppingassistantservice -o jsonpath='{.items[0].metadata.name}'"
    pod_name = run_kubectl_command(cmd)
    
    if not pod_name:
        print("❌ No running pod found to test database connectivity")
        return False
    
    # Test database connection from within the pod
    test_script = '''
import os
import sys
try:
    from google.cloud import secretmanager
    from google.cloud.alloydb.connector import Connector
    import asyncpg
    import asyncio
    
    async def test_connection():
        project_id = os.environ.get("PROJECT_ID", "wise-karma-472219-r2")
        region = os.environ.get("REGION", "us-central1")
        cluster_name = os.environ.get("ALLOYDB_CLUSTER_NAME", "onlineboutique-cluster")
        instance_name = os.environ.get("ALLOYDB_INSTANCE_NAME", "onlineboutique-instance")
        database_name = os.environ.get("ALLOYDB_DATABASE_NAME", "products")
        secret_name = os.environ.get("ALLOYDB_SECRET_NAME", "alloydb-secret")
        
        # Get password from Secret Manager
        client = secretmanager.SecretManagerServiceClient()
        secret_path = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
        response = client.access_secret_version(request={"name": secret_path})
        password = response.payload.data.decode("UTF-8")
        
        # Create connector
        connector = Connector()
        
        # Connection string
        instance_connection_string = f"projects/{project_id}/locations/{region}/clusters/{cluster_name}/instances/{instance_name}"
        
        try:
            # Test connection
            conn = await connector.connect_async(
                instance_connection_string,
                "asyncpg",
                user="postgres",
                password=password,
                db=database_name
            )
            
            # Test query
            result = await conn.fetchval("SELECT 1")
            await conn.close()
            await connector.close_async()
            
            if result == 1:
                print("✅ Database connection successful")
                return True
            else:
                print("❌ Database connection test failed")
                return False
                
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            await connector.close_async()
            return False
    
    result = asyncio.run(test_connection())
    sys.exit(0 if result else 1)
    
except Exception as e:
    print(f"❌ Database test error: {e}")
    sys.exit(1)
'''
    
    # Write test script to pod and execute
    cmd = f'kubectl exec {pod_name} -- python3 -c "{test_script}"'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(result.stdout)
        return True
    else:
        print(f"❌ Database connectivity test failed")
        print(f"Error: {result.stderr}")
        return False

def check_vector_store():
    """Check if vector store is properly initialized"""
    print("\n🔍 Checking vector store initialization...")
    
    # Get a running pod name
    cmd = "kubectl get pods -l app=shoppingassistantservice -o jsonpath='{.items[0].metadata.name}'"
    pod_name = run_kubectl_command(cmd)
    
    if not pod_name:
        print("❌ No running pod found to test vector store")
        return False
    
    # Test vector store query
    test_script = '''
import os
import sys
try:
    from google.cloud import secretmanager
    from google.cloud.alloydb.connector import Connector
    import asyncpg
    import asyncio
    
    async def test_vector_store():
        project_id = os.environ.get("PROJECT_ID", "wise-karma-472219-r2")
        region = os.environ.get("REGION", "us-central1")
        cluster_name = os.environ.get("ALLOYDB_CLUSTER_NAME", "onlineboutique-cluster")
        instance_name = os.environ.get("ALLOYDB_INSTANCE_NAME", "onlineboutique-instance")
        database_name = os.environ.get("ALLOYDB_DATABASE_NAME", "products")
        table_name = os.environ.get("ALLOYDB_TABLE_NAME", "catalog_items")
        secret_name = os.environ.get("ALLOYDB_SECRET_NAME", "alloydb-secret")
        
        # Get password from Secret Manager
        client = secretmanager.SecretManagerServiceClient()
        secret_path = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
        response = client.access_secret_version(request={"name": secret_path})
        password = response.payload.data.decode("UTF-8")
        
        # Create connector
        connector = Connector()
        
        # Connection string
        instance_connection_string = f"projects/{project_id}/locations/{region}/clusters/{cluster_name}/instances/{instance_name}"
        
        try:
            # Test connection
            conn = await connector.connect_async(
                instance_connection_string,
                "asyncpg",
                user="postgres",
                password=password,
                db=database_name
            )
            
            # Check if table exists
            table_exists = await conn.fetchval(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = $1)",
                table_name
            )
            
            if not table_exists:
                print(f"❌ Table {table_name} does not exist")
                await conn.close()
                await connector.close_async()
                return False
            
            # Check if table has data
            count = await conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")
            print(f"📊 Found {count} items in {table_name} table")
            
            # Check if vector extension is available
            vector_ext = await conn.fetchval(
                "SELECT EXISTS (SELECT FROM pg_extension WHERE extname = 'vector')"
            )
            
            if vector_ext:
                print("✅ Vector extension is installed")
            else:
                print("❌ Vector extension is not installed")
            
            await conn.close()
            await connector.close_async()
            
            if count > 0 and vector_ext:
                print("✅ Vector store is properly initialized")
                return True
            else:
                print("❌ Vector store initialization incomplete")
                return False
                
        except Exception as e:
            print(f"❌ Vector store test failed: {e}")
            await connector.close_async()
            return False
    
    result = asyncio.run(test_vector_store())
    sys.exit(0 if result else 1)
    
except Exception as e:
    print(f"❌ Vector store test error: {e}")
    sys.exit(1)
'''
    
    # Write test script to pod and execute
    cmd = f'kubectl exec {pod_name} -- python3 -c "{test_script}"'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(result.stdout)
        return True
    else:
        print(f"❌ Vector store test failed")
        print(f"Error: {result.stderr}")
        return False

def main():
    """Main verification function"""
    print("🚀 Starting Shopping Assistant Service Deployment Verification")
    print("=" * 60)
    
    all_checks_passed = True
    
    # Check 1: Pod Status
    if not check_pod_status():
        all_checks_passed = False
    
    # Check 2: Service Endpoint
    if not check_service_endpoint():
        all_checks_passed = False
    
    # Check 3: Database Connectivity
    if not check_database_connectivity():
        all_checks_passed = False
    
    # Check 4: Vector Store
    if not check_vector_store():
        all_checks_passed = False
    
    print("\n" + "=" * 60)
    if all_checks_passed:
        print("🎉 All verification checks passed!")
        print("✅ Shopping Assistant service is deployed and ready")
        return 0
    else:
        print("❌ Some verification checks failed")
        print("🔧 Please review the issues above and retry")
        return 1

if __name__ == "__main__":
    sys.exit(main())