const redis = require('redis');
const { spawn, exec } = require('child_process');
const path = require('path');

/**
 * Redis-based Video Queue Manager
 * Handles video generation jobs with persistence, retry logic, and real-time updates
 */
class VideoQueueManager {
    constructor() {
        // Redis client configuration - Redis Cloud
        // Try without TLS first (some Redis Cloud instances don't require it)
        this.client = redis.createClient({
            socket: {
                host: 'redis-13734.c292.ap-southeast-1-1.ec2.redns.redis-cloud.com',
                port: 13734,
                // Remove TLS for now - will add back if needed
            },
            password: '6zhDOqJpo5Z6EYsTfBoZF1d5oPVo7X67',
            retryDelayOnFailover: 100,
            enableReadyCheck: false,
            maxRetriesPerRequest: null,
        });

        // Event handlers for Redis connection
        this.client.on('error', (err) => {
            console.error('❌ Redis Client Error:', err);
        });

        this.client.on('connect', () => {
            console.log('✅ Connected to Redis server');
        });

        this.client.on('ready', () => {
            console.log('🚀 Redis client ready for operations');
        });

        // Queue processing state
        this.isProcessing = false;
        this.currentJob = null;
        this.currentProcess = null; // Track the current Python process

        // Redis queue keys
        this.keys = {
            pending: 'streamgank:queue:pending',
            processing: 'streamgank:queue:processing',
            completed: 'streamgank:queue:completed',
            failed: 'streamgank:queue:failed',
            jobs: 'streamgank:jobs',
        };
    }

    /**
     * Connect to Redis server
     */
    async connect() {
        try {
            await this.client.connect();
            console.log('🔗 Redis connection established');
        } catch (error) {
            console.error('❌ Failed to connect to Redis:', error);
            throw error;
        }
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
            maxRetries: 3,
            error: null,
            progress: 0,
            currentStep: 'Queued for processing...',
        };

