const redis = require('redis');
const { spawn, exec } = require('child_process');
const path = require('path');
const { promisify } = require('util');
const axios = require('axios'); // For Creatomate API requests
const { getFileLogger } = require('./utils/file_logger');

/**
 * Redis-based Video Queue Manager
 * Handles video generation jobs with persistence, retry logic, and real-time updates
 */
class VideoQueueManager {
    constructor() {
        // Redis client configuration with database selection - OPTIMIZED for performance and connection pooling
        const redisConfig = {
            host: process.env.REDIS_HOST,
            port: parseInt(process.env.REDIS_PORT),
            password: process.env.REDIS_PASSWORD,
            db: parseInt(process.env.REDIS_DB), // Database selection (0-15)
            retry_delay_on_failover: 100, // Faster failover for status requests
            enable_ready_check: true, // Enable ready check for better connection reliability
            max_attempts: 3, // Reduced retry attempts for faster failure
            connect_timeout: 1500, // Reduced connection timeout for status requests
            socket_keepalive: true, // Keep connections alive
            no_ready_check: false, // Ensure connection is ready
            // Connection pooling settings to prevent exhaustion during heavy processing
            return_buffers: false, // Use strings instead of buffers for better performance
            detect_buffers: false, // Disable buffer detection for speed
            socket_nodelay: true, // Disable Nagle algorithm for low latency
            family: 'IPv4' // Force IPv4 to avoid DNS lookup delays
        };

        console.log(`🔗 Connecting to Redis database ${redisConfig.db} on ${redisConfig.host}:${redisConfig.port}`);

        // Production-level Redis connection pooling for high concurrency
        this.clients = [];
        this.currentClientIndex = 0;
        this.poolSize = parseInt(process.env.REDIS_POOL_SIZE) || 1; // Single connection for efficiency

        console.log(`🔗 Creating Redis connection (professional single connection)...`);

        // Create single connection (professional approach)
        for (let i = 0; i < this.poolSize; i++) {
            const client = redis.createClient(redisConfig);

            // Event handlers for each client in the pool
            client.on('error', (err) => {
                console.error(`❌ Redis Client ${i} Error:`, err);
            });

            client.on('connect', () => {
                console.log(`✅ Redis Client ${i} connected`);
            });

            client.on('ready', () => {
                console.log(`🚀 Redis Client ${i} ready`);
            });

            this.clients.push(client);
        }

        // Primary client for backward compatibility
        this.client = this.clients[0];

        // Multi-worker queue processing state
        this.isProcessing = false;
        this.maxWorkers = parseInt(process.env.MAX_WORKERS) || 3; // Default to 3 workers
        this.concurrentProcessing = process.env.ENABLE_CONCURRENT_PROCESSING === 'true';
        this.activeJobs = new Map(); // Track multiple active jobs by jobId
        this.activeProcesses = new Map(); // Track multiple Python processes by jobId
        this.availableWorkers = this.maxWorkers; // Number of available worker slots
        this.jobLogs = new Map(); // Store logs for each job by jobId
        this.jobCache = new Map(); // PRODUCTION: In-memory job cache to reduce Redis calls

        console.log(
            `👥 Worker pool initialized: ${this.maxWorkers} max workers, concurrent processing: ${this.concurrentProcessing}`
        );

        // PROFESSIONAL: Minimal cleanup since webhooks handle real-time updates
        this.cleanupInterval = setInterval(
            () => {
                this.cleanupProcessingQueue().catch((error) => {
                    console.error('❌ Background cleanup error:', error);
                });
            },
            30 * 60 * 1000 // 30 minutes - much less frequent
        );

        // Redis queue keys with database-aware namespace
        const dbNumber = redisConfig.db;
        const namespace = `streamgankvideos:db${dbNumber}`;
        this.keys = {
            pending: `${namespace}:queue:pending`,
            processing: `${namespace}:queue:processing`,
            completed: `${namespace}:queue:completed`,
            failed: `${namespace}:queue:failed`,
            jobs: `${namespace}:jobs`
        };

        console.log(`📋 Using Redis namespace: ${namespace}`);
        console.log(`🔑 Queue keys: ${Object.keys(this.keys).join(', ')}`);

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
        this.hdelAsync = promisify(this.client.hdel).bind(this.client);
        this.quitAsync = promisify(this.client.quit).bind(this.client);

        // Production-level error tracking and recovery
        this.errorCount = 0;
        this.lastErrorTime = 0;
        this.maxErrorsBeforeAlert = 10;
        this.errorResetInterval = 300000; // 5 minutes

        // PRODUCTION FIX: Limit concurrent Creatomate monitoring to prevent log spam
        this.activeMonitoring = new Set(); // Track currently monitored jobs
        this.maxConcurrentMonitoring = 5; // Max 5 simultaneous monitoring jobs
        this.monitoringQueue = []; // Queue for monitoring when at limit

        // Webhook manager reference (will be set by server.js)
        this.webhookManager = null;

        // Initialize file logger for persistent logging
        this.fileLogger = getFileLogger();
    }

    /**
     * Set webhook manager for external notifications
     * @param {WebhookManager} webhookManager - Webhook manager instance
     */
    setWebhookManager(webhookManager) {
        this.webhookManager = webhookManager;
        console.log('🔗 Webhook manager integrated with queue processing');
    }

    /**
     * Send webhook notification for job events
     * @param {string} event - Event type (job.completed, job.failed, etc.)
     * @param {Object} job - Job object
     */
    async sendWebhookNotification(event, job) {
        if (!this.webhookManager) {
            // Webhook manager not configured - silent skip
            return;
        }

        try {
            // Prepare clean job data for webhook (remove sensitive info)
            const webhookData = {
                job_id: job.id,
                status: job.status,
                created_at: job.createdAt,
                started_at: job.startedAt,
                completed_at: job.completedAt,
                failed_at: job.failedAt,
                parameters: {
                    country: job.parameters.country,
                    platform: job.parameters.platform,
                    genre: job.parameters.genre,
                    contentType: job.parameters.contentType,
                    template: job.parameters.template
                },
                progress: job.progress,
                current_step: job.currentStep,
                video_url: job.videoUrl || null,
                creatomate_id: job.creatomateId || null,
                error: job.error || null,
                retry_count: job.retryCount || 0,
                processing_duration_ms:
                    job.completedAt && job.startedAt ? new Date(job.completedAt) - new Date(job.startedAt) : null
            };

            // Send webhook notification asynchronously (don't block job processing)
            this.webhookManager.sendWebhookNotification(event, webhookData).catch((error) => {
                console.warn(`⚠️ Webhook notification failed for job ${job.id}: ${error.message}`);
            });
        } catch (error) {
            console.warn(`⚠️ Failed to prepare webhook notification for job ${job.id}: ${error.message}`);
        }
    }

    /**
     * Get the next available Redis client from the connection pool
     * Round-robin load balancing across connections
     */
    getNextClient() {
        const client = this.clients[this.currentClientIndex];
        this.currentClientIndex = (this.currentClientIndex + 1) % this.poolSize;
        return client;
    }

    /**
     * Execute Redis command with connection pool and error recovery
     * @param {Function} operation - Redis operation function
     * @param {Array} args - Arguments for the operation
     * @param {string} operationName - Name of the operation for logging
     * @returns {Promise} Result of the operation
     */
    async executeWithPool(operation, args = [], operationName = 'redis_operation') {
        let lastError;

        // Try each client in the pool if needed
        for (let attempt = 0; attempt < this.poolSize; attempt++) {
            try {
                const client = this.getNextClient();
                const boundOperation = promisify(operation).bind(client);
                const result = await boundOperation(...args);

                // Reset error count on successful operation
                if (this.errorCount > 0 && Date.now() - this.lastErrorTime > this.errorResetInterval) {
                    this.errorCount = 0;
                }

                return result;
            } catch (error) {
                lastError = error;
                this.errorCount++;
                this.lastErrorTime = Date.now();

                console.warn(
                    `⚠️ Redis ${operationName} failed on attempt ${attempt + 1}/${this.poolSize}:`,
                    error.message
                );

                // If we've tried all clients, we'll break out and throw
                if (attempt === this.poolSize - 1) {
                    break;
                }

                // Small delay before trying next client
                await new Promise((resolve) => setTimeout(resolve, 50));
            }
        }

        // Alert on too many errors
        if (this.errorCount >= this.maxErrorsBeforeAlert) {
            console.error(
                `🚨 PRODUCTION ALERT: Redis error count exceeded ${this.maxErrorsBeforeAlert} in last ${this.errorResetInterval / 1000}s`
            );
        }

        throw lastError;
    }

    /**
     * Connect to Redis server (Redis v3 connects automatically)
     */
    async connect() {
        // Redis v3 connects automatically when first command is issued
        console.log('🔗 Redis client ready (v3 auto-connects)');
    }

