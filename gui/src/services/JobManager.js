/**
 * Job Manager - Professional job lifecycle management
 * Handles video generation jobs, monitoring, progress tracking, and status updates
 */
import APIService from './APIService.js';
import UIManager from '../components/UIManager.js';

export class JobManager extends EventTarget {
    constructor() {
        super();
        this.activeJobs = new Map();
        this.jobHistory = new Map();
        this.currentJob = null;
        this.maxJobHistory = 100;
        this.monitoringInterval = 5000; // 5 seconds
        this.monitoringTimer = null;
        this.isGenerationActive = false;
        this.creatomateMessages = new Set(); // Track unique messages
    }

    /**
     * Initialize Job Manager
     */
    init() {
        this.setupEventListeners();
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Listen for page unload to cleanup
        window.addEventListener('beforeunload', () => {
            this.cleanup();
        });
    }

    /**
     * Start video generation job with comprehensive monitoring
     * @param {Object} params - Generation parameters
     * @returns {Promise<Object>} Job creation result
     */
    async startVideoGeneration(params) {
        try {
            // Validate parameters
            this.validateGenerationParams(params);

            // Prevent concurrent generations
            if (this.isGenerationActive) {
                throw new Error('Another video generation is already in progress');
            }

            this.isGenerationActive = true;

            // Update UI state
            UIManager.showProgress();
            UIManager.disableGenerateButton('Starting generation...');
            UIManager.addStatusMessage('info', '🚀', 'Starting video generation...');

            // Reset message tracking
            this.creatomateMessages.clear();

            // Create job via API
            const result = await APIService.generateVideo(params);

            if (!result.success) {
                throw new Error(result.message || 'Failed to start video generation');
            }

            // Setup job tracking
            const job = this.createJobObject(result, params);

            // Store and monitor job
            this.activeJobs.set(job.id, job);
            this.currentJob = job;
            this.startJobMonitoring(job.id);

            // Update UI
            UIManager.addStatusMessage(
                'success',
                '✅',
                `Job queued successfully! ${job.queuePosition ? `Position: ${job.queuePosition}` : ''}`
            );
            UIManager.updateProgress(5, 'Job queued, waiting to start...');

            // Emit job started event
            this.dispatchEvent(new CustomEvent('jobStarted', { detail: { job } }));

            console.log(`💼 Job started: ${job.id}`);
            return { success: true, job };
        } catch (error) {
            console.error('❌ Failed to start video generation:', error);

            // Reset UI state
            this.resetGenerationState();
            UIManager.addStatusMessage('error', '❌', `Failed to start generation: ${error.message}`);

            this.dispatchEvent(new CustomEvent('jobError', { detail: { error } }));
            throw error;
        }
    }

    /**
     * Create job object from API result
     * @param {Object} result - API result
     * @param {Object} params - Generation parameters
     * @returns {Object} Job object
     */
    createJobObject(result, params) {
        return {
            id: result.jobId,
            params: params,
            status: 'pending',
            progress: 0,
            createdAt: new Date().toISOString(),
            startedAt: null,
            completedAt: null,
            queuePosition: result.queuePosition || 0,
            error: null,
            result: null,
            creatomateId: null,
            videoUrl: null
        };
    }

    /**
     * Validate generation parameters
     * @param {Object} params - Parameters to validate
     * @throws {Error} If validation fails
     */
    validateGenerationParams(params) {
        const required = ['country', 'platform', 'genre', 'contentType'];
        const missing = required.filter((field) => !params[field]);

        if (missing.length > 0) {
            throw new Error(`Missing required parameters: ${missing.join(', ')}`);
        }

        console.log('✅ Parameters validated:', params);
    }

    /**
     * Start monitoring a specific job
     * @param {string} jobId - Job ID to monitor
     */
    async startJobMonitoring(jobId) {
        if (this.monitoringTimer) {
            clearInterval(this.monitoringTimer);
        }

        console.log(`👀 Started monitoring job: ${jobId}`);

        this.monitoringTimer = setInterval(async () => {
            try {
                await this.updateJobStatus(jobId);
            } catch (error) {
                console.error('❌ Job monitoring error:', error);

                // Stop monitoring on repeated failures
                if (this.consecutiveErrors > 3) {
                    this.stopJobMonitoring();
                    UIManager.addStatusMessage('warning', '⚠️', 'Job monitoring stopped due to repeated errors');
                }
            }
        }, this.monitoringInterval);
    }

