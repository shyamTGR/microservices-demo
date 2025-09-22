@echo off
REM AlloyDB Setup Script for Windows
REM This script sets up the required databases for the Online Boutique Shopping Assistant

echo Setting up AlloyDB for Online Boutique Shopping Assistant...

REM Set default environment variables if not provided
if not defined PROJECT_ID set PROJECT_ID=wise-karma-472219-r2
if not defined REGION set REGION=us-central1
if not defined ALLOYDB_CLUSTER_NAME set ALLOYDB_CLUSTER_NAME=onlineboutique-cluster
if not defined ALLOYDB_INSTANCE_NAME set ALLOYDB_INSTANCE_NAME=onlineboutique-instance
if not defined ALLOYDB_SECRET_NAME set ALLOYDB_SECRET_NAME=alloydb-secret
if not defined ALLOYDB_PRIMARY_IP set ALLOYDB_PRIMARY_IP=10.36.0.2

echo Configuration:
echo   Project ID: %PROJECT_ID%
echo   Region: %REGION%
echo   Cluster: %ALLOYDB_CLUSTER_NAME%
echo   Instance: %ALLOYDB_INSTANCE_NAME%
echo   Primary IP: %ALLOYDB_PRIMARY_IP%
echo.

REM Check if we're running in the correct directory
if not exist "scripts\init_alloydb.py" (
    echo Error: Please run this script from the project root directory
    echo Usage: scripts\setup_alloydb.bat
    exit /b 1
)

REM Install Python dependencies
echo Installing Python dependencies...
pip install -r scripts\requirements.txt
if errorlevel 1 (
    echo Failed to install dependencies
    exit /b 1
)

REM Run the database initialization
echo Initializing AlloyDB databases...
python scripts\init_alloydb.py
if errorlevel 1 (
    echo Database initialization failed
    exit /b 1
)

echo.
echo AlloyDB setup completed successfully!
echo.
echo Next steps:
echo 1. Run: python scripts\populate_database.py
echo 2. Or run complete setup: python scripts\setup_complete_database.py
echo 3. Build and deploy the Shopping Assistant service