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
            // Clean up orphaned processing jobs before getting status
            await this.cleanupProcessingQueue();

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

                    // Ensure only one job is processed at a time
                    if (this.currentJob) {
                        console.log(`⚠️ Job ${job.id} skipped - another job ${this.currentJob.id} is still processing`);
                        // Put the job back at the front of the queue
                        await this.client.lPush(this.keys.pending, jobData.element);
                        await this.sleep(2000); // Wait before trying again
                        continue;
                    }

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
        console.log(`🔍 Current job before processing: ${this.currentJob ? this.currentJob.id : 'null'}`);
        console.log(`--- Python Script Output ---`);

        try {
            // Update job status to processing
            job.status = 'processing';
            job.startedAt = new Date().toISOString();
            job.progress = 10;
            job.currentStep = 'Starting video generation...';
            this.currentJob = job;
            console.log(`✅ Set current job to: ${job.id}`);

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

        console.log(`🧹 Clearing current job: ${this.currentJob ? this.currentJob.id : 'already null'}`);
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
                                step: '🗃️ Step 1/7: Extracting movies from database...',
                            },
                            {
                                patterns: ['✅ STEP 1 COMPLETED'],
                                progress: 20,
                                step: '✅ Step 1 completed: Movies extracted successfully',
                            },

                            // Step 2: Script Generation
                            {
                                patterns: ['STEP 2/7'],
                                progress: 25,
                                step: '🤖 Step 2/7: Generating AI-powered scripts...',
                            },
                            {
                                patterns: ['✅ STEP 2 COMPLETED'],
                                progress: 35,
                                step: '✅ Step 2 completed: AI scripts generated successfully',
                            },

                            // Step 3: Asset Preparation
                            {
                                patterns: ['STEP 3/7'],
                                progress: 40,
                                step: '🎨 Step 3/7: Creating enhanced posters and clips...',
                            },
                            {
                                patterns: ['✅ STEP 3 COMPLETED'],
                                progress: 50,
                                step: '✅ Step 3 completed: Assets created successfully',
                            },

                            // Step 4: HeyGen Video Creation
                            {
                                patterns: ['STEP 4/7'],
                                progress: 55,
                                step: '🎭 Step 4/7: Creating HeyGen AI avatar videos...',
                            },
                            {
                                patterns: ['✅ STEP 4 COMPLETED'],
                                progress: 65,
                                step: '✅ Step 4 completed: HeyGen videos created successfully',
                            },

                            // Step 5: HeyGen Video Processing
                            {
                                patterns: ['STEP 5/7'],
                                progress: 70,
                                step: '⏳ Step 5/7: Processing HeyGen video URLs...',
                            },
                            {
                                patterns: ['✅ STEP 5 COMPLETED'],
                                progress: 75,
                                step: '✅ Step 5 completed: Video URLs processed successfully',
                            },

                            // Step 6: Scroll Video Generation
                            {
                                patterns: ['STEP 6/7'],
                                progress: 80,
                                step: '📱 Step 6/7: Generating scroll video overlay...',
                            },
                            {
                                patterns: ['✅ STEP 6 COMPLETED'],
                                progress: 85,
                                step: '✅ Step 6 completed: Scroll overlay generated successfully',
                            },
                            {
                                patterns: ['STEP 6/7', 'SKIPPED'],
                                progress: 85,
                                step: '⏭️ Step 6 skipped: No scroll video needed',
                            },

                            // Step 7: Creatomate Assembly
                            {
                                patterns: ['STEP 7/7'],
                                progress: 90,
                                step: '🎬 Step 7/7: Assembling final video with Creatomate...',
                            },
                            {
                                patterns: ['✅ STEP 7 COMPLETED'],
                                progress: 95,
                                step: '✅ Step 7 completed: Final video submitted for rendering',
                            },

                            // Workflow Completion
                            {
                                patterns: ['🎉 WORKFLOW COMPLETED SUCCESSFULLY'],
                                progress: 100,
                                step: '🎉 Workflow completed successfully!',
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
                            reject(new Error(`🎭 HeyGen API error - ${errorMsg}. Please check your HeyGen account and API settings.`));
                            return;
                        }
                    }

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

                        reject(new Error(`🎬 Not enough movies available - only ${movieCount} found with current filters.${movieNames} Please try different genre, platform, or content type to find more movies.`));
                        return;
                    }

                    // Check for database errors
                    if (errorOutput.includes('No movies found matching criteria') || errorOutput.includes('Database query failed')) {
                        reject(new Error('🗃️ No movies found for the selected parameters (genre, platform, content type). Please try different filters to find available content.'));
                        return;
                    }

                    // Check for connection errors
                    if (errorOutput.includes('Connection failed') || errorOutput.includes('Database connection failed')) {
                        reject(new Error('🌐 Database connection failed. Please check your internet connection and try again.'));
                        return;
                    }

                    // Check for screenshot/browser errors
                    if (errorOutput.includes('Screenshot') && errorOutput.includes('failed')) {
                        reject(new Error('📸 Screenshot capture failed. This might be due to network issues or website accessibility. Please try again.'));
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
                const processPid = this.currentProcess.pid; // Store PID before nullifying
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
                        const processToKill = this.currentProcess; // Store reference before nullifying
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

                            await this.client.lRem(this.keys.processing, 1, jobStr);
                            await this.client.lPush(this.keys.failed, JSON.stringify(jobDetails));
                            await this.updateJob(jobDetails);
                            cleanedCount++;
                            console.log(`🧹 Cleaned up timed out processing job: ${job.id} (running for ${Math.round(timeDiff / 60000)} minutes)`);
                        }
                    }
                    // Remove jobs that don't exist in job store
                    else if (!jobDetails) {
                        await this.client.lRem(this.keys.processing, 1, jobStr);
                        cleanedCount++;
                        console.log(`🧹 Removed processing job with no details: ${job.id}`);
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
