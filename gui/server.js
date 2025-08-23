const express = require('express');
const { spawn } = require('child_process');
const path = require('path');
const VideoQueueManager = require('./queue-manager');
const WebhookManager = require('./webhook-manager');

// Enhanced in-memory cache to reduce Redis calls during heavy processing
const jobCache = new Map();
const statusCache = new Map(); // Cache for queue status to prevent Redis overload
const CACHE_TTL = 45000; // 45 seconds cache (optimized for 1min refresh interval)
const STATUS_CACHE_TTL = 30000; // 30 seconds cache - webhooks provide real-time updates

// Production-level optimizations for web deployment
const sseClients = new Set(); // Track Server-Sent Events clients
const requestDeduplication = new Map(); // Prevent duplicate concurrent requests
const rateLimiter = new Map(); // Rate limiting per IP
const RATE_LIMIT_WINDOW = 60000; // 1 minute window
const RATE_LIMIT_MAX_REQUESTS = 100; // Max requests per IP per minute

const app = express();
const port = process.env.PORT || 3000;

// Initialize Redis queue manager
const queueManager = new VideoQueueManager();

// Initialize professional webhook manager for external integrations
const webhookManager = new WebhookManager();

// Integrate webhook manager with queue processing
queueManager.setWebhookManager(webhookManager);

// Middleware for parsing JSON and serving static files from built dist/
app.use(express.json());
app.use(express.static(path.join(__dirname, 'dist')));

// Also serve original CSS and assets from gui folder (for style.css)
app.use('/css', express.static(path.join(__dirname, 'css')));
// REMOVED: app.use('/js', express.static(path.join(__dirname, 'js')));
// ^^^ This was causing conflicts - webpack /js/ files are served from dist/ by the express.static above

// Production-level rate limiting middleware
const rateLimit = (req, res, next) => {
    const clientIp = req.ip || req.connection.remoteAddress || 'unknown';
    const now = Date.now();

    // Clean old entries
    for (const [ip, data] of rateLimiter) {
        if (now - data.windowStart > RATE_LIMIT_WINDOW) {
            rateLimiter.delete(ip);
        }
    }

    // Check rate limit
    const clientData = rateLimiter.get(clientIp);
    if (clientData) {
        if (now - clientData.windowStart > RATE_LIMIT_WINDOW) {
            // Reset window
            rateLimiter.set(clientIp, { windowStart: now, requestCount: 1 });
        } else {
            clientData.requestCount++;
            if (clientData.requestCount > RATE_LIMIT_MAX_REQUESTS) {
                return res.status(429).json({
                    success: false,
                    message: 'Rate limit exceeded. Please slow down.',
                    retryAfter: Math.ceil((RATE_LIMIT_WINDOW - (now - clientData.windowStart)) / 1000)
                });
            }
        }
    } else {
        rateLimiter.set(clientIp, { windowStart: now, requestCount: 1 });
    }

    next();
};

// Apply rate limiting to API routes only
app.use('/api', rateLimit);

// Enable CORS with production settings
app.use((req, res, next) => {
    res.header('Access-Control-Allow-Origin', '*');
    res.header('Access-Control-Allow-Headers', 'Origin, X-Requested-With, Content-Type, Accept');
    res.header('Cache-Control', 'no-cache, no-store, must-revalidate'); // Prevent caching of API responses
    next();
});

// Route to serve the main HTML file
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'dist', 'index.html'));
});

// Health check endpoint for Docker
app.get('/health', (req, res) => {
    res.status(200).json({
        status: 'healthy',
        timestamp: new Date().toISOString(),
        service: 'streamgank-gui'
    });
});

// SPA Routing - Serve appropriate HTML files for client-side routes
app.get(['/dashboard', '/jobs'], (req, res) => {
    res.sendFile(path.join(__dirname, 'dist', 'index.html'));
});

// Job Detail Pages - Serve professional job detail page
app.get('/job/:jobId', (req, res) => {
    res.sendFile(path.join(__dirname, 'job-detail.html'));
});

// REMOVED: Catch-all route moved to end of file after all API routes