    /**
     * Stop job monitoring
     */
    stopJobMonitoring() {
        if (this.monitoringTimer) {
            clearInterval(this.monitoringTimer);
            this.monitoringTimer = null;
            console.log('⏹️ Job monitoring stopped');
        }
    }

    /**
     * Update job status from API
     * @param {string} jobId - Job ID to update
     */
    async updateJobStatus(jobId) {
        const job = this.activeJobs.get(jobId);
        if (!job) return;

        try {
            const result = await APIService.getJobStatus(jobId);

            if (result.success && result.job) {
                this.processJobUpdate(result.job);
            }
        } catch (error) {
            console.error(`❌ Failed to update job status for ${jobId}:`, error);
            throw error;
        }
    }

    /**
     * Process comprehensive job status update
     * @param {Object} jobData - Updated job data from API
     */
    processJobUpdate(jobData) {
        const job = this.activeJobs.get(jobData.id);
        if (!job) return;

        const previousStatus = job.status;
        const previousProgress = job.progress;

        // Update job data
        Object.assign(job, {
            status: jobData.status,
            progress: jobData.progress || 0,
            currentStep: jobData.currentStep,
            startedAt: jobData.startedAt || job.startedAt,
            completedAt: jobData.completedAt,
            error: jobData.error,
            result: jobData,
            creatomateId: jobData.creatomateId,
            videoUrl: jobData.videoUrl
        });

        // Handle status changes
        if (previousStatus !== job.status) {
            this.handleJobStatusChange(job, previousStatus);
        }

        // Handle progress changes
        if (previousProgress !== job.progress) {
            this.updateJobProgress(job);
        }

        // Handle creatomate monitoring for rendering jobs
        if (job.creatomateId && !job.videoUrl && job.status === 'completed') {
            this.startCreatomateMonitoring(job);
        }

        // Emit job updated event
        this.dispatchEvent(new CustomEvent('jobUpdated', { detail: { job, previousStatus } }));

        console.log(`💼 Job ${job.id} updated: ${job.status} (${job.progress}%)`);
    }

    /**
     * Handle comprehensive job status changes
     * @param {Object} job - Job object
     * @param {string} previousStatus - Previous job status
     */
    handleJobStatusChange(job, previousStatus) {
        switch (job.status) {
            case 'processing':
                if (previousStatus === 'pending') {
                    UIManager.addStatusMessage('info', '⚡', 'Job started processing!');
                    job.startedAt = new Date().toISOString();
                }
                break;

            case 'completed':
                this.handleJobCompletion(job);
                break;

            case 'failed':
                this.handleJobFailure(job);
                break;

            case 'cancelled':
                this.handleJobCancellation(job);
                break;
        }
    }

    /**
     * Handle job completion with video URL or Creatomate ID
     * @param {Object} job - Completed job
     */
    handleJobCompletion(job) {
        console.log(`✅ Job completed: ${job.id}`);

        if (job.videoUrl) {
            // Direct video URL available
            this.finishSuccessfulGeneration(job);
        } else if (job.creatomateId) {
            // Video is rendering, start Creatomate monitoring
            UIManager.updateProgress(90, 'Python script completed, video rendering...');
            UIManager.addStatusMessage(
                'info',
                '🎬',
                `Video rendering started (ID: ${job.creatomateId}). Monitoring progress...`
            );
            this.startCreatomateMonitoring(job);
        } else {
            // Completed but missing video data
            UIManager.addStatusMessage('warning', '⚠️', 'Job completed but video URL not yet available');
            this.moveJobToHistory(job);
        }

        this.dispatchEvent(new CustomEvent('jobCompleted', { detail: { job } }));
    }

