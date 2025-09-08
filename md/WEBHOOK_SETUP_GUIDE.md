# 🔗 StreamGank Webhook Configuration Guide

## 🔧 Environment Variable Setup

Add this to your `.env` file:

### **Local Development:**

```bash
WEBHOOK_CREATOMATE_URL=http://localhost:3000/api/webhooks/creatomate
```

### **Railway Production:**

```bash
WEBHOOK_CREATOMATE_URL=https://streamgank-app-production.up.railway.app/api/webhooks/creatomate
```

### **Other Production:**

```bash
WEBHOOK_CREATOMATE_URL=https://your-domain.com/api/webhooks/creatomate
```

## 🎬 Creatomate Dashboard Setup

1. **Go to Creatomate Dashboard**: https://creatomate.com/dashboard
2. **Select your StreamGank project**
3. **Go to Project Settings**
4. **Set "Webhook URL" to the value of your WEBHOOK_CREATOMATE_URL**:
    - **Local**: `http://localhost:3000/api/webhooks/creatomate`
    - **Railway**: `https://streamgank-app-production.up.railway.app/api/webhooks/creatomate`
      📝 **Tip**: Copy the exact URL from your `WEBHOOK_CREATOMATE_URL` environment variable

## 📊 Webhook Status Flow

The webhook will receive **ALL** Creatomate status updates according to their [official documentation](https://creatomate.com/docs/api/reference/what-is-a-render):

```
📋 planned → ⏳ waiting → 💬 transcribing → 🎬 rendering → ✅ succeeded/❌ failed
```

## 🧪 Testing Your Webhook

### **Node.js Test Script:**

```bash
# Local testing
WEBHOOK_CREATOMATE_URL=http://localhost:3000/api/webhooks/creatomate node test_webhook.js

# Railway testing
WEBHOOK_CREATOMATE_URL=https://streamgank-app-production.up.railway.app/api/webhooks/creatomate node test_webhook.js
```

### **Curl Test Script:**

```bash
# Local testing
WEBHOOK_CREATOMATE_URL=http://localhost:3000/api/webhooks/creatomate bash test-webhook-curl.sh

# Railway testing
WEBHOOK_CREATOMATE_URL=https://streamgank-app-production.up.railway.app/api/webhooks/creatomate bash test-webhook-curl.sh
```

## 📝 What the Webhook Handles

### **Status Updates:**

-   `planned` (85%) - "📋 Video queued for processing..."
-   `waiting` (87%) - "⏳ Video is being rendered..."
-   `transcribing` (88%) - "💬 Video is being rendered..."
-   `rendering` (90%) - "🎬 Video is being rendered..."
-   `succeeded` (100%) - Shows video player with Download/Copy URL/Fullscreen
-   `failed` - Shows error message

### **Persistent Job Logs:**

✅ **Success**: Video URL, completion time, progress  
❌ **Failure**: Error details, failure time, render ID

## 🔐 Token vs Webhook Security

### **Creatomate Tokens:**

-   **Public Token** (`public-5a5momxotwkguppxzpv99ifv`): Used for client-side API calls
-   **Private API Key**: Used for server-side API calls to Creatomate
-   **No webhook authentication**: Creatomate doesn't provide webhook signing

### **For Webhooks:**

❌ **Don't use**: Public token - not needed for webhook endpoints  
❌ **Don't use**: Private API key - webhooks come FROM Creatomate TO you  
✅ **Do use**: Payload validation + HTTPS for security

## 🛡️ Security Best Practices

### **Basic Security (Current):**

-   Validates render_id and status are present
-   Logs webhook source IP and User-Agent
-   Basic payload validation

### **Enhanced Security Notes:**

**Creatomate Limitation**: Creatomate doesn't currently support custom webhook signatures or secrets.

**Current Security Approach**:

-   Payload validation (render_id + status required)
-   IP address logging for monitoring
-   HTTPS for encrypted transport (production)
-   Server-level access control

## 🔐 Security Notes

-   **Local**: Use `http://localhost:3000` for development only
-   **Production**: Always use `https://` URLs for security
-   **Railway**: Automatically provides HTTPS
-   **Webhook Security**: Relies on payload validation + HTTPS encryption

## 🎯 Benefits

✅ **Instant Updates** - No polling delays  
✅ **Real-time UI** - Status updates in 1-2 seconds  
✅ **Production Ready** - Follows Creatomate best practices  
✅ **Environment Flexible** - Works in local/staging/production

---

_This setup follows the official [Creatomate webhook documentation](https://creatomate.com/docs/api/reference/set-up-a-webhook)_
