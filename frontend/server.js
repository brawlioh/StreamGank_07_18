const express = require("express");
const { spawn } = require("child_process");
const path = require("path");
const VideoQueueManager = require("./queue-manager");
const WebhookManager = require("./webhook-manager");
const { getFileLogger } = require("./utils/file_logger");

// Enhanced in-memory cache to reduce Redis calls during heavy processing - PRODUCTION OPTIMIZED
const jobCache = new Map();
const statusCache = new Map(); // Cache for queue status to prevent Redis overload
const CACHE_TTL = 60000; // 60 seconds cache for jobs (increased from 45s)
const STATUS_CACHE_TTL = 45000; // 45 seconds cache for queue status (increased from 30s)

// PRODUCTION OPTIMIZATION: Different cache TTLs based on job status
const getCacheTTL = (job) => {
    if (!job) return CACHE_TTL;

    // Completed/failed jobs rarely change - cache longer
    if (["completed", "failed", "cancelled"].includes(job.status)) {
        return 300000; // 5 minutes for finished jobs
    }

    // Active/pending jobs change frequently - much shorter cache for real-time accuracy
    return 5000; // 5 seconds for active jobs (reduced from 30s for better sync)
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
app.use(express.urlencoded({ extended: true }));

// Configure proper MIME types for JavaScript modules
express.static.mime.define({ "application/javascript": ["js"] });

// Serve React app static files from dist with proper MIME types
app.use(
    express.static(path.join(__dirname, "dist"), {
        setHeaders: (res, path) => {
            if (path.endsWith(".js")) {
                res.setHeader("Content-Type", "application/javascript");
            }
        },
    })
);

// Production-level rate limiting middleware
const rateLimit = (req, res, next) => {
    const clientIp = req.ip || req.connection.remoteAddress || "unknown";
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
                    message: "Rate limit exceeded. Please slow down.",
                    retryAfter: Math.ceil((RATE_LIMIT_WINDOW - (now - clientData.windowStart)) / 1000),
                });
            }
        }
    } else {
        rateLimiter.set(clientIp, { windowStart: now, requestCount: 1 });
    }

    next();
};

// Apply rate limiting to API routes only
app.use("/api", rateLimit);

// Enable CORS with production settings
app.use((req, res, next) => {
    res.header("Access-Control-Allow-Origin", "*");
    res.header("Access-Control-Allow-Headers", "Origin, X-Requested-With, Content-Type, Accept");
    res.header("Cache-Control", "no-cache, no-store, must-revalidate"); // Prevent caching of API responses
    next();
});

// Route to serve the React app
app.get("/", (req, res) => {
    console.log("📄 Serving React app index.html");
    res.sendFile(path.join(__dirname, "dist", "index.html"));
});

// Health check endpoint for Docker
app.get("/health", (req, res) => {
    res.status(200).json({
        status: "healthy",
        timestamp: new Date().toISOString(),
        service: "streamgank-frontend",
        frontend: "React + Vite + Tailwind v4",
        backend: "Express + Redis + Python",
    });
});

// Job Detail Pages - Serve main SPA index.html for client-side routing (MUST come first)
app.get("/job/:jobId", (req, res) => {
    console.log(`📄 Serving index.html for job route: ${req.params.jobId}`);
    res.sendFile(path.join(__dirname, "dist", "index.html"));
});

// SPA Routing - Serve React app for all client-side routes
app.get(["/dashboard", "/queue"], (req, res) => {
    console.log(`📄 Serving React app for route: ${req.path}`);
    res.sendFile(path.join(__dirname, "dist", "index.html"));
});

// REMOVED: Catch-all route moved to end of file after all API routes

// Job detail API route (enhanced with more details)
app.get("/api/job/:jobId/details", async (req, res) => {
    try {
        const { jobId } = req.params;
        const job = await queueManager.getJob(jobId);

        if (!job) {
            return res.status(404).json({
                success: false,
                message: "Job not found",
            });
        }

        // Enhanced job details with additional metadata
        const enhancedJob = {
            ...job,
            duration: job.startedAt ? Date.now() - new Date(job.startedAt).getTime() : null,
            detailsUrl: `/job/${jobId}`,
            isActive: ["pending", "processing"].includes(job.status),
        };

        res.json({
            success: true,
            job: enhancedJob,
        });
    } catch (error) {
        console.error("❌ Failed to get job details:", error);
        res.status(500).json({
            success: false,
            message: "Failed to get job details",
            error: error.message,
        });
    }
});

// Job logs API route removed - logs no longer fetched for better performance

// Platform mapping to match frontend values to Python script expectations
const platformMapping = {
    amazon: "Prime",
    "Prime Video": "Prime",
    apple: "Apple TV+",
    "Apple TV+": "Apple TV+",
    disney: "Disney+",
    "Disney+": "Disney+",
    hulu: "Hulu",
    Hulu: "Hulu",
    max: "Max",
    Max: "Max",
    netflix: "Netflix",
    Netflix: "Netflix", // Handle capitalized Netflix from frontend
    free: "Free",
    Free: "Free",
};

// Content type mapping
const contentTypeMapping = {
    Film: "Film",
    Serie: "Série",
    all: "Film", // Default to Film for 'all' option
};

// Helper function to execute Python script with async/await
async function executePythonScript(args, cwd = path.join(__dirname, ".."), timeoutMs = 30 * 60 * 1000) {
    return new Promise((resolve, reject) => {
        // Executing command (same as CLI)

        const pythonProcess = spawn("python", args, {
            cwd: cwd,
            env: {
                ...process.env,
                PYTHONIOENCODING: "utf-8",
                PYTHONUNBUFFERED: "1",
            },
        });

        let stdout = "";
        let stderr = "";
        let isResolved = false;

        // Set up timeout (30 minutes default)
        const timeout = setTimeout(() => {
            if (!isResolved) {
                isResolved = true;
                pythonProcess.kill("SIGTERM");
                reject({
                    code: -2,
                    error: "Python script execution timeout",
                    stdout,
                    stderr,
                });
            }
        }, timeoutMs);

        // Handle stdout data
        pythonProcess.stdout.on("data", (data) => {
            try {
                const output = data.toString("utf8");
                stdout += output;
                // Output exactly like CLI - no prefixes
                process.stdout.write(output);
            } catch (encodingError) {
                console.warn("Encoding error in stdout:", encodingError.message);
                const output = data.toString("latin1"); // Fallback encoding
                stdout += output;
                process.stdout.write(output);
            }
        });

        // Handle stderr data
        pythonProcess.stderr.on("data", (data) => {
            try {
                const output = data.toString("utf8");
                stderr += output;
                // Output exactly like CLI - no prefixes
                process.stderr.write(output);
            } catch (encodingError) {
                console.warn("Encoding error in stderr:", encodingError.message);
                const output = data.toString("latin1"); // Fallback encoding
                stderr += output;
                process.stderr.write(output);
            }
        });

        // Handle process completion
        pythonProcess.on("close", (code) => {
            if (!isResolved) {
                isResolved = true;
                clearTimeout(timeout);
                // Process completed (code logged internally only if needed)

                if (code !== 0) {
                    reject({
                        code,
                        error: stderr || "Python script failed with no error message",
                        stdout,
                    });
                } else {
                    resolve({
                        code,
                        stdout,
                        stderr,
                    });
                }
            }
        });

        // Handle process errors
        pythonProcess.on("error", (error) => {
            if (!isResolved) {
                isResolved = true;
                clearTimeout(timeout);
                console.error("Failed to start Python process:", error);
                reject({
                    code: -1,
                    error: error.message,
                    stdout: "",
                    stderr: "",
                });
            }
        });
    });
}

