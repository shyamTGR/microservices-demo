#!/usr/bin/env python3
"""
Complete Database Setup Script

This script runs the complete database setup process:
1. Initialize AlloyDB databases and tables
2. Generate product embeddings
3. Populate the database with product data and embeddings

Usage:
    python setup_complete_database.py
"""

import os
import sys
import logging
import subprocess

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_environment():
    """Check that required environment variables are set."""
    required_vars = ['GOOGLE_API_KEY']
    missing_vars = []
    
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please set the following environment variables:")
        for var in missing_vars:
            logger.error(f"  export {var}=<your_value>")
        return False
    
    return True

def run_script(script_name: str, description: str) -> bool:
    """Run a Python script and return success status."""
    try:
        logger.info(f"Starting: {description}")
        logger.info(f"Running: python {script_name}")
        
        result = subprocess.run([
            sys.executable, script_name
        ], check=True, capture_output=True, text=True)
        
        logger.info(f"✓ Completed: {description}")
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"✗ Failed: {description}")
        logger.error(f"Exit code: {e.returncode}")
        if e.stdout:
            logger.error(f"STDOUT:\n{e.stdout}")
        if e.stderr:
            logger.error(f"STDERR:\n{e.stderr}")
        return False
    except Exception as e:
        logger.error(f"✗ Failed: {description} - {e}")
        return False

def main():
    """Main function to run complete database setup."""
    logger.info("Starting complete AlloyDB setup for Shopping Assistant...")
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    # Change to scripts directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    original_dir = os.getcwd()
    
    try:
        os.chdir(os.path.dirname(script_dir))  # Go to project root
        
        # Step 1: Initialize databases
        if not run_script("scripts/init_alloydb.py", "Database initialization"):
            logger.error("Database initialization failed. Stopping.")
            sys.exit(1)
        
        # Step 2: Generate embeddings and populate database
        if not run_script("scripts/populate_database.py", "Embedding generation and database population"):
            logger.error("Database population failed. Stopping.")
            sys.exit(1)
        
        logger.info("")
        logger.info("🎉 Complete database setup finished successfully!")
        logger.info("")
        logger.info("Summary:")
        logger.info("✓ AlloyDB databases created (products, carts)")
        logger.info("✓ Database tables created with vector extensions")
        logger.info("✓ Product embeddings generated using Gemini")
        logger.info("✓ Database populated with product data and embeddings")
        logger.info("✓ Vector similarity search tested and working")
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. Build Shopping Assistant service: skaffold build")
        logger.info("2. Deploy the service to Kubernetes")
        logger.info("3. Test the Shopping Assistant API")
        
    finally:
        os.chdir(original_dir)

if __name__ == "__main__":
    main()