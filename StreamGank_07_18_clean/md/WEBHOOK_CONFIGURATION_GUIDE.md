# 🔗 StreamGank Webhook Configuration Guide

## 📋 **Overview**

StreamGank includes a **professional webhook system** for external service integrations. Your system now supports:

-   ✅ **Real-time job notifications** to external services
-   ✅ **HMAC security** with signature verification
-   ✅ **Automatic retries** with exponential backoff
-   ✅ **Rate limiting** and error tracking
-   ✅ **Professional API endpoints** for testing and management

---

## 🔧 **Environment Configuration**

### **Basic Webhook Setup**

```bash
# Comma-separated list of webhook URLs
WEBHOOK_URLS=https://your-app.com/webhooks/streamgank,https://hooks.slack.com/services/your/webhook

# Events to send (comma-separated)
WEBHOOK_EVENTS=job.completed,job.failed,job.cancelled

# Security settings
WEBHOOK_SECRET_KEY=your-secure-webhook-secret-key-here
WEBHOOK_TIMEOUT=10000                    # 10 seconds
WEBHOOK_MAX_RETRIES=3                    # Retry failed webhooks

# Custom headers (optional)
WEBHOOK_HEADERS=Authorization:Bearer your-token,X-Custom-Header:your-value
```

### **Advanced Configuration**

```bash
# Rate limiting (per webhook endpoint)
WEBHOOK_RATE_LIMIT_WINDOW=60000          # 1 minute window
WEBHOOK_RATE_LIMIT_MAX=100               # Max requests per window
WEBHOOK_RETRY_DELAY=1000                 # Base retry delay (1 second)
WEBHOOK_MAX_RETRY_DELAY=30000            # Maximum retry delay (30 seconds)
```

---

## 📨 **Available Webhook Events**

| Event                       | Description                 | Trigger                      |
| --------------------------- | --------------------------- | ---------------------------- |
| `job.completed`             | Job finished with video URL | Video successfully generated |
| `job.failed`                | Job permanently failed      | Exceeded max retries         |
| `job.cancelled`             | Job manually cancelled      | User cancellation            |
| `job.extraction_completed`  | Movie extraction done       | Pause-after-extraction jobs  |
| `job.script_completed`      | Python script finished      | Video still rendering        |
| `job.completed_with_issues` | Completed with problems     | Missing video URL/ID         |
| `job.failed_no_retry`       | Failed without retry        | Configuration errors         |
| `job.timeout`               | Job timed out               | 30-minute processing limit   |

---

## 📄 **Webhook Payload Structure**

### **Standard Payload**

```json
{
    "event": "job.completed",
    "data": {
        "job_id": "job_1704123456789_abc123",
        "status": "completed",
        "created_at": "2024-01-01T12:00:00.000Z",
        "started_at": "2024-01-01T12:00:05.000Z",
        "completed_at": "2024-01-01T12:05:30.000Z",
        "failed_at": null,
        "parameters": {
            "country": "us",
            "platform": "netflix",
            "genre": "action",
            "contentType": "movies",
            "template": "auto"
        },
        "progress": 100,
        "current_step": "Video generation completed!",
        "video_url": "https://cdn.creatomate.com/renders/abc123-video.mp4",
        "creatomate_id": "abc123-render-id",
        "error": null,
        "retry_count": 0,
        "processing_duration_ms": 330000
    },
    "timestamp": "2024-01-01T12:05:30.123Z",
    "webhook_id": "webhook_1",
    "source": "streamgank"
}
```

### **Security Headers**

```http
Content-Type: application/json
User-Agent: StreamGank-Webhook/1.0
X-StreamGank-Signature: sha256=abc123def456...
X-StreamGank-Event: job.completed
X-StreamGank-Delivery: 550e8400-e29b-41d4-a716-446655440000
Authorization: Bearer your-custom-token  # If configured
```

---

## 🛡️ **Security Implementation**

### **HMAC Signature Verification**

**Node.js Example:**

```javascript
const crypto = require("crypto");

function verifyWebhookSignature(payload, signature, secret) {
    const expectedSignature = crypto.createHmac("sha256", secret).update(JSON.stringify(payload)).digest("hex");

    const providedSignature = signature.replace("sha256=", "");

    return crypto.timingSafeEqual(Buffer.from(expectedSignature, "hex"), Buffer.from(providedSignature, "hex"));
}

// Usage in your webhook endpoint
app.post("/webhook/streamgank", (req, res) => {
    const signature = req.headers["x-streamgank-signature"];
    const secret = process.env.STREAMGANK_WEBHOOK_SECRET;

    if (!verifyWebhookSignature(req.body, signature, secret)) {
        return res.status(401).send("Invalid signature");
    }

    // Process webhook safely
    console.log("Job update:", req.body.data);
    res.status(200).send("OK");
});
```

**Python Example:**

```python
import hmac
import hashlib
import json

def verify_webhook_signature(payload: dict, signature: str, secret: str) -> bool:
    payload_string = json.dumps(payload, separators=(',', ':'))
    expected_signature = hmac.new(
        secret.encode('utf-8'),
        payload_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    provided_signature = signature.replace('sha256=', '')
    return hmac.compare_digest(expected_signature, provided_signature)

# Flask example
@app.route('/webhook/streamgank', methods=['POST'])
def handle_streamgank_webhook():
    signature = request.headers.get('X-StreamGank-Signature')
    secret = os.environ['STREAMGANK_WEBHOOK_SECRET']

    if not verify_webhook_signature(request.json, signature, secret):
        return 'Invalid signature', 401

    # Process webhook safely
    job_data = request.json['data']
    print(f"Job {job_data['job_id']} status: {job_data['status']}")
    return 'OK', 200
```

