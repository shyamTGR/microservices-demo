@echo off
echo Setting up AlloyDB from GCP VM...
echo.

echo Step 1: Copying files to GCP VM...
echo Running: gcloud compute scp --recurse scripts gce-linux:~/ --zone=us-central1-a

gcloud compute scp --recurse scripts gce-linux:~/ --zone=us-central1-a
if errorlevel 1 (
    echo Failed to copy files to VM
    pause
    exit /b 1
)

echo.
echo Step 2: Copying products.json to VM...
gcloud compute scp src/productcatalogservice/products.json gce-linux:~/scripts/ --zone=us-central1-a
if errorlevel 1 (
    echo Failed to copy products.json to VM
    pause
    exit /b 1
)

echo.
echo Step 3: Running database setup on VM...
echo This will SSH into the VM and run the database setup script...
echo.

gcloud compute ssh gce-linux --zone=us-central1-a --command="chmod +x ~/scripts/run_on_vm.sh && ~/scripts/run_on_vm.sh"

echo.
echo Database setup completed!
echo.
pause