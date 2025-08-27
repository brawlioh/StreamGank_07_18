const express = require('express');
const { spawn } = require('child_process');
const path = require('path');
const VideoQueueManager = require('./queue-manager');
const WebhookManager = require('./webhook-manager');
const { getFileLogger } = require('./utils/file_logger');

// Enhanced in-memory cache to reduce Redis calls during heavy processing - PRODUCTION OPTIMIZED
const jobCache = new Map();
const statusCache = new Map(); // Cache for queue status to prevent Redis overload
const CACHE_TTL = 60000; // 60 seconds cache for jobs (increased from 45s)
const STATUS_CACHE_TTL = 45000; // 45 seconds cache for queue status (increased from 30s)

// PRODUCTION OPTIMIZATION: Different cache TTLs based on job status
const getCacheTTL = (job) => {
    if (!job) return CACHE_TTL;

    // Completed/failed jobs rarely change - cache longer
    if (['completed', 'failed', 'cancelled'].includes(job.status)) {
        return 300000; // 5 minutes for finished jobs
    }

    // Active/pending jobs change frequently - shorter cache
    return 30000; // 30 seconds for active jobs
};

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

// Initialize file logger for persistent logging
const fileLogger = getFileLogger();

// Initialize job-specific SSE clients tracking
global.jobSSEClients = new Map(); // Map<job_id, Set<response_objects>>

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
    'Prime Video': 'Prime',
    apple: 'Apple TV+',
    'Apple TV+': 'Apple TV+',
    disney: 'Disney+',
    'Disney+': 'Disney+',
    hulu: 'Hulu',
    Hulu: 'Hulu',
    max: 'Max',
    Max: 'Max',
    netflix: 'Netflix',
    Netflix: 'Netflix', // Handle capitalized Netflix from frontend
    free: 'Free',
    Free: 'Free'
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

// Direct Creatomate API status check (no main.py dependency)
async function checkCreatomateStatus(renderId) {
    const apiKey = process.env.CREATOMATE_API_KEY;
    if (!apiKey) {
        return { success: false, error: 'Missing CREATOMATE_API_KEY environment variable' };
    }

    try {
        const axios = require('axios');
        const response = await axios.get(`https://api.creatomate.com/v1/renders/${renderId}`, {
            headers: {
                Authorization: `Bearer ${apiKey}`,
                'Content-Type': 'application/json'
            },
            timeout: 30000
        });

        if (response.status === 200) {
            const result = response.data;
            const status = result.status || 'unknown';
            const url = result.url || '';

            console.log(`✅ Creatomate render ${renderId} status: ${status}`);
            if (url && status === 'completed') {
                console.log(`🎬 Video ready at: ${url}`);
            }

            return {
                success: true,
                status: status,
                url: url,
                data: result
            };
        } else {
            console.error(`❌ Creatomate API error: ${response.status} - ${response.statusText}`);
            return {
                success: false,
                error: `HTTP ${response.status}: ${response.statusText}`
            };
        }
    } catch (error) {
        console.error(`❌ Error checking Creatomate status: ${error.message}`);
        return {
            success: false,
            error: error.message
        };
    }
}

