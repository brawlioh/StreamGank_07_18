# 🔗 Creatomate Webhook Setup Guide

## Overview

StreamGank now uses **webhooks instead of polling** for Creatomate video render completion notifications. This provides:

-   ✅ **Instant notifications** when videos are ready
-   ✅ **Zero API spam** - no more polling requests
-   ✅ **Better reliability** - webhook + backup polling system
-   ✅ **Real-time UI updates** via Server-Sent Events

## Configuration

### 1. Environment Variables

Add to your `.env` or environment:

```bash
# Webhook base URL (replace with your actual domain)
WEBHOOK_BASE_URL=https://your-domain.com

# For development (Docker/localhost)
WEBHOOK_BASE_URL=http://localhost:3000

# For production deployment
WEBHOOK_BASE_URL=https://your-streamgank-app.com
```

### 2. Webhook Endpoint

The system automatically configures the webhook URL as:

```
{WEBHOOK_BASE_URL}/api/webhooks/creatomate-completion
```

### 3. How It Works

#### Workflow Process:

1. **Python workflow** completes and submits video to Creatomate with webhook URL
2. **Job status** changes from `processing` → `rendering`
3. **Creatomate renders** video and sends webhook when complete
4. **Webhook endpoint** receives notification and updates job to `completed`
5. **Real-time UI** updates instantly via Server-Sent Events
6. **Backup polling** runs occasionally as failsafe (every 5-10 minutes)

#### Webhook Payload (from Creatomate):

```json
{
    "id": "render_id_here",
    "status": "completed",
    "url": "https://creatomate-video-url.mp4",
    "error": null
}
```

## Testing

### Test Webhook Endpoint

```bash
# Test that webhook endpoint is working
curl -X POST http://localhost:3000/api/webhooks/creatomate-completion \
  -H "Content-Type: application/json" \
  -d '{
    "id": "test_render_id",
    "status": "completed",
    "url": "https://example.com/test-video.mp4"
  }'
```

### Monitor Logs

Watch for these log messages:

```bash
# Webhook configuration  
🔗 Webhook URL configured: http://localhost:3000/api/webhooks/creatomate-completion

# Webhook received
🎬 Creatomate webhook received - Render ID: abc123, Status: completed

# Job updated
✅ Creatomate render completed successfully: https://video-url.mp4

# Real-time frontend update
📡 Sent render completion update to job xyz frontend client
```

## Production Deployment

### Docker Configuration

Update your `docker-compose.yml`:

```yaml
environment:
    - WEBHOOK_BASE_URL=https://your-domain.com
```

### External Webhook URLs

For services like Railway, Heroku, or custom domains:

```bash
# Railway
WEBHOOK_BASE_URL=https://your-app.railway.app

# Heroku
WEBHOOK_BASE_URL=https://your-app.herokuapp.com

# Custom domain
WEBHOOK_BASE_URL=https://streamgank.yourdomain.com
```

## Monitoring & Troubleshooting

### Common Issues

| Issue                       | Cause                     | Solution                              |
| --------------------------- | ------------------------- | ------------------------------------- |
| Videos stuck in "rendering" | Webhook URL unreachable   | Check `WEBHOOK_BASE_URL` and firewall |
| Jobs complete but no video  | Webhook not received      | Check Creatomate webhook logs         |
| Backup polling messages     | Webhooks working normally | Normal - backup system running        |

### Status Indicators

-   **`rendering`** - Creatomate is processing, waiting for webhook
-   **`completed`** - Video ready with URL (webhook received)
-   **`failed`** - Render failed (from webhook or timeout)

## Migration from Polling

The system automatically falls back to backup polling if webhooks fail, so migration is seamless:

-   **Before**: Polling every 30-60 seconds
-   **After**: Instant webhooks + backup polling every 5-10 minutes

No configuration changes needed - just set `WEBHOOK_BASE_URL` for optimal performance.
