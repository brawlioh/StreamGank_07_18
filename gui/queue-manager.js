const redis = require("redis");
const { spawn, exec } = require("child_process");
const path = require("path");
const { promisify } = require("util");

/**
 * Redis-based Video Queue Manager
 * Handles video generation jobs with persistence, retry logic, and real-time updates
 */
class VideoQueueManager {
    constructor() {
        // Redis client configuration with database selection
        const redisConfig = {
            host: process.env.REDIS_HOST,
            port: parseInt(process.env.REDIS_PORT),
            password: process.env.REDIS_PASSWORD,
            db: parseInt(process.env.REDIS_DB), // Database selection (0-15)
            retry_delay_on_failover: 100,
            enable_ready_check: false,
            max_attempts: null,
        };

        console.log(`🔗 Connecting to Redis database ${redisConfig.db} on ${redisConfig.host}:${redisConfig.port}`);
        this.client = redis.createClient(redisConfig);

        // Event handlers for Redis connection
        this.client.on("error", (err) => {
            console.error("❌ Redis Client Error:", err);
        });

        this.client.on("connect", () => {
            console.log("✅ Connected to Redis server");
        });

        this.client.on("ready", () => {
            console.log("🚀 Redis client ready for operations");
        });

        // Multi-worker queue processing state
        this.isProcessing = false;
        this.maxWorkers = parseInt(process.env.MAX_WORKERS) || 3; // Default to 3 workers
        this.concurrentProcessing = process.env.ENABLE_CONCURRENT_PROCESSING === "true";
        this.activeJobs = new Map(); // Track multiple active jobs by jobId
        this.activeProcesses = new Map(); // Track multiple Python processes by jobId
        this.availableWorkers = this.maxWorkers; // Number of available worker slots
        this.jobLogs = new Map(); // Store logs for each job by jobId

        console.log(`👥 Worker pool initialized: ${this.maxWorkers} max workers, concurrent processing: ${this.concurrentProcessing}`);

        // Start periodic cleanup (every 5 minutes) to avoid performance issues
        this.cleanupInterval = setInterval(() => {
            this.cleanupProcessingQueue().catch((error) => {
                console.error("❌ Background cleanup error:", error);
            });
        }, 5 * 60 * 1000); // 5 minutes

        // Redis queue keys with database-aware namespace
        const dbNumber = redisConfig.db;
        const namespace = `streamgankvideos:db${dbNumber}`;
        this.keys = {
            pending: `${namespace}:queue:pending`,
            processing: `${namespace}:queue:processing`,
            completed: `${namespace}:queue:completed`,
            failed: `${namespace}:queue:failed`,
            jobs: `${namespace}:jobs`,
        };

        console.log(`📋 Using Redis namespace: ${namespace}`);
        console.log(`🔑 Queue keys: ${Object.keys(this.keys).join(", ")}`);

        // Promisify Redis v3 methods for async/await usage
        this.lpushAsync = promisify(this.client.lpush).bind(this.client);
        this.hsetAsync = promisify(this.client.hset).bind(this.client);
        this.llenAsync = promisify(this.client.llen).bind(this.client);
        this.hgetallAsync = promisify(this.client.hgetall).bind(this.client);
        this.hgetAsync = promisify(this.client.hget).bind(this.client);
        this.brpopAsync = promisify(this.client.brpop).bind(this.client);
        this.lremAsync = promisify(this.client.lrem).bind(this.client);
        this.expireAsync = promisify(this.client.expire).bind(this.client);
        this.delAsync = promisify(this.client.del).bind(this.client);
        this.lrangeAsync = promisify(this.client.lrange).bind(this.client);
        this.quitAsync = promisify(this.client.quit).bind(this.client);
    }

    /**
     * Connect to Redis server (Redis v3 connects automatically)
     */
    async connect() {
        // Redis v3 connects automatically when first command is issued
        console.log("🔗 Redis client ready (v3 auto-connects)");
    }