    /**
     * Start monitoring Creatomate rendering status
     * @param {Object} job - Job with Creatomate ID
     */
    startCreatomateMonitoring(job) {
        let attempts = 0;
        const maxAttempts = 40; // 20 minutes max (30s * 40)

        const checkStatus = async () => {
            attempts++;

            try {
                const statusData = await APIService.getCreatomateStatus(job.creatomateId);

                if (statusData.success && statusData.videoUrl) {
                    // Video is ready!
                    job.videoUrl = statusData.videoUrl;
                    job.result.videoUrl = statusData.videoUrl;
                    this.finishSuccessfulGeneration(job);
                } else if (statusData.success && statusData.status) {
                    // Still rendering
                    const status = statusData.status.toLowerCase();
                    const statusText = status.charAt(0).toUpperCase() + status.slice(1);

                    if (attempts % 4 === 0) {
                        // Every 2 minutes
                        const messageKey = `rendering-update-${Math.floor(attempts / 4)}`;
                        if (!this.creatomateMessages.has(messageKey)) {
                            UIManager.addStatusMessage(
                                'info',
                                '⏳',
                                `Video status: ${statusText}... (${attempts}/${maxAttempts})`
                            );
                            this.creatomateMessages.add(messageKey);
                        }
                    }

                    // Update progress
                    let progressPercent = 90 + (attempts / maxAttempts) * 10;
                    if (status.includes('render') || status.includes('process')) {
                        progressPercent = Math.min(95, progressPercent);
                    }
                    UIManager.updateProgress(progressPercent, `Rendering: ${statusText}`);

                    // Schedule next check
                    if (attempts < maxAttempts) {
                        setTimeout(() => checkStatus(), 30000);
                    } else {
                        this.handleCreatomateTimeout(job);
                    }
                } else {
                    this.handleCreatomateError(job, statusData.message, attempts, maxAttempts, checkStatus);
                }
            } catch (error) {
                this.handleCreatomateNetworkError(job, error, attempts, maxAttempts, checkStatus);
            }
        };

        // Start monitoring
        checkStatus();
    }

    /**
     * Handle Creatomate monitoring timeout
     * @param {Object} job - Job object
     */
    handleCreatomateTimeout(job) {
        const timeoutKey = 'creatomate-timeout';
        if (!this.creatomateMessages.has(timeoutKey)) {
            UIManager.addStatusMessage(
                'warning',
                '⚠️',
                'Video rendering is taking longer than expected. Use "Check Status" to monitor manually.'
            );
            this.creatomateMessages.add(timeoutKey);
        }

        // Keep the job active for manual status checking
        UIManager.enableGenerateButton();
        this.isGenerationActive = false;
    }

    /**
     * Handle Creatomate API errors
     * @param {Object} job - Job object
     * @param {string} message - Error message
     * @param {number} attempts - Current attempt number
     * @param {number} maxAttempts - Maximum attempts
     * @param {Function} checkStatus - Status check function
     */
    handleCreatomateError(job, message, attempts, maxAttempts, checkStatus) {
        const errorKey = `creatomate-error-${message}`;
        if (!this.creatomateMessages.has(errorKey)) {
            UIManager.addStatusMessage('error', '❌', `Render status check failed: ${message || 'Unknown error'}`);
            this.creatomateMessages.add(errorKey);
        }

        if (attempts < maxAttempts) {
            setTimeout(() => checkStatus(), 30000);
        } else {
            UIManager.addStatusMessage('error', '❌', 'Unable to check render status after multiple attempts.');
            this.moveJobToHistory(job);
        }
    }

    /**
     * Handle Creatomate network errors
     * @param {Object} job - Job object
     * @param {Error} error - Network error
     * @param {number} attempts - Current attempt number
     * @param {number} maxAttempts - Maximum attempts
     * @param {Function} checkStatus - Status check function
     */
    handleCreatomateNetworkError(job, error, attempts, maxAttempts, checkStatus) {
        console.error('Creatomate status check error:', error);

        const networkErrorKey = `network-error-${attempts}`;
        if (attempts % 3 === 0 && !this.creatomateMessages.has(networkErrorKey)) {
            UIManager.addStatusMessage('warning', '⚠️', `Network error checking render status (attempt ${attempts})`);
            this.creatomateMessages.add(networkErrorKey);
        }

        if (attempts < maxAttempts) {
            setTimeout(() => checkStatus(), 30000);
        } else {
            UIManager.addStatusMessage('error', '❌', 'Network errors prevented render status monitoring.');
            this.moveJobToHistory(job);
        }
    }

    /**
     * Finish successful video generation
     * @param {Object} job - Completed job with video URL
     */
    finishSuccessfulGeneration(job) {
        UIManager.updateProgress(100, 'Generation completed!');
        UIManager.addStatusMessage('success', '🎉', 'Video generation completed successfully!');

        // Display video in UI
        UIManager.displayVideo({
            jobId: job.id,
            videoUrl: job.videoUrl,
            creatomateId: job.creatomateId,
            timestamp: new Date().toLocaleString()
        });

        // Cleanup and reset
        this.moveJobToHistory(job);
        this.resetGenerationState();
    }

