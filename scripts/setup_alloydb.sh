#!/bin/bash
# AlloyDB Setup Script
# This script sets up the required databases for the Online Boutique Shopping Assistant

set -e

echo "Setting up AlloyDB for Online Boutique Shopping Assistant..."

# Set default environment variables if not provided
export PROJECT_ID=${PROJECT_ID:-"wise-karma-472219-r2"}
export REGION=${REGION:-"us-central1"}
export ALLOYDB_CLUSTER_NAME=${ALLOYDB_CLUSTER_NAME:-"onlineboutique-cluster"}
export ALLOYDB_INSTANCE_NAME=${ALLOYDB_INSTANCE_NAME:-"onlineboutique-instance"}
export ALLOYDB_SECRET_NAME=${ALLOYDB_SECRET_NAME:-"alloydb-secret"}
export ALLOYDB_PRIMARY_IP=${ALLOYDB_PRIMARY_IP:-"10.36.0.2"}

echo "Configuration:"
echo "  Project ID: $PROJECT_ID"
echo "  Region: $REGION"
echo "  Cluster: $ALLOYDB_CLUSTER_NAME"
echo "  Instance: $ALLOYDB_INSTANCE_NAME"
echo "  Primary IP: $ALLOYDB_PRIMARY_IP"
echo ""

# Check if we're running in the correct directory
if [ ! -f "scripts/init_alloydb.py" ]; then
    echo "Error: Please run this script from the project root directory"
    echo "Usage: ./scripts/setup_alloydb.sh"
    exit 1
fi

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r scripts/requirements.txt

# Run the database initialization
echo "Initializing AlloyDB databases..."
python scripts/init_alloydb.py

echo ""
echo "AlloyDB setup completed successfully!"
echo ""
echo "Next steps:"
echo "1. Run: python scripts/generate_embeddings.py"
echo "2. Build and deploy the Shopping Assistant service"