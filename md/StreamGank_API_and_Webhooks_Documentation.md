# StreamGank GUI - Complete API Endpoints and Webhooks Documentation

## Table of Contents

-   [API Endpoints](#api-endpoints)
-   [Webhook System](#webhook-system)
-   [Real-time Integration](#real-time-integration)
-   [Security & Configuration](#security--configuration)

---

## API Endpoints

### 🎬 Video Generation & Jobs

-   **POST** `/api/generate` - Submit video generation job
-   **GET** `/api/job/:jobId` - Get job status by ID
-   **GET** `/api/job/:jobId/details` - Get detailed job information
-   **POST** `/api/job/:jobId/cancel` - Cancel a specific job
-   **POST** `/api/job/:jobId/retry` - Retry a failed job
-   **POST** `/api/job/:jobId/complete` - Mark job as complete
-   **GET** `/api/job/:jobId/stream` - Job-specific Server-Sent Events stream

### 📋 Queue Management

-   **GET** `/api/queue/status` - Get queue statistics and status
-   **GET** `/api/queue/jobs` - Get all jobs in queue
-   **POST** `/api/queue/clear` - Clear entire queue
-   **POST** `/api/queue/toggle` - Toggle queue processing on/off
-   **POST** `/api/queue/clear-failed` - Clear only failed jobs
-   **POST** `/api/queue/cleanup` - Cleanup old/stale jobs
-   **DELETE** `/api/queue/job/:jobId` - Delete specific job from queue
-   **DELETE** `/api/queue/job/:jobId/delete` - Alternative delete endpoint

### 📊 Real-time Updates

-   **GET** `/api/queue/status/stream` - Server-Sent Events for queue status updates

### 📝 Logging & Monitoring

-   **GET** `/api/queue/job/:jobId/logs` - Get in-memory logs for job
-   **GET** `/api/queue/job/:jobId/logs/persistent` - Get persistent logs for job
-   **POST** `/api/queue/job/:jobId/logs/archive` - Archive job logs
-   **GET** `/api/logs/search` - Search through logs
-   **GET** `/api/logs/stats` - Get logging statistics

### 🎥 Video Processing & Creatomate

-   **GET** `/api/status/:creatomateId` - Check Creatomate render status
-   **POST** `/api/queue/job/:jobId/monitor-creatomate` - Start Creatomate monitoring for job

### 🎭 Content & Metadata

-   **POST** `/api/movies/preview` - Preview movies for selected filters
-   **GET** `/api/platforms/:country` - Get available platforms for country
-   **GET** `/api/genres/:country` - Get available genres for country

### 🔧 Webhooks & Integration

-   **GET** `/api/webhooks/status` - Get webhook system status
-   **POST** `/api/webhooks/test` - Test webhook endpoint
-   **POST** `/api/webhooks/trigger` - Manually trigger webhook
-   **POST** `/api/webhooks/step-update` - Receive step update webhooks
-   **POST** `/api/webhooks/creatomate` - Receive Creatomate status webhooks

### 🔍 Validation & Utilities

-   **POST** `/api/validate-url` - Validate URLs
-   **GET** `/api/test` - Test endpoint (currently disabled)

### 📈 Health & Status

-   **GET** `/health` - Application health check

### 📄 Static Routes

-   **GET** `/` - Main application page
-   **GET** `/dashboard` - Dashboard page
-   **GET** `/queue` - Queue management page
-   **GET** `/job/:jobId` - Job detail page

### 🔄 Usage Patterns

The GUI uses these endpoints in several patterns:

1. **APIService.js** - Centralized HTTP client with caching, retry logic, and error handling
2. **Real-time Updates** - Combination of Server-Sent Events (`/api/queue/status/stream`, `/api/job/:jobId/stream`) with polling fallback
3. **Form Management** - Dynamic loading of platforms and genres based on country selection
4. **Job Monitoring** - Real-time job status updates via webhooks and SSE
5. **Video Processing** - Integration with Creatomate API for video rendering status

---

## Webhook System

### 📡 Webhook Architecture

The StreamGank system uses a sophisticated webhook architecture with **three main types**:

1. **🔄 Internal Workflow Webhooks** - From Python scripts to GUI
2. **🌐 External Service Webhooks** - From external services (Creatomate) to GUI
3. **📤 Outbound Webhooks** - From GUI to external services

---

### 📥 INCOMING WEBHOOKS (Received by GUI)

#### 1. 🐍 Python Workflow Step Updates

**Endpoint:** `POST /api/webhooks/step-update`

**Purpose:** Real-time updates from Python video generation workflow

**Payload Structure:**

```json
{
    "job_id": "job_123",
    "step_number": 3,
    "step_name": "Asset Preparation",
    "status": "started|completed",
    "duration": 1234,
    "details": { "creatomate_id": "abc123" },
    "timestamp": "2024-01-01T12:00:00Z",
    "step_key": "step_3_asset_prep",
    "sequence": 1704110400000,
    "workflow_stage": "processing"
}
```

**Step Numbers & Names:**

-   **Step 1:** Database Extraction
-   **Step 2:** Script Generation
-   **Step 3:** Asset Preparation
-   **Step 4:** HeyGen Video Creation
-   **Step 5:** HeyGen Processing
-   **Step 6:** Scroll Video Generation
-   **Step 7:** Creatomate Assembly

**Features:**

-   ✅ **Step Validation** - Prevents out-of-order updates
-   🔄 **Real-time SSE Broadcasting** - Instantly updates frontend
-   📝 **Persistent Logging** - All webhook events logged
-   🎯 **Sequence Tracking** - Prevents duplicate/old updates

#### 2. 🎬 Creatomate Video Rendering Updates

**Endpoint:** `POST /api/webhooks/creatomate`

**Purpose:** Status updates from Creatomate video rendering service

**Payload Structure:**

```json
{
    "id": "render_abc123",
    "status": "planned|waiting|transcribing|rendering|succeeded|failed",
    "url": "https://cdn.creatomate.com/video.mp4",
    "error": "Error message if failed",
    "data": { "additional": "metadata" }
}
```

**Status Flow:**

1. **`planned`** → Video queued for processing
2. **`waiting`** → Waiting in render queue
3. **`transcribing`** → Processing audio/text
4. **`rendering`** → Actively rendering video
5. **`succeeded`** → ✅ Video ready with URL
6. **`failed`** → ❌ Rendering failed with error

---

### 📤 OUTBOUND WEBHOOKS (Sent by GUI)

#### 🔗 External Service Notifications

**Managed by:** `WebhookManager` class

**Configuration:** Environment variables

```o bash
WEBHOOK_URLS=https://api.example.com/webhooks,https://slack.webhook.url
WEBHOOK_EVENTS=job.completed,job.failed
WEBHOOK_SECRET_KEY=your_secret_key
WEBHOOK_MAX_RETRIES=3
WEBHOOK_TIMEOUT=10000
```

**Event Types:**

-   **`job.completed`** - Video generation completed successfully
-   **`job.failed`** - Video generation failed
-   **`webhook.test`** - Connectivity test event

**Payload Structure:**

```json
{
    "event": "job.completed",
    "data": {
        "job_id": "job_123",
        "status": "completed",
        "video_url": "https://cdn.creatomate.com/video.mp4",
        "duration": "2m 34s",
        "metadata": { "country": "US", "platform": "Netflix" }
    },
    "timestamp": "2024-01-01T12:00:00Z",
    "webhook_id": "webhook_1",
    "source": "streamgank"
}
```

**Security Features:**

-   🔐 **HMAC Signatures** - `X-StreamGank-Signature: sha256=...`
-   🆔 **Delivery Tracking** - `X-StreamGank-Delivery: uuid`
-   📋 **Event Headers** - `X-StreamGank-Event: job.completed`
-   🔄 **Retry Logic** - Exponential backoff (3 attempts max)
-   ⏱️ **Rate Limiting** - 100 requests/minute per endpoint

---

## Real-time Integration

### 📡 Job-Specific Updates

**Endpoint:** `GET /api/job/:jobId/stream`

**SSE Event Types:**

-   **`step_update`** - Workflow step progress
-   **`render_completed`** - Video rendering finished
-   **`render_failed`** - Video rendering failed
-   **`render_planned`** - Video queued for rendering
-   **`render_waiting`** - Video waiting in render queue
-   **`render_transcribing`** - Video transcription phase
-   **`render_rendering`** - Video actively rendering
-   **`heartbeat`** - Keep connection alive

**Frontend Integration:**

```javascript
// Real-time webhook processing in job-detail-app.js
handleJobSSEMessage(data) {
  switch (data.type) {
    case 'step_update':
      // Update step progress in real-time
      this.currentActiveStep = data.step_number;
      break;

    case 'render_completed':
      // Instantly show completed video
      this.jobData.videoUrl = data.videoUrl;
      this.showCreatomateVideoResult();
      break;
  }
}
```

---

## Security & Configuration

### 🛡️ Webhook Security & Reliability

#### Security Measures:

-   **IP Logging** - All webhook sources tracked
-   **Payload Validation** - Required fields checked
-   **HMAC Signatures** - Cryptographic verification
-   **Rate Limiting** - Prevents abuse
-   **HTTPS Only** - Encrypted transmission

#### Reliability Features:

-   **Automatic Retries** - 3 attempts with exponential backoff
-   **Error Tracking** - Failed delivery statistics
-   **Timeout Handling** - 10-second request timeout
-   **Duplicate Prevention** - Sequence-based validation
-   **Connection Recovery** - SSE auto-reconnection

### 🔧 Webhook Management Endpoints

#### Status & Testing:

-   **`GET /api/webhooks/status`** - Get webhook system status
-   **`POST /api/webhooks/test`** - Test webhook endpoint connectivity
-   **`POST /api/webhooks/trigger`** - Manually trigger webhook events

#### Usage Example:

```bash
# Test webhook connectivity
curl -X POST http://localhost:3000/api/webhooks/test \
  -H "Content-Type: application/json" \
  -d '{"url": "https://your-webhook-endpoint.com"}'

# Manually trigger job completion webhook
curl -X POST http://localhost:3000/api/webhooks/trigger \
  -H "Content-Type: application/json" \
  -d '{"event": "job.completed", "data": {"job_id": "test_123"}}'
```

### 📊 Webhook Flow Diagram

```
🐍 Python Script → POST /api/webhooks/step-update → 📡 SSE Broadcast → 🖥️ Frontend Update
                                                  ↓
🎬 Creatomate → POST /api/webhooks/creatomate → 📡 SSE Broadcast → 🖥️ Video Display
                                               ↓
                                          📤 External Webhooks → 🌐 External Services
```

---

## Architecture Summary

The StreamGank GUI follows a modern SPA architecture with:

-   **Professional HTTP Client** - APIService.js with caching, retry logic, and error handling
-   **Real-time Communication** - Server-Sent Events with polling fallback
-   **Webhook Integration** - Both incoming and outgoing webhook support
-   **Security** - HMAC signatures, rate limiting, and payload validation
-   **Reliability** - Automatic retries, connection recovery, and error tracking
-   **Monitoring** - Comprehensive logging and status reporting

This comprehensive system provides **real-time updates**, **external integrations**, and **professional reliability** for the StreamGank video generation platform!