// API endpoint to add video to Redis queue
app.post("/api/generate", async (req, res) => {
    try {
        const { country, platform, genre, contentType, template, pauseAfterExtraction } = req.body;

        console.log("📨 Received queue request:", {
            country,
            platform,
            genre,
            contentType,
            template,
            pauseAfterExtraction,
        });

        // Validate required parameters (contentType is optional for "All")
        if (!country || !platform || !genre) {
            return res.status(400).json({
                success: false,
                message: "Missing required parameters",
                received: { country, platform, genre, contentType, template },
            });
        }

        // Map platform and content type to match Python script expectations
        const mappedPlatform = platformMapping[platform] || platform;
        const mappedContentType = contentTypeMapping[contentType] || contentType;

        console.log("🔄 Mapped values:", {
            country,
            platform: mappedPlatform,
            genre,
            contentType: mappedContentType,
            template: template || "auto", // Default to 'auto' if not provided
            pauseAfterExtraction: pauseAfterExtraction || false,
        });

        // Add job to Redis queue
        const job = await queueManager.addJob({
            country,
            platform: mappedPlatform,
            genre,
            contentType: mappedContentType,
            template: template || "auto", // Include template parameter
            pauseAfterExtraction: pauseAfterExtraction || false, // Include pause flag
        });

        // Get current queue status
        const queueStatus = await queueManager.getQueueStatus();

        // Return job info and queue status
        res.json({
            success: true,
            jobId: job.id,
            message: "Video added to queue successfully",
            queuePosition: queueStatus.pending + queueStatus.processing,
            queueStatus: queueStatus,
            job: job,
        });
    } catch (error) {
        console.error("❌ Failed to add job to queue:", error);

        res.status(500).json({
            success: false,
            message: "Failed to add video to queue",
            error: error.message,
        });
    }
});

// Direct Creatomate API status check (no main.py dependency)
async function checkCreatomateStatus(renderId) {
    const apiKey = process.env.CREATOMATE_API_KEY;
    if (!apiKey) {
        return { success: false, error: "Missing CREATOMATE_API_KEY environment variable" };
    }

    try {
        const axios = require("axios");
        const response = await axios.get(`https://api.creatomate.com/v1/renders/${renderId}`, {
            headers: {
                Authorization: `Bearer ${apiKey}`,
                "Content-Type": "application/json",
            },
            timeout: 30000,
        });

        if (response.status === 200) {
            const result = response.data;
            const status = result.status || "unknown";
            const url = result.url || "";

            console.log(`✅ Creatomate render ${renderId} status: ${status}`);
            if (url && status === "completed") {
                console.log(`🎬 Video ready at: ${url}`);
            }

            return {
                success: true,
                status: status,
                url: url,
                data: result,
            };
        } else {
            console.error(`❌ Creatomate API error: ${response.status} - ${response.statusText}`);
            return {
                success: false,
                error: `HTTP ${response.status}: ${response.statusText}`,
            };
        }
    } catch (error) {
        console.error(`❌ Error checking Creatomate status: ${error.message}`);
        return {
            success: false,
            error: error.message,
        };
    }
}

// API endpoint to check Creatomate status (OPTIMIZED - no main.py call)
app.get("/api/status/:creatomateId", async (req, res) => {
    try {
        const { creatomateId } = req.params;
        console.log(`🎬 Direct Creatomate API check for: ${creatomateId}`);

        // Direct API call - no main.py execution needed
        const statusResult = await checkCreatomateStatus(creatomateId);

        if (statusResult.success) {
            // 🎯 FIX: Update job records when Creatomate video is ready
            if (statusResult.status === "succeeded" && statusResult.url) {
                console.log(`✅ Creatomate render ${creatomateId} succeeded - updating job records...`);
                try {
                    const allJobs = await queueManager.getAllJobs();
                    const jobsToUpdate = allJobs.filter((job) => job.creatomateId === creatomateId);
                    console.log(`📋 Found ${jobsToUpdate.length} jobs to update with video URL`);

                    for (const job of jobsToUpdate) {
                        if (job.status === "rendering" || (job.status === "completed" && !job.videoUrl)) {
                            console.log(`📝 Updating job ${job.id} status to completed`);
                            job.status = "completed";
                            job.progress = 100;
                            job.videoUrl = statusResult.url;
                            job.currentStep = "✅ Video creation completed";
                            job.completedAt = new Date().toISOString();
                            await queueManager.updateJobFast(job); // RAILWAY OPTIMIZATION: Use fast pipelined update
                            console.log(`✅ Job ${job.id} updated with video URL: ${statusResult.url}`);
                        }
                    }
                } catch (updateError) {
                    console.error("❌ Error updating job records:", updateError);
                }
            }

            res.json({
                success: true,
                creatomateId,
                status: statusResult.status,
                videoUrl: statusResult.url,
                data: statusResult.data,
                source: "direct_api", // Indicate this bypassed main.py
            });
        } else {
            res.status(500).json({
                success: false,
                message: "Failed to check Creatomate status",
                error: statusResult.error,
                creatomateId,
            });
        }
    } catch (error) {
        console.error("❌ Failed to check Creatomate status:", error);
        res.status(500).json({
            success: false,
            message: "Failed to check Creatomate status",
            error: error.message,
            creatomateId: req.params.creatomateId,
        });
    }
});

// DISABLED: Test endpoint removed to reduce main.py load and improve performance
// Only video generation should use main.py - all other functionality extracted to Node.js
app.get("/api/test", async (req, res) => {
    console.log("⚡ Test endpoint disabled for performance - main.py reserved for video generation only");

    res.json({
        success: true,
        message: "Test endpoint disabled for performance optimization",
        info: "main.py is now reserved exclusively for video generation. Status checks use direct API calls.",
        performance: {
            optimization: "Eliminated unnecessary main.py calls",
            benefit: "Multiple users can generate videos simultaneously without interference",
            status_check: "Direct Creatomate API integration (no Python process)",
            video_generation: "Dedicated main.py processes per user",
        },
    });
});

// API endpoint to get job status by ID - PRODUCTION OPTIMIZED with smart caching
app.get("/api/job/:jobId", async (req, res) => {
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
                        cacheTTL: `${cacheTTL}ms`,
                    },
                });
            }
        }

        // PRODUCTION: Shorter timeout to fail fast and use cache fallback
        const timeoutPromise = new Promise((_, reject) => {
            setTimeout(() => reject(new Error("Redis request timeout")), 10000); // Increased to 10s for Railway production
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
                message: "Job not found",
            });
        }

        // Cache the result with smart TTL
        jobCache.set(cacheKey, {
            job: job,
            timestamp: Date.now(),
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
                cacheSize: jobCache.size,
            },
        });
    } catch (error) {
        const duration = Date.now() - startTime;

        // PRODUCTION: Return cached data during Redis failures to maintain user experience
        if (error.message.includes("timeout") || error.message.includes("Redis")) {
            console.error(`🚨 Redis error for job ${req.params.jobId.slice(-8)}: ${error.message} (${duration}ms)`);

            const cacheKey = `job_${req.params.jobId}`;
            const cachedData = jobCache.get(cacheKey);
            if (cachedData) {
                const age = Date.now() - cachedData.timestamp;
                console.log(`📋 Using stale cache for ${req.params.jobId.slice(-8)} due to Redis error (age: ${age}ms)`);
                return res.json({
                    success: true,
                    job: cachedData.job,
                    _debug: {
                        duration: `${duration}ms`,
                        cached: true,
                        stale: true,
                        cacheAge: `${age}ms`,
                        fallback: "redis_error",
                    },
                });
            }
        }

        console.error(`❌ Failed to get job (${duration}ms):`, error.message);

        res.status(500).json({
            success: false,
            message: "Failed to get job status",
            error: error.message,
            _debug: {
                duration: `${duration}ms`,
            },
        });
    }
});

// API endpoint to get queue status - OPTIMIZED with aggressive caching during processing
app.get("/api/queue/status", async (req, res) => {
    const startTime = Date.now();
    try {
        // Check if we have cached status data
        const statusCacheKey = "queue_status";
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
                        cacheAge: `${Date.now() - cachedStatus.timestamp}ms`,
                    },
                },
            });
        }

        // PROFESSIONAL: Longer timeout since webhooks handle real-time updates
        const timeoutPromise = new Promise((_, reject) => {
            setTimeout(() => reject(new Error("Status request timeout")), 10000); // Increased to 10s for Railway
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
            timestamp: Date.now(),
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
                    processing: isProcessing,
                },
            },
        });
    } catch (error) {
        console.error("❌ Failed to get queue status:", error);

        // Fallback to cached data if available during errors
        const statusCacheKey = "queue_status";
        const cachedStatus = statusCache.get(statusCacheKey);
        if (cachedStatus) {
            console.log("📋 Using cached status data due to error");
            return res.json({
                success: true,
                stats: {
                    ...cachedStatus.stats,
                    _debug: {
                        duration: `${Date.now() - startTime}ms`,
                        cached: true,
                        fallback: true,
                    },
                },
            });
        }

        res.status(500).json({
            success: false,
            message: "Failed to get queue status",
            error: error.message,
        });
    }
});

