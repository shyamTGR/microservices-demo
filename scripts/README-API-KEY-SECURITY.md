# API Key Security Notice

## Issue
Several files in this project contained hardcoded Gemini API keys that were exposed in the repository. These files have been removed from git tracking and added to .gitignore.

## Affected Files
- `scripts/verify_database_init.py`
- `scripts/verify-db-job.yaml`
- `scripts/simple-init-job.yaml`
- `scripts/cloud_shell_direct_init.py`
- `scripts/database-init-job.yaml`
- `scripts/direct-psycopg2-init-job.yaml`
- `scripts/fixed-alloydb-init-job.yaml`
- `scripts/run_on_vm.sh`
- `kustomize/components/shopping-assistant/shoppingassistantservice.yaml`

## Security Best Practices

### Instead of hardcoding API keys:
```python
GOOGLE_API_KEY = "AIzaSyCjvgLUncC4iVQlff_CwUXmAihYDvqEW74"  # ❌ NEVER DO THIS
```

### Use environment variables:
```python
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")  # ✅ SECURE
```

### Or use Google Cloud Secret Manager:
```python
def get_api_key():
    client = secretmanager_v1.SecretManagerServiceClient()
    secret_name = client.secret_version_path(
        project=PROJECT_ID, 
        secret="gemini-api-key", 
        secret_version="latest"
    )
    request = secretmanager_v1.AccessSecretVersionRequest(name=secret_name)
    response = client.access_secret_version(request=request)
    return response.payload.data.decode("UTF-8").strip()
```

### For Kubernetes manifests:
```yaml
env:
- name: GOOGLE_API_KEY
  valueFrom:
    secretKeyRef:
      name: gemini-api-secret
      key: api-key
```

## Next Steps
1. **Revoke the exposed API key** in Google Cloud Console
2. **Generate a new API key**
3. **Store it securely** using Secret Manager or environment variables
4. **Update the affected files** to use secure methods
5. **Test the updated configuration**

## Prevention
The .gitignore file has been updated with patterns to prevent similar issues:
- Files with exposed keys are explicitly ignored
- Patterns for common secret file names are added
- Environment files (.env) are ignored by default