// API endpoint to check Creatomate status (OPTIMIZED - no main.py call)
app.get('/api/status/:creatomateId', async (req, res) => {
    try {
        const { creatomateId } = req.params;
        console.log(`🎬 Direct Creatomate API check for: ${creatomateId}`);

        // Direct API call - no main.py execution needed
        const statusResult = await checkCreatomateStatus(creatomateId);

        if (statusResult.success) {
            // 🎯 FIX: Update job records when Creatomate video is ready
            if (statusResult.status === 'succeeded' && statusResult.url) {
                console.log(`✅ Creatomate render ${creatomateId} succeeded - updating job records...`);
                try {
                    const allJobs = await queueManager.getAllJobs();
                    const jobsToUpdate = allJobs.filter((job) => job.creatomateId === creatomateId);
                    console.log(`📋 Found ${jobsToUpdate.length} jobs to update with video URL`);

                    for (const job of jobsToUpdate) {
                        if (job.status === 'rendering' || (job.status === 'completed' && !job.videoUrl)) {
                            console.log(`📝 Updating job ${job.id} status to completed`);
                            job.status = 'completed';
                            job.progress = 100;
                            job.videoUrl = statusResult.url;
                            job.currentStep = '✅ Video creation completed';
                            job.completedAt = new Date().toISOString();
                            await queueManager.updateJob(job); // Persist to Redis
                            console.log(`✅ Job ${job.id} updated with video URL: ${statusResult.url}`);
                        }
                    }
                } catch (updateError) {
                    console.error('❌ Error updating job records:', updateError);
                }
            }

            res.json({
                success: true,
                creatomateId,
                status: statusResult.status,
                videoUrl: statusResult.url,
                data: statusResult.data,
                source: 'direct_api' // Indicate this bypassed main.py
            });
        } else {
            res.status(500).json({
                success: false,
                message: 'Failed to check Creatomate status',
                error: statusResult.error,
                creatomateId
            });
        }
    } catch (error) {
        console.error('❌ Failed to check Creatomate status:', error);
        res.status(500).json({
            success: false,
            message: 'Failed to check Creatomate status',
            error: error.message,
            creatomateId: req.params.creatomateId
        });
    }
});

// DISABLED: Test endpoint removed to reduce main.py load and improve performance
// Only video generation should use main.py - all other functionality extracted to Node.js
app.get('/api/test', async (req, res) => {
    console.log('⚡ Test endpoint disabled for performance - main.py reserved for video generation only');

    res.json({
        success: true,
        message: 'Test endpoint disabled for performance optimization',
        info: 'main.py is now reserved exclusively for video generation. Status checks use direct API calls.',
        performance: {
            optimization: 'Eliminated unnecessary main.py calls',
            benefit: 'Multiple users can generate videos simultaneously without interference',
            status_check: 'Direct Creatomate API integration (no Python process)',
            video_generation: 'Dedicated main.py processes per user'
        }
    });
});