// Job detail API route (enhanced with more details)
app.get('/api/job/:jobId/details', async (req, res) => {
    try {
        const { jobId } = req.params;
        const job = await queueManager.getJob(jobId);

        if (!job) {
            return res.status(404).json({
                success: false,
                message: 'Job not found'
            });
        }

        // Enhanced job details with additional metadata
        const enhancedJob = {
            ...job,
            duration: job.startedAt ? Date.now() - new Date(job.startedAt).getTime() : null,
            detailsUrl: `/job/${jobId}`,
            isActive: ['pending', 'processing'].includes(job.status)
        };

        res.json({
            success: true,
            job: enhancedJob
        });
    } catch (error) {
        console.error('❌ Failed to get job details:', error);
        res.status(500).json({
            success: false,
            message: 'Failed to get job details',
            error: error.message
        });
    }
});

// Job logs API route removed - logs no longer fetched for better performance

// Platform mapping to match frontend values to Python script expectations
const platformMapping = {
    amazon: 'Prime',
    apple: 'Apple TV+',
    disney: 'Disney+',
    hulu: 'Hulu',
    max: 'Max',
    netflix: 'Netflix',
    free: 'Free'
};

// Content type mapping
const contentTypeMapping = {
    Film: 'Film',
    Serie: 'Série',
    all: 'Film' // Default to Film for 'all' option
};

// Helper function to execute Python script with async/await
async function executePythonScript(args, cwd = path.join(__dirname, '..'), timeoutMs = 30 * 60 * 1000) {
    return new Promise((resolve, reject) => {
        // Executing command (same as CLI)

        const pythonProcess = spawn('python', args, {
            cwd: cwd,
            env: {
                ...process.env,
                PYTHONIOENCODING: 'utf-8',
                PYTHONUNBUFFERED: '1'
            }
        });

        let stdout = '';
        let stderr = '';
        let isResolved = false;

        // Set up timeout (30 minutes default)
        const timeout = setTimeout(() => {
            if (!isResolved) {
                isResolved = true;
                pythonProcess.kill('SIGTERM');
                reject({
                    code: -2,
                    error: 'Python script execution timeout',
                    stdout,
                    stderr
                });
            }
        }, timeoutMs);

        // Handle stdout data
        pythonProcess.stdout.on('data', (data) => {
            try {
                const output = data.toString('utf8');
                stdout += output;
                // Output exactly like CLI - no prefixes
                process.stdout.write(output);
            } catch (encodingError) {
                console.warn('Encoding error in stdout:', encodingError.message);
                const output = data.toString('latin1'); // Fallback encoding
                stdout += output;
                process.stdout.write(output);
            }
        });

        // Handle stderr data
        pythonProcess.stderr.on('data', (data) => {
            try {
                const output = data.toString('utf8');
                stderr += output;
                // Output exactly like CLI - no prefixes
                process.stderr.write(output);
            } catch (encodingError) {
                console.warn('Encoding error in stderr:', encodingError.message);
                const output = data.toString('latin1'); // Fallback encoding
                stderr += output;
                process.stderr.write(output);
            }
        });

        // Handle process completion
        pythonProcess.on('close', (code) => {
            if (!isResolved) {
                isResolved = true;
                clearTimeout(timeout);
                // Process completed (code logged internally only if needed)

                if (code !== 0) {
                    reject({
                        code,
                        error: stderr || 'Python script failed with no error message',
                        stdout
                    });
                } else {
                    resolve({
                        code,
                        stdout,
                        stderr
                    });
                }
            }
        });

        // Handle process errors
        pythonProcess.on('error', (error) => {
            if (!isResolved) {
                isResolved = true;
                clearTimeout(timeout);
                console.error('Failed to start Python process:', error);
                reject({
                    code: -1,
                    error: error.message,
                    stdout: '',
                    stderr: ''
                });
            }
        });
    });
}