// Server-Sent Events endpoint for real-time queue status updates - PRODUCTION OPTIMIZED
app.get("/api/queue/status/stream", (req, res) => {
    const clientIp = req.ip || req.connection.remoteAddress || "unknown";

    // Set up SSE headers
    res.writeHead(200, {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        Connection: "keep-alive",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Cache-Control",
    });

    const clientId = `${clientIp}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const client = {
        id: clientId,
        res: res,
        lastUpdate: Date.now(),
        ip: clientIp,
    };

    sseClients.add(client);
    console.log(`📡 SSE client connected: ${clientId} (${sseClients.size} total clients)`);

    // Send initial status
    sendStatusToClient(client);

    // Handle client disconnect
    req.on("close", () => {
        sseClients.delete(client);
        console.log(`📡 SSE client disconnected: ${clientId} (${sseClients.size} total clients)`);
    });

    // Keep connection alive
    const keepAlive = setInterval(() => {
        if (res.writable) {
            res.write("event: heartbeat\ndata: {}\n\n");
        } else {
            clearInterval(keepAlive);
            sseClients.delete(client);
        }
    }, 30000); // Heartbeat every 30 seconds

    req.on("close", () => {
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
            clientId: client.id,
        });

        if (client.res.writable) {
            client.res.write(`event: status\ndata: ${data}\n\n`);
            client.lastUpdate = Date.now();
        } else {
            sseClients.delete(client);
        }
    } catch (error) {
        console.error("❌ Failed to send status to SSE client:", error);
        if (client.res.writable) {
            const errorData = JSON.stringify({
                success: false,
                error: error.message,
                timestamp: Date.now(),
            });
            client.res.write(`event: error\ndata: ${errorData}\n\n`);
        }
    }
}

// Request deduplication wrapper for getQueueStats
async function getQueueStatsWithDeduplication() {
    const dedupeKey = "queue_stats";
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
        timestamp: now,
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
                    client.write(`data: ${JSON.stringify({ type: "heartbeat", timestamp: Date.now() })}\n\n`);
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
app.get("/api/webhooks/status", (req, res) => {
    try {
        const status = webhookManager.getWebhookStatus();
        res.json({
            success: true,
            webhooks: status,
            timestamp: new Date().toISOString(),
        });
    } catch (error) {
        console.error("❌ Failed to get webhook status:", error);
        res.status(500).json({
            success: false,
            message: "Failed to get webhook status",
            error: error.message,
        });
    }
});

// API endpoint to receive step completion webhooks from Python workflow
app.post("/api/webhooks/step-update", async (req, res) => {
    try {
        // 📡 HANDLE INTERNAL PYTHON WORKFLOW WEBHOOKS WITH STEP VALIDATION
        const { job_id, step_number, step_name, status, duration, details, timestamp, step_key, sequence, workflow_stage } = req.body;

        console.log(`📡 WEBHOOK RECEIVED: Job ${job_id} - Step ${step_number} (${step_name}) ${status}`);
        console.log(`📡 WEBHOOK PAYLOAD:`, JSON.stringify(req.body, null, 2));

        // Log only essential webhook events to reduce spam
        if (step_number >= 1 && step_number <= 7) {
            fileLogger.logWebhookReceived(job_id, step_number, step_name, status, details);
        }

        // Update job with step progress - WITH STEP VALIDATION
        const job = await queueManager.getJob(job_id);
        if (job) {
            // ✅ IMMEDIATE STATUS UPDATE: Update job status immediately on webhook receive
            console.log(`📊 Job ${job_id} current status: ${job.status} -> Processing webhook for step ${step_number}`);

            // ✅ STEP VALIDATION: Prevent out-of-order step updates
            const lastSequence = job.lastStepSequence || 0;
            const currentSequence = sequence || Date.now();

            if (currentSequence < lastSequence) {
                console.warn(`⚠️ REJECTED: Out-of-order step update for ${job_id}`);
                console.warn(`   Current sequence: ${currentSequence}, Last: ${lastSequence}`);
                console.warn(`   Step ${step_number} ${status} SKIPPED to prevent UI desync`);
                return res.json({
                    success: false,
                    message: "Out-of-order step update rejected",
                    reason: "sequence_validation_failed",
                });
            }

            // Update last sequence to prevent future out-of-order updates
            job.lastStepSequence = currentSequence;

            // ✅ STEP PROGRESSION VALIDATION: Ensure logical step progression
            const currentStepNum = job.currentStepNumber || 0;

            // Allow step progression or completion of current step
            if (status === "started" && step_number < currentStepNum) {
                console.warn(`⚠️ REJECTED: Backward step progression for ${job_id}`);
                console.warn(`   Trying to start step ${step_number}, but already on step ${currentStepNum}`);
                return res.json({
                    success: false,
                    message: "Backward step progression rejected",
                    reason: "step_progression_validation_failed",
                });
            }

            // Update current step number tracking
            if (status === "started") {
                job.currentStepNumber = step_number;
            }

            console.log(`✅ VALIDATED: Step ${step_number} ${status} (sequence: ${currentSequence})`);

            // Handle special cases for workflow start/completion
            if (step_number === 0 && step_name === "Workflow Started") {
                job.currentStep = "🚀 Workflow started - processing movies...";
                job.progress = 5;
            } else if (step_number === 8 && step_name === "Workflow Completed") {
                job.currentStep = "🎉 All steps completed - starting video rendering...";
                job.progress = 95;
                job.status = "rendering"; // Set to rendering status for Creatomate monitoring
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
            } else if (step_name === "Workflow Failed") {
                job.currentStep = `❌ Workflow failed: ${details?.error || "Unknown error"}`;
                job.status = "failed";
                job.error = details?.error || "Workflow failed";
            } else {
                // 🎬 CRITICAL FIX: Handle Step 7 (Creatomate Assembly) completion to immediately store creatomate_id
                if (step_number === 7 && (status === "completed" || status === "creatomate_ready") && details?.creatomate_id) {
                    console.log(`🎬 Step 7 ${status} with Creatomate ID: ${details.creatomate_id}`);
                    job.creatomateId = details.creatomate_id;

                    if (status === "creatomate_ready") {
                        job.currentStep = `🚀 Creatomate ID ready - starting video rendering...`;
                        job.status = "rendering"; // Immediately set to rendering status
                    } else {
                        job.currentStep = `${step_name} - ✅ Completed (ID: ${details.creatomate_id.substring(0, 8)}...)`;
                    }

                    // 🚀 IMMEDIATE UPDATE: Trigger Creatomate monitoring right after step 7 completes
                    console.log(`🚀 Starting immediate Creatomate monitoring for job ${job_id}...`);
                    setTimeout(() => {
                        queueManager.startCreatomateMonitoring(job_id, details.creatomate_id);
                    }, 100); // Faster trigger for creatomate_ready
                } else {
                    // Normal step progression display
                    job.currentStep = `${step_name} - ${status}`;
                }

                // Normal step progression (1-7) - UNIFIED progress calculation
                if (step_number <= 7) {
                    // Standardized progress: started = (step-1)/7 * 85, completed = step/7 * 85
                    // This matches frontend expectations and caps at 85% (leaving 15% for Creatomate)
                    if (status === "started") {
                        job.progress = Math.max(job.progress || 0, Math.round(((step_number - 1) / 7) * 85));
                    } else if (status === "completed") {
                        job.progress = Math.max(job.progress || 0, Math.round((step_number / 7) * 85));
                    }
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

            // RAILWAY OPTIMIZATION: Use fast pipelined job update
            await queueManager.updateJobFast(job);

            // CRITICAL FIX: Immediately clear job cache to ensure UI shows real-time updates
            // This prevents the UI from showing stale data while workflow progresses
            if (jobCache.has(job_id)) {
                jobCache.delete(job_id);
                console.log(`🗑️ Cleared job cache for ${job_id} to ensure real-time accuracy`);
            }

            // Also clear any related cache keys to prevent stale data
            const cacheKeysToClear = [
                `job_${job_id}`,
                `job_${job_id.slice(-8)}`, // Short job ID format
                `queue_status`, // Clear queue status cache too
            ];

            cacheKeysToClear.forEach((key) => {
                if (jobCache.has(key)) {
                    jobCache.delete(key);
                }
                if (statusCache.has(key)) {
                    statusCache.delete(key);
                }
            });

            console.log(`✅ Real-time update: Job ${job_id} - ${job.progress}% - ${job.currentStep}`);

            // 🚨 CRITICAL: Handle failure status immediately
            if (status === "failed" || (details && details.error)) {
                console.log(`🚨 FAILURE DETECTED: Setting job ${job_id} to failed status`);
                job.status = "failed";
                job.error = details?.error || "Workflow step failed";
                job.failedAt = new Date().toISOString();
                job.currentStep = `❌ Failed at ${step_name}`;

                // Update job in Redis immediately
                await queueManager.updateJob(job);

                // Move to failed queue
                await queueManager.lremAsync(queueManager.keys.processing, 1, JSON.stringify(job));
                await queueManager.rpushAsync(queueManager.keys.failed, JSON.stringify(job));

                console.log(`🗂️ Job ${job_id} moved to failed queue due to webhook failure notification`);
                queueManager.addJobLog(job_id, `❌ Step ${step_number}/7 failed: ${step_name} - ${details?.error || "Unknown error"}`, "error");
            } else {
                // Add essential real-time log entries only for successful steps
                if (step_number >= 1 && step_number <= 7 && status === "completed") {
                    queueManager.addJobLog(job_id, `✅ Step ${step_number}/7 completed: ${step_name}`, "success");
                }
            }

            // REAL-TIME FRONTEND UPDATE: Send job update to connected SSE clients
            console.log(`📡 Checking SSE clients for job ${job_id}...`);
            console.log(`📡 Global SSE clients map exists: ${!!global.jobSSEClients}`);
            console.log(`📡 Job ${job_id} has SSE clients: ${global.jobSSEClients ? global.jobSSEClients.has(job_id) : "no global map"}`);

            if (global.jobSSEClients && global.jobSSEClients.has(job_id)) {
                const sseClients = global.jobSSEClients.get(job_id);
                console.log(`📡 Found ${sseClients.size} SSE clients for job ${job_id}`);
                const updateData = {
                    type: "step_update",
                    job_id: job_id,
                    step_number: step_number,
                    step_name: step_name,
                    status: status,
                    progress: job.progress,
                    currentStep: job.currentStep,
                    timestamp: new Date().toISOString(),
                    // ✅ NEW: Step tracking for accuracy
                    step_key: step_key,
                    sequence: currentSequence,
                    workflow_stage: workflow_stage,
                    validated: true, // Indicates this update passed validation
                    // 🎬 CRITICAL: Include details in SSE update for immediate frontend access
                    details: details || {},
                    // 🚀 IMMEDIATE ACCESS: If step 7 completed, include creatomate_id directly
                    creatomate_id: step_number === 7 && status === "completed" ? details?.creatomate_id : undefined,
                    // 🚨 CRITICAL: Include failure information for immediate frontend updates
                    job_status: job.status,
                    error: job.error || null,
                    failed: job.status === "failed",
                    failedAt: job.failedAt || null,
                };

                console.log(`📡 SSE UPDATE DATA:`, JSON.stringify(updateData, null, 2));

                sseClients.forEach((client, index) => {
                    try {
                        client.write(`data: ${JSON.stringify(updateData)}\n\n`);
                        console.log(`📡 ✅ Sent SSE update to client ${index + 1}/${sseClients.size} for job ${job_id}`);
                    } catch (error) {
                        console.warn(`⚠️ Failed to send SSE to job ${job_id} client ${index + 1}:`, error.message);
                    }
                });
            } else {
                console.warn(`📡 ❌ No SSE clients found for job ${job_id} - UI won't update in real-time`);
                if (global.jobSSEClients) {
                    console.warn(`📡 Available job SSE clients: ${Array.from(global.jobSSEClients.keys()).join(", ")}`);
                }
            }
        } else {
            console.warn(`⚠️ Webhook received for unknown job: ${job_id}`);
        }

        res.json({ success: true, message: "Real-time step update processed" });
    } catch (error) {
        console.error("❌ Real-time webhook error:", error);
        res.status(500).json({ success: false, error: error.message });
    }
});