// API endpoint to get job status by ID - PRODUCTION OPTIMIZED with smart caching
app.get('/api/job/:jobId', async (req, res) => {
    const startTime = Date.now();
    try {
        const { jobId } = req.params;

        // Check cache first with smart TTL based on job status
        const cacheKey = `job_${jobId}`;
        const cachedData = jobCache.get(cacheKey);

        if (cachedData) {
            const age = Date.now() - cachedData.timestamp;
            const cacheTTL = getCacheTTL(cachedData.job);

            if (age < cacheTTL) {
                const duration = Date.now() - startTime;
                console.log(`📋 Job ${jobId.slice(-8)} served from cache (age: ${age}ms, TTL: ${cacheTTL}ms)`);
                return res.json({
                    success: true,
                    job: cachedData.job,
                    _debug: {
                        duration: `${duration}ms`,
                        cached: true,
                        cacheAge: `${age}ms`,
                        cacheTTL: `${cacheTTL}ms`
                    }
                });
            }
        }

        // PRODUCTION: Shorter timeout to fail fast and use cache fallback
        const timeoutPromise = new Promise((_, reject) => {
            setTimeout(() => reject(new Error('Redis request timeout')), 2000); // 2 second timeout
        });

        const jobPromise = queueManager.getJob(jobId);
        const job = await Promise.race([jobPromise, timeoutPromise]);

        const duration = Date.now() - startTime;

        // Log slow requests for production monitoring
        if (duration > 300) {
            console.warn(`⚠️ Slow job request for ${jobId.slice(-8)}: ${duration}ms`);
        }

        if (!job) {
            return res.status(404).json({
                success: false,
                message: 'Job not found'
            });
        }

        // Cache the result with smart TTL
        jobCache.set(cacheKey, {
            job: job,
            timestamp: Date.now()
        });

        // PRODUCTION: More aggressive cache cleaning to prevent memory bloat
        if (jobCache.size > 500) {
            const now = Date.now();
            let cleanedCount = 0;
            for (const [key, value] of jobCache) {
                const maxAge = getCacheTTL(value.job) * 2; // Clean entries older than 2x their TTL
                if (now - value.timestamp > maxAge) {
                    jobCache.delete(key);
                    cleanedCount++;
                }
            }
            if (cleanedCount > 0) {
                console.log(`🧹 Cleaned ${cleanedCount} expired job cache entries (${jobCache.size} remaining)`);
            }
        }

        res.json({
            success: true,
            job: job,
            _debug: {
                duration: `${duration}ms`,
                cached: false,
                cacheSize: jobCache.size
            }
        });
    } catch (error) {
        const duration = Date.now() - startTime;

        // PRODUCTION: Return cached data during Redis failures to maintain user experience
        if (error.message.includes('timeout') || error.message.includes('Redis')) {
            console.error(`🚨 Redis error for job ${req.params.jobId.slice(-8)}: ${error.message} (${duration}ms)`);

            const cacheKey = `job_${req.params.jobId}`;
            const cachedData = jobCache.get(cacheKey);
            if (cachedData) {
                const age = Date.now() - cachedData.timestamp;
                console.log(
                    `📋 Using stale cache for ${req.params.jobId.slice(-8)} due to Redis error (age: ${age}ms)`
                );
                return res.json({
                    success: true,
                    job: cachedData.job,
                    _debug: {
                        duration: `${duration}ms`,
                        cached: true,
                        stale: true,
                        cacheAge: `${age}ms`,
                        fallback: 'redis_error'
                    }
                });
            }
        }

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
        // 📡 HANDLE INTERNAL PYTHON WORKFLOW WEBHOOKS ONLY
        const { job_id, step_number, step_name, status, duration, details, timestamp } = req.body;

        console.log(`📡 Real-time webhook: Job ${job_id} - Step ${step_number} (${step_name}) ${status}`);

        // Log only essential webhook events to reduce spam
        if (step_number >= 1 && step_number <= 7) {
            fileLogger.logWebhookReceived(job_id, step_number, step_name, status, details);
        }

        // Update job with step progress
        const job = await queueManager.getJob(job_id);
        if (job) {
            // Handle special cases for workflow start/completion
            if (step_number === 0 && step_name === 'Workflow Started') {
                job.currentStep = '🚀 Workflow started - processing movies...';
                job.progress = 5;
            } else if (step_number === 8 && step_name === 'Workflow Completed') {
                job.currentStep = '🎉 All steps completed - starting video rendering...';
                job.progress = 95;
                job.status = 'rendering'; // Set to rendering status for Creatomate monitoring
                if (details?.creatomate_id) {
                    job.creatomateId = details.creatomate_id;

                    // 🎬 CRITICAL FIX: Start Creatomate monitoring immediately after workflow completion
                    console.log(`🎬 Workflow completed with Creatomate ID: ${details.creatomate_id}`);
                    console.log(`🎬 Starting Creatomate monitoring for job ${job_id}...`);

                    // Start monitoring in the next tick to ensure job is updated first
                    setTimeout(() => {
                        queueManager.startCreatomateMonitoring(job_id, details.creatomate_id);
                    }, 100);
                }
            } else if (step_name === 'Workflow Failed') {
                job.currentStep = `❌ Workflow failed: ${details?.error || 'Unknown error'}`;
                job.status = 'failed';
                job.error = details?.error || 'Workflow failed';
            } else {
                // Normal step progression (1-7)
                job.currentStep = `${step_name} - ${status}`;
                if (step_number <= 7) {
                    job.progress = Math.max(job.progress || 0, Math.round((step_number / 7) * 90)); // Max 90% until video ready
                }
            }

            job.lastUpdate = new Date().toISOString();

            // Add step details and duration
            if (details) {
                job.stepDetails = { ...job.stepDetails, [`step_${step_number}`]: details };
            }
            if (duration) {
                job.stepDuration = { ...job.stepDuration, [`step_${step_number}`]: duration };
            }

            await queueManager.updateJob(job);

            // Clear job cache to force fresh data on next request
            if (jobCache.has(job_id)) {
                jobCache.delete(job_id);
            }

            console.log(`✅ Real-time update: Job ${job_id} - ${job.progress}% - ${job.currentStep}`);

            // Add essential real-time log entries only
            if (step_number >= 1 && step_number <= 7 && status === 'completed') {
                queueManager.addJobLog(job_id, `✅ Step ${step_number}/7 completed: ${step_name}`, 'success');
            }

            // REAL-TIME FRONTEND UPDATE: Send job update to connected SSE clients
            if (global.jobSSEClients && global.jobSSEClients.has(job_id)) {
                const sseClients = global.jobSSEClients.get(job_id);
                const updateData = {
                    type: 'step_update',
                    job_id: job_id,
                    step_number: step_number,
                    step_name: step_name,
                    status: status,
                    progress: job.progress,
                    currentStep: job.currentStep,
                    timestamp: new Date().toISOString()
                };

                sseClients.forEach((client) => {
                    try {
                        client.write(`data: ${JSON.stringify(updateData)}\n\n`);
                        console.log(`📡 Sent real-time update to job ${job_id} frontend client`);
                    } catch (error) {
                        console.warn(`⚠️ Failed to send SSE to job ${job_id} client:`, error.message);
                    }
                });
            }
        } else {
            console.warn(`⚠️ Webhook received for unknown job: ${job_id}`);
        }

        res.json({ success: true, message: 'Real-time step update processed' });
    } catch (error) {
        console.error('❌ Real-time webhook error:', error);
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

// ===== REMOVED: Separate Creatomate endpoint - now using unified webhook handler above =====

/**
 * SAFE: Original Creatomate webhook endpoint - FULLY FUNCTIONAL
 * Keeping original implementation to ensure no breaking changes
 */
app.post('/api/webhooks/creatomate-completion', async (req, res) => {
    try {
        const { id: render_id, status, url: video_url, error, data } = req.body;

        console.log(`🎬 Creatomate webhook received (legacy endpoint) - Render ID: ${render_id}, Status: ${status}`);

        if (!render_id) {
            return res.status(400).json({
                success: false,
                message: 'Render ID is required'
            });
        }

        // Find job by creatomateId
        const allJobs = await queueManager.getAllJobs();
        const job = allJobs.find((j) => j.creatomateId === render_id);

        if (!job) {
            console.warn(`⚠️ No job found for Creatomate render ID: ${render_id}`);
            return res.status(404).json({
                success: false,
                message: 'Job not found for render ID'
            });
        }

        console.log(`📋 Processing Creatomate webhook for job: ${job.id}`);

        // Handle successful completion
        if (status === 'completed' && video_url) {
            console.log(`✅ Creatomate render completed successfully: ${video_url}`);

            // Update job with final video URL
            job.status = 'completed';
            job.progress = 100;
            job.currentStep = '🎉 Video rendering completed successfully!';
            job.videoUrl = video_url;
            job.completedAt = new Date().toISOString();

            await queueManager.updateJob(job);
            await queueManager.addJobLog(job.id, `✅ Video rendered successfully: ${video_url}`, 'success');

            // Send real-time update to frontend
            if (global.jobSSEClients && global.jobSSEClients.has(job.id)) {
                const sseClients = global.jobSSEClients.get(job.id);
                const updateData = {
                    type: 'render_completed',
                    job_id: job.id,
                    status: 'completed',
                    progress: 100,
                    currentStep: job.currentStep,
                    videoUrl: video_url,
                    timestamp: new Date().toISOString()
                };

                sseClients.forEach((client) => {
                    try {
                        client.write(`data: ${JSON.stringify(updateData)}\n\n`);
                        console.log(`📡 Sent render completion update to job ${job.id} frontend client`);
                    } catch (error) {
                        console.warn(`⚠️ Failed to send SSE to job ${job.id} client:`, error.message);
                    }
                });
            }

            // Trigger webhook notifications to external services
            if (webhookManager) {
                await webhookManager.sendWebhookNotification('job.completed', {
                    job_id: job.id,
                    video_url: video_url,
                    parameters: job.parameters,
                    duration: job.duration,
                    completed_at: job.completedAt
                });
            }
        } else if (status === 'failed' || error) {
            console.error(`❌ Creatomate render failed: ${error || 'Unknown error'}`);

            // Update job with error status
            job.status = 'failed';
            job.currentStep = `❌ Video rendering failed: ${error || 'Unknown error'}`;
            job.error = error || 'Creatomate render failed';

            await queueManager.updateJob(job);
            await queueManager.addJobLog(job.id, `❌ Render failed: ${error || 'Unknown error'}`, 'error');

            // Send real-time update to frontend
            if (global.jobSSEClients && global.jobSSEClients.has(job.id)) {
                const sseClients = global.jobSSEClients.get(job.id);
                const updateData = {
                    type: 'render_failed',
                    job_id: job.id,
                    status: 'failed',
                    currentStep: job.currentStep,
                    error: job.error,
                    timestamp: new Date().toISOString()
                };

                sseClients.forEach((client) => {
                    try {
                        client.write(`data: ${JSON.stringify(updateData)}\n\n`);
                        console.log(`📡 Sent render failure update to job ${job.id} frontend client`);
                    } catch (error) {
                        console.warn(`⚠️ Failed to send SSE to job ${job.id} client:`, error.message);
                    }
                });
            }

            // Trigger webhook notifications to external services
            if (webhookManager) {
                await webhookManager.sendWebhookNotification('job.failed', {
                    job_id: job.id,
                    error: job.error,
                    parameters: job.parameters
                });
            }
        } else {
            // Handle in-progress status updates
            console.log(`📊 Creatomate render in progress: ${status}`);

            job.currentStep = `🎬 Rendering video: ${status}...`;

            // Update progress based on status
            if (status === 'queued') {
                job.progress = 85;
            } else if (status === 'rendering') {
                job.progress = 90;
            } else if (status === 'processing') {
                job.progress = 95;
            }

            await queueManager.updateJob(job);
            await queueManager.addJobLog(job.id, `⏳ Render status: ${status}`, 'info');
        }

        res.json({
            success: true,
            message: 'Creatomate webhook processed successfully',
            job_id: job.id,
            status: job.status
        });
    } catch (error) {
        console.error('❌ Creatomate webhook processing error:', error);
        res.status(500).json({
            success: false,
            message: 'Failed to process Creatomate webhook',
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

// API endpoint to cancel a job (DELETE method for frontend compatibility)
app.delete('/api/queue/job/:jobId', async (req, res) => {
    try {
        const { jobId } = req.params;
        console.log(`🛑 Cancelling job via DELETE: ${jobId}`);

        // Use the queue manager's cancelJob method which handles process killing
        const job = await queueManager.cancelJob(jobId);

        res.json({
            success: true,
            message: 'Job cancelled successfully',
            job: job
        });
    } catch (error) {
        console.error('❌ Failed to cancel job via DELETE:', error);
        res.status(500).json({
            success: false,
            message: 'Failed to cancel job',
            error: error.message
        });
    }
});

// API endpoint to get real-time logs for a specific job
app.get('/api/queue/job/:jobId/logs', async (req, res) => {
    try {
        const { jobId } = req.params;
        console.log(`📋 API: Getting logs for job ${jobId}`);

        // Get real logs from the queue manager
        const logs = queueManager.getJobLogs(jobId);

        res.json({
            success: true,
            data: {
                jobId: jobId,
                logs: logs,
                count: logs.length,
                lastUpdate: new Date().toISOString()
            }
        });
    } catch (error) {
        console.error('❌ Error getting job logs:', error);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

// API endpoint to get persistent file-based logs for a specific job
app.get('/api/queue/job/:jobId/logs/persistent', async (req, res) => {
    try {
        const { jobId } = req.params;
        const { limit = 1000 } = req.query;

        console.log(`📋 API: Getting persistent logs for job ${jobId}`);

        // Get persistent logs from file logger
        const logs = await fileLogger.readJobLogs(jobId, parseInt(limit));

        res.json({
            success: true,
            data: {
                jobId: jobId,
                logs: logs,
                count: logs.length,
                source: 'file_logger',
                lastUpdate: new Date().toISOString()
            }
        });
    } catch (error) {
        console.error('❌ Error getting persistent job logs:', error);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

// API endpoint to search logs across all jobs
app.get('/api/logs/search', async (req, res) => {
    try {
        const { jobId, eventType, level, messageContains, limit = 100 } = req.query;

        console.log(`🔍 API: Searching logs with filters:`, { jobId, eventType, level, messageContains, limit });

        const logs = await fileLogger.searchLogs({
            jobId,
            eventType,
            level,
            messageContains,
            limit: parseInt(limit)
        });

        res.json({
            success: true,
            data: {
                logs: logs,
                count: logs.length,
                filters: { jobId, eventType, level, messageContains, limit },
                searchTime: new Date().toISOString()
            }
        });
    } catch (error) {
        console.error('❌ Error searching logs:', error);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

// API endpoint to get logging system statistics
app.get('/api/logs/stats', async (req, res) => {
    try {
        console.log('📊 API: Getting logging system statistics');

        const stats = await fileLogger.getLogStats();

        res.json({
            success: true,
            data: {
                ...stats,
                timestamp: new Date().toISOString()
            }
        });
    } catch (error) {
        console.error('❌ Error getting log stats:', error);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

// API endpoint to archive job logs
app.post('/api/queue/job/:jobId/logs/archive', async (req, res) => {
    try {
        const { jobId } = req.params;

        console.log(`📦 API: Archiving logs for job ${jobId}`);

        const success = await fileLogger.archiveJobLogs(jobId);

        if (success) {
            res.json({
                success: true,
                message: `Logs for job ${jobId} archived successfully`,
                jobId: jobId,
                timestamp: new Date().toISOString()
            });
        } else {
            res.status(500).json({
                success: false,
                message: `Failed to archive logs for job ${jobId}`,
                jobId: jobId
            });
        }
    } catch (error) {
        console.error(`❌ Error archiving logs for job ${req.params.jobId}:`, error);
        res.status(500).json({
            success: false,
            error: error.message,
            jobId: req.params.jobId
        });
    }
});

// SSE endpoint for job-specific real-time updates
app.get('/api/job/:jobId/stream', (req, res) => {
    const { jobId } = req.params;

    console.log(`📡 SSE: Job ${jobId} client connected for real-time updates`);

    // Set SSE headers
    res.writeHead(200, {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        Connection: 'keep-alive',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Cache-Control'
    });

    // Initialize job SSE clients set if not exists
    if (!global.jobSSEClients.has(jobId)) {
        global.jobSSEClients.set(jobId, new Set());
    }

    // Add this client to the job's SSE clients
    const jobClients = global.jobSSEClients.get(jobId);
    jobClients.add(res);

    // Send initial connection confirmation
    res.write(
        `data: ${JSON.stringify({
            type: 'connected',
            job_id: jobId,
            message: 'Real-time job updates connected',
            timestamp: new Date().toISOString()
        })}\n\n`
    );

    // Heartbeat to keep connection alive
    const heartbeat = setInterval(() => {
        try {
            res.write(
                `data: ${JSON.stringify({
                    type: 'heartbeat',
                    job_id: jobId,
                    timestamp: new Date().toISOString()
                })}\n\n`
            );
        } catch (error) {
            clearInterval(heartbeat);
        }
    }, 30000); // Every 30 seconds

    // Clean up when client disconnects
    req.on('close', () => {
        console.log(`📡 SSE: Job ${jobId} client disconnected`);
        clearInterval(heartbeat);

        // Remove client from job clients set
        if (global.jobSSEClients.has(jobId)) {
            const jobClients = global.jobSSEClients.get(jobId);
            jobClients.delete(res);

            // Clean up empty job client sets
            if (jobClients.size === 0) {
                global.jobSSEClients.delete(jobId);
                console.log(`📡 SSE: Removed empty client set for job ${jobId}`);
            }
        }
    });

    req.on('error', (error) => {
        console.warn(`⚠️ SSE client error for job ${jobId}:`, error.message);
        clearInterval(heartbeat);
    });
});

// API endpoint to manually trigger Creatomate monitoring for a job
app.post('/api/queue/job/:jobId/monitor-creatomate', async (req, res) => {
    try {
        const { jobId } = req.params;
        console.log(`🎬 Manual Creatomate monitoring trigger for job: ${jobId}`);

        const job = await queueManager.getJob(jobId);
        if (!job) {
            return res.status(404).json({
                success: false,
                message: 'Job not found'
            });
        }

        if (!job.creatomateId) {
            return res.status(400).json({
                success: false,
                message: 'Job has no Creatomate ID'
            });
        }

        if (job.videoUrl) {
            return res.status(400).json({
                success: false,
                message: 'Job already has video URL'
            });
        }

        // Check if workflow was marked as incomplete
        if (job.workflowIncomplete) {
            return res.status(400).json({
                success: false,
                message: 'Job workflow was incomplete - manual verification needed before monitoring',
                details:
                    'The Python workflow did not complete all 7 steps properly. Check logs and verify Creatomate render manually.'
            });
        }

        // Update job to rendering status if it's completed without video
        if (job.status === 'completed' && !job.videoUrl) {
            job.status = 'rendering';
            job.currentStep = 'Video rendering in progress with Creatomate...';
            await queueManager.updateJob(job);
        }

        // Start monitoring
        queueManager.startCreatomateMonitoring(jobId, job.creatomateId);

        res.json({
            success: true,
            message: `Started Creatomate monitoring for job ${jobId}`,
            job: job,
            creatomateId: job.creatomateId
        });
    } catch (error) {
        console.error('❌ Failed to start Creatomate monitoring:', error);
        res.status(500).json({
            success: false,
            message: 'Failed to start Creatomate monitoring',
            error: error.message
        });
    }
});

// API endpoint to permanently delete a completed or failed job
app.delete('/api/queue/job/:jobId/delete', async (req, res) => {
    try {
        const { jobId } = req.params;
        console.log(`🗑️ Permanently deleting job: ${jobId}`);

        // Get the job first to check its status
        const job = await queueManager.getJob(jobId);

        if (!job) {
            return res.status(404).json({
                success: false,
                message: 'Job not found',
                error: 'Job does not exist'
            });
        }

        // Only allow deletion of completed, failed, or cancelled jobs
        if (!['completed', 'failed', 'cancelled'].includes(job.status)) {
            return res.status(400).json({
                success: false,
                message: 'Job cannot be deleted',
                error: `Cannot delete job with status: ${job.status}. Only completed, failed, or cancelled jobs can be deleted.`
            });
        }

        // Use the queue manager's deleteJob method (permanent removal)
        const result = await queueManager.deleteJob(jobId);

        res.json({
            success: true,
            message: `Job ${jobId.slice(-8)} deleted permanently`,
            job: job,
            deletedAt: new Date().toISOString()
        });
    } catch (error) {
        console.error('❌ Failed to delete job:', error);
        res.status(500).json({
            success: false,
            message: 'Failed to delete job',
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

        // Check for existing jobs needing Creatomate monitoring (after 5 seconds)
        setTimeout(() => {
            queueManager.checkExistingJobsForCreatomateMonitoring();
        }, 5000);

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