// API endpoint to add video to Redis queue
app.post('/api/generate', async (req, res) => {
    try {
        const { country, platform, genre, contentType, template, pauseAfterExtraction } = req.body;

        console.log('📨 Received queue request:', {
            country,
            platform,
            genre,
            contentType,
            template,
            pauseAfterExtraction
        });

        if (!country || !platform || !genre || !contentType) {
            return res.status(400).json({
                success: false,
                message: 'Missing required parameters',
                received: { country, platform, genre, contentType, template }
            });
        }

        // Map platform and content type to match Python script expectations
        const mappedPlatform = platformMapping[platform] || platform;
        const mappedContentType = contentTypeMapping[contentType] || contentType;

        console.log('🔄 Mapped values:', {
            country,
            platform: mappedPlatform,
            genre,
            contentType: mappedContentType,
            template: template || 'auto', // Default to 'auto' if not provided
            pauseAfterExtraction: pauseAfterExtraction || false
        });

        // Add job to Redis queue
        const job = await queueManager.addJob({
            country,
            platform: mappedPlatform,
            genre,
            contentType: mappedContentType,
            template: template || 'auto', // Include template parameter
            pauseAfterExtraction: pauseAfterExtraction || false // Include pause flag
        });

        // Get current queue status
        const queueStatus = await queueManager.getQueueStatus();

        // Return job info and queue status
        res.json({
            success: true,
            jobId: job.id,
            message: 'Video added to queue successfully',
            queuePosition: queueStatus.pending + queueStatus.processing,
            queueStatus: queueStatus,
            job: job
        });
    } catch (error) {
        console.error('❌ Failed to add job to queue:', error);

        res.status(500).json({
            success: false,
            message: 'Failed to add video to queue',
            error: error.message
        });
    }
});

// API endpoint to check Creatomate status
app.get('/api/status/:creatomateId', async (req, res) => {
    try {
        const { creatomateId } = req.params;

        const scriptPath = path.join(__dirname, '../main.py');
        const args = [scriptPath, '--check-creatomate', creatomateId];

        // Execute Python script with async/await
        const result = await executePythonScript(args);
        const { stdout } = result;

        // Parse status from output
        let status = 'unknown';
        let videoUrl = '';

        const statusMatch = stdout.match(/Render Status[:\s]+(\w+)/i);
        if (statusMatch && statusMatch[1]) {
            status = statusMatch[1];
        }

        const urlMatch = stdout.match(/Video URL[:\s]+(https:\/\/[^\s\n]+)/i);
        if (urlMatch && urlMatch[1]) {
            videoUrl = urlMatch[1];
        }

        res.json({
            success: true,
            status: status,
            videoUrl: videoUrl,
            creatomateId: creatomateId
        });
    } catch (error) {
        console.error('Status check failed:', error);

        res.status(500).json({
            success: false,
            message: 'Failed to check status',
            error: error.error || error.message
        });
    }
});

// API endpoint to test Python script and database connection
app.get('/api/test', async (req, res) => {
    try {
        console.log('Testing Python script and database connection...');

        const scriptPath = path.join(__dirname, '../main.py');
        const args = [
            scriptPath,
            '--country',
            'FR',
            '--platform',
            'Netflix',
            '--genre',
            'Horror',
            '--content-type',
            'Film'
        ];

        // Execute with shorter timeout for testing
        const result = await executePythonScript(args, path.join(__dirname, '..'), 5 * 60 * 1000);

        res.json({
            success: true,
            message: 'Python script test completed',
            hasOutput: result.stdout.length > 0,
            outputLength: result.stdout.length,
            preview: result.stdout.substring(0, 500) + (result.stdout.length > 500 ? '...' : '')
        });
    } catch (error) {
        console.error('Python script test failed:', error);

        res.json({
            success: false,
            message: 'Python script test failed',
            error: error.error || error.message,
            code: error.code,
            stdout: error.stdout ? error.stdout.substring(0, 500) : '',
            stderr: error.stderr ? error.stderr.substring(0, 500) : ''
        });
    }
});