// Test webhook endpoint connectivity
app.post("/api/webhooks/test", async (req, res) => {
    try {
        const { url } = req.body;

        if (!url) {
            return res.status(400).json({
                success: false,
                message: "Webhook URL is required",
            });
        }

        console.log(`🧪 Testing webhook endpoint: ${url}`);
        const testResult = await webhookManager.validateWebhookEndpoint(url);

        res.json({
            success: true,
            test_result: testResult,
            timestamp: new Date().toISOString(),
        });
    } catch (error) {
        console.error("❌ Failed to test webhook endpoint:", error);
        res.status(500).json({
            success: false,
            message: "Failed to test webhook endpoint",
            error: error.message,
        });
    }
});

// ===== REMOVED: Separate Creatomate endpoint - now using unified webhook handler above =====

/**
 * SAFE: Original Creatomate webhook endpoint - FULLY FUNCTIONAL
 * Keeping original implementation to ensure no breaking changes
 */
app.post("/api/webhooks/creatomate", async (req, res) => {
    try {
        // Security: Log webhook source for debugging
        const clientIP = req.ip || req.connection.remoteAddress || req.headers["x-forwarded-for"];
        const userAgent = req.headers["user-agent"] || "Unknown";

        console.log(`🔐 Webhook received from IP: ${clientIP}, User-Agent: ${userAgent}`);

        const { id: render_id, status, url: video_url, error, data } = req.body;

        console.log(`🎬 Creatomate PROJECT-LEVEL webhook received - Render ID: ${render_id}, Status: ${status}`);

        // Security: Basic validation of webhook payload
        if (!render_id) {
            console.warn(`⚠️ Security: Invalid webhook - missing render_id from ${clientIP}`);
            return res.status(400).json({
                success: false,
                message: "Invalid webhook: missing render_id",
            });
        }

        if (!status) {
            console.warn(`⚠️ Security: Invalid webhook - missing status from ${clientIP}`);
            return res.status(400).json({
                success: false,
                message: "Invalid webhook: missing status",
            });
        }

        // Security: Log successful webhook reception
        console.log(`✅ Security: Valid webhook payload received from ${clientIP}`);

        // Note: Creatomate doesn't support custom webhook secrets/signatures
        // Current security relies on payload validation + HTTPS + server access control

        // Find job by creatomateId
        const allJobs = await queueManager.getAllJobs();
        const job = allJobs.find((j) => j.creatomateId === render_id);

        if (!job) {
            console.warn(`⚠️ No job found for Creatomate render ID: ${render_id}`);
            return res.status(404).json({
                success: false,
                message: "Job not found for render ID",
            });
        }

        console.log(`📋 Processing Creatomate webhook for job: ${job.id}`);

        // Handle successful completion - using exact Creatomate status from documentation
        if (status === "succeeded" && video_url) {
            console.log(`✅ Creatomate render succeeded: ${video_url}`);

            // Update job with final video URL and completion data
            job.status = "completed";
            job.progress = 100;
            job.currentStep = "✅ Video creation completed successfully!";
            job.videoUrl = video_url;
            job.completedAt = new Date().toISOString();

            await queueManager.updateJob(job);

            // Add persistent job logs for completed status
            await queueManager.addJobLog(job.id, `✅ Video rendered successfully`, "success");
            await queueManager.addJobLog(job.id, `🔗 Video URL: ${video_url}`, "success");
            await queueManager.addJobLog(job.id, `🎉 Job completed at: ${job.completedAt}`, "success");
            await queueManager.addJobLog(job.id, `📊 Final progress: 100%`, "success");

            // Send real-time update to frontend for video display
            if (global.jobSSEClients && global.jobSSEClients.has(job.id)) {
                const sseClients = global.jobSSEClients.get(job.id);
                const updateData = {
                    type: "render_completed",
                    job_id: job.id,
                    status: "completed",
                    progress: 100,
                    currentStep: job.currentStep,
                    videoUrl: video_url,
                    timestamp: job.completedAt,
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
                await webhookManager.sendWebhookNotification("job.completed", {
                    job_id: job.id,
                    video_url: video_url,
                    parameters: job.parameters,
                    duration: job.duration,
                    completed_at: job.completedAt,
                });
            }
        } else if (status === "failed") {
            // Handle failed renders - using exact Creatomate status from documentation
            console.error(`❌ Creatomate render failed: ${render_id} - ${error || "Unknown error"}`);

            // Update job with error status and completion timestamp
            job.status = "failed";
            job.currentStep = `❌ Video rendering failed: ${error || "Unknown error"}`;
            job.error = error || "Creatomate render failed";
            job.completedAt = new Date().toISOString();

            await queueManager.updateJob(job);

            // Add persistent job logs for failed status
            await queueManager.addJobLog(job.id, `❌ Render failed: ${error || "Unknown error"}`, "error");
            await queueManager.addJobLog(job.id, `⚠️ Failure time: ${job.completedAt}`, "error");
            await queueManager.addJobLog(job.id, `🔍 Render ID: ${render_id}`, "error");
            await queueManager.addJobLog(job.id, `📊 Progress at failure: ${job.progress || 0}%`, "error");

            // Send real-time update to frontend
            if (global.jobSSEClients && global.jobSSEClients.has(job.id)) {
                const sseClients = global.jobSSEClients.get(job.id);
                const updateData = {
                    type: "render_failed",
                    job_id: job.id,
                    status: "failed",
                    currentStep: job.currentStep,
                    error: job.error,
                    timestamp: job.completedAt,
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
                await webhookManager.sendWebhookNotification("job.failed", {
                    job_id: job.id,
                    error: job.error,
                    parameters: job.parameters,
                    failed_at: job.completedAt,
                });
            }
        } else if (status === "planned") {
            // Video planned/queued - using exact Creatomate status from documentation
            console.log(`📋 Creatomate render planned (queued): ${render_id}`);

            job.currentStep = "📋 Video queued for processing...";
            job.progress = 85;
            job.status = "rendering"; // Keep internal status as 'rendering'

            await queueManager.updateJob(job);
            await queueManager.addJobLog(job.id, "📋 Video queued for processing", "info");

            // Send real-time SSE update
            if (global.jobSSEClients && global.jobSSEClients.has(job.id)) {
                const sseClients = global.jobSSEClients.get(job.id);
                const updateData = {
                    type: "render_planned",
                    job_id: job.id,
                    status: "rendering",
                    progress: 85,
                    currentStep: job.currentStep,
                    timestamp: new Date().toISOString(),
                };
                sseClients.forEach((client) => {
                    try {
                        client.write(`data: ${JSON.stringify(updateData)}\n\n`);
                        console.log(`📡 Sent render planned update to job ${job.id} frontend client`);
                    } catch (error) {
                        console.warn(`⚠️ Failed to send SSE to job ${job.id} client:`, error.message);
                    }
                });
            }
        } else if (status === "waiting") {
            // Video waiting for third-party integration - using exact Creatomate status
            console.log(`⏳ Creatomate render waiting: ${render_id}`);

            job.currentStep = "⏳ Video is being rendered...";
            job.progress = 87;
            job.status = "rendering";

            await queueManager.updateJob(job);
            await queueManager.addJobLog(job.id, "⏳ Waiting for third-party integration", "info");

            // Send real-time SSE update
            if (global.jobSSEClients && global.jobSSEClients.has(job.id)) {
                const sseClients = global.jobSSEClients.get(job.id);
                const updateData = {
                    type: "render_waiting",
                    job_id: job.id,
                    status: "rendering",
                    progress: 87,
                    currentStep: job.currentStep,
                    timestamp: new Date().toISOString(),
                };
                sseClients.forEach((client) => {
                    try {
                        client.write(`data: ${JSON.stringify(updateData)}\n\n`);
                        console.log(`📡 Sent render waiting update to job ${job.id} frontend client`);
                    } catch (error) {
                        console.warn(`⚠️ Failed to send SSE to job ${job.id} client:`, error.message);
                    }
                });
            }
        } else if (status === "transcribing") {
            // Video transcribing (generating subtitles) - using exact Creatomate status
            console.log(`💬 Creatomate render transcribing: ${render_id}`);

            job.currentStep = "💬 Video is being rendered...";
            job.progress = 88;
            job.status = "rendering";

            await queueManager.updateJob(job);
            await queueManager.addJobLog(job.id, "💬 Generating subtitles", "info");

            // Send real-time SSE update
            if (global.jobSSEClients && global.jobSSEClients.has(job.id)) {
                const sseClients = global.jobSSEClients.get(job.id);
                const updateData = {
                    type: "render_transcribing",
                    job_id: job.id,
                    status: "rendering",
                    progress: 88,
                    currentStep: job.currentStep,
                    timestamp: new Date().toISOString(),
                };
                sseClients.forEach((client) => {
                    try {
                        client.write(`data: ${JSON.stringify(updateData)}\n\n`);
                        console.log(`📡 Sent render transcribing update to job ${job.id} frontend client`);
                    } catch (error) {
                        console.warn(`⚠️ Failed to send SSE to job ${job.id} client:`, error.message);
                    }
                });
            }
        } else if (status === "rendering") {
            // Video actively rendering - using exact Creatomate status from documentation
            console.log(`🎬 Creatomate actively rendering: ${render_id}`);

            job.currentStep = "🎬 Video is being rendered...";
            job.progress = 90;
            job.status = "rendering";

            await queueManager.updateJob(job);
            await queueManager.addJobLog(job.id, "🎬 Video is currently being generated", "info");

            // Send real-time SSE update
            if (global.jobSSEClients && global.jobSSEClients.has(job.id)) {
                const sseClients = global.jobSSEClients.get(job.id);
                const updateData = {
                    type: "render_rendering",
                    job_id: job.id,
                    status: "rendering",
                    progress: 90,
                    currentStep: job.currentStep,
                    timestamp: new Date().toISOString(),
                };
                sseClients.forEach((client) => {
                    try {
                        client.write(`data: ${JSON.stringify(updateData)}\n\n`);
                        console.log(`📡 Sent rendering progress update to job ${job.id} frontend client`);
                    } catch (error) {
                        console.warn(`⚠️ Failed to send SSE to job ${job.id} client:`, error.message);
                    }
                });
            }
        } else {
            // Handle any other status updates (project-level webhook)
            console.log(`📊 Creatomate status update: ${status} for ${render_id}`);

            job.currentStep = `🎬 Video status: ${status}...`;

            // Set generic progress if not already set
            if (!job.progress || job.progress < 85) {
                job.progress = 88;
            }

            await queueManager.updateJob(job);
            await queueManager.addJobLog(job.id, `⏳ Render status: ${status}`, "info");
        }

        res.json({
            success: true,
            message: "Creatomate webhook processed successfully",
            job_id: job.id,
            status: job.status,
        });
    } catch (error) {
        console.error("❌ Creatomate webhook processing error:", error);
        res.status(500).json({
            success: false,
            message: "Failed to process Creatomate webhook",
            error: error.message,
        });
    }
});

// Manual webhook trigger (for testing purposes)
app.post("/api/webhooks/trigger", async (req, res) => {
    try {
        const { event, data } = req.body;

        if (!event) {
            return res.status(400).json({
                success: false,
                message: "Event name is required",
            });
        }

        const testData = data || {
            message: "Manual webhook test trigger",
            timestamp: new Date().toISOString(),
            manual: true,
        };

        console.log(`🔗 Manually triggering webhook event: ${event}`);
        const results = await webhookManager.sendWebhookNotification(event, testData);

        const successful = results.filter((r) => r.status === "fulfilled").length;
        const failed = results.filter((r) => r.status === "rejected").length;

        res.json({
            success: true,
            message: `Webhook notifications sent`,
            results: {
                total: results.length,
                successful,
                failed,
            },
            timestamp: new Date().toISOString(),
        });
    } catch (error) {
        console.error("❌ Failed to trigger webhook:", error);
        res.status(500).json({
            success: false,
            message: "Failed to trigger webhook",
            error: error.message,
        });
    }
});

// API endpoint to get all jobs
app.get("/api/queue/jobs", async (req, res) => {
    try {
        const jobs = await queueManager.getAllJobs();
        res.json({
            success: true,
            jobs: jobs,
        });
    } catch (error) {
        console.error("❌ Failed to get all jobs:", error);
        res.status(500).json({
            success: false,
            message: "Failed to get jobs",
            error: error.message,
        });
    }
});

// API endpoint to clear queue (admin only)
app.post("/api/queue/clear", async (req, res) => {
    try {
        await queueManager.clearAllQueues();
        res.json({
            success: true,
            message: "All queues cleared successfully",
        });
    } catch (error) {
        console.error("❌ Failed to clear queues:", error);
        res.status(500).json({
            success: false,
            message: "Failed to clear queues",
            error: error.message,
        });
    }
});

// API endpoint to toggle queue processing (pause/resume)
app.post("/api/queue/toggle", async (req, res) => {
    try {
        const wasProcessing = queueManager.isProcessing;

        if (wasProcessing) {
            queueManager.stopProcessing();
        } else {
            queueManager.startProcessing();
        }

        const newStatus = queueManager.isProcessing;
        res.json({
            success: true,
            message: `Queue processing ${newStatus ? "started" : "stopped"}`,
            isProcessing: newStatus,
            wasProcessing: wasProcessing,
        });
    } catch (error) {
        console.error("❌ Failed to toggle queue processing:", error);
        res.status(500).json({
            success: false,
            message: "Failed to toggle queue processing",
            error: error.message,
        });
    }
});

// API endpoint to clear failed jobs only
app.post("/api/queue/clear-failed", async (req, res) => {
    try {
        const beforeCount = await queueManager.llenAsync(queueManager.keys.failed);
        await queueManager.delAsync(queueManager.keys.failed);

        res.json({
            success: true,
            message: `Cleared ${beforeCount} failed jobs`,
            clearedCount: beforeCount,
        });
    } catch (error) {
        console.error("❌ Failed to clear failed jobs:", error);
        res.status(500).json({
            success: false,
            message: "Failed to clear failed jobs",
            error: error.message,
        });
    }
});

// API endpoint to clean up stuck processing jobs
app.post("/api/queue/cleanup", async (req, res) => {
    try {
        await queueManager.cleanupProcessingQueue();
        res.json({
            success: true,
            message: "Processing queue cleaned up successfully",
        });
    } catch (error) {
        console.error("❌ Failed to cleanup processing queue:", error);
        res.status(500).json({
            success: false,
            message: "Failed to cleanup processing queue",
            error: error.message,
        });
    }
});

// API endpoint to update job with video URL after Creatomate completion
app.post("/api/job/:jobId/complete", async (req, res) => {
    try {
        const { jobId } = req.params;
        const { videoUrl } = req.body;

        if (!videoUrl) {
            return res.status(400).json({
                success: false,
                message: "Video URL is required",
            });
        }

        const job = await queueManager.getJob(jobId);
        if (!job) {
            return res.status(404).json({
                success: false,
                message: "Job not found",
            });
        }

        // Update job with final video URL
        job.videoUrl = videoUrl;
        job.progress = 100;
        job.completedAt = new Date().toISOString();
        job.currentStep = "Video rendering completed!";

        await queueManager.updateJob(job);

        res.json({
            success: true,
            message: "Job updated with video URL",
            job: job,
        });
    } catch (error) {
        console.error("❌ Failed to update job:", error);
        res.status(500).json({
            success: false,
            message: "Failed to update job",
            error: error.message,
        });
    }
});

// API endpoint to cancel a job
app.post("/api/job/:jobId/cancel", async (req, res) => {
    try {
        const { jobId } = req.params;
        console.log(`🛑 Cancelling job: ${jobId}`);

        // Use the queue manager's cancelJob method which handles process killing
        const job = await queueManager.cancelJob(jobId);

        res.json({
            success: true,
            message: "Job cancelled successfully",
            job: job,
        });
    } catch (error) {
        console.error("❌ Failed to cancel job:", error);
        res.status(500).json({
            success: false,
            message: "Failed to cancel job",
            error: error.message,
        });
    }
});

// API endpoint to retry a failed job
app.post("/api/job/:jobId/retry", async (req, res) => {
    try {
        const { jobId } = req.params;
        console.log(`🔄 Retrying job: ${jobId}`);

        // Get the job details
        const job = await queueManager.getJob(jobId);
        if (!job) {
            return res.status(404).json({
                success: false,
                message: "Job not found",
            });
        }

        // Only allow retry for failed jobs
        if (job.status !== "failed") {
            return res.status(400).json({
                success: false,
                message: `Cannot retry job with status: ${job.status}. Only failed jobs can be retried.`,
            });
        }

        // Reset job status and add back to queue
        job.status = "pending";
        job.error = null;
        job.progress = 0;
        job.currentStep = "Queued for retry...";
        job.startedAt = null;
        job.completedAt = null;
        job.retryCount = (job.retryCount || 0) + 1;

        // Update job in storage
        await queueManager.updateJob(job);

        // Add back to pending queue
        await queueManager.lpushAsync(queueManager.keys.pending, JSON.stringify(job));

        // Remove from failed queue
        const failedJobs = await queueManager.lrangeAsync(queueManager.keys.failed, 0, -1);
        const updatedFailedJobs = failedJobs.filter((jobStr) => {
            const failedJob = JSON.parse(jobStr);
            return failedJob.id !== jobId;
        });

        await queueManager.delAsync(queueManager.keys.failed);
        if (updatedFailedJobs.length > 0) {
            await queueManager.lpushAsync(queueManager.keys.failed, ...updatedFailedJobs);
        }

        res.json({
            success: true,
            message: `Job retry initiated (attempt ${job.retryCount})`,
            job: job,
        });
    } catch (error) {
        console.error("❌ Failed to retry job:", error);
        res.status(500).json({
            success: false,
            message: "Failed to retry job",
            error: error.message,
        });
    }
});

// API endpoint to cancel a job (DELETE method for frontend compatibility)
app.delete("/api/queue/job/:jobId", async (req, res) => {
    try {
        const { jobId } = req.params;
        console.log(`🛑 Cancelling job via DELETE: ${jobId}`);

        // Use the queue manager's cancelJob method which handles process killing
        const job = await queueManager.cancelJob(jobId);

        res.json({
            success: true,
            message: "Job cancelled successfully",
            job: job,
        });
    } catch (error) {
        console.error("❌ Failed to cancel job via DELETE:", error);
        res.status(500).json({
            success: false,
            message: "Failed to cancel job",
            error: error.message,
        });
    }
});

// API endpoint to get real-time logs for a specific job
app.get("/api/queue/job/:jobId/logs", async (req, res) => {
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
                lastUpdate: new Date().toISOString(),
            },
        });
    } catch (error) {
        console.error("❌ Error getting job logs:", error);
        res.status(500).json({
            success: false,
            error: error.message,
        });
    }
});