---

## 🔍 **Testing Your Webhooks**

### **Manual Testing via API**

```bash
# Test webhook endpoint connectivity
curl -X POST "http://localhost:3000/api/webhooks/test" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://your-app.com/webhooks/streamgank"}'

# Manual webhook trigger
curl -X POST "http://localhost:3000/api/webhooks/trigger" \
     -H "Content-Type: application/json" \
     -d '{
       "event": "job.completed",
       "data": {
         "job_id": "test_job_123",
         "status": "completed",
         "video_url": "https://example.com/test-video.mp4"
       }
     }'

# Get webhook system status
curl "http://localhost:3000/api/webhooks/status"
```

### **Response Examples**

**Successful Test:**

```json
{
    "success": true,
    "test_result": {
        "success": true,
        "status": 200,
        "duration": 156,
        "url": "https://your-app.com/webhooks/streamgank",
        "message": "Webhook endpoint is reachable"
    }
}
```

**Failed Test:**

```json
{
    "success": true,
    "test_result": {
        "success": false,
        "status": 0,
        "duration": 0,
        "url": "https://invalid-url.com/webhook",
        "message": "getaddrinfo ENOTFOUND invalid-url.com",
        "error": "ENOTFOUND"
    }
}
```

---

## 🎯 **Integration Examples**

### **Slack Integration**

```bash
# Environment setup
WEBHOOK_URLS=https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX
WEBHOOK_EVENTS=job.completed,job.failed

# Your Slack channel will receive:
# ✅ StreamGank Job Completed
# Job ID: job_1704123456789_abc123
# Video: https://cdn.creatomate.com/video.mp4
# Duration: 5m 30s
```

### **Discord Integration**

```bash
# Environment setup
WEBHOOK_URLS=https://discord.com/api/webhooks/123456789/your-webhook-token
WEBHOOK_EVENTS=job.completed,job.failed,job.cancelled

# Discord embed will show job status with rich formatting
```

### **Custom Application Integration**

```javascript
// Your webhook endpoint
app.post("/webhooks/streamgank", (req, res) => {
    const { event, data } = req.body;

    switch (event) {
        case "job.completed":
            // Send email notification
            sendEmailNotification(data.video_url);
            // Update database
            updateJobStatus(data.job_id, "completed");
            break;

        case "job.failed":
            // Alert monitoring system
            alertMonitoringSystem(data.error);
            break;

        case "job.cancelled":
            // Clean up resources
            cleanupJobResources(data.job_id);
            break;
    }

    res.status(200).send("OK");
});
```

---

## 📊 **Monitoring & Troubleshooting**

### **Server Logs to Monitor**

```bash
# Webhook system initialization
"🔗 Webhook Manager initialized with 2 configured endpoints"
"🔗 Webhook manager integrated with queue processing"

# Successful webhook deliveries
"✅ Webhook delivered successfully: webhook_1 (156ms, status: 200)"
"🔗 Sending webhook notifications for event: job.completed to 2 endpoints"

# Failed webhook deliveries
"⚠️ Webhook delivery failed (attempt 1/4): webhook_1 - timeout of 10000ms exceeded. Retrying in 1000ms..."
"❌ Webhook delivery failed after 4 attempts: ECONNREFUSED"

# Rate limiting
"⚠️ Rate limit exceeded for webhook webhook_1: 101/100"
```

### **Common Issues & Solutions**

| Issue                 | Cause                   | Solution                          |
| --------------------- | ----------------------- | --------------------------------- |
| `ECONNREFUSED`        | Webhook URL unreachable | Check URL and firewall settings   |
| `Invalid signature`   | Secret key mismatch     | Verify `WEBHOOK_SECRET_KEY`       |
| `Rate limit exceeded` | Too many requests       | Increase `WEBHOOK_RATE_LIMIT_MAX` |
| `timeout exceeded`    | Slow webhook endpoint   | Increase `WEBHOOK_TIMEOUT`        |

---

## ✅ **Best Practices**

### **Webhook Endpoint Design**

-   ✅ **Respond quickly** (< 5 seconds) to avoid timeouts
-   ✅ **Return 200 status** for successful processing
-   ✅ **Verify signatures** for security
-   ✅ **Handle retries** gracefully (check delivery ID)
-   ✅ **Log webhook data** for debugging

### **Security**

-   ✅ **Use HTTPS** for webhook URLs in production
-   ✅ **Validate signatures** on every request
-   ✅ **Keep secret keys** secure and rotate regularly
-   ✅ **Implement rate limiting** on your webhook endpoints
-   ✅ **Sanitize webhook data** before processing

### **Error Handling**

-   ✅ **Return 200** even for minor processing errors
-   ✅ **Return 400/500** only for malformed requests
-   ✅ **Implement idempotency** using delivery IDs
-   ✅ **Queue failed processing** for retry
-   ✅ **Monitor webhook failures** and alert

---

Your StreamGank webhook system is now **production-ready** with enterprise-level security, reliability, and monitoring! 🚀