        try {
            // Add to pending queue (FIFO - First In, First Out)
            await this.client.lPush(this.keys.pending, JSON.stringify(job));

            // Store job details in hash for quick lookup
            await this.client.hSet(this.keys.jobs, job.id, JSON.stringify(job));

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
     * Get current queue status
     * @returns {Object} Queue statistics
     */
    async getQueueStatus() {
        try {
            const [pending, processing, completed, failed] = await Promise.all([this.client.lLen(this.keys.pending), this.client.lLen(this.keys.processing), this.client.lLen(this.keys.completed), this.client.lLen(this.keys.failed)]);

            return {
                pending,
                processing,
                completed,
                failed,
                total: pending + processing + completed + failed,
            };
        } catch (error) {
            console.error('❌ Failed to get queue status:', error);
            return { pending: 0, processing: 0, completed: 0, failed: 0, total: 0 };
        }
    }

    /**
     * Get all jobs with details
     * @returns {Object} All jobs indexed by job ID
     */
    async getAllJobs() {
        try {
            const allJobs = await this.client.hGetAll(this.keys.jobs);
            const jobs = {};

            for (const [jobId, jobData] of Object.entries(allJobs)) {
                jobs[jobId] = JSON.parse(jobData);
            }

            return jobs;
        } catch (error) {
            console.error('❌ Failed to get all jobs:', error);
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
            const jobData = await this.client.hGet(this.keys.jobs, jobId);
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
            await this.client.hSet(this.keys.jobs, job.id, JSON.stringify(job));
        } catch (error) {
            console.error(`❌ Failed to update job ${job.id}:`, error);
        }
    }

    /**
     * Start queue processing loop
     */
    async startProcessing() {
        if (this.isProcessing) {
            console.log('⚠️ Queue processing already running');
            return;
        }

        this.isProcessing = true;
        console.log('🚀 Starting queue processing worker...');

        // Main processing loop
        while (this.isProcessing) {
            try {
                // Blocking pop from pending queue (waits up to 5 seconds)
                const jobData = await this.client.brPop(this.keys.pending, 5);

                if (jobData && jobData.element) {
                    const job = JSON.parse(jobData.element);
                    await this.processJob(job);
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
     * Process individual video generation job
     * @param {Object} job - Job to process
     */
    async processJob(job) {
        // Job processing (UI queue management)
        console.log(`\n🔄 Starting job: ${job.id}`);
        console.log(`📋 Parameters:`, job.parameters);
        console.log(`--- Python Script Output ---`);

        try {
            // Update job status to processing
            job.status = 'processing';
            job.startedAt = new Date().toISOString();
            job.progress = 10;
            job.currentStep = 'Starting video generation...';
            this.currentJob = job;

            // Move to processing queue and update job store
            await this.client.lPush(this.keys.processing, JSON.stringify(job));
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
                await this.client.lRem(this.keys.processing, 1, processingJobState);
                await this.client.lPush(this.keys.completed, JSON.stringify(job));
            } else if (result.videoUrl) {
                // Video is fully complete
                job.status = 'completed';
                job.completedAt = new Date().toISOString();
                job.creatomateId = result.creatomateId;
                job.videoUrl = result.videoUrl;
                job.progress = 100;
                job.currentStep = 'Video generation completed!';

                // Remove from processing queue and add to completed
                await this.client.lRem(this.keys.processing, 1, processingJobState);
                await this.client.lPush(this.keys.completed, JSON.stringify(job));
            } else if (result.creatomateId) {
                // Python script done but video still rendering
                job.status = 'completed'; // Mark as completed for Python script
                job.creatomateId = result.creatomateId;
                job.videoUrl = null; // No video URL yet
                job.progress = 90;
                job.currentStep = 'Python script completed, video rendering in progress...';

                // Remove from processing queue and add to completed (but video not ready)
                await this.client.lRem(this.keys.processing, 1, processingJobState);
                await this.client.lPush(this.keys.completed, JSON.stringify(job));
            } else {
                // No video URL or Creatomate ID - something went wrong
                job.status = 'completed';
                job.progress = 100;
                job.currentStep = 'Script completed but no video information available';
                job.error = 'No video URL or Creatomate ID returned';

                // Remove from processing queue and add to completed
                await this.client.lRem(this.keys.processing, 1, processingJobState);
                await this.client.lPush(this.keys.completed, JSON.stringify(job));
            }

            await this.updateJob(job);

            // Set TTL for completed jobs (24 hours)
            await this.client.expire(`${this.keys.jobs}:${job.id}`, 86400);

            console.log(`\n--- Job Completed ---`);
            console.log(`✅ ${job.id} completed successfully`);
            if (job.videoUrl) {
                console.log(`🎬 Video URL: ${job.videoUrl}`);
            }
        } catch (error) {
            console.error(`❌ Job failed: ${job.id}`, error);

            // Store the processing job state before updating
            const processingJobState = JSON.stringify(job);

            // Handle job failure
            job.status = 'failed';
            job.error = error.message;
            job.retryCount++;
            job.progress = 0;
            job.currentStep = `Failed: ${error.message}`;

            // Retry logic
            if (job.retryCount < job.maxRetries) {
                console.log(`🔄 Retrying job: ${job.id} (attempt ${job.retryCount + 1}/${job.maxRetries})`);
                job.status = 'pending';
                job.currentStep = 'Queued for retry...';
                await this.client.lPush(this.keys.pending, JSON.stringify(job));
            } else {
                console.log(`💀 Job permanently failed: ${job.id} (max retries exceeded)`);
                await this.client.lPush(this.keys.failed, JSON.stringify(job));
            }

            // Remove from processing queue using the original processing state
            await this.client.lRem(this.keys.processing, 1, processingJobState);
            await this.updateJob(job);
        }

        this.currentJob = null;
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
            const scriptPath = path.join(__dirname, '../main.py');
            const args = [scriptPath, '--country', country, '--platform', platform, '--genre', genre, '--content-type', contentType];

            // Add template parameter if provided and not 'auto'
            if (template && template !== 'auto') {
                args.push('--heygen-template-id', template);
            }

            // Add pause flag if enabled
            if (pauseAfterExtraction) {
                args.push('--pause-after-extraction');
            }

            // Executing exact CLI command as requested
            console.log('🚀 Executing exact CLI command:', 'python', args.join(' '));

            // Spawn Python process
            const pythonProcess = spawn('python', args, {
                cwd: path.join(__dirname, '..'),
                env: {
                    ...process.env,
                    PYTHONIOENCODING: 'utf-8',
                    PYTHONUNBUFFERED: '1',
                },
            });

            // Store reference to current process for cancellation
            this.currentProcess = pythonProcess;

            let stdout = '';
            let stderr = '';

            // Handle Python process output
            pythonProcess.stdout.on('data', async (data) => {
                const output = data.toString('utf8');
                stdout += output;

                // Check for movie extraction completion and log movie names
                if (output.includes('📋 Movies extracted from database:')) {
                    console.log('\n🎬 Movies successfully extracted - details will be shown in UI');
                }

                // Output exactly like CLI - no prefixes
                process.stdout.write(output);

                // Update job progress and status based on output
                if (job) {
                    let progressUpdated = false;

                    // First check for CLI percentage progress (like 3%, 5%, 10%, etc.)
                    // Handle different progress bar formats
                    const percentageMatches = [
                        output.match(/(\d{1,3})%/), // Simple percentage: 5%
                        output.match(/\[.*?(\d{1,3})%.*?\]/), // Progress bar: [=====> 25%    ]
                        output.match(/Progress:\s*(\d{1,3})%/i), // Progress: 50%
                        output.match(/(\d{1,3})%\s*\|/), // 75% |████████
                        output.match(/(\d{1,3})%\s*complete/i), // 90% complete
                    ];

                    for (const match of percentageMatches) {
                        if (match && match[1]) {
                            const percentage = parseInt(match[1]);
                            // Only update if it's a reasonable progress value and higher than current
                            // Allow 1% increments but avoid going backwards
                            if (percentage >= 0 && percentage <= 100 && percentage > job.progress) {
                                // Try to extract more context about what's being processed
                                let stepContext = 'Processing';
                                const lowerOutput = output.toLowerCase();

                                // More specific context detection
                                if (lowerOutput.includes('download')) stepContext = 'Downloading';
                                else if (lowerOutput.includes('upload')) stepContext = 'Uploading';
                                else if (lowerOutput.includes('screenshot')) stepContext = 'Capturing screenshots';
                                else if (lowerOutput.includes('scroll')) stepContext = 'Creating scroll video';
                                else if (lowerOutput.includes('render')) stepContext = 'Rendering';
                                else if (lowerOutput.includes('convert')) stepContext = 'Converting';
                                else if (lowerOutput.includes('extract')) stepContext = 'Extracting data';
                                else if (lowerOutput.includes('generat')) stepContext = 'Generating content';
                                else if (lowerOutput.includes('creat')) stepContext = 'Creating';
                                else if (lowerOutput.includes('process')) stepContext = 'Processing';
                                else if (lowerOutput.includes('analyz')) stepContext = 'Analyzing';
                                else if (lowerOutput.includes('fetch')) stepContext = 'Fetching data';
                                else if (lowerOutput.includes('build')) stepContext = 'Building';

                                // Try to extract more specific details from the line
                                let additionalContext = '';
                                const contextMatch = output.match(/([A-Za-z\s]+).*?(\d{1,3})%/);
                                if (contextMatch && contextMatch[1]) {
                                    const detectedContext = contextMatch[1].trim();
                                    if (detectedContext.length > 3 && detectedContext.length < 50) {
                                        additionalContext = ` - ${detectedContext}`;
                                    }
                                }

                                job.progress = percentage;
                                job.currentStep = `${stepContext}... ${percentage}%${additionalContext}`;
                                progressUpdated = true;
                                // Progress tracked internally - no extra logging to keep output clean
                                break; // Exit loop once we find a match
                            }
                        }
                    }

                    // More detailed progress tracking (fallback if no percentage found)
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

                    if (progressUpdated) {
                        await this.updateJob(job);
                    }
                }
            });

            pythonProcess.stderr.on('data', (data) => {
                const output = data.toString('utf8');
                stderr += output;
                // Output exactly like CLI - no prefixes
                process.stderr.write(output);
            });

            // Handle process completion
            pythonProcess.on('close', (code) => {
                // Clear process reference
                if (this.currentProcess === pythonProcess) {
                    this.currentProcess = null;
                }
                console.log(`\n--- Python Script Completed ---`);
                if (code !== 0) {
                    // Check for specific error messages to make them more user-friendly
                    const errorOutput = stdout + stderr;

                    // Check for insufficient movies error (less than 3 movies found)
                    if (errorOutput.includes('Insufficient movies found') || (errorOutput.includes('only') && errorOutput.includes('movie(s) available'))) {
                        const movieCountMatch = errorOutput.match(/only (\d+) movie\(s\) available/);
                        const movieCount = movieCountMatch ? movieCountMatch[1] : 'few';

                        // Try to extract movie names from the output
                        let movieNames = '';
                        const movieSectionMatch = errorOutput.match(/🎬 Movies found with current filters:([\s\S]*?)(?:\n\n|\n   Please try)/);
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

                        reject(new Error(`Not enough movies available - only ${movieCount} found with current filters.${movieNames} Please try different genre, platform, or content type to find more movies.`));
                        return;
                    }

                    if (errorOutput.includes('No movies found matching criteria') || errorOutput.includes('Database query failed')) {
                        reject(new Error('No movies found for the selected parameters (genre, platform, content type). Please try different filters to find available content.'));
                        return;
                    }

                    if (errorOutput.includes('Connection failed') || errorOutput.includes('Database connection failed')) {
                        reject(new Error('Database connection failed. Please check your internet connection and try again.'));
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
                        message: 'Movie extraction completed - process paused for review',
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
            const processingItems = await this.client.lRange(this.keys.processing, 0, -1);

            // Find and remove the job
            for (let i = 0; i < processingItems.length; i++) {
                const item = JSON.parse(processingItems[i]);
                if (item.id === job.id) {
                    // Remove this specific item from the list
                    await this.client.lRem(this.keys.processing, 1, processingItems[i]);
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

            console.log(`🔍 Debug - currentJob: ${this.currentJob ? this.currentJob.id : 'null'}, requested jobId: ${jobId}, currentProcess: ${this.currentProcess ? this.currentProcess.pid : 'null'}`);

            // If this is the currently processing job, kill the Python process
            if (this.currentJob && this.currentJob.id === jobId && this.currentProcess) {
                console.log(`🛑 Killing Python process for job ${jobId} (PID: ${this.currentProcess.pid})`);

                try {
                    // On Windows, use taskkill for more reliable process termination
                    if (process.platform === 'win32') {
                        console.log('🪟 Using Windows taskkill for process termination');

                        // Kill the process tree (including child processes)
                        exec(`taskkill /pid ${this.currentProcess.pid} /t /f`, (error, stdout, stderr) => {
                            if (error) {
                                console.error(`❌ Error killing process: ${error}`);
                            } else {
                                console.log(`✅ Process ${this.currentProcess.pid} killed successfully`);
                            }
                        });
                    } else {
                        // Unix-like systems: use SIGTERM first, then SIGKILL
                        this.currentProcess.kill('SIGTERM');

                        // Force kill after 5 seconds if still running
                        setTimeout(() => {
                            if (this.currentProcess && !this.currentProcess.killed) {
                                console.log(`🔪 Force killing Python process for job ${jobId}`);
                                this.currentProcess.kill('SIGKILL');
                            }
                        }, 5000);
                    }
                } catch (error) {
                    console.error(`❌ Failed to kill process: ${error}`);
                }

                this.currentProcess = null;
                this.currentJob = null;
            } else {
                console.log(`⚠️ Cannot kill process - either job is not currently processing or process reference is missing`);
                if (!this.currentJob) {
                    console.log(`   - No current job running`);
                } else if (this.currentJob.id !== jobId) {
                    console.log(`   - Current job ID (${this.currentJob.id}) doesn't match requested job ID (${jobId})`);
                } else if (!this.currentProcess) {
                    console.log(`   - No process reference available`);
                }
            }

            // Update job status
            job.status = 'cancelled';
            job.progress = 0;
            job.cancelledAt = new Date().toISOString();
            job.currentStep = 'Job cancelled by user';
            job.error = 'Process stopped by user request';

            // Remove from processing queue if it's there
            await this.removeFromProcessingQueue(job);

            // Update job in storage
            await this.updateJob(job);

            // Move to failed queue (cancelled jobs go here for tracking)
            await this.client.lPush(this.keys.failed, JSON.stringify(job));

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
        console.log('🛑 Queue processing stopped');
    }

    /**
     * Clear all queues (use with caution!)
     */
    async clearAllQueues() {
        try {
            await Promise.all([this.client.del(this.keys.pending), this.client.del(this.keys.processing), this.client.del(this.keys.completed), this.client.del(this.keys.failed), this.client.del(this.keys.jobs)]);
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
            const processingJobs = await this.client.lRange(this.keys.processing, 0, -1);
            let cleanedCount = 0;

            for (const jobStr of processingJobs) {
                try {
                    const job = JSON.parse(jobStr);
                    const jobDetails = await this.getJob(job.id);

                    // If job is completed or failed in job store but still in processing queue, remove it
                    if (jobDetails && (jobDetails.status === 'completed' || jobDetails.status === 'failed')) {
                        await this.client.lRem(this.keys.processing, 1, jobStr);
                        cleanedCount++;
                        console.log(`🧹 Cleaned up orphaned processing job: ${job.id}`);
                    }
                } catch (parseError) {
                    // Remove invalid JSON entries
                    await this.client.lRem(this.keys.processing, 1, jobStr);
                    cleanedCount++;
                    console.log(`🧹 Removed invalid processing queue entry`);
                }
            }

            if (cleanedCount > 0) {
                console.log(`🧹 Cleaned up ${cleanedCount} orphaned processing jobs`);
            }

            return cleanedCount;
        } catch (error) {
            console.error('❌ Failed to cleanup processing queue:', error);
            return 0;
        }
    }

    /**
     * Get queue statistics for monitoring
     */
    async getQueueStats() {
        try {
            const status = await this.getQueueStatus();
            const jobs = await this.getAllJobs();

            const jobsByStatus = {
                pending: Object.values(jobs).filter((job) => job.status === 'pending').length,
                processing: Object.values(jobs).filter((job) => job.status === 'processing').length,
                completed: Object.values(jobs).filter((job) => job.status === 'completed').length,
                failed: Object.values(jobs).filter((job) => job.status === 'failed').length,
            };

            return {
                ...status,
                jobsByStatus,
                currentJob: this.currentJob,
                isProcessing: this.isProcessing,
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
     * Close Redis connection
     */
    async close() {
        try {
            this.stopProcessing();
            await this.client.quit();
            console.log('🔌 Redis connection closed');
        } catch (error) {
            console.error('❌ Error closing Redis connection:', error);
        }
    }
}

module.exports = VideoQueueManager;
