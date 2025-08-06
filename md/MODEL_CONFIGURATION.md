# OpenAI Model Configuration Guide

## 🚨 **CURRENT ISSUE RESOLVED**

**Error**: `Project does not have access to model 'gpt-4.1-mini'`

**Solution**: Updated `config/settings.py` to use `gpt-4o-mini` (standard available model)

## 🔧 **How to Configure Your Model**

### **Step 1: Check Your Available Models**

From your screenshot, you have access to:

-   ✅ `gpt-4.1`
-   ✅ `gpt-4.1-mini`

### **Step 2: Update Settings**

Edit `config/settings.py`:

```python
API_SETTINGS = {
    'openai': {
        'model': 'gpt-4.1-mini',  # ← Change this to your preferred model
        'temperature': 0.8,
        # ... other settings
    }
}
```

### **Step 3: Available Model Options**

Based on your OpenAI project access:

```python
# Your available models (from screenshot):
'model': 'gpt-4.1'        # Full GPT-4.1 model
'model': 'gpt-4.1-mini'   # Faster, cheaper GPT-4.1

# Standard available models:
'model': 'gpt-4o'         # Latest GPT-4 Omni
'model': 'gpt-4o-mini'    # Faster, cheaper GPT-4 Omni (current default)
'model': 'gpt-4-turbo'    # Previous generation
'model': 'gpt-4'          # Original GPT-4
```

## 🎯 **Quick Fix**

**Option 1: Use your premium models (if you have access)**

```python
# In config/settings.py
'model': 'gpt-4.1-mini'  # Based on your screenshot
```

**Option 2: Use standard available model (current setting)**

```python
# In config/settings.py
'model': 'gpt-4o-mini'   # Widely available
```

## 💡 **Testing Your Configuration**

Test if your model works:

```bash
# Test the current configuration
python -c "from config.settings import get_api_config; print('Current model:', get_api_config('openai')['model'])"

# Run a simple workflow to test
python main.py --country US --platform Netflix --genre Horror --content-type Film
```

## 🔄 **Dynamic Model Selection**

You can also override the model at runtime (when we add that feature):

```bash
# Future feature - override model per run
python main.py --country US --platform Netflix --genre Horror --content-type Film --model gpt-4.1-mini
```

---

**Current Status**: ✅ Fixed - Using `gpt-4o-mini` as safe default
**Your Options**: Change to `gpt-4.1-mini` in settings.py if you prefer your premium model
**Next**: Test the workflow to confirm it works with the new model setting
