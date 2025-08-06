# APP_ENV Configuration Guide

## 🌍 **Environment Variable: APP_ENV**

The `APP_ENV` environment variable controls the behavior of the test data caching system and other environment-specific features.

## 📋 **Supported Values**

| Value     | Description         | Cache Behavior  | Use Case                        |
| --------- | ------------------- | --------------- | ------------------------------- |
| `local`   | Local development   | ✅ **ENABLED**  | Development, testing, debugging |
| `prod`    | Production          | ❌ **DISABLED** | Live production deployment      |
| `staging` | Staging environment | ✅ **ENABLED**  | Pre-production testing          |
| `test`    | Testing environment | ✅ **ENABLED**  | Automated testing               |

## 🔧 **How to Set APP_ENV**

### **Method 1: Environment Variable**

```bash
# Linux/Mac
export APP_ENV=local

# Windows
set APP_ENV=local
```

### **Method 2: .env File**

Create a `.env` file in the project root:

```env
APP_ENV=local
```

### **Method 3: Command Line**

```bash
APP_ENV=local python main.py --country US --genre Horror
```

## 🚀 **Behavior by Environment**

### **APP_ENV=local (Default)**

```
🌍 Environment: APP_ENV='local' (Cache: ENABLED)
📂 Using cached script data from test_output...
📋 Loaded 3 cached scripts
📂 Using cached asset data from test_output...
📋 Loaded 3 cached posters and 3 cached clips
```

**Benefits:**

-   ⚡ **99% faster** subsequent runs
-   💰 **Reduced API costs** (no repeated OpenAI/Cloudinary calls)
-   🔒 **Consistent data** for testing and debugging

### **APP_ENV=prod**

```
🌍 Environment: APP_ENV='prod' (Cache: DISABLED)
🚫 Cache disabled for APP_ENV='prod' - will generate fresh data
🔄 No cached data found, generating new scripts...
🔄 No cached assets found, generating new assets...
```

**Benefits:**

-   🆕 **Always fresh data** for production
-   🎯 **No stale cache issues**
-   📊 **Real-time data generation**

## 💡 **Usage Examples**

### **Development Workflow**

```bash
# Set environment for development (enables caching)
export APP_ENV=local

# Run workflow - will use cached data if available
python main.py --country US --genre Horror --platform Netflix

# First run: generates and caches data
# Second run: uses cached data (99% faster)
```

### **Production Deployment**

```bash
# Set environment for production (disables caching)
export APP_ENV=prod

# Run workflow - always generates fresh data
python main.py --country US --genre Horror --platform Netflix

# Every run: generates fresh data
```

### **Clear Cache and Force Fresh Data**

```bash
# Method 1: Clear cache files
python -c "from utils.test_data_cache import clear_test_data; clear_test_data()"

# Method 2: Temporarily use prod environment
APP_ENV=prod python main.py --country US --genre Horror
```

## 🔍 **Checking Current Environment**

```python
from utils.test_data_cache import get_app_env, should_use_cache

print(f"Current environment: {get_app_env()}")
print(f"Cache enabled: {should_use_cache()}")
```

## 📊 **Cache File Structure**

When `APP_ENV=local`, cache files are saved to:

```
test_output/
├── script_result_us_horror_netflix.json
├── assets_us_horror_netflix.json
├── script_result_canada_comedy_disney.json
└── assets_canada_comedy_disney.json
```

Each file includes metadata:

```json
{
    "data": {
        /* cached data */
    },
    "metadata": {
        "data_type": "script_result",
        "parameters": { "country": "US", "genre": "Horror", "platform": "Netflix" },
        "saved_timestamp": 1704649200,
        "saved_datetime": "2024-01-07 15:30:00"
    }
}
```

## ⚙️ **Advanced Configuration**

### **Custom Environment Logic**

You can extend the caching logic for custom environments:

```python
# In utils/test_data_cache.py
def should_use_cache() -> bool:
    app_env = get_app_env()

    if app_env == 'local':
        return True
    elif app_env == 'prod':
        return False
    elif app_env == 'staging':
        return True  # Enable cache for staging
    elif app_env == 'ci':
        return False  # Disable cache for CI/CD
    else:
        return True  # Default to cache enabled
```

### **Environment-Specific Settings**

```python
# Load different settings based on environment
if get_app_env() == 'prod':
    # Use production settings
    max_retries = 5
    timeout = 60
else:
    # Use development settings
    max_retries = 3
    timeout = 30
```

## 🎯 **Best Practices**

1. **Development**: Always use `APP_ENV=local` for faster iteration
2. **Production**: Always use `APP_ENV=prod` for fresh data
3. **CI/CD**: Use `APP_ENV=prod` or custom environment
4. **Testing**: Use `APP_ENV=test` with controlled cache behavior
5. **Staging**: Use `APP_ENV=staging` to test with cached data

## 🚨 **Important Notes**

-   **Default Value**: If `APP_ENV` is not set, it defaults to `'local'`
-   **Case Insensitive**: `APP_ENV=LOCAL` is the same as `APP_ENV=local`
-   **Cache Location**: All cache files are stored in `test_output/` directory
-   **Memory**: Cache files can grow large - monitor disk usage in production

---

**Set your `APP_ENV` appropriately for your use case! 🌍**