    /**
     * Handle job failure
     * @param {Object} job - Failed job
     */
    handleJobFailure(job) {
        console.error(`❌ Job failed: ${job.id}`, job.error);

        UIManager.updateProgress(0, 'Generation failed');
        UIManager.addStatusMessage('error', '❌', `Generation failed: ${job.error || 'Unknown error'}`, false);

        this.moveJobToHistory(job);
        this.dispatchEvent(new CustomEvent('jobFailed', { detail: { job } }));
        this.resetGenerationState();
    }

    /**
     * Handle job cancellation
     * @param {Object} job - Cancelled job
     */
    handleJobCancellation(job) {
        console.log(`⏹️ Job cancelled: ${job.id}`);

        UIManager.addStatusMessage('warning', '⏹️', 'Job was cancelled');
        this.moveJobToHistory(job);
        this.dispatchEvent(new CustomEvent('jobCancelled', { detail: { job } }));
        this.resetGenerationState();
    }

    /**
     * Update job progress in UI
     * @param {Object} job - Job object
     */
    updateJobProgress(job) {
        if (job === this.currentJob) {
            UIManager.updateProgress(job.progress, job.currentStep || 'Processing...');
        }
    }

    /**
     * Reset generation state after completion/failure
     */
    resetGenerationState() {
        UIManager.hideProgress();
        UIManager.enableGenerateButton();
        this.isGenerationActive = false;
        this.stopJobMonitoring();
    }

    /**
     * Cancel active job
     * @param {string} jobId - Job ID to cancel
     * @returns {Promise<boolean>} Cancellation success
     */
    async cancelJob(jobId) {
        try {
            const result = await APIService.cancelJob(jobId);

            if (result.success) {
                UIManager.addStatusMessage('info', '⏹️', 'Job cancellation requested');
                return true;
            } else {
                throw new Error(result.message || 'Failed to cancel job');
            }
        } catch (error) {
            console.error('❌ Failed to cancel job:', error);
            UIManager.addStatusMessage('error', '❌', `Failed to cancel job: ${error.message}`);
            return false;
        }
    }

    /**
     * Stop video generation
     */
    stopVideoGeneration() {
        if (this.currentJob) {
            this.cancelJob(this.currentJob.id);
        }

        this.resetGenerationState();
        UIManager.addStatusMessage('warning', '⏹️', 'Video generation stopped');
    }

    /**
     * Move job from active to history
     * @param {Object} job - Job to move
     */
    moveJobToHistory(job) {
        this.activeJobs.delete(job.id);

        this.jobHistory.set(job.id, {
            ...job,
            movedToHistoryAt: new Date().toISOString()
        });

        if (this.currentJob && this.currentJob.id === job.id) {
            this.currentJob = null;
        }

        this.limitJobHistory();
    }

    /**
     * Limit job history size
     */
    limitJobHistory() {
        if (this.jobHistory.size > this.maxJobHistory) {
            const entries = Array.from(this.jobHistory.entries());
            const toRemove = entries.slice(0, entries.length - this.maxJobHistory);

            toRemove.forEach(([jobId]) => {
                this.jobHistory.delete(jobId);
            });

            console.log(`🧹 Cleaned up ${toRemove.length} old job records`);
        }
    }

    /**
     * Get job by ID
     * @param {string} jobId - Job ID
     * @returns {Object|null} Job object or null
     */
    getJob(jobId) {
        return this.activeJobs.get(jobId) || this.jobHistory.get(jobId) || null;
    }

    /**
     * Get all active jobs
     * @returns {Array} Array of active jobs
     */
    getActiveJobs() {
        return Array.from(this.activeJobs.values());
    }

    /**
     * Get job statistics
     * @returns {Object} Job statistics
     */
    getJobStats() {
        return {
            active: this.activeJobs.size,
            history: this.jobHistory.size,
            total: this.activeJobs.size + this.jobHistory.size,
            currentJob: this.currentJob?.id || null,
            isMonitoring: !!this.monitoringTimer,
            isGenerationActive: this.isGenerationActive
        };
    }

    /**
     * Cleanup resources
     */
    cleanup() {
        this.stopJobMonitoring();
        console.log('🧹 Job Manager cleaned up');
    }
}

// Export singleton instance
export default new JobManager();
