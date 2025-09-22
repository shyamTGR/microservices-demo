#!/bin/bash
# Script to run database setup on GCP VM
# This script should be copied to and run from the GCP VM

echo "Setting up AlloyDB from GCP VM..."

# Set environment variables
export PROJECT_ID="wise-karma-472219-r2"
export REGION="us-central1"
export ALLOYDB_CLUSTER_NAME="onlineboutique-cluster"
export ALLOYDB_INSTANCE_NAME="onlineboutique-instance"
export ALLOYDB_SECRET_NAME="alloydb-secret"
export ALLOYDB_PRIMARY_IP="10.36.0.2"
export GOOGLE_API_KEY="AIzaSyCjvgLUncC4iVQlff_CwUXmAihYDvqEW74"

echo "Environment variables set:"
echo "  PROJECT_ID: $PROJECT_ID"
echo "  ALLOYDB_PRIMARY_IP: $ALLOYDB_PRIMARY_IP"
echo ""

# Install Python dependencies
echo "Installing Python dependencies..."
pip3 install psycopg2-binary google-cloud-secret-manager langchain-google-genai

# Check if we can reach AlloyDB
echo "Testing AlloyDB connectivity..."
python3 -c "
import psycopg2
from google.cloud import secretmanager_v1
import os

try:
    # Get password from Secret Manager
    client = secretmanager_v1.SecretManagerServiceClient()
    secret_name = client.secret_version_path(
        project='$PROJECT_ID', 
        secret='$ALLOYDB_SECRET_NAME', 
        secret_version='latest'
    )
    request = secretmanager_v1.AccessSecretVersionRequest(name=secret_name)
    response = client.access_secret_version(request=request)
    password = response.payload.data.decode('UTF-8').strip()
    
    # Test connection
    conn = psycopg2.connect(
        host='$ALLOYDB_PRIMARY_IP',
        port=5432,
        user='postgres',
        password=password,
        connect_timeout=10
    )
    print('✓ AlloyDB connection successful')
    conn.close()
except Exception as e:
    print(f'✗ AlloyDB connection failed: {e}')
    exit(1)
"

if [ $? -eq 0 ]; then
    echo ""
    echo "Running database initialization..."
    python3 scripts/init_alloydb.py
    
    echo ""
    echo "Running database population..."
    python3 scripts/populate_database.py
    
    echo ""
    echo "Database setup completed!"
else
    echo "Connection test failed. Please check your AlloyDB configuration."
    exit 1
fi