// API endpoint to get job status by ID - OPTIMIZED with caching and performance monitoring
app.get('/api/job/:jobId', async (req, res) => {
    const startTime = Date.now();
    try {
        const { jobId } = req.params;

        // Check cache first
        const cacheKey = `job_${jobId}`;
        const cachedData = jobCache.get(cacheKey);

        if (cachedData && Date.now() - cachedData.timestamp < CACHE_TTL) {
            const duration = Date.now() - startTime;
            return res.json({
                success: true,
                job: cachedData.job,
                _debug: {
                    duration: `${duration}ms`,
                    cached: true
                }
            });
        }

        // Add timeout to prevent hanging requests
        const timeoutPromise = new Promise((_, reject) => {
            setTimeout(() => reject(new Error('Request timeout')), 3000); // 3 second timeout
        });

        const jobPromise = queueManager.getJob(jobId);
        const job = await Promise.race([jobPromise, timeoutPromise]);

        const duration = Date.now() - startTime;

        // Log slow requests for debugging
        if (duration > 500) {
            console.warn(`⚠️ Slow job request for ${jobId.slice(-8)}: ${duration}ms`);
        }

        if (!job) {
            return res.status(404).json({
                success: false,
                message: 'Job not found'
            });
        }

        // Cache the result
        jobCache.set(cacheKey, {
            job: job,
            timestamp: Date.now()
        });

        // Clean old cache entries occasionally
        if (jobCache.size > 100) {
            const now = Date.now();
            for (const [key, value] of jobCache) {
                if (now - value.timestamp > CACHE_TTL * 5) {
                    jobCache.delete(key);
                }
            }
        }

        res.json({
            success: true,
            job: job,
            _debug: {
                duration: `${duration}ms`,
                cached: false
            }
        });
    } catch (error) {
        const duration = Date.now() - startTime;
        console.error(`❌ Failed to get job (${duration}ms):`, error.message);

        res.status(500).json({
            success: false,
            message: 'Failed to get job status',
            error: error.message,
            _debug: {
                duration: `${duration}ms`
            }
        });
    }
});

// API endpoint to get queue status - OPTIMIZED with aggressive caching during processing
app.get('/api/queue/status', async (req, res) => {
    const startTime = Date.now();
    try {
        // Check if we have cached status data
        const statusCacheKey = 'queue_status';
        const cachedStatus = statusCache.get(statusCacheKey);

        // PROFESSIONAL: Use longer cache since webhooks provide real-time updates
        const isProcessing = await queueManager.isActivelyProcessing();
        const cacheTimeout = STATUS_CACHE_TTL; // Fixed cache timeout, webhooks handle real-time updates

        if (cachedStatus && Date.now() - cachedStatus.timestamp < cacheTimeout) {
            const duration = Date.now() - startTime;
            return res.json({
                success: true,
                stats: {
                    ...cachedStatus.stats,
                    _debug: {
                        duration: `${duration}ms`,
                        cached: true,
                        cacheAge: `${Date.now() - cachedStatus.timestamp}ms`
                    }
                }
            });
        }

        // PROFESSIONAL: Longer timeout since webhooks handle real-time updates
        const timeoutPromise = new Promise((_, reject) => {
            setTimeout(() => reject(new Error('Status request timeout')), 5000); // 5 second timeout
        });

        // Get fresh stats from Redis
        const statsPromise = queueManager.getQueueStats();
        const stats = await Promise.race([statsPromise, timeoutPromise]);

        const duration = Date.now() - startTime;

        // Log slow status requests for debugging
        if (duration > 200) {
            console.warn(`⚠️ Slow status request: ${duration}ms (processing: ${isProcessing})`);
        }

        // Cache the fresh result
        statusCache.set(statusCacheKey, {
            stats: stats,
            timestamp: Date.now()
        });

        // Clean old status cache entries
        if (statusCache.size > 10) {
            const now = Date.now();
            for (const [key, value] of statusCache) {
                if (now - value.timestamp > STATUS_CACHE_TTL * 3) {
                    statusCache.delete(key);
                }
            }
        }

        res.json({
            success: true,
            stats: {
                ...stats,
                _debug: {
                    duration: `${duration}ms`,
                    cached: false,
                    processing: isProcessing
                }
            }
        });
    } catch (error) {
        console.error('❌ Failed to get queue status:', error);

        // Fallback to cached data if available during errors
        const statusCacheKey = 'queue_status';
        const cachedStatus = statusCache.get(statusCacheKey);
        if (cachedStatus) {
            console.log('📋 Using cached status data due to error');
            return res.json({
                success: true,
                stats: {
                    ...cachedStatus.stats,
                    _debug: {
                        duration: `${Date.now() - startTime}ms`,
                        cached: true,
                        fallback: true
                    }
                }
            });
        }

        res.status(500).json({
            success: false,
            message: 'Failed to get queue status',
            error: error.message
        });
    }
});