    /**
     * Add video generation job to queue
     * @param {Object} parameters - Video generation parameters
     * @returns {Object} Created job object
     */
    async addJob(parameters) {
        const job = {
            id: `job_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
            status: 'pending',
            parameters: parameters,
            createdAt: new Date().toISOString(),
            startedAt: null,
            completedAt: null,
            creatomateId: null,
            videoUrl: null,
            retryCount: 0,
            maxRetries: 1, // Reduced from 3 to prevent excessive retries
            error: null,
            progress: 0,
            currentStep: 'Queued for processing...'
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
            console.error('❌ Failed to add job to queue:', error);
            throw error;
        }
    }

    /**
     * Get current queue status - PRODUCTION OPTIMIZED with connection pooling and timeout protection
     * @returns {Object} Queue statistics
     */
    async getQueueStatus() {
        try {
            // Add timeout protection to prevent hanging during heavy processing
            const timeoutPromise = new Promise((_, reject) => {
                setTimeout(() => reject(new Error('Queue status timeout')), 800); // 800ms timeout for Redis operations
            });

            // Use connection pool for Redis operations with load balancing
            const statusPromise = Promise.all([
                this.executeWithPool(this.getNextClient().llen, [this.keys.pending], 'llen_pending'),
                this.executeWithPool(this.getNextClient().llen, [this.keys.processing], 'llen_processing'),
                this.executeWithPool(this.getNextClient().llen, [this.keys.completed], 'llen_completed'),
                this.executeWithPool(this.getNextClient().llen, [this.keys.failed], 'llen_failed')
            ]);

            const [pending, processing, completed, failed] = await Promise.race([statusPromise, timeoutPromise]);

            return {
                pending,
                processing,
                completed,
                failed,
                total: pending + processing + completed + failed,
                _poolUsed: true // Debug flag for production monitoring
            };
        } catch (error) {
            // Enhanced error handling with production-level recovery
            if (error.message === 'Queue status timeout') {
                console.warn('⚠️ Redis queue status request timed out (system likely under heavy load)');
            } else {
                console.error('❌ Failed to get queue status:', error.message);

                // Try fallback to primary client as last resort
                try {
                    console.log('🔄 Attempting fallback to primary client...');
                    const [pending, processing, completed, failed] = await Promise.all([
                        this.llenAsync(this.keys.pending),
                        this.llenAsync(this.keys.processing),
                        this.llenAsync(this.keys.completed),
                        this.llenAsync(this.keys.failed)
                    ]);

                    console.log('✅ Fallback to primary client successful');
                    return {
                        pending,
                        processing,
                        completed,
                        failed,
                        total: pending + processing + completed + failed,
                        _fallback: true
                    };
                } catch (fallbackError) {
                    console.error('❌ Fallback to primary client also failed:', fallbackError.message);
                }
            }

            // Return safe defaults during complete Redis failure
            return {
                pending: 0,
                processing: 0,
                completed: 0,
                failed: 0,
                total: 0,
                _error: true,
                _errorMessage: error.message,
                _errorCount: this.errorCount
            };
        }
    }

    /**
     * Get all jobs with details
     * @returns {Array} All jobs as array
     */
    async getAllJobs() {
        try {
            const allJobs = await this.hgetallAsync(this.keys.jobs);
            const jobs = [];

            // Handle empty Redis database (allJobs can be null on first startup)
            if (!allJobs || Object.keys(allJobs).length === 0) {
                return [];
            }

            for (const [jobId, jobData] of Object.entries(allJobs)) {
                const jobInfo = JSON.parse(jobData);
                jobInfo.id = jobId; // Ensure job ID is included
                jobs.push(jobInfo);
            }

            return jobs;
        } catch (error) {
            console.error('❌ Failed to get all jobs:', error);
            return [];
        }
    }

    /**
     * Get specific job by ID - OPTIMIZED with performance monitoring and aggressive caching
     * @param {string} jobId - Job identifier
     * @returns {Object|null} Job object or null if not found
     */
    async getJob(jobId) {
        const startTime = Date.now();

        // PRODUCTION OPTIMIZATION: Check in-memory cache first to avoid Redis calls
        const cacheKey = `job_${jobId}`;
        if (this.jobCache && this.jobCache.has(cacheKey)) {
            const cached = this.jobCache.get(cacheKey);
            const age = Date.now() - cached.timestamp;

            // Use longer cache for completed/failed jobs (they don't change)
            const isStatic = cached.job && ['completed', 'failed', 'cancelled'].includes(cached.job.status);
            const maxAge = isStatic ? 300000 : 30000; // 5 minutes for static, 30 seconds for active

            if (age < maxAge) {
                // Cache hit - no Redis request needed
                console.log(`📋 Job cache hit for ${jobId.slice(-8)} (age: ${age}ms)`);
                return cached.job;
            }
        }

        try {
            // Add timeout protection specifically for Redis operations
            const timeoutPromise = new Promise((_, reject) => {
                setTimeout(() => reject(new Error(`Redis timeout for job ${jobId.slice(-8)}`)), 2000);
            });

            const redisPromise = this.executeWithPool(this.getNextClient().hget, [this.keys.jobs, jobId], 'hget_job');
            const jobData = await Promise.race([redisPromise, timeoutPromise]);

            const duration = Date.now() - startTime;

            // Log slow Redis operations with more context
            if (duration > 200) {
                console.warn(`⚠️ Slow Redis getJob for ${jobId.slice(-8)}: ${duration}ms (pool usage: active)`);
            }

            const job = jobData ? JSON.parse(jobData) : null;

            // Cache the result to prevent immediate re-fetching
            if (job) {
                if (!this.jobCache) this.jobCache = new Map();
                this.jobCache.set(cacheKey, {
                    job: job,
                    timestamp: Date.now()
                });

                // Clean old cache entries to prevent memory leaks
                if (this.jobCache.size > 1000) {
                    const now = Date.now();
                    for (const [key, value] of this.jobCache) {
                        if (now - value.timestamp > 600000) {
                            // 10 minutes
                            this.jobCache.delete(key);
                        }
                    }
                }
            }

            return job;
        } catch (error) {
            const duration = Date.now() - startTime;

            if (error.message.includes('timeout')) {
                console.error(`🚨 PRODUCTION ALERT: Redis timeout for job ${jobId.slice(-8)} after ${duration}ms`);

                // Return cached data if available during timeout
                const cacheKey = `job_${jobId}`;
                if (this.jobCache && this.jobCache.has(cacheKey)) {
                    const cached = this.jobCache.get(cacheKey);
                    console.log(`📋 Using stale cache for ${jobId.slice(-8)} due to Redis timeout`);
                    return cached.job;
                }
            }

            console.error(`❌ Failed to get job ${jobId.slice(-8)} (${duration}ms):`, error.message);
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

            // PRODUCTION OPTIMIZATION: Invalidate cache when job is updated
            const cacheKey = `job_${job.id}`;
            if (this.jobCache && this.jobCache.has(cacheKey)) {
                // Update cache with fresh data instead of invalidating
                this.jobCache.set(cacheKey, {
                    job: job,
                    timestamp: Date.now()
                });
                console.log(`📋 Job cache updated for ${job.id.slice(-8)}`);
            }
        } catch (error) {
            console.error(`❌ Failed to update job ${job.id}:`, error);
        }
    }

    /**
     * Start multi-worker queue processing loop
     */
    async startProcessing() {
        if (this.isProcessing) {
            console.log('⚠️ Queue processing already running');
            return;
        }

        this.isProcessing = true;
        console.log(
            `🚀 Starting multi-worker queue processing (${this.maxWorkers} max workers, concurrent: ${this.concurrentProcessing})...`
        );

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
                        console.log(
                            `⚠️ Job ${job.id} skipped - concurrent processing disabled and ${this.activeJobs.size} job(s) still processing`
                        );
                        // Put the job back at the front of the queue
                        await this.lpushAsync(this.keys.pending, jobData[1]);
                        await this.sleep(2000); // Wait before trying again
                        continue;
                    }

                    // Process job if we have available workers
                    if (this.availableWorkers > 0) {
                        this.availableWorkers--;
                        console.log(
                            `👤 Assigning job ${job.id} to worker (${this.availableWorkers}/${this.maxWorkers} workers available)`
                        );

                        // Process job asynchronously (don't await - allows multiple jobs)
                        this.processJobAsync(job).finally(() => {
                            this.availableWorkers++;
                            console.log(
                                `✅ Worker freed for job ${job.id} (${this.availableWorkers}/${this.maxWorkers} workers available)`
                            );
                        });
                    }
                }
            } catch (error) {
                console.error('❌ Queue processing error:', error);
                // Wait before retrying to avoid rapid error loops
                await this.sleep(5000);
            }
        }

        console.log('🛑 Queue processing stopped');
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
            this.addJobLog(job.id, `Job ${job.id} started with worker pool`, 'info');
            this.addJobLog(job.id, `Parameters: ${JSON.stringify(job.parameters)}`, 'info');

            // Log job start to file logger
            this.fileLogger.logJobStarted(job.id, job.workerId || 'default');

            await this.processJob(job);
        } catch (error) {
            console.error(`❌ Error in processJobAsync for job ${job.id}:`, error);
            this.addJobLog(job.id, `Job error: ${error.message}`, 'error');

            // Log job failure to file logger
            this.fileLogger.logJobFailed(job.id, error.message);
        } finally {
            // Always clean up job tracking
            this.activeJobs.delete(job.id);
            this.activeProcesses.delete(job.id);
            console.log(
                `🧹 Removed job ${job.id} from active tracking (${this.activeJobs.size}/${this.maxWorkers} active)`
            );

            // Add completion log
            this.addJobLog(job.id, 'Job processing completed and removed from active pool', 'info');

            // Log job completion to file logger (if successful)
            const finalJob = await this.getJob(job.id).catch(() => null);
            if (finalJob && finalJob.status === 'completed') {
                const duration =
                    finalJob.completedAt && finalJob.startedAt
                        ? (new Date(finalJob.completedAt) - new Date(finalJob.startedAt)) / 1000
                        : null;
                this.fileLogger.logJobCompleted(job.id, duration, {
                    status: finalJob.status,
                    videoUrl: finalJob.videoUrl,
                    creatomateId: finalJob.creatomateId
                });
            }

            // Keep logs for 10 minutes after job completion
            setTimeout(
                () => {
                    this.clearJobLogs(job.id);
                },
                10 * 60 * 1000
            ); // 10 minutes
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
        console.log(`🔍 Active jobs: ${Array.from(this.activeJobs.keys()).join(', ') || 'none'}`);
        console.log(`--- Python Script Output ---`);

        try {
            // Update job status to processing
            job.status = 'processing';
            job.startedAt = new Date().toISOString();
            job.progress = 10;
            job.currentStep = 'Starting video generation...';
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
                job.status = 'completed';
                job.completedAt = new Date().toISOString();
                job.progress = 100;
                job.currentStep = 'Movie extraction completed - process paused for review';
                job.pausedAfterExtraction = true;

                // Extract movie information from stdout for UI display
                const movieMatch = result.stdout.match(/📋 Found \d+ movies:([\s\S]*?)(?:\n\n|\n💡)/);
                if (movieMatch && movieMatch[1]) {
                    job.extractedMovies = movieMatch[1].trim();
                }

                // Remove from processing queue and add to completed
                await this.lremAsync(this.keys.processing, 1, processingJobState);
                await this.lpushAsync(this.keys.completed, JSON.stringify(job));

                // Send webhook notification for partial completion (extraction done)
                this.sendWebhookNotification('job.extraction_completed', job);
            } else if (result.videoUrl) {
                // Video is fully complete
                job.status = 'completed';
                job.completedAt = new Date().toISOString();
                job.creatomateId = result.creatomateId;
                job.videoUrl = result.videoUrl;
                job.progress = 100;
                job.currentStep = 'Video generation completed!';

                // Remove from processing queue and add to completed
                await this.lremAsync(this.keys.processing, 1, processingJobState);
                await this.lpushAsync(this.keys.completed, JSON.stringify(job));

                // Send webhook notification for full completion
                this.sendWebhookNotification('job.completed', job);
            } else if (result.creatomateId) {
                // PRODUCTION FIX: Only start Creatomate monitoring if workflow fully completed
                if (result.workflowFullyComplete) {
                    console.log(`✅ Workflow fully complete for job ${job.id} - Starting Creatomate monitoring`);

                    // Python script done but video still rendering
                    job.status = 'rendering'; // Use 'rendering' status to distinguish from fully completed
                    job.creatomateId = result.creatomateId;
                    job.videoUrl = null; // No video URL yet
                    job.progress = 90;
                    job.currentStep = 'All 7 steps completed - Video rendering with Creatomate...';

                    // Remove from processing queue and add to completed (but video not ready)
                    await this.lremAsync(this.keys.processing, 1, processingJobState);
                    await this.lpushAsync(this.keys.completed, JSON.stringify(job));

                    // Send webhook notification for script completion (video still rendering)
                    this.sendWebhookNotification('job.script_completed', job);

                    // Log Creatomate monitoring start
                    this.fileLogger.logCreatomateMonitoring(job.id, job.creatomateId, 'monitoring_started');

                    // Start monitoring Creatomate render status ONLY after full workflow completion
                    console.log(`🎬 Starting Creatomate monitoring for job ${job.id} (Render ID: ${job.creatomateId})`);
                    this.startCreatomateMonitoring(job.id, job.creatomateId);
                } else {
                    // Workflow incomplete - mark as completed but note the issue
                    console.warn(`⚠️ Job ${job.id} has Creatomate ID but workflow not fully complete:`);
                    console.warn(`   - Step 7 completed: ${result.step7Completed}`);
                    console.warn(`   - Workflow completed message: ${result.workflowCompleted}`);

                    job.status = 'completed';
                    job.creatomateId = result.creatomateId;
                    job.videoUrl = null;
                    job.progress = 85; // Not full 90% since workflow incomplete
                    job.currentStep = '⚠️ Python script completed but workflow may be incomplete - Manual check needed';
                    job.workflowIncomplete = true;

                    // Remove from processing queue and add to completed
                    await this.lremAsync(this.keys.processing, 1, processingJobState);
                    await this.lpushAsync(this.keys.completed, JSON.stringify(job));

                    // Send notification about incomplete workflow
                    this.sendWebhookNotification('job.workflow_incomplete', job);

                    // Add warning to job logs
                    this.addJobLog(
                        job.id,
                        `⚠️ Workflow may be incomplete - Step 7: ${result.step7Completed}, Workflow message: ${result.workflowCompleted}`,
                        'warning'
                    );
                    this.addJobLog(
                        job.id,
                        `🔍 Manual verification needed for Creatomate ID: ${result.creatomateId}`,
                        'info'
                    );
                }
            } else {
                // No video URL or Creatomate ID - something went wrong
                job.status = 'completed';
                job.progress = 100;
                job.currentStep = 'Script completed but no video information available';
                job.error = 'No video URL or Creatomate ID returned';

                // Remove from processing queue and add to completed
                await this.lremAsync(this.keys.processing, 1, processingJobState);
                await this.lpushAsync(this.keys.completed, JSON.stringify(job));

                // Send webhook notification for incomplete completion
                this.sendWebhookNotification('job.completed_with_issues', job);
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
                jobParameters: job.parameters
            });

            // Kill any running Python process immediately (multi-worker support)
            const activeProcess = this.activeProcesses.get(job.id);
            if (activeProcess && !activeProcess.killed) {
                console.log(`🔪 EMERGENCY: Killing Python process for failed job ${job.id}`);
                try {
                    // Force kill the process tree
                    if (process.platform === 'win32') {
                        exec(`taskkill /f /t /pid ${activeProcess.pid}`, (killError) => {
                            if (killError) {
                                console.error(`❌ Failed to kill process: ${killError.message}`);
                            } else {
                                console.log(`✅ Process ${activeProcess.pid} killed successfully`);
                            }
                        });
                    } else {
                        activeProcess.kill('SIGKILL');
                    }
                    // Cleanup will be handled by processJobAsync finally block
                } catch (killError) {
                    console.error(`❌ Error killing process: ${killError.message}`);
                }
            }

            // Store the processing job state before updating
            const processingJobState = JSON.stringify(job);

            // Mark job as FAILED immediately - reset everything for complete restart
            job.status = 'failed';
            job.error = this.categorizeError(error.message);
            job.retryCount++;
            job.progress = 0; // Reset progress to 0 for fresh start
            job.currentStep = `❌ FAILED: ${job.error}`;
            job.failedAt = new Date().toISOString();

            // Stop any active Creatomate monitoring for this job
            if (this.activeMonitoring.has(job.id)) {
                console.log(`🛑 Stopping Creatomate monitoring due to job failure: ${job.id}`);
                this.finishMonitoring(job.id);
            }

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
                job.status = 'pending';
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

                // Send webhook notification for job failure (no retry)
                this.sendWebhookNotification('job.failed_no_retry', job);
            } else {
                console.log(`💀 PERMANENT FAILURE: Job ${job.id} exceeded max retries (${job.maxRetries})`);
                console.log(`📊 Final failure reason: ${job.error}`);

                // Move to failed queue for manual review
                await this.lpushAsync(this.keys.failed, JSON.stringify(job));
                console.log(`🗂️ Job ${job.id} moved to failed queue for manual review`);

                // Send webhook notification for permanent job failure
                this.sendWebhookNotification('job.failed', job);
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
            console.log(`Will Retry: ${job.retryCount < job.maxRetries ? 'YES' : 'NO'}`);
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
        if (!errorMessage) return 'Unknown error occurred';

        const message = errorMessage.toLowerCase();

        // HeyGen API errors (highest priority - payment issues)
        if (message.includes('insufficient credit') || message.includes('movio_payment_insufficient_credit')) {
            return '💳 HeyGen Credits Exhausted - Please add credits to your HeyGen account';
        }
        if (message.includes('heygen') && (message.includes('authentication') || message.includes('unauthorized'))) {
            return '🔐 HeyGen Authentication Failed - Check your API key';
        }
        if (message.includes('heygen') && message.includes('rate limit')) {
            return '⏳ HeyGen Rate Limit Exceeded - Too many requests';
        }
        if (message.includes('heygen') && message.includes('error')) {
            return '🎭 HeyGen API Error - Service temporarily unavailable';
        }

        // Creatomate API errors
        if (message.includes('creatomate') && message.includes('insufficient credit')) {
            return '💳 Creatomate Credits Exhausted - Please add credits to your account';
        }
        if (message.includes('creatomate') && (message.includes('authentication') || message.includes('401'))) {
            return '🔐 Creatomate Authentication Failed - Check your API key';
        }
        if (message.includes('creatomate') && (message.includes('rate limit') || message.includes('429'))) {
            return '⏳ Creatomate Rate Limit Exceeded - Please wait before retrying';
        }
        if (message.includes('creatomate') && message.includes('api error')) {
            return '🎬 Creatomate API Error - Video service temporarily unavailable';
        }

        // Database and content errors
        if (
            message.includes('insufficient movies') ||
            (message.includes('only') && message.includes('found with current filters'))
        ) {
            return '🎬 Not Enough Movies Available - Try different filters';
        }
        if (message.includes('no movies found') || message.includes('database query failed')) {
            return '🗃️ No Movies Found - Change genre/platform/content type';
        }
        if (message.includes('connection failed') || message.includes('database connection failed')) {
            return '🌐 Database Connection Failed - Check internet connection';
        }

        // Screenshot and browser errors
        if (message.includes('screenshot') && message.includes('failed')) {
            return '📸 Screenshot Capture Failed - Network or website issue';
        }
        if (message.includes('browser') || message.includes('playwright')) {
            return '🌐 Browser Automation Failed - Website access issue';
        }

        // Process and system errors
        if (message.includes('killed') || message.includes('cancelled') || message.includes('stopped')) {
            return '🛑 Process Cancelled - Job was stopped by user or system';
        }
        if (message.includes('timeout') || message.includes('timed out')) {
            return '⏱️ Process Timeout - Operation took too long';
        }
        if (message.includes('memory') || message.includes('out of memory')) {
            return '🧠 Memory Error - Insufficient system memory';
        }
        if (message.includes('disk') || message.includes('space')) {
            return '💾 Disk Space Error - Insufficient storage available';
        }

        // Network and connectivity errors
        if (message.includes('network') || message.includes('connection refused') || message.includes('unreachable')) {
            return '🌐 Network Error - Check internet connection';
        }
        if (message.includes('ssl') || message.includes('certificate')) {
            return '🔒 SSL Certificate Error - Network security issue';
        }

        // File and permission errors
        if (message.includes('permission') || message.includes('access denied')) {
            return '🔒 Permission Error - File access denied';
        }
        if (message.includes('file not found') || message.includes('no such file')) {
            return '📁 File Not Found - Missing required file';
        }

        // Generic API errors
        if (message.includes('api') && message.includes('error')) {
            return '🔧 API Error - External service temporarily unavailable';
        }

        // Python/script specific errors
        if (message.includes('failed to process exactly') && message.includes('movie clips')) {
            return '🎬 Movie Processing Failed - Critical workflow error';
        }
        if (message.includes('python') || message.includes('traceback')) {
            return '🐍 Script Error - Internal processing failure';
        }

        // Fallback for any unmatched errors
        return `⚠️ ${errorMessage.substring(0, 100)}${errorMessage.length > 100 ? '...' : ''}`;
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
            /File system.*read-only/i
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
        if (output.includes('MOVIO_PAYMENT_INSUFFICIENT_CREDIT') || output.includes('Insufficient credit')) {
            return 'HeyGen credits exhausted - Please add credits to continue';
        }

        // Critical workflow failures
        if (output.includes('Failed to process exactly') && output.includes('movie clips')) {
            return 'Critical workflow failure - Movie processing failed';
        }

        // Authentication errors
        if (output.includes('Authentication failed') || output.includes('Invalid API key')) {
            return 'API authentication failed - Check your credentials';
        }

        // System resource errors
        if (output.includes('Out of memory')) {
            return 'System out of memory - Process cannot continue';
        }

        if (output.includes('No space left') || output.includes('Disk quota exceeded')) {
            return 'Insufficient disk space - Cannot continue processing';
        }

        // Generic critical error
        return 'Critical error detected - Process terminated';
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
                reason: 'Generic error - standard retry',
                delaySeconds: Math.pow(2, currentRetryCount) * 30,
                solution: 'Monitor logs for specific error details'
            };
        }

        const error = errorMessage.toLowerCase();

        // ❌ NEVER RETRY - Credit/Payment Issues
        if (error.includes('credits exhausted') || error.includes('insufficient credit') || error.includes('payment')) {
            return {
                retry: false,
                reason: 'Payment/credit issue requires manual resolution',
                delaySeconds: 0,
                solution: 'Add credits to your HeyGen/Creatomate account before retrying'
            };
        }

        // ❌ NEVER RETRY - Authentication Issues
        if (
            error.includes('authentication failed') ||
            error.includes('invalid api key') ||
            error.includes('unauthorized')
        ) {
            return {
                retry: false,
                reason: 'Authentication failure requires credential fix',
                delaySeconds: 0,
                solution: 'Check and update your API keys in environment variables'
            };
        }

        // ❌ NEVER RETRY - System Resource Issues
        if (error.includes('out of memory') || error.includes('disk space') || error.includes('quota exceeded')) {
            return {
                retry: false,
                reason: 'System resource exhaustion requires admin intervention',
                delaySeconds: 0,
                solution: 'Free up system resources (memory/disk) before retrying'
            };
        }

        // ❌ NEVER RETRY - Critical Workflow Failures (until manual review)
        if (
            error.includes('critical workflow') ||
            error.includes('movie processing failed') ||
            error.includes('database extraction failed') ||
            error.includes('no movies found') ||
            error.includes('workflow failed') ||
            error.includes('script execution failed')
        ) {
            return {
                retry: false,
                reason: 'Critical workflow failure - manual intervention required',
                delaySeconds: 0,
                solution: 'Check system logs, verify API keys, or try different movie parameters'
            };
        }

        // 🟡 LIMITED RETRY - Rate Limits (short backoff)
        if (error.includes('rate limit') || error.includes('too many requests')) {
            return {
                retry: currentRetryCount < Math.min(maxRetries, 2), // Max 2 retries for rate limits
                reason: 'Rate limit - short retry with backoff',
                delaySeconds: Math.pow(2, currentRetryCount + 2) * 60, // 4, 8, 16 minutes
                solution: 'Wait for rate limit window to reset'
            };
        }

        // 🟡 SMART RETRY - Network Issues (medium backoff)
        if (error.includes('network') || error.includes('connection') || error.includes('timeout')) {
            return {
                retry: currentRetryCount < maxRetries,
                reason: 'Network issue - medium retry with backoff',
                delaySeconds: Math.pow(2, currentRetryCount) * 60, // 1, 2, 4 minutes
                solution: 'Check internet connection stability'
            };
        }

        // 🟡 SMART RETRY - Screenshot/Browser Issues (medium backoff)
        if (error.includes('screenshot') || error.includes('browser')) {
            return {
                retry: currentRetryCount < maxRetries,
                reason: 'Screenshot/browser issue - medium retry',
                delaySeconds: Math.pow(2, currentRetryCount) * 45, // 45s, 90s, 180s
                solution: 'Website may be temporarily inaccessible'
            };
        }

        // 🟡 SMART RETRY - Database/Content Issues (longer backoff)
        if (error.includes('not enough movies')) {
            return {
                retry: currentRetryCount < Math.min(maxRetries, 1), // Only 1 retry
                reason: 'Content issue - single retry with different filters suggested',
                delaySeconds: 120, // 2 minutes
                solution: 'Try different genre/platform/content type combination'
            };
        }

        // 🟡 SMART RETRY - API Service Issues (adaptive backoff)
        if (error.includes('api error') || error.includes('service') || error.includes('temporarily unavailable')) {
            return {
                retry: currentRetryCount < maxRetries,
                reason: 'External API issue - adaptive retry',
                delaySeconds: Math.pow(2, currentRetryCount + 1) * 30, // 1, 2, 4 minutes
                solution: 'External service is experiencing issues'
            };
        }

        // 🟡 SMART RETRY - Process Cancellation (immediate retry allowed)
        if (error.includes('cancelled') || error.includes('stopped') || error.includes('killed')) {
            return {
                retry: currentRetryCount < maxRetries,
                reason: 'Process was cancelled - can retry immediately',
                delaySeconds: 30, // Short delay
                solution: 'Job was stopped, safe to retry'
            };
        }

        // ✅ DEFAULT RETRY - Unknown errors (standard exponential backoff)
        return {
            retry: currentRetryCount < maxRetries,
            reason: 'Unknown error - standard exponential backoff',
            delaySeconds: Math.pow(2, currentRetryCount) * 30, // 30s, 1m, 2m, 4m
            solution: 'Monitor logs for specific error patterns'
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

            // Track workflow completion state
            let allStepsCompleted = false;
            let step7Completed = false;
            let workflowCompleted = false;

            // Construct Python command (Using main.py modular system as requested)
            // Check if running in Docker or locally
            const isDocker = process.env.PYTHON_BACKEND_PATH === '/app';
            const scriptPath = isDocker ? 'main.py' : path.join(__dirname, '../main.py');
            const args = [
                scriptPath,
                '--country',
                country,
                '--platform',
                platform,
                '--genre',
                genre,
                '--content-type',
                contentType
            ];

            // Add template parameter if provided and not 'auto'
            if (template && template !== 'auto') {
                args.push('--heygen-template-id', template);
            }

            // Note: Vizard template ID and job ID not supported by main.py CLI
            // Removed unsupported arguments: --vizard-template-id and --job-id

            // Add pause flag if enabled
            if (pauseAfterExtraction) {
                args.push('--pause-after-extraction');
            }

            // Executing exact CLI command as requested
            console.log('🚀 Executing exact CLI command:', 'python', args.join(' '));

            // Spawn Python process
            const workingDir = isDocker ? '/app' : path.join(__dirname, '..');
            const pythonProcess = spawn('python', args, {
                cwd: workingDir,
                env: {
                    ...process.env,
                    PYTHONIOENCODING: 'utf-8',
                    PYTHONUNBUFFERED: '1',
                    JOB_ID: job.id, // Pass job ID for real-time webhook updates
                    WEBHOOK_BASE_URL: process.env.WEBHOOK_BASE_URL || 'http://localhost:3000'
                }
            });

            console.log(`📡 Real-time webhooks enabled for job: ${job.id}`);

            // Store reference to current process for cancellation (multi-worker support)
            this.activeProcesses.set(job.id, pythonProcess);
            console.log(`🔗 Stored process for job ${job.id} (${this.activeProcesses.size} active processes)`);

            let stdout = '';
            let stderr = '';

            // Handle Python process output
            pythonProcess.stdout.on('data', async (data) => {
                const output = data.toString('utf8');
                stdout += output;

                // 🚨 IMMEDIATE CRITICAL ERROR DETECTION - Stop process on fatal errors
                if (this.detectCriticalErrors(output)) {
                    console.log('🚨 CRITICAL ERROR DETECTED - Stopping process immediately');
                    if (pythonProcess && !pythonProcess.killed) {
                        pythonProcess.kill('SIGKILL');
                    }
                    reject(new Error(this.extractCriticalErrorMessage(output)));
                    return;
                }

                // Check for movie extraction completion and capture for UI display
                if (output.includes('📋 Movies extracted from database:')) {
                    // Initialize movie capture for UI display only
                    job.extractedMoviesOutput = '';
                    job.capturingMovies = true;
                }

                // Capture movie lines after the extraction header (for normal workflow)
                if (job.capturingMovies) {
                    // Look for movie lines with format "   1. Title (Year) - IMDB: Score" or similar variations
                    const movieLineMatch = output.match(/^\s+\d+\.\s+.+\(\d{4}\)\s+-\s+IMDB:/);
                    if (movieLineMatch) {
                        job.extractedMoviesOutput += output.trim() + '\n';
                        console.log(`📋 Captured movie line: ${output.trim()}`);
                    }

                    // Stop capturing when we hit the next step or completion
                    if (output.includes('✅ STEP 1 COMPLETED') || output.includes('[STEP 2/7]')) {
                        // Finalize the captured movies and immediately display in UI
                        if (job.extractedMoviesOutput.trim()) {
                            job.extractedMovies = job.extractedMoviesOutput.trim();
                            // Movies captured for UI display only

                            // Update job progress with movie extraction step and trigger UI update
                            job.progress = Math.max(job.progress, 22);
                            job.currentStep = '📋 Movies extracted - displaying in UI...';
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
                                patterns: ['STEP 1/7'],
                                progress: 15,
                                step: '🗃️ Step 1/7: Extracting movies from database...'
                            },
                            {
                                patterns: ['✅ STEP 1 COMPLETED'],
                                progress: 20,
                                step: '✅ Step 1 completed: Movies extracted successfully'
                            },

                            // Step 2: Script Generation
                            {
                                patterns: ['STEP 2/7'],
                                progress: 25,
                                step: '🤖 Step 2/7: Generating AI-powered scripts...'
                            },
                            {
                                patterns: ['✅ STEP 2 COMPLETED'],
                                progress: 35,
                                step: '✅ Step 2 completed: AI scripts generated successfully'
                            },

                            // Step 3: Asset Preparation
                            {
                                patterns: ['STEP 3/7'],
                                progress: 40,
                                step: '🎨 Step 3/7: Creating enhanced posters and clips...'
                            },
                            {
                                patterns: ['✅ STEP 3 COMPLETED'],
                                progress: 50,
                                step: '✅ Step 3 completed: Assets created successfully'
                            },

                            // Step 4: HeyGen Video Creation
                            {
                                patterns: ['STEP 4/7'],
                                progress: 55,
                                step: '🎭 Step 4/7: Creating HeyGen AI avatar videos...'
                            },
                            {
                                patterns: ['✅ STEP 4 COMPLETED'],
                                progress: 65,
                                step: '✅ Step 4 completed: HeyGen videos created successfully'
                            },

                            // Step 5: HeyGen Video Processing
                            {
                                patterns: ['STEP 5/7'],
                                progress: 70,
                                step: '⏳ Step 5/7: Processing HeyGen video URLs...'
                            },
                            {
                                patterns: ['✅ STEP 5 COMPLETED'],
                                progress: 75,
                                step: '✅ Step 5 completed: Video URLs processed successfully'
                            },

                            // Step 6: Scroll Video Generation
                            {
                                patterns: ['STEP 6/7'],
                                progress: 80,
                                step: '📱 Step 6/7: Generating scroll video overlay...'
                            },
                            {
                                patterns: ['✅ STEP 6 COMPLETED'],
                                progress: 85,
                                step: '✅ Step 6 completed: Scroll overlay generated successfully'
                            },
                            {
                                patterns: ['STEP 6/7', 'SKIPPED'],
                                progress: 85,
                                step: '⏭️ Step 6 skipped: No scroll video needed'
                            },

                            // Step 7: Creatomate Assembly
                            {
                                patterns: ['STEP 7/7'],
                                progress: 90,
                                step: '🎬 Step 7/7: Assembling final video with Creatomate...'
                            },
                            {
                                patterns: ['✅ STEP 7 COMPLETED'],
                                progress: 95,
                                step: '✅ Step 7 completed: Final video submitted for rendering'
                            },

                            // Workflow Completion
                            {
                                patterns: ['🎉 WORKFLOW COMPLETED SUCCESSFULLY'],
                                progress: 100,
                                step: '🎉 Workflow completed successfully!'
                            }
                        ];

                        // Check each pattern to find a match
                        for (const pattern of stepPatterns) {
                            const matchesAll = pattern.patterns.every((p) =>
                                output.toLowerCase().includes(p.toLowerCase())
                            );

                            if (matchesAll) {
                                // Step pattern matched - update job for UI display only
                                job.progress = Math.max(job.progress, pattern.progress);
                                job.currentStep = pattern.step;
                                progressUpdated = true;

                                // PRODUCTION FIX: Track workflow completion properly
                                if (pattern.patterns.includes('✅ STEP 7 COMPLETED')) {
                                    step7Completed = true;
                                    console.log(`✅ Step 7 completed for job ${job.id} - Final step done`);
                                }

                                if (pattern.patterns.includes('🎉 WORKFLOW COMPLETED SUCCESSFULLY')) {
                                    workflowCompleted = true;
                                    allStepsCompleted = step7Completed && workflowCompleted;
                                    console.log(
                                        `🎉 Workflow completion detected for job ${job.id} - All steps: ${allStepsCompleted}`
                                    );
                                }

                                await this.updateJob(job); // Force immediate job update for UI
                                break; // Stop at first match to avoid conflicts
                            }
                        }

                        // Note: CLI output remains unchanged - only UI logs are enhanced

                        // Legacy detection patterns (fallback for any missed cases)
                        if (!progressUpdated) {
                            if (output.includes('Connecting to database') || output.includes('extracting movies')) {
                                job.progress = Math.max(job.progress, 25);
                                job.currentStep = 'Extracting movies from database...';
                                progressUpdated = true;
                            }
                            if (output.includes('Movies processed') || output.includes('Successfully extracted')) {
                                job.progress = Math.max(job.progress, 35);
                                job.currentStep = 'Movies extracted successfully';
                                progressUpdated = true;
                            }
                            if (output.includes('Capturing StreamGank screenshots') || output.includes('Screenshot')) {
                                job.progress = Math.max(job.progress, 45);
                                job.currentStep = 'Capturing screenshots...';
                                progressUpdated = true;
                            }
                            if (output.includes('Uploading') && output.includes('Cloudinary')) {
                                job.progress = Math.max(job.progress, 55);
                                job.currentStep = 'Uploading files to Cloudinary...';
                                progressUpdated = true;
                            }
                            if (output.includes('Enriching movie data') || output.includes('AI descriptions')) {
                                job.progress = Math.max(job.progress, 65);
                                job.currentStep = 'Enriching movie data with AI...';
                                progressUpdated = true;
                            }
                            if (output.includes('HeyGen videos created') || output.includes('Creating HeyGen')) {
                                job.progress = Math.max(job.progress, 75);
                                job.currentStep = 'Creating HeyGen avatar videos...';
                                progressUpdated = true;
                            }
                            if (output.includes('Creatomate') && !output.includes('Video URL')) {
                                job.progress = Math.max(job.progress, 85);
                                job.currentStep = 'Submitting to Creatomate for rendering...';
                                progressUpdated = true;
                            }
                            if (output.includes('Video URL') || output.includes('succeeded')) {
                                job.progress = Math.max(job.progress, 95);
                                job.currentStep = 'Video rendering completed!';
                                progressUpdated = true;
                            }
                        }
                    }

                    if (progressUpdated) {
                        await this.updateJob(job);
                    }
                }
            });

            pythonProcess.stderr.on('data', (data) => {
                const output = data.toString('utf8');
                stderr += output;

                // 🚨 IMMEDIATE CRITICAL ERROR DETECTION in stderr
                if (this.detectCriticalErrors(output)) {
                    console.log('🚨 CRITICAL ERROR DETECTED in stderr - Stopping process immediately');
                    if (pythonProcess && !pythonProcess.killed) {
                        pythonProcess.kill('SIGKILL');
                    }
                    reject(new Error(this.extractCriticalErrorMessage(output)));
                    return;
                }

                // Output exactly like CLI - no prefixes
                process.stderr.write(output);

                // Capture stderr as job-specific logs (usually errors)
                this.addJobLog(job.id, output, 'error');
            });

            // Handle process completion
            pythonProcess.on('close', (code) => {
                // Clear process reference from multi-worker tracking
                this.activeProcesses.delete(job.id);
                console.log(`🧹 Cleaned up process for job ${job.id} (${this.activeProcesses.size} active processes)`);
                console.log(`\n--- Python Script Completed ---`);
                if (code !== 0) {
                    // Check for specific error messages to make them more user-friendly
                    const errorOutput = stdout + stderr;

                    // Check for Creatomate API errors (insufficient credits, etc.)
                    if (errorOutput.includes('Creatomate API error')) {
                        const creatomateErrorMatch = errorOutput.match(/Creatomate API error: (\d+) - ({.*?})/);
                        if (creatomateErrorMatch) {
                            const statusCode = creatomateErrorMatch[1];
                            let errorMessage = '';

                            try {
                                const errorData = JSON.parse(creatomateErrorMatch[2]);
                                if (statusCode === '402') {
                                    errorMessage = `💳 Insufficient Creatomate credits - ${errorData.hint || 'Please check your subscription usage'}`;
                                } else if (statusCode === '401') {
                                    errorMessage = `🔐 Creatomate authentication failed - ${errorData.hint || 'Please check your API key'}`;
                                } else if (statusCode === '429') {
                                    errorMessage = `⏳ Creatomate rate limit exceeded - ${errorData.hint || 'Please wait before retrying'}`;
                                } else if (statusCode === '400') {
                                    errorMessage = `⚠️ Invalid Creatomate request - ${errorData.hint || errorData.message || 'Please check your video parameters'}`;
                                } else {
                                    errorMessage = `🔧 Creatomate API error (${statusCode}) - ${errorData.hint || errorData.message || 'Unknown API error'}`;
                                }
                            } catch (e) {
                                errorMessage = `🔧 Creatomate API error (${statusCode}) - Please check your account status and try again`;
                            }

                            reject(new Error(errorMessage));
                            return;
                        }
                    }

                    // Check for HeyGen API errors
                    if (errorOutput.includes('HeyGen API error') || errorOutput.includes('HeyGen error')) {
                        const heygenErrorMatch = errorOutput.match(/HeyGen.*?error[:\s]+(.*?)(?:\n|$)/i);
                        if (heygenErrorMatch) {
                            const errorMsg = heygenErrorMatch[1].trim();
                            reject(
                                new Error(
                                    `🎭 HeyGen API error - ${errorMsg}. Please check your HeyGen account and API settings.`
                                )
                            );
                            return;
                        }
                    }

                    // Check for insufficient movies error (less than 3 movies found)
                    if (
                        errorOutput.includes('Insufficient movies found') ||
                        (errorOutput.includes('only') && errorOutput.includes('movie(s) available'))
                    ) {
                        const movieCountMatch = errorOutput.match(/only (\d+) movie\(s\) available/);
                        const movieCount = movieCountMatch ? movieCountMatch[1] : 'few';

                        // Try to extract movie names from the output
                        let movieNames = '';
                        const movieSectionMatch = errorOutput.match(
                            /🎬 Movies found with current filters:([\s\S]*?)(?:\n\n|\n   Please try)/
                        );
                        if (movieSectionMatch && movieSectionMatch[1]) {
                            const movieLines = movieSectionMatch[1].trim().split('\n');
                            const movies = movieLines
                                .filter((line) => line.trim().match(/^\d+\./))
                                .map((line) => line.trim().replace(/^\d+\.\s*/, ''))
                                .join(', ');
                            if (movies) {
                                movieNames = ` Found movies: ${movies}.`;
                            }
                        }

                        reject(
                            new Error(
                                `🎬 Not enough movies available - only ${movieCount} found with current filters.${movieNames} Please try different genre, platform, or content type to find more movies.`
                            )
                        );
                        return;
                    }

                    // Check for database errors
                    if (
                        errorOutput.includes('No movies found matching criteria') ||
                        errorOutput.includes('Database query failed')
                    ) {
                        reject(
                            new Error(
                                '🗃️ No movies found for the selected parameters (genre, platform, content type). Please try different filters to find available content.'
                            )
                        );
                        return;
                    }

                    // Check for connection errors
                    if (
                        errorOutput.includes('Connection failed') ||
                        errorOutput.includes('Database connection failed')
                    ) {
                        reject(
                            new Error(
                                '🌐 Database connection failed. Please check your internet connection and try again.'
                            )
                        );
                        return;
                    }

                    // Check for screenshot/browser errors
                    if (errorOutput.includes('Screenshot') && errorOutput.includes('failed')) {
                        reject(
                            new Error(
                                '📸 Screenshot capture failed. This might be due to network issues or website accessibility. Please try again.'
                            )
                        );
                        return;
                    }

                    // Generic error message for other failures
                    reject(new Error(`Video generation failed: ${stderr || 'Unknown error occurred'}`));
                    return;
                }

                // Parse results from Python output
                let creatomateId = '';
                let videoUrl = '';
                let pausedAfterExtraction = false;

                // Check if process was paused after extraction
                if (stdout.includes('PROCESS PAUSED - Movie extraction completed')) {
                    pausedAfterExtraction = true;
                    console.log('📋 Process paused after movie extraction');
                }

                // Extract Creatomate ID (UUID format)
                const creatomateMatch = stdout.match(
                    /Creatomate.*?([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})/i
                );
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
                        message: 'Movie extraction completed - process paused for review',
                        stdout: stdout,
                        stderr: stderr
                    });
                } else {
                    // PRODUCTION FIX: Only consider workflow complete if all steps actually finished
                    const workflowFullyComplete = allStepsCompleted && step7Completed && workflowCompleted;

                    console.log(`📊 Workflow completion status for job ${job.id}:`);
                    console.log(`   - Step 7 completed: ${step7Completed}`);
                    console.log(`   - Workflow completed message: ${workflowCompleted}`);
                    console.log(`   - All steps complete: ${workflowFullyComplete}`);
                    console.log(`   - Creatomate ID: ${creatomateId || 'None'}`);

                    resolve({
                        creatomateId,
                        videoUrl,
                        stdout,
                        stderr,
                        workflowFullyComplete, // Pass this flag to the job processing logic
                        step7Completed,
                        workflowCompleted
                    });
                }
            });

            // Handle process errors
            pythonProcess.on('error', (error) => {
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
                throw new Error('Job not found');
            }

            const activeJob = this.activeJobs.get(jobId);
            const activeProcess = this.activeProcesses.get(jobId);
            console.log(
                `🔍 Debug - activeJob: ${activeJob ? jobId : 'null'}, activeProcess: ${activeProcess ? activeProcess.pid : 'null'}`
            );
            console.log(`🔍 Active jobs: ${Array.from(this.activeJobs.keys()).join(', ') || 'none'}`);

            // If this job is currently processing, kill the Python process
            if (activeJob && activeProcess) {
                const processPid = activeProcess.pid;
                console.log(`🛑 Killing Python process for job ${jobId} (PID: ${processPid})`);

                try {
                    // On Windows, use taskkill for more reliable process termination
                    if (process.platform === 'win32') {
                        console.log('🪟 Using Windows taskkill for process termination');

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
                        processToKill.kill('SIGTERM');

                        // Force kill after 5 seconds if still running
                        setTimeout(() => {
                            if (processToKill && !processToKill.killed) {
                                console.log(`🔪 Force killing Python process for job ${jobId} (PID: ${processPid})`);
                                processToKill.kill('SIGKILL');
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
                console.log(
                    `🧹 Cleaned up job ${jobId} from active tracking (${this.availableWorkers}/${this.maxWorkers} workers available)`
                );
            } else {
                console.log(`⚠️ Cannot kill process - job ${jobId} is not currently processing`);
                if (!activeJob) {
                    console.log(`   - Job ${jobId} is not in active jobs`);
                } else if (!activeProcess) {
                    console.log(`   - No process reference available`);
                }
            }

            // Update job status
            job.status = 'cancelled';
            job.progress = 0;
            job.cancelledAt = new Date().toISOString();
            job.currentStep = 'Job cancelled by user';
            job.error = 'Process stopped by user request';

            // Stop any active Creatomate monitoring for this cancelled job
            if (this.activeMonitoring.has(jobId)) {
                console.log(`🛑 Stopping Creatomate monitoring for cancelled job: ${jobId}`);
                this.finishMonitoring(jobId);
            }

            // Remove from processing queue if it's there
            await this.removeFromProcessingQueue(job);

            // Update job in storage
            await this.updateJob(job);

            // Move to failed queue (cancelled jobs go here for tracking)
            await this.lpushAsync(this.keys.failed, JSON.stringify(job));

            // Send webhook notification for job cancellation
            this.sendWebhookNotification('job.cancelled', job);

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
     * Permanently delete a completed, failed, or cancelled job
     * @param {string} jobId - Job ID
     * @returns {boolean} True if successfully deleted
     */
    async deleteJob(jobId) {
        try {
            // Get the job to verify it exists and check its status
            const job = await this.getJob(jobId);
            if (!job) {
                throw new Error('Job not found');
            }

            // Only allow deletion of non-active jobs
            if (!['completed', 'failed', 'cancelled'].includes(job.status)) {
                throw new Error(
                    `Cannot delete job with status: ${job.status}. Only completed, failed, or cancelled jobs can be deleted.`
                );
            }

            // Ensure job is not currently running
            const activeJob = this.activeJobs.get(jobId);
            if (activeJob) {
                throw new Error('Cannot delete a job that is currently processing');
            }

            console.log(`🗑️ Permanently deleting job ${jobId} (status: ${job.status})`);

            // Remove from jobs hash
            await this.hdelAsync(this.keys.jobs, jobId);

            // Remove from all possible queue states (try to remove from all lists)
            // Note: We don't know exactly which queue the job is in, so try to remove from all
            const queueKeys = [this.keys.waiting, this.keys.active, this.keys.completed, this.keys.failed];

            for (const queueKey of queueKeys) {
                try {
                    // Try to remove the job from this queue
                    // Since jobs in queues might have slight formatting differences,
                    // we'll get the entire queue and filter it
                    const allJobs = await this.lrangeAsync(queueKey, 0, -1);
                    for (let i = 0; i < allJobs.length; i++) {
                        try {
                            const queueJob = JSON.parse(allJobs[i]);
                            if (queueJob.id === jobId) {
                                await this.lremAsync(queueKey, 1, allJobs[i]);
                                console.log(`🗑️ Removed job ${jobId} from queue: ${queueKey}`);
                                break;
                            }
                        } catch (parseError) {
                            // Skip malformed entries
                            continue;
                        }
                    }
                } catch (error) {
                    console.warn(`⚠️ Could not clean job from queue ${queueKey}:`, error.message);
                }
            }

            // Remove job logs and data
            await this.delAsync(`${this.keys.logs}:${jobId}`);
            await this.delAsync(`${this.keys.data}:${jobId}`);

            // Clean up in-memory data
            this.jobLogs.delete(jobId);

            // Send webhook notification for job deletion
            this.sendWebhookNotification('job.deleted', {
                ...job,
                deletedAt: new Date().toISOString()
            });

            console.log(`✅ Job ${jobId} permanently deleted from all storage`);

            return true;
        } catch (error) {
            console.error(`❌ Failed to delete job ${jobId}:`, error);
            throw error;
        }
    }

    /**
     * Stop queue processing
     */
    stopProcessing() {
        this.isProcessing = false;
        console.log('🛑 Queue processing stopped');
    }

    /**
     * Clear all queues (use with caution!)
     */
    async clearAllQueues() {
        try {
            await Promise.all([
                this.delAsync(this.keys.pending),
                this.delAsync(this.keys.processing),
                this.delAsync(this.keys.completed),
                this.delAsync(this.keys.failed),
                this.delAsync(this.keys.jobs)
            ]);
            console.log('🗑️ All queues cleared');
        } catch (error) {
            console.error('❌ Failed to clear queues:', error);
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
                    if (jobDetails && (jobDetails.status === 'completed' || jobDetails.status === 'failed')) {
                        await this.lremAsync(this.keys.processing, 1, jobStr);
                        cleanedCount++;
                        console.log(`🧹 Cleaned up orphaned processing job: ${job.id} (status: ${jobDetails.status})`);
                    }
                    // Also check for jobs stuck in processing for more than 30 minutes
                    else if (jobDetails && jobDetails.status === 'processing' && jobDetails.startedAt) {
                        const startTime = new Date(jobDetails.startedAt);
                        const now = new Date();
                        const timeDiff = now - startTime;
                        const thirtyMinutes = 30 * 60 * 1000; // 30 minutes in milliseconds

                        if (timeDiff > thirtyMinutes) {
                            // Mark as failed and remove from processing queue
                            jobDetails.status = 'failed';
                            jobDetails.error = 'Job timed out after 30 minutes';
                            jobDetails.failedAt = new Date().toISOString();

                            await this.lremAsync(this.keys.processing, 1, jobStr);
                            await this.lpushAsync(this.keys.failed, JSON.stringify(jobDetails));
                            await this.updateJob(jobDetails);

                            // Send webhook notification for timeout
                            this.sendWebhookNotification('job.timeout', jobDetails);

                            cleanedCount++;
                            console.log(
                                `🧹 Cleaned up timed out processing job: ${job.id} (running for ${Math.round(timeDiff / 60000)} minutes)`
                            );
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

            // PRODUCTION OPTIMIZATION: Clean job cache during periodic cleanup
            if (this.jobCache && this.jobCache.size > 0) {
                const now = Date.now();
                let cacheCleanedCount = 0;

                for (const [key, value] of this.jobCache) {
                    // Remove entries older than 10 minutes
                    if (now - value.timestamp > 600000) {
                        this.jobCache.delete(key);
                        cacheCleanedCount++;
                    }
                }

                if (cacheCleanedCount > 0) {
                    console.log(
                        `🧹 Cleaned up ${cacheCleanedCount} expired job cache entries (${this.jobCache.size} remaining)`
                    );
                }
            }

            return cleanedCount;
        } catch (error) {
            console.error('❌ Failed to cleanup processing queue:', error);
            return 0;
        }
    }

    /**
     * Check if system is actively processing jobs (for caching decisions)
     */
    async isActivelyProcessing() {
        try {
            // Check if we have active jobs or processing queue has items
            const hasActiveJobs = this.activeJobs.size > 0;
            const processingCount = await this.llenAsync(this.keys.processing);
            return hasActiveJobs || processingCount > 0 || this.isProcessing;
        } catch (error) {
            console.error('❌ Failed to check processing status:', error);
            // Assume processing during errors to use cached data
            return true;
        }
    }

    /**
     * Get queue statistics for monitoring - OPTIMIZED for performance during processing
     */
    async getQueueStats() {
        try {
            const status = await this.getQueueStatus();
            // Removed expensive getAllJobs() call - use queue counts for performance

            const jobsByStatus = {
                pending: status.pending,
                processing: status.processing,
                completed: status.completed,
                failed: status.failed
            };

            return {
                ...status,
                jobsByStatus,
                activeJobs: Array.from(this.activeJobs.keys()), // List of active job IDs
                activeWorkers: this.maxWorkers - this.availableWorkers,
                availableWorkers: this.availableWorkers,
                maxWorkers: this.maxWorkers,
                concurrentProcessing: this.concurrentProcessing,
                isProcessing: this.isProcessing
            };
        } catch (error) {
            console.error('❌ Failed to get queue stats:', error);
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

        if (text.includes('error') || text.includes('❌') || text.includes('failed') || text.includes('exception')) {
            return 'error';
        } else if (text.includes('warning') || text.includes('⚠️') || text.includes('warn')) {
            return 'warning';
        } else if (
            text.includes('✅') ||
            text.includes('success') ||
            text.includes('completed') ||
            text.includes('done')
        ) {
            return 'success';
        } else if (
            text.includes('step') ||
            text.includes('[step') ||
            text.includes('🔄') ||
            text.includes('🗃️') ||
            text.includes('🤖')
        ) {
            return 'step';
        } else {
            return 'info';
        }
    }

    /**
     * Add log entry for a specific job
     * @param {string} jobId - Job ID
     * @param {string} message - Log message
     * @param {string} type - Log type (info, success, warning, error, step)
     */
    addJobLog(jobId, message, type = 'info') {
        // PRODUCTION OPTIMIZED: Smart filtering - keep important step messages, filter noise
        const shouldSkipLog =
            // CLEAN TIMELINE VIEW: Only show essential workflow steps
            // Filter out ALL detailed technical messages

            message.includes('Parameters: {') ||
            message.includes('Job job_') ||
            message.includes('started with worker') ||
            message.includes('Queue position:') ||
            message.includes('Queue stats') ||
            message.includes('Processing job') ||
            message.includes('Using settings') ||
            message.includes('cached script') ||
            message.includes('cached asset') ||
            message.includes('Loaded') ||
            message.includes('Found existing') ||
            message.includes('Loading existing') ||
            message.includes('completion and removed') ||
            message.includes('Apps directory') ||
            message.includes('Database connection') ||
            message.includes('RedisService') ||
            message.includes('processing completed') ||
            // Filter out detailed technical messages
            (message.includes('Creating enhanced posters') && !message.includes('✅')) ||
            (message.includes('Generating scripts for') && !message.includes('[STEP')) ||
            (message.includes('waiting for video completion') && !message.includes('STEP')) ||
            // CLEAN TIMELINE: Filter out "started" messages - only show "completed"
            (message.includes('Step ') && message.includes('/7') && message.includes('started')) ||
            (message.includes('🗃️ Step') && !message.includes('✅')) ||
            (message.includes('🤖 Step') && !message.includes('✅')) ||
            (message.includes('📦 Step') && !message.includes('✅')) ||
            (message.includes('🎬 Step') && !message.includes('✅')) ||
            (message.includes('⏳ Step') && !message.includes('✅')) ||
            (message.includes('📊 Step') && !message.includes('✅')) ||
            (message.includes('🎯 Step') && !message.includes('✅'));

        if (shouldSkipLog) {
            // Still log to console for debugging, but don't store for GUI
            console.log(`🔇 [${jobId.slice(-8)}] FILTERED: ${message.trim()}`);
            return;
        }

        if (!this.jobLogs.has(jobId)) {
            this.jobLogs.set(jobId, []);
        }

        const logEntry = {
            timestamp: new Date().toISOString(),
            message: message.trim(),
            type: type
        };

        const logs = this.jobLogs.get(jobId);
        logs.push(logEntry);

        // Keep only last 200 log entries per job
        if (logs.length > 200) {
            logs.splice(0, logs.length - 200);
        }

        // Clean logging - only essential messages
        if (
            type === 'error' ||
            message.includes('STEP') ||
            message.includes('completed') ||
            message.includes('Video is ready')
        ) {
            this.fileLogger.logJobEvent(jobId, 'job_log', message.trim(), { source: 'queue_manager' }, type);
            console.log(`📝 [${jobId.slice(-8)}] ${type.toUpperCase()}: ${message.trim()}`);
        }
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
                console.log('🧹 Stopped periodic cleanup');
            }

            await this.quitAsync();
            console.log('🔌 Redis connection closed');
        } catch (error) {
            console.error('❌ Error closing Redis connection:', error);
        }
    }

    /**
     * Start monitoring Creatomate render status and update job when complete
     * @param {string} jobId - Job ID to update
     * @param {string} creatomateId - Creatomate render ID
     */
    async startCreatomateMonitoring(jobId, creatomateId) {
        if (!creatomateId) {
            console.error(`❌ Cannot monitor Creatomate for job ${jobId}: No render ID provided`);
            return;
        }

        // PRODUCTION FIX: Concurrency control to prevent log spam with multiple jobs
        if (this.activeMonitoring.size >= this.maxConcurrentMonitoring) {
            this.monitoringQueue.push({ jobId, creatomateId });
            console.log(
                `📋 Queued monitoring: ${jobId} (${this.monitoringQueue.length} in queue, ${this.activeMonitoring.size} active)`
            );
            return;
        }

        // Add to active monitoring set
        this.activeMonitoring.add(jobId);

        let attempts = 0;
        const maxAttempts = 4; // Reduced to 4 - webhooks handle most cases
        let checkInterval = 300000; // Start with 5 minutes (webhook backup only)
        const maxInterval = 600000; // Max 10 minutes between checks
        let lastLoggedStatus = null;
        let lastProgressUpdate = 0;

        // Single startup log
        console.log(
            `🎬 Starting webhook-backup monitoring [${this.activeMonitoring.size}/${this.maxConcurrentMonitoring}]: ${jobId} → ${creatomateId}`
        );
        console.log(
            `🔗 Primary: Webhook notifications | 🔄 Backup: ${maxAttempts} checks over ${Math.round((maxAttempts * checkInterval) / 60000)}min`
        );

        const checkStatus = async () => {
            attempts++;

            // Check if job has failed before making API calls
            try {
                const currentJob = await this.getJob(jobId);
                if (currentJob && currentJob.status === 'failed') {
                    console.log(`🛑 Stopping Creatomate monitoring for failed job: ${jobId}`);
                    this.finishMonitoring(jobId);
                    return;
                }
            } catch (jobCheckError) {
                // Continue monitoring if we can't check job status
                console.warn(`⚠️ Could not verify job status for ${jobId}: ${jobCheckError.message}`);
            }

            try {
                const response = await this.checkCreatomateStatusDirect(creatomateId);

                if (
                    response.success &&
                    (response.status === 'completed' || response.status === 'succeeded') &&
                    response.url
                ) {
                    // Video ready - ALWAYS log success
                    console.log(`✅ Video ready: ${jobId} → ${response.url} (status: ${response.status})`);
                    await this.updateJobWithVideo(jobId, response.url);
                    this.finishMonitoring(jobId);
                    return;
                } else if (response.success && (response.status === 'failed' || response.status === 'error')) {
                    // CRITICAL FIX: Handle failed render by triggering webhook notification
                    console.log(`❌ MONITORING DETECTED: Render failed for ${jobId} → Status: ${response.status}`);

                    // Get detailed error information from Creatomate response
                    let errorMessage = 'Render failed';
                    if (response.error) {
                        errorMessage = response.error;
                    } else if (response.data && response.data.error) {
                        errorMessage = response.data.error;
                    } else if (response.data && response.data.message) {
                        errorMessage = response.data.message;
                    }

                    console.log(`❌ Error details: ${errorMessage}`);
                    await this.markJobAsRenderFailed(jobId, creatomateId, errorMessage);
                    this.finishMonitoring(jobId);
                    return;
                } else if (response.success && response.status) {
                    const status = response.status.toLowerCase();

                    // WEBHOOK-BACKUP LOGGING: Less frequent since webhooks handle most updates
                    const shouldLog = status !== lastLoggedStatus || attempts === 1;

                    if (shouldLog) {
                        console.log(
                            `⏳ Backup check ${jobId}: ${status} [${attempts}/${maxAttempts}] (webhook primary)`
                        );
                        lastLoggedStatus = status;
                    }

                    // SMART PROGRESS UPDATES: Only every 2nd attempt or significant progress
                    const now = Date.now();
                    const shouldUpdateProgress = now - lastProgressUpdate > 120000 || attempts % 2 === 0;

                    if (shouldUpdateProgress) {
                        await this.updateJobRenderingProgress(jobId, status, attempts, maxAttempts);
                        lastProgressUpdate = now;
                    }

                    // PROGRESSIVE INTERVALS: Start fast, slow down over time
                    if (attempts > 3) {
                        checkInterval = Math.min(maxInterval, checkInterval + 30000); // Increase by 30s
                    }
                } else if (response.success === false) {
                    // MINIMAL ERROR LOGGING: Only every 3rd error
                    if (attempts % 3 === 1) {
                        console.warn(`⚠️ API error ${jobId}: ${response.error}`);
                    }
                }

                // Schedule next check or timeout
                if (attempts < maxAttempts) {
                    setTimeout(checkStatus, checkInterval);
                } else {
                    console.log(`⏰ Timeout: ${jobId} after ${maxAttempts} attempts`);
                    await this.markJobAsRenderTimeout(jobId, creatomateId);
                    this.finishMonitoring(jobId);
                }
            } catch (error) {
                // MINIMAL ERROR LOGGING: Only every 3rd error
                if (attempts % 3 === 1) {
                    console.error(`❌ Error ${jobId}: ${error.message}`);
                }

                if (attempts < maxAttempts) {
                    setTimeout(checkStatus, Math.min(120000, checkInterval)); // Cap error retry at 2min
                } else {
                    await this.markJobAsRenderTimeout(jobId, creatomateId);
                    this.finishMonitoring(jobId);
                }
            }
        };

        // Start backup monitoring with longer delay - webhooks handle immediate updates
        setTimeout(checkStatus, 120000); // 2 minute delay for webhook backup
    }

    /**
     * Mark job as render failed and send webhook notification (triggered by monitoring)
     * @param {string} jobId - Job ID
     * @param {string} creatomateId - Creatomate render ID
     * @param {string} error - Error message
     */
    async markJobAsRenderFailed(jobId, creatomateId, error) {
        try {
            console.log(`❌ MONITORING FAILURE: Marking job ${jobId} as render failed`);

            const job = await this.getJob(jobId);
            if (!job) {
                console.error(`❌ Job not found: ${jobId}`);
                return;
            }

            // Update job status to failed
            job.status = 'failed';
            job.currentStep = `❌ Video rendering failed: ${error}`;
            job.error = error;
            job.failedAt = new Date().toISOString();

            await this.updateJob(job);
            await this.addJobLog(job.id, `❌ Render failed: ${error}`, 'error');

            console.log(`📝 Job ${jobId} marked as failed: ${error}`);

            // Send real-time update to frontend (same as webhook endpoint)
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
                        console.log(`📡 MONITORING: Sent render failure update to job ${job.id} frontend client`);
                    } catch (sseError) {
                        console.warn(`⚠️ Failed to send SSE to job ${job.id} client:`, sseError.message);
                    }
                });
            }

            // Trigger external webhook notifications
            if (this.webhookManager) {
                await this.webhookManager.sendWebhookNotification('job.failed', {
                    job_id: job.id,
                    error: job.error,
                    parameters: job.parameters
                });
            }

            console.log(`✅ MONITORING: Job ${jobId} failure notifications sent`);
        } catch (error) {
            console.error(`❌ Failed to mark job ${jobId} as render failed:`, error);
        }
    }

    /**
     * Clean up monitoring and start next queued job
     */
    finishMonitoring(jobId) {
        this.activeMonitoring.delete(jobId);

        // Start next job in queue if any
        if (this.monitoringQueue.length > 0) {
            const next = this.monitoringQueue.shift();
            console.log(`📋 Starting queued monitoring: ${next.jobId} (${this.monitoringQueue.length} remaining)`);
            setTimeout(() => this.startCreatomateMonitoring(next.jobId, next.creatomateId), 5000);
        }
    }

    /**
     * Direct Creatomate API status check
     * @param {string} renderId - Creatomate render ID
     * @returns {Promise<Object>} Status response
     */
    async checkCreatomateStatusDirect(renderId) {
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

                return {
                    success: true,
                    status: status,
                    url: url,
                    data: result
                };
            } else {
                return {
                    success: false,
                    error: `HTTP ${response.status}: ${response.statusText}`
                };
            }
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    /**
     * Update job with final video URL when Creatomate completes
     * @param {string} jobId - Job ID
     * @param {string} videoUrl - Final video URL
     */
    async updateJobWithVideo(jobId, videoUrl) {
        try {
            const job = await this.getJob(jobId);
            if (!job) {
                console.error(`❌ Cannot update job ${jobId} with video: Job not found`);
                return;
            }

            // Update job with final video URL
            job.status = 'completed';
            job.videoUrl = videoUrl;
            job.progress = 100;
            job.completedAt = new Date().toISOString();
            job.currentStep = '🎉 Video rendering completed successfully!';

            await this.updateJob(job);

            // Send webhook notification for full completion
            this.sendWebhookNotification('job.completed', job);

            console.log(`🎬 Job ${jobId} updated with final video: ${videoUrl}`);
            this.addJobLog(jobId, `🎬 Video rendering completed: ${videoUrl}`, 'success');
            this.addJobLog(jobId, `✅ Final video is ready for viewing and download`, 'success');

            // Log video completion to file logger
            this.fileLogger.logCreatomateMonitoring(jobId, job.creatomateId || 'unknown', 'completed', { videoUrl });
        } catch (error) {
            console.error(`❌ Failed to update job ${jobId} with video:`, error.message);
        }
    }

    /**
     * Update job rendering progress
     * @param {string} jobId - Job ID
     * @param {string} status - Creatomate status
     * @param {number} attempts - Current attempt number
     * @param {number} maxAttempts - Maximum attempts
     */
    async updateJobRenderingProgress(jobId, status, attempts, maxAttempts) {
        try {
            const job = await this.getJob(jobId);
            if (!job) return;

            // Calculate progress based on attempts and status
            let progressPercent = 90 + (attempts / maxAttempts) * 10;

            if (status.includes('render') || status.includes('process')) {
                progressPercent = Math.min(95, progressPercent);
            }

            job.progress = Math.round(progressPercent);
            job.currentStep = `🎬 Rendering video: ${status.charAt(0).toUpperCase() + status.slice(1)}... (${attempts}/${maxAttempts})`;

            await this.updateJob(job);

            // Add periodic log updates (every 4th attempt = every 2 minutes)
            if (attempts % 4 === 0) {
                this.addJobLog(jobId, `⏳ Video render status: ${status} (check ${attempts}/${maxAttempts})`, 'info');
            }
        } catch (error) {
            console.error(`❌ Failed to update job ${jobId} rendering progress:`, error.message);
        }
    }

    /**
     * Mark job as render timeout
     * @param {string} jobId - Job ID
     * @param {string} creatomateId - Creatomate render ID
     */
    async markJobAsRenderTimeout(jobId, creatomateId) {
        try {
            const job = await this.getJob(jobId);
            if (!job) return;

            job.status = 'completed';
            job.progress = 95;
            job.currentStep = `⚠️ Video render timeout - Check manually: ${creatomateId}`;
            job.renderTimeout = true;
            job.timeoutAt = new Date().toISOString();

            await this.updateJob(job);

            this.addJobLog(jobId, `⚠️ Video rendering timed out after 20 minutes`, 'warning');
            this.addJobLog(
                jobId,
                `🔍 Check render manually: python main.py --check-creatomate ${creatomateId}`,
                'info'
            );

            // Send webhook notification for timeout
            this.sendWebhookNotification('job.render_timeout', job);

            console.log(`⚠️ Job ${jobId} marked as render timeout (Creatomate ID: ${creatomateId})`);
        } catch (error) {
            console.error(`❌ Failed to mark job ${jobId} as render timeout:`, error.message);
        }
    }

    /**
     * Check existing jobs for Creatomate monitoring needs (startup recovery)
     */
    async checkExistingJobsForCreatomateMonitoring() {
        try {
            console.log('🔍 Checking existing jobs for Creatomate monitoring needs...');

            const allJobs = await this.getAllJobs();
            let monitoringStarted = 0;

            for (const job of allJobs) {
                // Find jobs that have Creatomate ID but no video URL and status is 'completed' or 'rendering'
                if (job.creatomateId && !job.videoUrl && ['completed', 'rendering'].includes(job.status)) {
                    // PRODUCTION FIX: Only start monitoring for jobs that don't have workflow issues
                    if (job.workflowIncomplete) {
                        console.log(`⚠️ Skipping job ${job.id} - marked as workflow incomplete`);
                        continue;
                    }

                    console.log(`🎬 Found job ${job.id} needing Creatomate monitoring (ID: ${job.creatomateId})`);

                    // Update status to 'rendering' if it's 'completed' without video
                    if (job.status === 'completed') {
                        job.status = 'rendering';
                        job.currentStep = 'Video rendering in progress with Creatomate...';
                        await this.updateJob(job);
                    }

                    // Start monitoring
                    this.startCreatomateMonitoring(job.id, job.creatomateId);
                    monitoringStarted++;
                }
            }

            if (monitoringStarted > 0) {
                console.log(`✅ Started Creatomate monitoring for ${monitoringStarted} existing jobs`);
            } else {
                console.log('📋 No existing jobs need Creatomate monitoring');
            }
        } catch (error) {
            console.error('❌ Error checking existing jobs for Creatomate monitoring:', error.message);
        }
    }
}

module.exports = VideoQueueManager;