// API endpoint to get persistent file-based logs for a specific job
app.get("/api/queue/job/:jobId/logs/persistent", async (req, res) => {
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
                source: "file_logger",
                lastUpdate: new Date().toISOString(),
            },
        });
    } catch (error) {
        console.error("❌ Error getting persistent job logs:", error);
        res.status(500).json({
            success: false,
            error: error.message,
        });
    }
});

// API endpoint to search logs across all jobs
app.get("/api/logs/search", async (req, res) => {
    try {
        const { jobId, eventType, level, messageContains, limit = 100 } = req.query;

        console.log(`🔍 API: Searching logs with filters:`, { jobId, eventType, level, messageContains, limit });

        const logs = await fileLogger.searchLogs({
            jobId,
            eventType,
            level,
            messageContains,
            limit: parseInt(limit),
        });

        res.json({
            success: true,
            data: {
                logs: logs,
                count: logs.length,
                filters: { jobId, eventType, level, messageContains, limit },
                searchTime: new Date().toISOString(),
            },
        });
    } catch (error) {
        console.error("❌ Error searching logs:", error);
        res.status(500).json({
            success: false,
            error: error.message,
        });
    }
});

// API endpoint to get logging system statistics
app.get("/api/logs/stats", async (req, res) => {
    try {
        console.log("📊 API: Getting logging system statistics");

        const stats = await fileLogger.getLogStats();

        res.json({
            success: true,
            data: {
                ...stats,
                timestamp: new Date().toISOString(),
            },
        });
    } catch (error) {
        console.error("❌ Error getting log stats:", error);
        res.status(500).json({
            success: false,
            error: error.message,
        });
    }
});

