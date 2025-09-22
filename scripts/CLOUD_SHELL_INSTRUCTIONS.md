# AlloyDB Database Initialization via Cloud Shell

## Overview
Since the AlloyDB connector library has issues connecting from within GKE pods, we'll initialize the database directly from Cloud Shell where AlloyDB is accessible.

## Steps

### 1. Open Cloud Shell
Go to [Google Cloud Console](https://console.cloud.google.com) and open Cloud Shell.

### 2. Set up the environment
```bash
# Set project
gcloud config set project wise-karma-472219-r2

# Install required Python packages
pip3 install --user psycopg2-binary requests google-cloud-secret-manager
```

### 3. Upload the initialization script
Copy the contents of `scripts/cloud_shell_direct_init.py` and create it in Cloud Shell:

```bash
cat > init_alloydb.py << 'EOF'
[PASTE THE SCRIPT CONTENTS HERE]
EOF
```

### 4. Run the initialization
```bash
python3 init_alloydb.py
```

The script will:
1. Connect to AlloyDB at `10.36.0.2`
2. Get the password from Secret Manager (or prompt for it)
3. Create the `products` database if needed
4. Create the `catalog_items` table with vector extension
5. Generate embeddings for all products using Gemini API
6. Insert products with embeddings into the database
7. Test vector search functionality

### 5. Verify the initialization
After successful completion, you should see:
- ✅ Successfully inserted 9 products
- ✅ Vector search test results showing similar products

## Expected Output
```
INFO:__main__:Starting AlloyDB initialization...
INFO:__main__:Connecting to AlloyDB at 10.36.0.2...
INFO:__main__:Database products already exists
INFO:__main__:Enabling vector extension...
INFO:__main__:Creating catalog_items table...
INFO:__main__:Creating vector similarity index...
INFO:__main__:Generating embeddings for 9 texts...
INFO:__main__:Generated embedding 1/9
...
INFO:__main__:Generated embedding 9/9
INFO:__main__:Inserting products with embeddings...
INFO:__main__:✅ Successfully inserted 9 products
INFO:__main__:Testing vector search...
INFO:__main__:Generating embeddings for 1 texts...
INFO:__main__:Generated embedding 1/1
INFO:__main__:✅ Vector search test results:
INFO:__main__:  - Sunglasses: Add a modern touch to your outfits with these sle... (distance: 0.2345)
INFO:__main__:  - Watch: This gold-tone stainless steel watch will work with... (distance: 0.3456)
INFO:__main__:  - Loafers: A neat addition to your summer wardrobe... (distance: 0.4567)
INFO:__main__:🎉 Database initialization completed successfully!
INFO:__main__:SUCCESS: AlloyDB initialization complete
```

## Troubleshooting

### Connection Issues
If you get connection errors:
1. Verify AlloyDB instance is running: `gcloud alloydb instances describe onlineboutique-instance --cluster=onlineboutique-cluster --region=us-central1`
2. Check the IP address matches: `10.36.0.2`
3. Ensure you're in the correct project: `gcloud config get-value project`

### Permission Issues
If you get permission errors:
1. Ensure you have AlloyDB Client role
2. Verify Secret Manager access
3. Check Gemini API key is valid

### API Quota Issues
If you hit Gemini API limits:
1. The script processes embeddings one by one to avoid rate limits
2. Wait a few minutes and retry if needed
3. Check your API quota in the console

## Next Steps
After successful database initialization:
1. The Shopping Assistant service should be able to connect to AlloyDB
2. Test the service deployment
3. Verify frontend integration