// Server-Sent Events endpoint for real-time queue status updates - PRODUCTION OPTIMIZED
app.get('/api/queue/status/stream', (req, res) => {
    const clientIp = req.ip || req.connection.remoteAddress || 'unknown';

    // Set up SSE headers
    res.writeHead(200, {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        Connection: 'keep-alive',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Cache-Control'
    });

    const clientId = `${clientIp}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const client = {
        id: clientId,
        res: res,
        lastUpdate: Date.now(),
        ip: clientIp
    };

    sseClients.add(client);
    console.log(`📡 SSE client connected: ${clientId} (${sseClients.size} total clients)`);

    // Send initial status
    sendStatusToClient(client);

    // Handle client disconnect
    req.on('close', () => {
        sseClients.delete(client);
        console.log(`📡 SSE client disconnected: ${clientId} (${sseClients.size} total clients)`);
    });

    // Keep connection alive
    const keepAlive = setInterval(() => {
        if (res.writable) {
            res.write('event: heartbeat\ndata: {}\n\n');
        } else {
            clearInterval(keepAlive);
            sseClients.delete(client);
        }
    }, 30000); // Heartbeat every 30 seconds

    req.on('close', () => {
        clearInterval(keepAlive);
    });
});

// Function to send status updates to SSE clients
async function sendStatusToClient(client) {
    try {
        const stats = await getQueueStatsWithDeduplication();
        const data = JSON.stringify({
            success: true,
            stats: stats,
            timestamp: Date.now(),
            clientId: client.id
        });

        if (client.res.writable) {
            client.res.write(`event: status\ndata: ${data}\n\n`);
            client.lastUpdate = Date.now();
        } else {
            sseClients.delete(client);
        }
    } catch (error) {
        console.error('❌ Failed to send status to SSE client:', error);
        if (client.res.writable) {
            const errorData = JSON.stringify({
                success: false,
                error: error.message,
                timestamp: Date.now()
            });
            client.res.write(`event: error\ndata: ${errorData}\n\n`);
        }
    }
}

// Request deduplication wrapper for getQueueStats
async function getQueueStatsWithDeduplication() {
    const dedupeKey = 'queue_stats';
    const now = Date.now();

    // Check if there's already a pending request
    const pendingRequest = requestDeduplication.get(dedupeKey);
    if (pendingRequest && now - pendingRequest.timestamp < 1000) {
        // 1 second deduplication window
        return pendingRequest.promise;
    }

    // Create new request
    const promise = queueManager.getQueueStats();
    requestDeduplication.set(dedupeKey, {
        promise: promise,
        timestamp: now
    });

    // Clean up after request completes
    promise.finally(() => {
        const current = requestDeduplication.get(dedupeKey);
        if (current && current.timestamp === now) {
            requestDeduplication.delete(dedupeKey);
        }
    });

    return promise;
}

// Broadcast status updates to all SSE clients periodically
let broadcastInterval;
function startStatusBroadcast() {
    if (broadcastInterval) {
        clearInterval(broadcastInterval);
    }

    broadcastInterval = setInterval(async () => {
        if (sseClients.size === 0) {
            return; // No clients to update
        }

        // PROFESSIONAL: Only broadcast on webhook events, minimal polling
        // Webhooks handle real-time updates, this is just a health check
        const isProcessing = await queueManager.isActivelyProcessing();
        if (isProcessing) {
            // Send lightweight status only during processing
            const clientsToRemove = [];
            for (const client of sseClients) {
                try {
                    client.write(`data: ${JSON.stringify({ type: 'heartbeat', timestamp: Date.now() })}\n\n`);
                } catch (error) {
                    clientsToRemove.push(client);
                }
            }

            // Clean up broken connections
            clientsToRemove.forEach((client) => {
                sseClients.delete(client);
            });
        }
    }, 60000); // PROFESSIONAL: Only heartbeat every 60 seconds, webhooks do the real work
}

// Start the broadcast system
startStatusBroadcast();

// ===== PROFESSIONAL WEBHOOK API ENDPOINTS =====

// Get webhook system status and configuration
app.get('/api/webhooks/status', (req, res) => {
    try {
        const status = webhookManager.getWebhookStatus();
        res.json({
            success: true,
            webhooks: status,
            timestamp: new Date().toISOString()
        });
    } catch (error) {
        console.error('❌ Failed to get webhook status:', error);
        res.status(500).json({
            success: false,
            message: 'Failed to get webhook status',
            error: error.message
        });
    }
});

// API endpoint to receive step completion webhooks from Python workflow
app.post('/api/webhooks/step-update', async (req, res) => {
    try {
        const { job_id, step_number, step_name, status, duration, details } = req.body;

        console.log(`📡 Step webhook received: Job ${job_id} - Step ${step_number} (${step_name}) ${status}`);

        // Update job with step progress
        const job = await queueManager.getJob(job_id);
        if (job) {
            job.currentStep = `Step ${step_number}: ${step_name}`;
            job.progress = Math.round((step_number / 7) * 100);
            job.lastUpdate = new Date().toISOString();

            // Add step details if provided
            if (details) {
                job.stepDetails = details;
            }

            await queueManager.updateJob(job);

            console.log(`✅ Job ${job_id} updated: ${job.progress}% complete`);
        }

        res.json({ success: true, message: 'Step update received' });
    } catch (error) {
        console.error('❌ Step webhook error:', error);
        res.status(500).json({ success: false, error: error.message });
    }
});

// Test webhook endpoint connectivity
app.post('/api/webhooks/test', async (req, res) => {
    try {
        const { url } = req.body;

        if (!url) {
            return res.status(400).json({
                success: false,
                message: 'Webhook URL is required'
            });
        }

        console.log(`🧪 Testing webhook endpoint: ${url}`);
        const testResult = await webhookManager.validateWebhookEndpoint(url);

        res.json({
            success: true,
            test_result: testResult,
            timestamp: new Date().toISOString()
        });
    } catch (error) {
        console.error('❌ Failed to test webhook endpoint:', error);
        res.status(500).json({
            success: false,
            message: 'Failed to test webhook endpoint',
            error: error.message
        });
    }
});

// Manual webhook trigger (for testing purposes)
app.post('/api/webhooks/trigger', async (req, res) => {
    try {
        const { event, data } = req.body;

        if (!event) {
            return res.status(400).json({
                success: false,
                message: 'Event name is required'
            });
        }

        const testData = data || {
            message: 'Manual webhook test trigger',
            timestamp: new Date().toISOString(),
            manual: true
        };

        console.log(`🔗 Manually triggering webhook event: ${event}`);
        const results = await webhookManager.sendWebhookNotification(event, testData);

        const successful = results.filter((r) => r.status === 'fulfilled').length;
        const failed = results.filter((r) => r.status === 'rejected').length;

        res.json({
            success: true,
            message: `Webhook notifications sent`,
            results: {
                total: results.length,
                successful,
                failed
            },
            timestamp: new Date().toISOString()
        });
    } catch (error) {
        console.error('❌ Failed to trigger webhook:', error);
        res.status(500).json({
            success: false,
            message: 'Failed to trigger webhook',
            error: error.message
        });
    }
});

// API endpoint to get all jobs
app.get('/api/queue/jobs', async (req, res) => {
    try {
        const jobs = await queueManager.getAllJobs();
        res.json({
            success: true,
            jobs: jobs
        });
    } catch (error) {
        console.error('❌ Failed to get all jobs:', error);
        res.status(500).json({
            success: false,
            message: 'Failed to get jobs',
            error: error.message
        });
    }
});

// API endpoint to clear queue (admin only)
app.post('/api/queue/clear', async (req, res) => {
    try {
        await queueManager.clearAllQueues();
        res.json({
            success: true,
            message: 'All queues cleared successfully'
        });
    } catch (error) {
        console.error('❌ Failed to clear queues:', error);
        res.status(500).json({
            success: false,
            message: 'Failed to clear queues',
            error: error.message
        });
    }
});

// API endpoint to clean up stuck processing jobs
app.post('/api/queue/cleanup', async (req, res) => {
    try {
        await queueManager.cleanupProcessingQueue();
        res.json({
            success: true,
            message: 'Processing queue cleaned up successfully'
        });
    } catch (error) {
        console.error('❌ Failed to cleanup processing queue:', error);
        res.status(500).json({
            success: false,
            message: 'Failed to cleanup processing queue',
            error: error.message
        });
    }
});

// API endpoint to update job with video URL after Creatomate completion
app.post('/api/job/:jobId/complete', async (req, res) => {
    try {
        const { jobId } = req.params;
        const { videoUrl } = req.body;

        if (!videoUrl) {
            return res.status(400).json({
                success: false,
                message: 'Video URL is required'
            });
        }

        const job = await queueManager.getJob(jobId);
        if (!job) {
            return res.status(404).json({
                success: false,
                message: 'Job not found'
            });
        }

        // Update job with final video URL
        job.videoUrl = videoUrl;
        job.progress = 100;
        job.completedAt = new Date().toISOString();
        job.currentStep = 'Video rendering completed!';

        await queueManager.updateJob(job);

        res.json({
            success: true,
            message: 'Job updated with video URL',
            job: job
        });
    } catch (error) {
        console.error('❌ Failed to update job:', error);
        res.status(500).json({
            success: false,
            message: 'Failed to update job',
            error: error.message
        });
    }
});

// API endpoint to cancel a job
app.post('/api/job/:jobId/cancel', async (req, res) => {
    try {
        const { jobId } = req.params;
        console.log(`🛑 Cancelling job: ${jobId}`);

        // Use the queue manager's cancelJob method which handles process killing
        const job = await queueManager.cancelJob(jobId);

        res.json({
            success: true,
            message: 'Job cancelled successfully',
            job: job
        });
    } catch (error) {
        console.error('❌ Failed to cancel job:', error);
        res.status(500).json({
            success: false,
            message: 'Failed to cancel job',
            error: error.message
        });
    }
});

// API endpoint to get available platforms by region from database
app.get('/api/platforms/:country', async (req, res) => {
    try {
        const { country } = req.params;
        console.log(`🌍 Fetching platforms for country: ${country}`);

        // Use the exact platform data provided by the user
        const availablePlatforms = {
            FR: ['Prime', 'Apple TV+', 'Disney+', 'Max', 'Netflix', 'Free'],
            US: ['Prime', 'Apple TV+', 'Disney+', 'Hulu', 'Max', 'Netflix', 'Free']
        };

        const platforms = availablePlatforms[country] || availablePlatforms['US']; // Default to US if country not found

        console.log(`✅ Found ${platforms.length} platforms for ${country}:`, platforms);

        res.json({
            success: true,
            country: country,
            platforms: platforms,
            source: 'user_defined',
            count: platforms.length
        });
    } catch (error) {
        console.error('❌ Error fetching platforms:', error);
        res.status(500).json({
            success: false,
            message: 'Failed to fetch platforms',
            error: error.message
        });
    }
});

// API endpoint to get available genres by region
app.get('/api/genres/:country', async (req, res) => {
    try {
        const { country } = req.params;
        console.log(`🎭 Fetching genres for country: ${country}`);

        // Use the exact genre data for the system - Updated to match StreamGank
        const availableGenres = {
            FR: [
                'Action & Aventure',
                'Animation',
                'Comédie',
                'Comédie Romantique',
                'Crime & Thriller',
                'Documentaire',
                'Drame',
                'Fantastique',
                'Film de guerre',
                'Histoire',
                'Horreur',
                'Musique & Comédie Musicale',
                'Mystère & Thriller',
                'Pour enfants',
                'Reality TV',
                'Réalisé en Europe',
                'Science-Fiction',
                'Sport & Fitness',
                'Western'
            ],
            US: [
                'Action & Adventure',
                'Animation',
                'Comedy',
                'Crime',
                'Documentary',
                'Drama',
                'Fantasy',
                'History',
                'Horror',
                'Kids & Family',
                'Made in Europe',
                'Music & Musical',
                'Mystery & Thriller',
                'Reality TV',
                'Romance',
                'Science-Fiction',
                'Sport',
                'War & Military',
                'Western'
            ]
        };

        const genres = availableGenres[country] || availableGenres['US'];

        console.log(`✅ Found ${genres.length} genres for ${country}:`, genres);

        res.json({
            success: true,
            country: country,
            genres: genres,
            source: 'user_defined',
            count: genres.length
        });
    } catch (error) {
        console.error('❌ Error fetching genres:', error);
        res.status(500).json({
            success: false,
            message: 'Failed to fetch genres',
            error: error.message
        });
    }
});

// API endpoint to validate StreamGank URL
app.post('/api/validate-url', async (req, res) => {
    try {
        const { url } = req.body;

        if (!url) {
            return res.status(400).json({
                success: false,
                message: 'URL is required'
            });
        }

        console.log(`🔍 Validating URL: ${url}`);

        // Use node's built-in fetch or a library like axios to check the URL
        const https = require('https');
        const http = require('http');
        const urlParsed = new URL(url);

        const client = urlParsed.protocol === 'https:' ? https : http;

        const validation = await new Promise((resolve, reject) => {
            const request = client.get(
                url,
                {
                    headers: {
                        'User-Agent':
                            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                    },
                    timeout: 10000
                },
                (response) => {
                    let data = '';

                    response.on('data', (chunk) => {
                        data += chunk;
                    });

                    response.on('end', () => {
                        // Simplified validation - check basic HTTP response success
                        console.log(`🔍 Simplified validation for: ${url} - Status Code: ${response.statusCode}`);

                        // Log first 200 characters of content for debugging
                        console.log(`📄 First 200 chars of page content: ${data.substring(0, 200)}`);

                        // Always return valid=true since no movies validation is removed
                        resolve({
                            valid: true,
                            reason: 'URL validation passed - no movies check removed',
                            details: `Page loaded successfully with ${data.length} bytes of content`
                        });
                    });
                }
            );

            request.on('error', (error) => {
                console.error('Validation request error:', error);
                reject(error);
            });

            request.on('timeout', () => {
                request.destroy();
                reject(new Error('Request timeout'));
            });
        });

        console.log(`✅ Validation result: ${validation.valid ? 'Valid' : 'Invalid'} - ${validation.reason}`);

        res.json({
            success: true,
            ...validation
        });
    } catch (error) {
        console.error('❌ Error validating URL:', error);

        // If validation fails, return valid=true to continue (fail-safe approach)
        res.json({
            success: true,
            valid: true,
            reason: 'Validation failed, proceeding anyway',
            details: `Validation error: ${error.message}`
        });
    }
});

// Catch-all route for any other client-side routes
// This MUST come AFTER all API routes but BEFORE error handlers
app.get('*', (req, res) => {
    // Only serve index.html for routes that don't start with /api
    if (!req.path.startsWith('/api')) {
        res.sendFile(path.join(__dirname, 'dist', 'index.html'));
    } else {
        // API route not found
        res.status(404).json({
            success: false,
            error: 'API endpoint not found'
        });
    }
});

// Initialize Redis connection and start server
async function startServer() {
    try {
        // Connect to Redis
        await queueManager.connect();
        console.log('🔗 Redis queue manager connected');

        // Start the server
        app.listen(port, '0.0.0.0', () => {
            console.log(`🚀 StreamGank Video Generator GUI server running at http://0.0.0.0:${port}`);
            console.log(`📋 Redis queue system active`);
            console.log(`🗂️ Platform mappings loaded: ${Object.keys(platformMapping).length} platforms`);
            console.log(`📝 Content type mappings: ${Object.keys(contentTypeMapping).join(', ')}`);
        });
    } catch (error) {
        console.error('❌ Failed to start server:', error);
        process.exit(1);
    }
}

// Handle graceful shutdown
process.on('SIGINT', async () => {
    console.log('\n🛑 Shutting down server...');
    await queueManager.close();
    process.exit(0);
});

process.on('SIGTERM', async () => {
    console.log('\n🛑 Shutting down server...');
    await queueManager.close();
    process.exit(0);
});

// Start the server
startServer();