    /**
     * Add video generation job to queue
     * @param {Object} parameters - Video generation parameters
     * @returns {Object} Created job object
     */
    async addJob(parameters) {
        const job = {
            id: `job_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
            status: "pending",
            parameters: parameters,
            createdAt: new Date().toISOString(),
            startedAt: null,
            completedAt: null,
            creatomateId: null,
            videoUrl: null,
            retryCount: 0,
            maxRetries: 3,
            error: null,
            progress: 0,
            currentStep: "Queued for processing...",
        };

        try {
            // Add to pending queue (FIFO - First In, First Out)
            await this.lpushAsync(this.keys.pending, JSON.stringify(job));

            // Store job details in hash for quick lookup
            await this.hsetAsync(this.keys.jobs, job.id, JSON.stringify(job));

            console.log(`📋 Added job to queue: ${job.id}`);
            console.log(`📊 Queue parameters:`, parameters);

            // Start processing if not already running
            if (!this.isProcessing) {
                this.startProcessing();
            }

            return job;
        } catch (error) {
            console.error("❌ Failed to add job to queue:", error);
            throw error;
        }
    }

    /**
     * Get current queue status
     * @returns {Object} Queue statistics
     */
    async getQueueStatus() {
        try {
            // Optimized for performance - removed expensive cleanup operations
            const [pending, processing, completed, failed] = await Promise.all([this.llenAsync(this.keys.pending), this.llenAsync(this.keys.processing), this.llenAsync(this.keys.completed), this.llenAsync(this.keys.failed)]);

            return {
                pending,
                processing,
                completed,
                failed,
                total: pending + processing + completed + failed,
            };
        } catch (error) {
            console.error("❌ Failed to get queue status:", error);
            return { pending: 0, processing: 0, completed: 0, failed: 0, total: 0 };
        }
    }

    /**
     * Get all jobs with details
     * @returns {Object} All jobs indexed by job ID
     */
    async getAllJobs() {
        try {
            const allJobs = await this.hgetallAsync(this.keys.jobs);
            const jobs = {};

            for (const [jobId, jobData] of Object.entries(allJobs)) {
                jobs[jobId] = JSON.parse(jobData);
            }

            return jobs;
        } catch (error) {
            console.error("❌ Failed to get all jobs:", error);
            return {};
        }
    }

    /**
     * Get specific job by ID
     * @param {string} jobId - Job identifier
     * @returns {Object|null} Job object or null if not found
     */
    async getJob(jobId) {
        try {
            const jobData = await this.hgetAsync(this.keys.jobs, jobId);
            return jobData ? JSON.parse(jobData) : null;
        } catch (error) {
            console.error(`❌ Failed to get job ${jobId}:`, error);
            return null;
        }
    }

    /**
     * Update job status and data
     * @param {Object} job - Job object to update
     */
    async updateJob(job) {
        try {
            await this.hsetAsync(this.keys.jobs, job.id, JSON.stringify(job));
        } catch (error) {
            console.error(`❌ Failed to update job ${job.id}:`, error);
        }
    }

    /**
     * Start multi-worker queue processing loop
     */
    async startProcessing() {
        if (this.isProcessing) {
            console.log("⚠️ Queue processing already running");
            return;
        }

        this.isProcessing = true;
        console.log(`🚀 Starting multi-worker queue processing (${this.maxWorkers} max workers, concurrent: ${this.concurrentProcessing})...`);

        // Main processing loop
        while (this.isProcessing) {
            try {
                // Check if we have available worker slots
                if (this.availableWorkers <= 0) {
                    console.log(`⏳ All ${this.maxWorkers} workers busy, waiting...`);
                    await this.sleep(2000); // Wait before checking again
                    continue;
                }

                // Blocking pop from pending queue (waits up to 5 seconds)
                const jobData = await this.brpopAsync(this.keys.pending, 5);

                if (jobData && jobData[1]) {
                    const job = JSON.parse(jobData[1]);

                    // Check concurrent processing setting
                    if (!this.concurrentProcessing && this.activeJobs.size > 0) {
                        console.log(`⚠️ Job ${job.id} skipped - concurrent processing disabled and ${this.activeJobs.size} job(s) still processing`);
                        // Put the job back at the front of the queue
                        await this.lpushAsync(this.keys.pending, jobData[1]);
                        await this.sleep(2000); // Wait before trying again
                        continue;
                    }

                    // Process job if we have available workers
                    if (this.availableWorkers > 0) {
                        this.availableWorkers--;
                        console.log(`👤 Assigning job ${job.id} to worker (${this.availableWorkers}/${this.maxWorkers} workers available)`);

                        // Process job asynchronously (don't await - allows multiple jobs)
                        this.processJobAsync(job).finally(() => {
                            this.availableWorkers++;
                            console.log(`✅ Worker freed for job ${job.id} (${this.availableWorkers}/${this.maxWorkers} workers available)`);
                        });
                    }
                }
            } catch (error) {
                console.error("❌ Queue processing error:", error);
                // Wait before retrying to avoid rapid error loops
                await this.sleep(5000);
            }
        }

        console.log("🛑 Queue processing stopped");
    }

    /**
     * Async wrapper for processing jobs in multi-worker environment
     * @param {Object} job - Job to process
     */
    async processJobAsync(job) {
        try {
            // Add job to active jobs tracking
            this.activeJobs.set(job.id, job);
            console.log(`📝 Added job ${job.id} to active jobs (${this.activeJobs.size}/${this.maxWorkers} active)`);

            // Initialize job logs
            this.addJobLog(job.id, `Job ${job.id} started with worker pool`, "info");
            this.addJobLog(job.id, `Parameters: ${JSON.stringify(job.parameters)}`, "info");

            await this.processJob(job);
        } catch (error) {
            console.error(`❌ Error in processJobAsync for job ${job.id}:`, error);
            this.addJobLog(job.id, `Job error: ${error.message}`, "error");
        } finally {
            // Always clean up job tracking
            this.activeJobs.delete(job.id);
            this.activeProcesses.delete(job.id);
            console.log(`🧹 Removed job ${job.id} from active tracking (${this.activeJobs.size}/${this.maxWorkers} active)`);

            // Add completion log
            this.addJobLog(job.id, "Job processing completed and removed from active pool", "info");

            // Keep logs for 10 minutes after job completion
            setTimeout(() => {
                this.clearJobLogs(job.id);
            }, 10 * 60 * 1000); // 10 minutes
        }
    }

    /**
     * Process individual video generation job
     * @param {Object} job - Job to process
     */
    async processJob(job) {
        // Job processing (UI queue management)
        console.log(`\n🔄 Starting job: ${job.id}`);
        console.log(`📋 Parameters:`, job.parameters);
        console.log(`🔍 Active jobs: ${Array.from(this.activeJobs.keys()).join(", ") || "none"}`);
        console.log(`--- Python Script Output ---`);

        try {
            // Update job status to processing
            job.status = "processing";
            job.startedAt = new Date().toISOString();
            job.progress = 10;
            job.currentStep = "Starting video generation...";
            job.workerId = `worker-${Date.now()}-${Math.random().toString(36).substr(2, 5)}`;
            console.log(`✅ Assigned worker ID ${job.workerId} to job: ${job.id}`);

            // Move to processing queue and update job store
            await this.lpushAsync(this.keys.processing, JSON.stringify(job));
            await this.updateJob(job);

            // Job queued for processing

            // Execute Python script for video generation
            job.progress = 20;
            await this.updateJob(job);

            const result = await this.executePythonScript(job.parameters, job);

            // Store the processing job state before updating
            const processingJobState = JSON.stringify(job);

            // Check if we have a video URL, Creatomate ID, or paused after extraction
            if (result.pausedAfterExtraction) {
                // Process was paused after movie extraction - this is a successful completion
                job.status = "completed";
                job.completedAt = new Date().toISOString();
                job.progress = 100;
                job.currentStep = "Movie extraction completed - process paused for review";
                job.pausedAfterExtraction = true;

                // Extract movie information from stdout for UI display
                const movieMatch = result.stdout.match(/📋 Found \d+ movies:([\s\S]*?)(?:\n\n|\n💡)/);
                if (movieMatch && movieMatch[1]) {
                    job.extractedMovies = movieMatch[1].trim();
                }

                // Remove from processing queue and add to completed
                await this.lremAsync(this.keys.processing, 1, processingJobState);
                await this.lpushAsync(this.keys.completed, JSON.stringify(job));
            } else if (result.videoUrl) {
                // Video is fully complete
                job.status = "completed";
                job.completedAt = new Date().toISOString();
                job.creatomateId = result.creatomateId;
                job.videoUrl = result.videoUrl;
                job.progress = 100;
                job.currentStep = "Video generation completed!";

                // Remove from processing queue and add to completed
                await this.lremAsync(this.keys.processing, 1, processingJobState);
                await this.lpushAsync(this.keys.completed, JSON.stringify(job));
            } else if (result.creatomateId) {
                // Python script done but video still rendering
                job.status = "completed"; // Mark as completed for Python script
                job.creatomateId = result.creatomateId;
                job.videoUrl = null; // No video URL yet
                job.progress = 90;
                job.currentStep = "Python script completed, video rendering in progress...";

                // Remove from processing queue and add to completed (but video not ready)
                await this.lremAsync(this.keys.processing, 1, processingJobState);
                await this.lpushAsync(this.keys.completed, JSON.stringify(job));
            } else {
                // No video URL or Creatomate ID - something went wrong
                job.status = "completed";
                job.progress = 100;
                job.currentStep = "Script completed but no video information available";
                job.error = "No video URL or Creatomate ID returned";

                // Remove from processing queue and add to completed
                await this.lremAsync(this.keys.processing, 1, processingJobState);
                await this.lpushAsync(this.keys.completed, JSON.stringify(job));
            }

            await this.updateJob(job);

            // Set TTL for completed jobs (24 hours)
            await this.expireAsync(`${this.keys.jobs}:${job.id}`, 86400);

            console.log(`\n--- Job Completed ---`);
            console.log(`✅ ${job.id} completed successfully`);
            if (job.videoUrl) {
                console.log(`🎬 Video URL: ${job.videoUrl}`);
            }
        } catch (error) {
            // 🚨 ENHANCED ERROR HANDLING - Stop process immediately and mark as failed
            console.error(`❌ FATAL ERROR - Job failed: ${job.id}`, error);
            console.error(`❌ Error details:`, {
                message: error.message,
                stack: error.stack,
                timestamp: new Date().toISOString(),
                jobId: job.id,
                jobParameters: job.parameters,
            });

            // Kill any running Python process immediately (multi-worker support)
            const activeProcess = this.activeProcesses.get(job.id);
            if (activeProcess && !activeProcess.killed) {
                console.log(`🔪 EMERGENCY: Killing Python process for failed job ${job.id}`);
                try {
                    // Force kill the process tree
                    if (process.platform === "win32") {
                        exec(`taskkill /f /t /pid ${activeProcess.pid}`, (killError) => {
                            if (killError) {
                                console.error(`❌ Failed to kill process: ${killError.message}`);
                            } else {
                                console.log(`✅ Process ${activeProcess.pid} killed successfully`);
                            }
                        });
                    } else {
                        activeProcess.kill("SIGKILL");
                    }
                    // Cleanup will be handled by processJobAsync finally block
                } catch (killError) {
                    console.error(`❌ Error killing process: ${killError.message}`);
                }
            }

            // Store the processing job state before updating
            const processingJobState = JSON.stringify(job);

            // Mark job as FAILED immediately - reset everything for complete restart
            job.status = "failed";
            job.error = this.categorizeError(error.message);
            job.retryCount++;
            job.progress = 0; // Reset progress to 0 for fresh start
            job.currentStep = `❌ FAILED: ${job.error}`;
            job.failedAt = new Date().toISOString();

            // Clear any partial state for complete restart
            job.extractedMovies = null;
            job.extractedMoviesOutput = null;
            job.showExtractedMovies = false;
            job.capturingMovies = false;
            job.pausedAfterExtraction = false;
            job.creatomateId = null;
            job.videoUrl = null;

            // 🧠 SMART RETRY LOGIC - Different strategies based on error type
            const shouldRetry = this.shouldRetryError(job.error, job.retryCount, job.maxRetries);

            if (shouldRetry.retry && job.retryCount < job.maxRetries) {
                console.log(`🔄 RETRY SCHEDULED: Job ${job.id} (attempt ${job.retryCount + 1}/${job.maxRetries})`);
                console.log(`📋 Retry reason: ${shouldRetry.reason}`);
                console.log(`⏰ Will retry after ${shouldRetry.delaySeconds}s delay`);

                // Reset job to fresh state for complete restart
                job.status = "pending";
                job.progress = 0;
                job.currentStep = `🔄 Scheduled for retry (attempt ${job.retryCount + 1}/${job.maxRetries}) - ${shouldRetry.reason}`;
                job.error = null; // Clear error for fresh start

                // Use smart delay based on error type
                job.retryAfter = new Date(Date.now() + shouldRetry.delaySeconds * 1000).toISOString();
                job.currentStep += ` (retry in ${shouldRetry.delaySeconds}s)`;

                await this.lpushAsync(this.keys.pending, JSON.stringify(job));
                console.log(`📋 Job ${job.id} queued for retry with ${shouldRetry.delaySeconds}s delay`);
            } else if (!shouldRetry.retry) {
                console.log(`🚫 NO RETRY: Job ${job.id} - ${shouldRetry.reason}`);
                console.log(`💡 Resolution: ${shouldRetry.solution}`);

                // Move directly to failed queue with detailed reason
                job.currentStep = `❌ No retry - ${shouldRetry.reason}`;
                job.noRetryReason = shouldRetry.reason;
                job.suggestedSolution = shouldRetry.solution;

                await this.lpushAsync(this.keys.failed, JSON.stringify(job));
                console.log(`🗂️ Job ${job.id} moved to failed queue - requires manual intervention`);
            } else {
                console.log(`💀 PERMANENT FAILURE: Job ${job.id} exceeded max retries (${job.maxRetries})`);
                console.log(`📊 Final failure reason: ${job.error}`);

                // Move to failed queue for manual review
                await this.lpushAsync(this.keys.failed, JSON.stringify(job));
                console.log(`🗂️ Job ${job.id} moved to failed queue for manual review`);
            }

            // Remove from processing queue using the original processing state
            try {
                await this.lremAsync(this.keys.processing, 1, processingJobState);
                console.log(`🧹 Removed job ${job.id} from processing queue`);
            } catch (removeError) {
                console.error(`❌ Failed to remove job from processing queue: ${removeError.message}`);
            }

            // Update job state in Redis
            try {
                await this.updateJob(job);
                console.log(`💾 Job ${job.id} state updated in Redis`);
            } catch (updateError) {
                console.error(`❌ Failed to update job state: ${updateError.message}`);
            }

            // Log comprehensive failure summary
            console.log(`\n--- JOB FAILURE SUMMARY ---`);
            console.log(`Job ID: ${job.id}`);
            console.log(`Error: ${job.error}`);
            console.log(`Retry Count: ${job.retryCount}/${job.maxRetries}`);
            console.log(`Will Retry: ${job.retryCount < job.maxRetries ? "YES" : "NO"}`);
            console.log(`Failed At: ${job.failedAt}`);
            console.log(`Parameters: ${JSON.stringify(job.parameters, null, 2)}`);
            console.log(`--- END FAILURE SUMMARY ---\n`);
        }

        console.log(`🧹 Job ${job.id} processing completed - cleanup handled by processJobAsync`);
    }

    /**
     * Categorize error messages for better user feedback and handling
     * @param {string} errorMessage - Raw error message
     * @returns {string} Categorized and formatted error message
     */
    categorizeError(errorMessage) {
        if (!errorMessage) return "Unknown error occurred";

        const message = errorMessage.toLowerCase();

        // HeyGen API errors (highest priority - payment issues)
        if (message.includes("insufficient credit") || message.includes("movio_payment_insufficient_credit")) {
            return "💳 HeyGen Credits Exhausted - Please add credits to your HeyGen account";
        }
        if (message.includes("heygen") && (message.includes("authentication") || message.includes("unauthorized"))) {
            return "🔐 HeyGen Authentication Failed - Check your API key";
        }
        if (message.includes("heygen") && message.includes("rate limit")) {
            return "⏳ HeyGen Rate Limit Exceeded - Too many requests";
        }
        if (message.includes("heygen") && message.includes("error")) {
            return "🎭 HeyGen API Error - Service temporarily unavailable";
        }

        // Creatomate API errors
        if (message.includes("creatomate") && message.includes("insufficient credit")) {
            return "💳 Creatomate Credits Exhausted - Please add credits to your account";
        }
        if (message.includes("creatomate") && (message.includes("authentication") || message.includes("401"))) {
            return "🔐 Creatomate Authentication Failed - Check your API key";
        }
        if (message.includes("creatomate") && (message.includes("rate limit") || message.includes("429"))) {
            return "⏳ Creatomate Rate Limit Exceeded - Please wait before retrying";
        }
        if (message.includes("creatomate") && message.includes("api error")) {
            return "🎬 Creatomate API Error - Video service temporarily unavailable";
        }

        // Database and content errors
        if (message.includes("insufficient movies") || (message.includes("only") && message.includes("found with current filters"))) {
            return "🎬 Not Enough Movies Available - Try different filters";
        }
        if (message.includes("no movies found") || message.includes("database query failed")) {
            return "🗃️ No Movies Found - Change genre/platform/content type";
        }
        if (message.includes("connection failed") || message.includes("database connection failed")) {
            return "🌐 Database Connection Failed - Check internet connection";
        }

        // Screenshot and browser errors
        if (message.includes("screenshot") && message.includes("failed")) {
            return "📸 Screenshot Capture Failed - Network or website issue";
        }
        if (message.includes("browser") || message.includes("playwright")) {
            return "🌐 Browser Automation Failed - Website access issue";
        }

        // Process and system errors
        if (message.includes("killed") || message.includes("cancelled") || message.includes("stopped")) {
            return "🛑 Process Cancelled - Job was stopped by user or system";
        }
        if (message.includes("timeout") || message.includes("timed out")) {
            return "⏱️ Process Timeout - Operation took too long";
        }
        if (message.includes("memory") || message.includes("out of memory")) {
            return "🧠 Memory Error - Insufficient system memory";
        }
        if (message.includes("disk") || message.includes("space")) {
            return "💾 Disk Space Error - Insufficient storage available";
        }

        // Network and connectivity errors
        if (message.includes("network") || message.includes("connection refused") || message.includes("unreachable")) {
            return "🌐 Network Error - Check internet connection";
        }
        if (message.includes("ssl") || message.includes("certificate")) {
            return "🔒 SSL Certificate Error - Network security issue";
        }

        // File and permission errors
        if (message.includes("permission") || message.includes("access denied")) {
            return "🔒 Permission Error - File access denied";
        }
        if (message.includes("file not found") || message.includes("no such file")) {
            return "📁 File Not Found - Missing required file";
        }

        // Generic API errors
        if (message.includes("api") && message.includes("error")) {
            return "🔧 API Error - External service temporarily unavailable";
        }

        // Python/script specific errors
        if (message.includes("failed to process exactly") && message.includes("movie clips")) {
            return "🎬 Movie Processing Failed - Critical workflow error";
        }
        if (message.includes("python") || message.includes("traceback")) {
            return "🐍 Script Error - Internal processing failure";
        }

        // Fallback for any unmatched errors
        return `⚠️ ${errorMessage.substring(0, 100)}${errorMessage.length > 100 ? "..." : ""}`;
    }

    /**
     * Detect critical errors in Python output that require immediate process termination
     * @param {string} output - Python script output
     * @returns {boolean} True if critical error detected
     */
    detectCriticalErrors(output) {
        const criticalPatterns = [
            // HeyGen credit/payment failures
            /MOVIO_PAYMENT_INSUFFICIENT_CREDIT/i,
            /Insufficient credit/i,
            /HeyGen.*insufficient.*credit/i,

            // Critical workflow failures
            /Failed to process exactly.*movie clips/i,
            /CRITICAL:.*Failed to process/i,
            /RuntimeError.*CRITICAL/i,

            // Authentication failures
            /Authentication failed/i,
            /Invalid API key/i,
            /Unauthorized.*API/i,

            // System resource failures
            /Out of memory/i,
            /No space left on device/i,
            /Disk quota exceeded/i,

            // Network/connection failures (severe)
            /Connection timeout.*critical/i,
            /Network unreachable.*critical/i,

            // File system failures
            /Permission denied.*critical/i,
            /File system.*read-only/i,
        ];

        return criticalPatterns.some((pattern) => pattern.test(output));
    }

    /**
     * Extract meaningful error message from critical error output
     * @param {string} output - Python script output containing error
     * @returns {string} Extracted error message
     */
    extractCriticalErrorMessage(output) {
        // HeyGen credit errors
        if (output.includes("MOVIO_PAYMENT_INSUFFICIENT_CREDIT") || output.includes("Insufficient credit")) {
            return "HeyGen credits exhausted - Please add credits to continue";
        }

        // Critical workflow failures
        if (output.includes("Failed to process exactly") && output.includes("movie clips")) {
            return "Critical workflow failure - Movie processing failed";
        }

        // Authentication errors
        if (output.includes("Authentication failed") || output.includes("Invalid API key")) {
            return "API authentication failed - Check your credentials";
        }

        // System resource errors
        if (output.includes("Out of memory")) {
            return "System out of memory - Process cannot continue";
        }

        if (output.includes("No space left") || output.includes("Disk quota exceeded")) {
            return "Insufficient disk space - Cannot continue processing";
        }

        // Generic critical error
        return "Critical error detected - Process terminated";
    }

    /**
     * Determine if an error should be retried and with what strategy
     * @param {string} errorMessage - Categorized error message
     * @param {number} currentRetryCount - Current retry attempt
     * @param {number} maxRetries - Maximum allowed retries
     * @returns {Object} Retry decision with reason, delay, and solution
     */
    shouldRetryError(errorMessage, currentRetryCount, maxRetries) {
        if (!errorMessage) {
            return {
                retry: true,
                reason: "Generic error - standard retry",
                delaySeconds: Math.pow(2, currentRetryCount) * 30,
                solution: "Monitor logs for specific error details",
            };
        }

        const error = errorMessage.toLowerCase();

        // ❌ NEVER RETRY - Credit/Payment Issues
        if (error.includes("credits exhausted") || error.includes("insufficient credit") || error.includes("payment")) {
            return {
                retry: false,
                reason: "Payment/credit issue requires manual resolution",
                delaySeconds: 0,
                solution: "Add credits to your HeyGen/Creatomate account before retrying",
            };
        }

        // ❌ NEVER RETRY - Authentication Issues
        if (error.includes("authentication failed") || error.includes("invalid api key") || error.includes("unauthorized")) {
            return {
                retry: false,
                reason: "Authentication failure requires credential fix",
                delaySeconds: 0,
                solution: "Check and update your API keys in environment variables",
            };
        }

        // ❌ NEVER RETRY - System Resource Issues
        if (error.includes("out of memory") || error.includes("disk space") || error.includes("quota exceeded")) {
            return {
                retry: false,
                reason: "System resource exhaustion requires admin intervention",
                delaySeconds: 0,
                solution: "Free up system resources (memory/disk) before retrying",
            };
        }

        // ❌ NEVER RETRY - Critical Workflow Failures (until manual review)
        if (error.includes("critical workflow") || error.includes("movie processing failed")) {
            return {
                retry: false,
                reason: "Critical workflow failure needs investigation",
                delaySeconds: 0,
                solution: "Check system logs and try different movie parameters",
            };
        }

        // 🟡 LIMITED RETRY - Rate Limits (short backoff)
        if (error.includes("rate limit") || error.includes("too many requests")) {
            return {
                retry: currentRetryCount < Math.min(maxRetries, 2), // Max 2 retries for rate limits
                reason: "Rate limit - short retry with backoff",
                delaySeconds: Math.pow(2, currentRetryCount + 2) * 60, // 4, 8, 16 minutes
                solution: "Wait for rate limit window to reset",
            };
        }

        // 🟡 SMART RETRY - Network Issues (medium backoff)
        if (error.includes("network") || error.includes("connection") || error.includes("timeout")) {
            return {
                retry: currentRetryCount < maxRetries,
                reason: "Network issue - medium retry with backoff",
                delaySeconds: Math.pow(2, currentRetryCount) * 60, // 1, 2, 4 minutes
                solution: "Check internet connection stability",
            };
        }

        // 🟡 SMART RETRY - Screenshot/Browser Issues (medium backoff)
        if (error.includes("screenshot") || error.includes("browser")) {
            return {
                retry: currentRetryCount < maxRetries,
                reason: "Screenshot/browser issue - medium retry",
                delaySeconds: Math.pow(2, currentRetryCount) * 45, // 45s, 90s, 180s
                solution: "Website may be temporarily inaccessible",
            };
        }

        // 🟡 SMART RETRY - Database/Content Issues (longer backoff)
        if (error.includes("no movies found") || error.includes("not enough movies")) {
            return {
                retry: currentRetryCount < Math.min(maxRetries, 1), // Only 1 retry
                reason: "Content issue - single retry with different filters suggested",
                delaySeconds: 120, // 2 minutes
                solution: "Try different genre/platform/content type combination",
            };
        }

        // 🟡 SMART RETRY - API Service Issues (adaptive backoff)
        if (error.includes("api error") || error.includes("service") || error.includes("temporarily unavailable")) {
            return {
                retry: currentRetryCount < maxRetries,
                reason: "External API issue - adaptive retry",
                delaySeconds: Math.pow(2, currentRetryCount + 1) * 30, // 1, 2, 4 minutes
                solution: "External service is experiencing issues",
            };
        }

        // 🟡 SMART RETRY - Process Cancellation (immediate retry allowed)
        if (error.includes("cancelled") || error.includes("stopped") || error.includes("killed")) {
            return {
                retry: currentRetryCount < maxRetries,
                reason: "Process was cancelled - can retry immediately",
                delaySeconds: 30, // Short delay
                solution: "Job was stopped, safe to retry",
            };
        }

        // ✅ DEFAULT RETRY - Unknown errors (standard exponential backoff)
        return {
            retry: currentRetryCount < maxRetries,
            reason: "Unknown error - standard exponential backoff",
            delaySeconds: Math.pow(2, currentRetryCount) * 30, // 30s, 1m, 2m, 4m
            solution: "Monitor logs for specific error patterns",
        };
    }

    /**
     * Execute Python video generation script
     * @param {Object} parameters - Video generation parameters
     * @param {Object} job - Job object for progress updates
     * @returns {Promise<Object>} Execution results
     */
    async executePythonScript(parameters, job) {
        return new Promise((resolve, reject) => {
            const { country, platform, genre, contentType, template, pauseAfterExtraction } = parameters;

            // Construct Python command (Using main.py modular system as requested)
            // Check if running in Docker or locally
            const isDocker = process.env.PYTHON_BACKEND_PATH === "/app";
            const scriptPath = isDocker ? "main.py" : path.join(__dirname, "../main.py");
            const args = [scriptPath, "--country", country, "--platform", platform, "--genre", genre, "--content-type", contentType];

            // Add template parameter if provided and not 'auto'
            if (template && template !== "auto") {
                args.push("--heygen-template-id", template);
            }

            // Add pause flag if enabled
            if (pauseAfterExtraction) {
                args.push("--pause-after-extraction");
            }

            // Executing exact CLI command as requested
            console.log("🚀 Executing exact CLI command:", "python", args.join(" "));

            // Spawn Python process
            const workingDir = isDocker ? "/app" : path.join(__dirname, "..");
            const pythonProcess = spawn("python", args, {
                cwd: workingDir,
                env: {
                    ...process.env,
                    PYTHONIOENCODING: "utf-8",
                    PYTHONUNBUFFERED: "1",
                },
            });

            // Store reference to current process for cancellation (multi-worker support)
            this.activeProcesses.set(job.id, pythonProcess);
            console.log(`🔗 Stored process for job ${job.id} (${this.activeProcesses.size} active processes)`);

            let stdout = "";
            let stderr = "";

            // Handle Python process output
            pythonProcess.stdout.on("data", async (data) => {
                const output = data.toString("utf8");
                stdout += output;

                // 🚨 IMMEDIATE CRITICAL ERROR DETECTION - Stop process on fatal errors
                if (this.detectCriticalErrors(output)) {
                    console.log("🚨 CRITICAL ERROR DETECTED - Stopping process immediately");
                    if (pythonProcess && !pythonProcess.killed) {
                        pythonProcess.kill("SIGKILL");
                    }
                    reject(new Error(this.extractCriticalErrorMessage(output)));
                    return;
                }

                // Check for movie extraction completion and capture for UI display
                if (output.includes("📋 Movies extracted from database:")) {
                    // Initialize movie capture for UI display only
                    job.extractedMoviesOutput = "";
                    job.capturingMovies = true;
                }

                // Capture movie lines after the extraction header (for normal workflow)
                if (job.capturingMovies) {
                    // Look for movie lines with format "   1. Title (Year) - IMDB: Score" or similar variations
                    const movieLineMatch = output.match(/^\s+\d+\.\s+.+\(\d{4}\)\s+-\s+IMDB:/);
                    if (movieLineMatch) {
                        job.extractedMoviesOutput += output.trim() + "\n";
                        console.log(`📋 Captured movie line: ${output.trim()}`);
                    }

                    // Stop capturing when we hit the next step or completion
                    if (output.includes("✅ STEP 1 COMPLETED") || output.includes("[STEP 2/7]")) {
                        // Finalize the captured movies and immediately display in UI
                        if (job.extractedMoviesOutput.trim()) {
                            job.extractedMovies = job.extractedMoviesOutput.trim();
                            // Movies captured for UI display only

                            // Update job progress with movie extraction step and trigger UI update
                            job.progress = Math.max(job.progress, 22);
                            job.currentStep = "📋 Movies extracted - displaying in UI...";
                            job.showExtractedMovies = true; // Flag to trigger immediate UI display
                            await this.updateJob(job);
                        }
                        // Clean up temporary properties
                        delete job.extractedMoviesOutput;
                        delete job.capturingMovies;
                    }
                }

                // Output exactly like CLI - no prefixes
                process.stdout.write(output);

                // Capture output as job-specific logs
                this.addJobLog(job.id, output, this.getLogTypeFromOutput(output));

                // Update job progress and status based on output
                if (job) {
                    let progressUpdated = false;

                    // DISABLED: Generic percentage-based progress updates
                    // We now use detailed step-by-step progress tracking instead of generic "Downloading... X%" messages
                    // This provides much better user experience with specific workflow information

                    // Enhanced step detection with detailed CLI workflow steps (fallback if no percentage found)
                    if (!progressUpdated) {
                        // Detect and capture specific workflow step messages
                        const stepPatterns = [
                            // Step 1: Database Extraction
                            {
                                patterns: ["STEP 1/7"],
                                progress: 15,
                                step: "🗃️ Step 1/7: Extracting movies from database...",
                            },
                            {
                                patterns: ["✅ STEP 1 COMPLETED"],
                                progress: 20,
                                step: "✅ Step 1 completed: Movies extracted successfully",
                            },

                            // Step 2: Script Generation
                            {
                                patterns: ["STEP 2/7"],
                                progress: 25,
                                step: "🤖 Step 2/7: Generating AI-powered scripts...",
                            },
                            {
                                patterns: ["✅ STEP 2 COMPLETED"],
                                progress: 35,
                                step: "✅ Step 2 completed: AI scripts generated successfully",
                            },

                            // Step 3: Asset Preparation
                            {
                                patterns: ["STEP 3/7"],
                                progress: 40,
                                step: "🎨 Step 3/7: Creating enhanced posters and clips...",
                            },
                            {
                                patterns: ["✅ STEP 3 COMPLETED"],
                                progress: 50,
                                step: "✅ Step 3 completed: Assets created successfully",
                            },

                            // Step 4: HeyGen Video Creation
                            {
                                patterns: ["STEP 4/7"],
                                progress: 55,
                                step: "🎭 Step 4/7: Creating HeyGen AI avatar videos...",
                            },
                            {
                                patterns: ["✅ STEP 4 COMPLETED"],
                                progress: 65,
                                step: "✅ Step 4 completed: HeyGen videos created successfully",
                            },

                            // Step 5: HeyGen Video Processing
                            {
                                patterns: ["STEP 5/7"],
                                progress: 70,
                                step: "⏳ Step 5/7: Processing HeyGen video URLs...",
                            },
                            {
                                patterns: ["✅ STEP 5 COMPLETED"],
                                progress: 75,
                                step: "✅ Step 5 completed: Video URLs processed successfully",
                            },

                            // Step 6: Scroll Video Generation
                            {
                                patterns: ["STEP 6/7"],
                                progress: 80,
                                step: "📱 Step 6/7: Generating scroll video overlay...",
                            },
                            {
                                patterns: ["✅ STEP 6 COMPLETED"],
                                progress: 85,
                                step: "✅ Step 6 completed: Scroll overlay generated successfully",
                            },
                            {
                                patterns: ["STEP 6/7", "SKIPPED"],
                                progress: 85,
                                step: "⏭️ Step 6 skipped: No scroll video needed",
                            },

                            // Step 7: Creatomate Assembly
                            {
                                patterns: ["STEP 7/7"],
                                progress: 90,
                                step: "🎬 Step 7/7: Assembling final video with Creatomate...",
                            },
                            {
                                patterns: ["✅ STEP 7 COMPLETED"],
                                progress: 95,
                                step: "✅ Step 7 completed: Final video submitted for rendering",
                            },

                            // Workflow Completion
                            {
                                patterns: ["🎉 WORKFLOW COMPLETED SUCCESSFULLY"],
                                progress: 100,
                                step: "🎉 Workflow completed successfully!",
                            },
                        ];

                        // Check each pattern to find a match
                        for (const pattern of stepPatterns) {
                            const matchesAll = pattern.patterns.every((p) => output.toLowerCase().includes(p.toLowerCase()));

                            if (matchesAll) {
                                // Step pattern matched - update job for UI display only
                                job.progress = Math.max(job.progress, pattern.progress);
                                job.currentStep = pattern.step;
                                progressUpdated = true;
                                await this.updateJob(job); // Force immediate job update for UI
                                break; // Stop at first match to avoid conflicts
                            }
                        }

                        // Note: CLI output remains unchanged - only UI logs are enhanced

                        // Legacy detection patterns (fallback for any missed cases)
                        if (!progressUpdated) {
                            if (output.includes("Connecting to database") || output.includes("extracting movies")) {
                                job.progress = Math.max(job.progress, 25);
                                job.currentStep = "Extracting movies from database...";
                                progressUpdated = true;
                            }
                            if (output.includes("Movies processed") || output.includes("Successfully extracted")) {
                                job.progress = Math.max(job.progress, 35);
                                job.currentStep = "Movies extracted successfully";
                                progressUpdated = true;
                            }
                            if (output.includes("Capturing StreamGank screenshots") || output.includes("Screenshot")) {
                                job.progress = Math.max(job.progress, 45);
                                job.currentStep = "Capturing screenshots...";
                                progressUpdated = true;
                            }
                            if (output.includes("Uploading") && output.includes("Cloudinary")) {
                                job.progress = Math.max(job.progress, 55);
                                job.currentStep = "Uploading files to Cloudinary...";
                                progressUpdated = true;
                            }
                            if (output.includes("Enriching movie data") || output.includes("AI descriptions")) {
                                job.progress = Math.max(job.progress, 65);
                                job.currentStep = "Enriching movie data with AI...";
                                progressUpdated = true;
                            }
                            if (output.includes("HeyGen videos created") || output.includes("Creating HeyGen")) {
                                job.progress = Math.max(job.progress, 75);
                                job.currentStep = "Creating HeyGen avatar videos...";
                                progressUpdated = true;
                            }
                            if (output.includes("Creatomate") && !output.includes("Video URL")) {
                                job.progress = Math.max(job.progress, 85);
                                job.currentStep = "Submitting to Creatomate for rendering...";
                                progressUpdated = true;
                            }
                            if (output.includes("Video URL") || output.includes("succeeded")) {
                                job.progress = Math.max(job.progress, 95);
                                job.currentStep = "Video rendering completed!";
                                progressUpdated = true;
                            }
                        }
                    }

                    if (progressUpdated) {
                        await this.updateJob(job);
                    }
                }
            });

            pythonProcess.stderr.on("data", (data) => {
                const output = data.toString("utf8");
                stderr += output;

                // 🚨 IMMEDIATE CRITICAL ERROR DETECTION in stderr
                if (this.detectCriticalErrors(output)) {
                    console.log("🚨 CRITICAL ERROR DETECTED in stderr - Stopping process immediately");
                    if (pythonProcess && !pythonProcess.killed) {
                        pythonProcess.kill("SIGKILL");
                    }
                    reject(new Error(this.extractCriticalErrorMessage(output)));
                    return;
                }

                // Output exactly like CLI - no prefixes
                process.stderr.write(output);

                // Capture stderr as job-specific logs (usually errors)
                this.addJobLog(job.id, output, "error");
            });

            // Handle process completion
            pythonProcess.on("close", (code) => {
                // Clear process reference from multi-worker tracking
                this.activeProcesses.delete(job.id);
                console.log(`🧹 Cleaned up process for job ${job.id} (${this.activeProcesses.size} active processes)`);
                console.log(`\n--- Python Script Completed ---`);
                if (code !== 0) {
                    // Check for specific error messages to make them more user-friendly
                    const errorOutput = stdout + stderr;

                    // Check for Creatomate API errors (insufficient credits, etc.)
                    if (errorOutput.includes("Creatomate API error")) {
                        const creatomateErrorMatch = errorOutput.match(/Creatomate API error: (\d+) - ({.*?})/);
                        if (creatomateErrorMatch) {
                            const statusCode = creatomateErrorMatch[1];
                            let errorMessage = "";

                            try {
                                const errorData = JSON.parse(creatomateErrorMatch[2]);
                                if (statusCode === "402") {
                                    errorMessage = `💳 Insufficient Creatomate credits - ${errorData.hint || "Please check your subscription usage"}`;
                                } else if (statusCode === "401") {
                                    errorMessage = `🔐 Creatomate authentication failed - ${errorData.hint || "Please check your API key"}`;
                                } else if (statusCode === "429") {
                                    errorMessage = `⏳ Creatomate rate limit exceeded - ${errorData.hint || "Please wait before retrying"}`;
                                } else if (statusCode === "400") {
                                    errorMessage = `⚠️ Invalid Creatomate request - ${errorData.hint || errorData.message || "Please check your video parameters"}`;
                                } else {
                                    errorMessage = `🔧 Creatomate API error (${statusCode}) - ${errorData.hint || errorData.message || "Unknown API error"}`;
                                }
                            } catch (e) {
                                errorMessage = `🔧 Creatomate API error (${statusCode}) - Please check your account status and try again`;
                            }

                            reject(new Error(errorMessage));
                            return;
                        }
                    }

                    // Check for HeyGen API errors
                    if (errorOutput.includes("HeyGen API error") || errorOutput.includes("HeyGen error")) {
                        const heygenErrorMatch = errorOutput.match(/HeyGen.*?error[:\s]+(.*?)(?:\n|$)/i);
                        if (heygenErrorMatch) {
                            const errorMsg = heygenErrorMatch[1].trim();
                            reject(new Error(`🎭 HeyGen API error - ${errorMsg}. Please check your HeyGen account and API settings.`));
                            return;
                        }
                    }

                    // Check for insufficient movies error (less than 3 movies found)
                    if (errorOutput.includes("Insufficient movies found") || (errorOutput.includes("only") && errorOutput.includes("movie(s) available"))) {
                        const movieCountMatch = errorOutput.match(/only (\d+) movie\(s\) available/);
                        const movieCount = movieCountMatch ? movieCountMatch[1] : "few";

                        // Try to extract movie names from the output
                        let movieNames = "";
                        const movieSectionMatch = errorOutput.match(/🎬 Movies found with current filters:([\s\S]*?)(?:\n\n|\n   Please try)/);
                        if (movieSectionMatch && movieSectionMatch[1]) {
                            const movieLines = movieSectionMatch[1].trim().split("\n");
                            const movies = movieLines
                                .filter((line) => line.trim().match(/^\d+\./))
                                .map((line) => line.trim().replace(/^\d+\.\s*/, ""))
                                .join(", ");
                            if (movies) {
                                movieNames = ` Found movies: ${movies}.`;
                            }
                        }

                        reject(new Error(`🎬 Not enough movies available - only ${movieCount} found with current filters.${movieNames} Please try different genre, platform, or content type to find more movies.`));
                        return;
                    }

                    // Check for database errors
                    if (errorOutput.includes("No movies found matching criteria") || errorOutput.includes("Database query failed")) {
                        reject(new Error("🗃️ No movies found for the selected parameters (genre, platform, content type). Please try different filters to find available content."));
                        return;
                    }

                    // Check for connection errors
                    if (errorOutput.includes("Connection failed") || errorOutput.includes("Database connection failed")) {
                        reject(new Error("🌐 Database connection failed. Please check your internet connection and try again."));
                        return;
                    }

                    // Check for screenshot/browser errors
                    if (errorOutput.includes("Screenshot") && errorOutput.includes("failed")) {
                        reject(new Error("📸 Screenshot capture failed. This might be due to network issues or website accessibility. Please try again."));
                        return;
                    }

                    // Generic error message for other failures
                    reject(new Error(`Video generation failed: ${stderr || "Unknown error occurred"}`));
                    return;
                }

                // Parse results from Python output
                let creatomateId = "";
                let videoUrl = "";
                let pausedAfterExtraction = false;

                // Check if process was paused after extraction
                if (stdout.includes("PROCESS PAUSED - Movie extraction completed")) {
                    pausedAfterExtraction = true;
                    console.log("📋 Process paused after movie extraction");
                }

                // Extract Creatomate ID (UUID format)
                const creatomateMatch = stdout.match(/Creatomate.*?([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})/i);
                if (creatomateMatch && creatomateMatch[1]) {
                    creatomateId = creatomateMatch[1];
                }

                // Extract video URL
                const videoUrlMatch = stdout.match(/video[_\s]+(?:URL|url)[:\s]+(https:\/\/[^\s\n]+)/i);
                if (videoUrlMatch && videoUrlMatch[1]) {
                    videoUrl = videoUrlMatch[1];
                }

                if (pausedAfterExtraction) {
                    console.log(`⏸️ Python script paused after movie extraction`);
                    console.log(`📋 Movies extracted successfully - process stopped for review`);

                    resolve({
                        success: true,
                        pausedAfterExtraction: true,
                        message: "Movie extraction completed - process paused for review",
                        stdout: stdout,
                        stderr: stderr,
                    });
                } else {
                    resolve({
                        creatomateId,
                        videoUrl,
                        stdout,
                        stderr,
                    });
                }
            });

            // Handle process errors
            pythonProcess.on("error", (error) => {
                reject(new Error(`Failed to start Python process: ${error.message}`));
            });
        });
    }

    /**
     * Remove a job from the processing queue
     * @param {Object} job - The job to remove
     */
    async removeFromProcessingQueue(job) {
        try {
            // Get all items in processing queue
            const processingItems = await this.lrangeAsync(this.keys.processing, 0, -1);

            // Find and remove the job
            for (let i = 0; i < processingItems.length; i++) {
                const item = JSON.parse(processingItems[i]);
                if (item.id === job.id) {
                    // Remove this specific item from the list
                    await this.lremAsync(this.keys.processing, 1, processingItems[i]);
                    console.log(`🗑️ Removed job ${job.id} from processing queue`);
                    break;
                }
            }
        } catch (error) {
            console.error(`❌ Failed to remove job ${job.id} from processing queue:`, error);
        }
    }

    /**
     * Cancel a specific job
     * @param {string} jobId - The job ID to cancel
     * @returns {Object} Updated job object
     */
    async cancelJob(jobId) {
        try {
            // Get the job
            const job = await this.getJob(jobId);
            if (!job) {
                throw new Error("Job not found");
            }

            const activeJob = this.activeJobs.get(jobId);
            const activeProcess = this.activeProcesses.get(jobId);
            console.log(`🔍 Debug - activeJob: ${activeJob ? jobId : "null"}, activeProcess: ${activeProcess ? activeProcess.pid : "null"}`);
            console.log(`🔍 Active jobs: ${Array.from(this.activeJobs.keys()).join(", ") || "none"}`);

            // If this job is currently processing, kill the Python process
            if (activeJob && activeProcess) {
                const processPid = activeProcess.pid;
                console.log(`🛑 Killing Python process for job ${jobId} (PID: ${processPid})`);

                try {
                    // On Windows, use taskkill for more reliable process termination
                    if (process.platform === "win32") {
                        console.log("🪟 Using Windows taskkill for process termination");

                        // Kill the process tree (including child processes)
                        exec(`taskkill /pid ${processPid} /t /f`, (error, stdout, stderr) => {
                            if (error) {
                                console.error(`❌ Error killing process: ${error}`);
                            } else {
                                console.log(`✅ Process ${processPid} killed successfully`);
                            }
                        });
                    } else {
                        // Unix-like systems: use SIGTERM first, then SIGKILL
                        const processToKill = activeProcess;
                        processToKill.kill("SIGTERM");

                        // Force kill after 5 seconds if still running
                        setTimeout(() => {
                            if (processToKill && !processToKill.killed) {
                                console.log(`🔪 Force killing Python process for job ${jobId} (PID: ${processPid})`);
                                processToKill.kill("SIGKILL");
                            }
                        }, 5000);
                    }
                } catch (error) {
                    console.error(`❌ Failed to kill process: ${error}`);
                }

                // Clean up job and process tracking
                this.activeJobs.delete(jobId);
                this.activeProcesses.delete(jobId);
                this.availableWorkers++;
                console.log(`🧹 Cleaned up job ${jobId} from active tracking (${this.availableWorkers}/${this.maxWorkers} workers available)`);
            } else {
                console.log(`⚠️ Cannot kill process - job ${jobId} is not currently processing`);
                if (!activeJob) {
                    console.log(`   - Job ${jobId} is not in active jobs`);
                } else if (!activeProcess) {
                    console.log(`   - No process reference available`);
                }
            }

            // Update job status
            job.status = "cancelled";
            job.progress = 0;
            job.cancelledAt = new Date().toISOString();
            job.currentStep = "Job cancelled by user";
            job.error = "Process stopped by user request";

            // Remove from processing queue if it's there
            await this.removeFromProcessingQueue(job);

            // Update job in storage
            await this.updateJob(job);

            // Move to failed queue (cancelled jobs go here for tracking)
            await this.lpushAsync(this.keys.failed, JSON.stringify(job));

            console.log(`✅ Job ${jobId} cancelled successfully`);

            // The processing loop will automatically continue with the next job
            // No need to manually trigger processing since startProcessing() runs in a loop

            return job;
        } catch (error) {
            console.error(`❌ Failed to cancel job ${jobId}:`, error);
            throw error;
        }
    }

    /**
     * Stop queue processing
     */
    stopProcessing() {
        this.isProcessing = false;
        console.log("🛑 Queue processing stopped");
    }

    /**
     * Clear all queues (use with caution!)
     */
    async clearAllQueues() {
        try {
            await Promise.all([this.delAsync(this.keys.pending), this.delAsync(this.keys.processing), this.delAsync(this.keys.completed), this.delAsync(this.keys.failed), this.delAsync(this.keys.jobs)]);
            console.log("🗑️ All queues cleared");
        } catch (error) {
            console.error("❌ Failed to clear queues:", error);
        }
    }

    /**
     * Clean up orphaned processing jobs (jobs stuck in processing state)
     */
    async cleanupProcessingQueue() {
        try {
            const processingJobs = await this.lrangeAsync(this.keys.processing, 0, -1);
            let cleanedCount = 0;

            for (const jobStr of processingJobs) {
                try {
                    const job = JSON.parse(jobStr);
                    const jobDetails = await this.getJob(job.id);

                    // If job is completed or failed in job store but still in processing queue, remove it
                    if (jobDetails && (jobDetails.status === "completed" || jobDetails.status === "failed")) {
                        await this.lremAsync(this.keys.processing, 1, jobStr);
                        cleanedCount++;
                        console.log(`🧹 Cleaned up orphaned processing job: ${job.id} (status: ${jobDetails.status})`);
                    }
                    // Also check for jobs stuck in processing for more than 30 minutes
                    else if (jobDetails && jobDetails.status === "processing" && jobDetails.startedAt) {
                        const startTime = new Date(jobDetails.startedAt);
                        const now = new Date();
                        const timeDiff = now - startTime;
                        const thirtyMinutes = 30 * 60 * 1000; // 30 minutes in milliseconds

                        if (timeDiff > thirtyMinutes) {
                            // Mark as failed and remove from processing queue
                            jobDetails.status = "failed";
                            jobDetails.error = "Job timed out after 30 minutes";
                            jobDetails.failedAt = new Date().toISOString();

                            await this.lremAsync(this.keys.processing, 1, jobStr);
                            await this.lpushAsync(this.keys.failed, JSON.stringify(jobDetails));
                            await this.updateJob(jobDetails);
                            cleanedCount++;
                            console.log(`🧹 Cleaned up timed out processing job: ${job.id} (running for ${Math.round(timeDiff / 60000)} minutes)`);
                        }
                    }
                    // Remove jobs that don't exist in job store
                    else if (!jobDetails) {
                        await this.lremAsync(this.keys.processing, 1, jobStr);
                        cleanedCount++;
                        console.log(`🧹 Removed processing job with no details: ${job.id}`);
                    }
                } catch (parseError) {
                    // Remove invalid JSON entries
                    await this.lremAsync(this.keys.processing, 1, jobStr);
                    cleanedCount++;
                    console.log(`🧹 Removed invalid processing queue entry`);
                }
            }

            if (cleanedCount > 0) {
                console.log(`🧹 Cleaned up ${cleanedCount} orphaned processing jobs`);
            }

            return cleanedCount;
        } catch (error) {
            console.error("❌ Failed to cleanup processing queue:", error);
            return 0;
        }
    }

    /**
     * Get queue statistics for monitoring
     */
    async getQueueStats() {
        try {
            const status = await this.getQueueStatus();
            // Removed expensive getAllJobs() call - use queue counts for performance

            const jobsByStatus = {
                pending: status.pending,
                processing: status.processing,
                completed: status.completed,
                failed: status.failed,
            };

            return {
                ...status,
                jobsByStatus,
                activeJobs: Array.from(this.activeJobs.keys()), // List of active job IDs
                activeWorkers: this.maxWorkers - this.availableWorkers,
                availableWorkers: this.availableWorkers,
                maxWorkers: this.maxWorkers,
                concurrentProcessing: this.concurrentProcessing,
                isProcessing: this.isProcessing,
            };
        } catch (error) {
            console.error("❌ Failed to get queue stats:", error);
            return null;
        }
    }

    /**
     * Helper function for delays
     * @param {number} ms - Milliseconds to sleep
     */
    sleep(ms) {
        return new Promise((resolve) => setTimeout(resolve, ms));
    }

    /**
     * Determine log type based on output content
     * @param {string} output - Output text
     * @returns {string} Log type (info, success, warning, error, step)
     */
    getLogTypeFromOutput(output) {
        const text = output.toLowerCase();

        if (text.includes("error") || text.includes("❌") || text.includes("failed") || text.includes("exception")) {
            return "error";
        } else if (text.includes("warning") || text.includes("⚠️") || text.includes("warn")) {
            return "warning";
        } else if (text.includes("✅") || text.includes("success") || text.includes("completed") || text.includes("done")) {
            return "success";
        } else if (text.includes("step") || text.includes("[step") || text.includes("🔄") || text.includes("🗃️") || text.includes("🤖")) {
            return "step";
        } else {
            return "info";
        }
    }

    /**
     * Add log entry for a specific job
     * @param {string} jobId - Job ID
     * @param {string} message - Log message
     * @param {string} type - Log type (info, success, warning, error, step)
     */
    addJobLog(jobId, message, type = "info") {
        if (!this.jobLogs.has(jobId)) {
            this.jobLogs.set(jobId, []);
        }

        const logEntry = {
            timestamp: new Date().toISOString(),
            message: message.trim(),
            type: type,
        };

        const logs = this.jobLogs.get(jobId);
        logs.push(logEntry);

        // Keep only last 200 log entries per job
        if (logs.length > 200) {
            logs.splice(0, logs.length - 200);
        }

        console.log(`📝 [${jobId.slice(-8)}] ${type.toUpperCase()}: ${message.trim()}`);
    }

    /**
     * Get logs for a specific job
     * @param {string} jobId - Job ID
     * @returns {Array} Array of log entries
     */
    getJobLogs(jobId) {
        return this.jobLogs.get(jobId) || [];
    }

    /**
     * Clear logs for a specific job
     * @param {string} jobId - Job ID
     */
    clearJobLogs(jobId) {
        this.jobLogs.delete(jobId);
        console.log(`🗑️ Cleared logs for job ${jobId}`);
    }

    /**
     * Close Redis connection
     */
    async close() {
        try {
            this.stopProcessing();

            // Clear the periodic cleanup interval
            if (this.cleanupInterval) {
                clearInterval(this.cleanupInterval);
                console.log("🧹 Stopped periodic cleanup");
            }

            await this.quitAsync();
            console.log("🔌 Redis connection closed");
        } catch (error) {
            console.error("❌ Error closing Redis connection:", error);
        }
    }
}

module.exports = VideoQueueManager;