// API endpoint to archive job logs
app.post("/api/queue/job/:jobId/logs/archive", async (req, res) => {
    try {
        const { jobId } = req.params;

        console.log(`📦 API: Archiving logs for job ${jobId}`);

        const success = await fileLogger.archiveJobLogs(jobId);

        if (success) {
            res.json({
                success: true,
                message: `Logs for job ${jobId} archived successfully`,
                jobId: jobId,
                timestamp: new Date().toISOString(),
            });
        } else {
            res.status(500).json({
                success: false,
                message: `Failed to archive logs for job ${jobId}`,
                jobId: jobId,
            });
        }
    } catch (error) {
        console.error(`❌ Error archiving logs for job ${req.params.jobId}:`, error);
        res.status(500).json({
            success: false,
            error: error.message,
            jobId: req.params.jobId,
        });
    }
});

// SSE endpoint for job-specific real-time updates
app.get("/api/job/:jobId/stream", (req, res) => {
    const { jobId } = req.params;

    console.log(`📡 SSE: Job ${jobId} client connected for real-time updates`);

    // Set SSE headers
    res.writeHead(200, {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        Connection: "keep-alive",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Cache-Control",
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
            type: "connected",
            job_id: jobId,
            message: "Real-time job updates connected",
            timestamp: new Date().toISOString(),
        })}\n\n`
    );

    // Heartbeat to keep connection alive
    const heartbeat = setInterval(() => {
        try {
            res.write(
                `data: ${JSON.stringify({
                    type: "heartbeat",
                    job_id: jobId,
                    timestamp: new Date().toISOString(),
                })}\n\n`
            );
        } catch (error) {
            clearInterval(heartbeat);
        }
    }, 30000); // Every 30 seconds

    // Clean up when client disconnects
    req.on("close", () => {
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

    req.on("error", (error) => {
        console.warn(`⚠️ SSE client error for job ${jobId}:`, error.message);
        clearInterval(heartbeat);
    });
});

// API endpoint to manually trigger Creatomate monitoring for a job
app.post("/api/queue/job/:jobId/monitor-creatomate", async (req, res) => {
    try {
        const { jobId } = req.params;
        console.log(`🎬 Manual Creatomate monitoring trigger for job: ${jobId}`);

        const job = await queueManager.getJob(jobId);
        if (!job) {
            return res.status(404).json({
                success: false,
                message: "Job not found",
            });
        }

        if (!job.creatomateId) {
            return res.status(400).json({
                success: false,
                message: "Job has no Creatomate ID",
            });
        }

        if (job.videoUrl) {
            return res.status(400).json({
                success: false,
                message: "Job already has video URL",
            });
        }

        // Check if workflow was marked as incomplete
        if (job.workflowIncomplete) {
            return res.status(400).json({
                success: false,
                message: "Job workflow was incomplete - manual verification needed before monitoring",
                details: "The Python workflow did not complete all 7 steps properly. Check logs and verify Creatomate render manually.",
            });
        }

        // Update job to rendering status if it's completed without video
        if (job.status === "completed" && !job.videoUrl) {
            job.status = "rendering";
            job.currentStep = "Video rendering in progress with Creatomate...";
            await queueManager.updateJob(job);
        }

        // Start monitoring
        queueManager.startCreatomateMonitoring(jobId, job.creatomateId);

        res.json({
            success: true,
            message: `Started Creatomate monitoring for job ${jobId}`,
            job: job,
            creatomateId: job.creatomateId,
        });
    } catch (error) {
        console.error("❌ Failed to start Creatomate monitoring:", error);
        res.status(500).json({
            success: false,
            message: "Failed to start Creatomate monitoring",
            error: error.message,
        });
    }
});

// API endpoint to permanently delete a completed or failed job (alternative endpoint)
app.delete("/api/queue/job/:jobId/delete", async (req, res) => {
    try {
        const { jobId } = req.params;
        console.log(`🗑️ Permanently deleting job: ${jobId}`);

        // Get the job first to check its status
        const job = await queueManager.getJob(jobId);

        if (!job) {
            return res.status(404).json({
                success: false,
                message: "Job not found",
                error: "Job does not exist",
            });
        }

        // Only allow deletion of completed, failed, or cancelled jobs
        if (!["completed", "failed", "cancelled"].includes(job.status)) {
            return res.status(400).json({
                success: false,
                message: "Job cannot be deleted",
                error: `Cannot delete job with status: ${job.status}. Only completed, failed, or cancelled jobs can be deleted.`,
            });
        }

        // Use the queue manager's deleteJob method (permanent removal)
        const result = await queueManager.deleteJob(jobId);

        res.json({
            success: true,
            message: `Job ${jobId.slice(-8)} deleted permanently`,
            job: job,
            deletedAt: new Date().toISOString(),
        });
    } catch (error) {
        console.error("❌ Failed to delete job:", error);
        res.status(500).json({
            success: false,
            message: "Failed to delete job",
            error: error.message,
        });
    }
});

// Preview movies endpoint - fetch filtered movies without generating video
app.post("/api/movies/preview", async (req, res) => {
    try {
        const { country, platforms, genres, genre, contentType } = req.body;

        // Support both 'genres' (from Dashboard) and 'genre' (legacy) parameters
        const genreList = genres || genre;

        console.log("📋 Movie preview request:", { country, platforms, genres: genreList, contentType });

        // Validate required parameters
        if (!country || !platforms || platforms.length === 0 || !genreList || (Array.isArray(genreList) && genreList.length === 0)) {
            return res.status(400).json({
                success: false,
                error: "Missing required parameters: country, platforms, and genres are required",
            });
        }

        // Call the Python movie extraction directly (preview only, not video generation)
        const pythonScript = path.join(__dirname, "..", "database", "movie_extractor.py");
        // Build Python arguments, skip content-type if "All" or null
        const pythonArgs = ["--country", country, "--platform", Array.isArray(platforms) ? platforms.join(",") : platforms, "--genre", Array.isArray(genreList) ? genreList.join(",") : genreList];

        // Only add content-type if it's not "All" or null
        if (contentType && contentType !== "All") {
            pythonArgs.push("--content-type", contentType);
        }

        pythonArgs.push("--limit", "3", "--preview-only");

        console.log("🐍 Executing Python script:", pythonScript, pythonArgs);

        const { spawn } = require("child_process");
        const pythonProcess = spawn("python", [pythonScript, ...pythonArgs], {
            cwd: path.join(__dirname, ".."),
            env: { ...process.env, PYTHONPATH: path.join(__dirname, "..") },
        });

        let outputData = "";
        let errorData = "";

        pythonProcess.stdout.on("data", (data) => {
            outputData += data.toString();
        });

        pythonProcess.stderr.on("data", (data) => {
            errorData += data.toString();
        });

        pythonProcess.on("close", (code) => {
            if (code !== 0) {
                console.error("❌ Python script failed:", errorData);
                return res.status(500).json({
                    success: false,
                    error: "Failed to fetch movie preview",
                    details: errorData,
                });
            }

            try {
                // Parse the JSON output from Python script
                const result = JSON.parse(outputData.trim());

                console.log(`✅ Found ${result.movies?.length || 0} movies for preview`);

                res.json({
                    success: true,
                    movies: result.movies || [],
                    count: result.movies?.length || 0,
                    filters: { country, platforms, genre, contentType },
                });
            } catch (parseError) {
                console.error("❌ Failed to parse Python output:", parseError);
                res.status(500).json({
                    success: false,
                    error: "Failed to parse movie data",
                    details: parseError.message,
                });
            }
        });
    } catch (error) {
        console.error("❌ Movie preview error:", error);
        res.status(500).json({
            success: false,
            error: "Internal server error",
            details: error.message,
        });
    }
});

// API endpoint to get available platforms by region from database
app.get("/api/platforms/:country", async (req, res) => {
    try {
        const { country } = req.params;
        console.log(`🌍 Fetching platforms for country: ${country}`);

        // US only - platform data provided by the user
        const availablePlatforms = {
            US: ["Netflix", "Hulu", "Crunchyroll", "Kanopy", "Apple TV+", "Disney+", "Disney Plus", "Rakuten TV", "Amazon Prime Video", "HBO Max", "free", "Sky Go", "Max"],
        };

        const platforms = availablePlatforms[country] || availablePlatforms["US"]; // Default to US if country not found

        console.log(`✅ Found ${platforms.length} platforms for ${country}:`, platforms);

        res.json({
            success: true,
            country: country,
            platforms: platforms,
            source: "user_defined",
            count: platforms.length,
        });
    } catch (error) {
        console.error("❌ Error fetching platforms:", error);
        res.status(500).json({
            success: false,
            message: "Failed to fetch platforms",
            error: error.message,
        });
    }
});

// API endpoint to get available genres by region
app.get("/api/genres/:country", async (req, res) => {
    try {
        const { country } = req.params;
        console.log(`🎭 Fetching genres for country: ${country}`);

        // US only - genre data provided by user
        const availableGenres = {
            US: ["Action & Adventure", "Animation", "Comedy", "Crime", "Documentary", "Drama", "Fantasy", "History", "Horror", "Kids & Family", "Made in Europe", "Music & Musical", "Mystery & Thriller", "Reality TV", "Romance", "Science-Fiction", "Sport", "War & Military", "Western"],
        };

        const genres = availableGenres[country] || availableGenres["US"];

        console.log(`✅ Found ${genres.length} genres for ${country}:`, genres);

        res.json({
            success: true,
            country: country,
            genres: genres,
            source: "user_defined",
            count: genres.length,
        });
    } catch (error) {
        console.error("❌ Error fetching genres:", error);
        res.status(500).json({
            success: false,
            message: "Failed to fetch genres",
            error: error.message,
        });
    }
});

// API endpoint to get available video templates
app.get("/api/templates", async (req, res) => {
    try {
        console.log("🎨 Fetching available HeyGen templates");

        // HeyGen Templates Configuration (from config/templates.py)
        const availableTemplates = [
            {
                id: "cc6718c5363e42b282a123f99b94b335",
                name: "Default Template",
                description: "General-purpose template for all content types",
                genres: ["*"],
                isDefault: true,
            },
            {
                id: "ed21a309a5c84b0d873fde68642adea3",
                name: "Horror",
                description: "Specialized template for horror content",
                genres: ["Horror"],
                isDefault: false,
            },
            {
                id: "7f8db20ddcd94a33a1235599aa8bf473",
                name: "Action & Adventure",
                description: "High-energy template for action and adventure content",
                genres: ["Action & Adventure"],
                isDefault: false,
            },
            {
                id: "bc62f68a6b074406b571df42bdc6b71a",
                name: "Romance/Comedy",
                description: "Romantic template for love and relationship content",
                genres: ["Romance"],
                isDefault: false,
            },
        ];

        console.log(`✅ Found ${availableTemplates.length} available templates`);

        res.json({
            success: true,
            templates: availableTemplates,
            count: availableTemplates.length,
            source: "heygen_config",
        });
    } catch (error) {
        console.error("❌ Error fetching templates:", error);
        res.status(500).json({
            success: false,
            message: "Failed to fetch templates",
            error: error.message,
        });
    }
});

// Remove duplicate - using the existing /api/movies/preview endpoint above

// API endpoint to validate StreamGank URL
app.post("/api/validate-url", async (req, res) => {
    try {
        const { url } = req.body;

        if (!url) {
            return res.status(400).json({
                success: false,
                message: "URL is required",
            });
        }

        console.log(`🔍 Validating URL: ${url}`);

        // Use node's built-in fetch or a library like axios to check the URL
        const https = require("https");
        const http = require("http");
        const urlParsed = new URL(url);

        const client = urlParsed.protocol === "https:" ? https : http;

        const validation = await new Promise((resolve, reject) => {
            const request = client.get(
                url,
                {
                    headers: {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                    },
                    timeout: 10000,
                },
                (response) => {
                    let data = "";

                    response.on("data", (chunk) => {
                        data += chunk;
                    });

                    response.on("end", () => {
                        // Simplified validation - check basic HTTP response success
                        console.log(`🔍 Simplified validation for: ${url} - Status Code: ${response.statusCode}`);

                        // Log first 200 characters of content for debugging
                        console.log(`📄 First 200 chars of page content: ${data.substring(0, 200)}`);

                        // Always return valid=true since no movies validation is removed
                        resolve({
                            valid: true,
                            reason: "URL validation passed - no movies check removed",
                            details: `Page loaded successfully with ${data.length} bytes of content`,
                        });
                    });
                }
            );

            request.on("error", (error) => {
                console.error("Validation request error:", error);
                reject(error);
            });

            request.on("timeout", () => {
                request.destroy();
                reject(new Error("Request timeout"));
            });
        });

        console.log(`✅ Validation result: ${validation.valid ? "Valid" : "Invalid"} - ${validation.reason}`);

        res.json({
            success: true,
            ...validation,
        });
    } catch (error) {
        console.error("❌ Error validating URL:", error);

        // If validation fails, return valid=true to continue (fail-safe approach)
        res.json({
            success: true,
            valid: true,
            reason: "Validation failed, proceeding anyway",
            details: `Validation error: ${error.message}`,
        });
    }
});

// Catch-all route for any other client-side routes
// This MUST come AFTER all API routes but BEFORE error handlers
app.get("*", (req, res) => {
    // Only serve index.html for routes that don't start with /api
    if (!req.path.startsWith("/api")) {
        res.sendFile(path.join(__dirname, "dist", "index.html"));
    } else {
        // API route not found
        res.status(404).json({
            success: false,
            error: "API endpoint not found",
        });
    }
});

// Global error handler (MUST be last)
app.use((error, req, res, next) => {
    console.error("❌ Server Error:", error);

    // Don't send error details in production
    const isDevelopment = process.env.NODE_ENV !== "production";

    res.status(error.status || 500).json({
        success: false,
        error: isDevelopment ? error.message : "Internal server error",
        ...(isDevelopment && { stack: error.stack }),
    });
});

// Initialize Redis connection and start server
async function startServer() {
    try {
        // Connect to Redis
        await queueManager.connect();
        console.log("🔗 Redis queue manager connected");

        // Check for existing jobs needing Creatomate monitoring (after 5 seconds)
        setTimeout(() => {
            queueManager.checkExistingJobsForCreatomateMonitoring();
        }, 5000);

        // Start the server
        app.listen(port, "0.0.0.0", () => {
            console.log(`🚀 StreamGank Video Generator Frontend server running at http://0.0.0.0:${port}`);
            console.log(`📋 Redis queue system active`);
            console.log(`🗂️ Platform mappings loaded: ${Object.keys(platformMapping).length} platforms`);
            console.log(`📝 Content type mappings: ${Object.keys(contentTypeMapping).join(", ")}`);
        });
    } catch (error) {
        console.error("❌ Failed to start server:", error);
        process.exit(1);
    }
}

// Handle graceful shutdown
process.on("SIGINT", async () => {
    console.log("\n🛑 Shutting down server...");
    await queueManager.close();
    process.exit(0);
});

process.on("SIGTERM", async () => {
    console.log("\n🛑 Shutting down server...");
    await queueManager.close();
    process.exit(0);
});

// Start the server
startServer();
