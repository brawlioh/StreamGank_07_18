/**
 * JobDetail Page - Individual job information and monitoring
 * Shows detailed job progress, logs, and results
 */

import UIManager from '../components/UIManager.js';
import APIService from '../services/APIService.js';
import JobManager from '../services/JobManager.js';

export class JobDetailPage {
    constructor() {
        this.currentJobId = null;
        this.jobData = null;
        this.refreshTimer = null;
        this.refreshInterval = 5000; // 5 seconds
    }

    /**
     * Render the job detail page
     * @param {HTMLElement} container - Container to render into
     * @param {Object} params - Route parameters (contains jobId)
     */
    async render(container, params = {}) {
        const { jobId } = params;

        if (!container) {
            console.error('📄 JobDetail: No container provided');
            return;
        }

        if (!jobId) {
            console.error('📄 JobDetail: No job ID provided');
            this.renderError(container, 'No job ID specified');
            return;
        }

        this.currentJobId = jobId;

        // Show loading state first
        container.innerHTML = this.createLoadingTemplate();

        try {
            // Fetch job data
            await this.loadJobData(jobId);

            // Render job details
            container.innerHTML = this.createJobTemplate();

            // Start auto-refresh for active jobs
            this.startAutoRefresh();

            console.log(`📄 JobDetail rendered for job: ${jobId}`);
        } catch (error) {
            console.error('📄 JobDetail render error:', error);
            this.renderError(container, error.message);
        }
    }

    /**
     * Load job data from API or local storage
     * @param {string} jobId - Job ID to load
     */
    async loadJobData(jobId) {
        try {
            // First try to get from JobManager (active jobs)
            let job = JobManager.getJob(jobId);

            if (!job) {
                // If not in JobManager, try API
                const response = await APIService.getJobStatus(jobId);
                if (response.success) {
                    job = response.job;
                }
            }

            if (!job) {
                throw new Error(`Job ${jobId} not found`);
            }

            this.jobData = job;

            // Update page title
            document.title = `Job ${jobId} - StreamGank`;
        } catch (error) {
            throw new Error(`Failed to load job data: ${error.message}`);
        }
    }

    /**
     * Create loading template
     * @returns {string} Loading HTML
     */
    createLoadingTemplate() {
        return `
            <div class="job-detail-page">
                <div class="container-fluid">
                    <!-- Header with navigation -->
                    <div class="d-flex justify-content-between align-items-center mb-4">
                        <div>
                            <button class="btn btn-outline-secondary me-3" onclick="history.back()">
                                ← Back
                            </button>
                            <h1 class="h3 mb-0">Loading Job...</h1>
                        </div>
                        <div class="nav-links">
                            <a href="/dashboard" class="btn btn-outline-primary me-2">Dashboard</a>
                        </div>
                    </div>
                    
                    <!-- Loading State -->
                    <div class="text-center py-5">
                        <div class="spinner-border text-primary" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                        <p class="mt-3 text-muted">Loading job details...</p>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Create main job detail template
     * @returns {string} Job detail HTML
     */
    createJobTemplate() {
        const job = this.jobData;
        const statusClass = this.getStatusClass(job.status);
        const statusIcon = this.getStatusIcon(job.status);

        return `
            <div class="job-detail-page">
                <div class="container-fluid">
                    <!-- Header with navigation and actions -->
                    <div class="d-flex justify-content-between align-items-center mb-4">
                        <div>
                            <button class="btn btn-outline-secondary me-3" onclick="history.back()">
                                ← Back
                            </button>
                            <h1 class="h3 mb-0">Job ${job.id}</h1>
                            <div class="mt-1">
                                <span class="badge ${statusClass} me-2">${statusIcon} ${job.status.toUpperCase()}</span>
                                <small class="text-muted">Created: ${this.formatDate(job.createdAt)}</small>
                            </div>
                        </div>
                        <div class="nav-links">
                            <a href="/dashboard" class="btn btn-outline-primary me-2">Dashboard</a>
                            ${this.createActionButtons(job)}
                        </div>
                    </div>

                    <div class="row">
                        <!-- Left Column - Job Information -->
                        <div class="col-md-6">
                            <!-- Job Parameters -->
                            <div class="card mb-4">
                                <div class="card-header">
                                    <h5 class="mb-0">📋 Job Parameters</h5>
                                </div>
                                <div class="card-body">
                                    <dl class="row mb-0">
                                        <dt class="col-sm-4">Country:</dt>
                                        <dd class="col-sm-8">${job.params?.country || 'N/A'}</dd>
                                        
                                        <dt class="col-sm-4">Platform:</dt>
                                        <dd class="col-sm-8">${job.params?.platform || 'N/A'}</dd>
                                        
                                        <dt class="col-sm-4">Genre:</dt>
                                        <dd class="col-sm-8">${job.params?.genre || 'N/A'}</dd>
                                        
                                        <dt class="col-sm-4">Content Type:</dt>
                                        <dd class="col-sm-8">${job.params?.contentType || 'N/A'}</dd>
                                        
                                        <dt class="col-sm-4">Template:</dt>
                                        <dd class="col-sm-8">${job.params?.template || 'Default'}</dd>
                                        
                                        ${
                                            job.params?.url
                                                ? `
                                        <dt class="col-sm-4">Source URL:</dt>
                                        <dd class="col-sm-8">
                                            <a href="${job.params.url}" target="_blank" class="text-break">
                                                ${job.params.url}
                                            </a>
                                        </dd>
                                        `
                                                : ''
                                        }
                                    </dl>
                                </div>
                            </div>

                            <!-- Job Timeline -->
                            <div class="card mb-4">
                                <div class="card-header">
                                    <h5 class="mb-0">⏱️ Timeline</h5>
                                </div>
                                <div class="card-body">
                                    ${this.createTimeline(job)}
                                </div>
                            </div>

                            <!-- Video Result (if available) -->
                            ${job.videoUrl ? this.createVideoResult(job) : ''}
                        </div>

                        <!-- Right Column - Progress and Status -->
                        <div class="col-md-6">
                            <!-- Progress Card -->
                            <div class="card mb-4">
                                <div class="card-header">
                                    <h5 class="mb-0">📊 Progress</h5>
                                </div>
                                <div class="card-body">
                                    <div class="mb-3">
                                        <div class="d-flex justify-content-between mb-1">
                                            <span class="fw-medium">${job.currentStep || 'Processing'}</span>
                                            <span class="text-muted">${job.progress || 0}%</span>
                                        </div>
                                        <div class="progress">
                                            <div class="progress-bar ${this.getProgressClass(job.progress)}" 
                                                 role="progressbar" style="width: ${job.progress || 0}%">
                                            </div>
                                        </div>
                                    </div>
                                    
                                    ${
                                        job.error
                                            ? `
                                    <div class="alert alert-danger">
                                        <h6 class="alert-heading">❌ Error</h6>
                                        <p class="mb-0">${job.error}</p>
                                    </div>
                                    `
                                            : ''
                                    }
                                    
                                    ${
                                        job.creatomateId
                                            ? `
                                    <div class="mt-3">
                                        <h6>🎬 Creatomate Render</h6>
                                        <p class="mb-1">
                                            <strong>ID:</strong> 
                                            <code>${job.creatomateId}</code>
                                        </p>
                                        <button class="btn btn-outline-primary btn-sm" onclick="checkCreatomateStatus('${job.creatomateId}')">
                                            Check Render Status
                                        </button>
                                    </div>
                                    `
                                            : ''
                                    }
                                </div>
                            </div>

                            <!-- Queue Information -->
                            <div class="card mb-4">
                                <div class="card-header">
                                    <h5 class="mb-0">📋 Queue Information</h5>
                                </div>
                                <div class="card-body">
                                    <dl class="row mb-0">
                                        <dt class="col-sm-6">Queue Position:</dt>
                                        <dd class="col-sm-6">${job.queuePosition || 'N/A'}</dd>
                                        
                                        <dt class="col-sm-6">Processing Time:</dt>
                                        <dd class="col-sm-6">${this.calculateDuration(job)}</dd>
                                        
                                        <dt class="col-sm-6">Last Updated:</dt>
                                        <dd class="col-sm-6">${this.formatDate(job.updatedAt || job.createdAt)}</dd>
                                    </dl>
                                </div>
                            </div>

                            <!-- Status Messages -->
                            <div class="card">
                                <div class="card-header">
                                    <h5 class="mb-0">📝 Status Messages</h5>
                                </div>
                                <div class="card-body">
                                    <div id="job-status-messages" class="status-messages" style="max-height: 300px; overflow-y: auto;">
                                        <!-- Status messages will be populated here -->
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Create action buttons based on job status
     * @param {Object} job - Job data
     * @returns {string} Action buttons HTML
     */
    createActionButtons(job) {
        const buttons = [];

        if (job.status === 'processing' || job.status === 'pending') {
            buttons.push(`
                <button class="btn btn-warning me-2" onclick="cancelJob('${job.id}')">
                    ⏹️ Cancel Job
                </button>
            `);
        }

        if (job.status === 'failed') {
            buttons.push(`
                <button class="btn btn-primary me-2" onclick="retryJob('${job.id}')">
                    🔄 Retry Job
                </button>
            `);
        }

        buttons.push(`
            <button class="btn btn-outline-secondary me-2" onclick="refreshJobData('${job.id}')">
                🔄 Refresh
            </button>
        `);

        return buttons.join('');
    }

    /**
     * Create timeline HTML
     * @param {Object} job - Job data
     * @returns {string} Timeline HTML
     */
    createTimeline(job) {
        const events = [];

        events.push({
            time: job.createdAt,
            status: 'created',
            message: 'Job created and queued'
        });

        if (job.startedAt) {
            events.push({
                time: job.startedAt,
                status: 'started',
                message: 'Job processing started'
            });
        }

        if (job.completedAt) {
            events.push({
                time: job.completedAt,
                status: 'completed',
                message: 'Job completed successfully'
            });
        }

        return events
            .map(
                (event) => `
            <div class="timeline-item mb-3">
                <div class="d-flex align-items-start">
                    <div class="timeline-icon me-3">
                        ${this.getStatusIcon(event.status)}
                    </div>
                    <div class="timeline-content">
                        <p class="mb-1 fw-medium">${event.message}</p>
                        <small class="text-muted">${this.formatDate(event.time)}</small>
                    </div>
                </div>
            </div>
        `
            )
            .join('');
    }

    /**
     * Create video result section
     * @param {Object} job - Job data
     * @returns {string} Video result HTML
     */
    createVideoResult(job) {
        return `
            <div class="card mb-4">
                <div class="card-header">
                    <h5 class="mb-0">🎬 Video Result</h5>
                </div>
                <div class="card-body">
                    <video controls class="w-100 mb-3" style="max-height: 400px;">
                        <source src="${job.videoUrl}" type="video/mp4">
                        Your browser does not support the video tag.
                    </video>
                    <div class="d-flex gap-2">
                        <a href="${job.videoUrl}" target="_blank" class="btn btn-primary">
                            🔗 Open Video
                        </a>
                        <a href="${job.videoUrl}" download class="btn btn-outline-secondary">
                            💾 Download
                        </a>
                        <button class="btn btn-outline-info" onclick="copyToClipboard('${job.videoUrl}')">
                            📋 Copy URL
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Start auto-refresh timer for active jobs
     */
    startAutoRefresh() {
        this.stopAutoRefresh();

        if (this.jobData && ['pending', 'processing'].includes(this.jobData.status)) {
            this.refreshTimer = setInterval(() => {
                this.refreshJobData(this.currentJobId);
            }, this.refreshInterval);

            console.log(`📄 Auto-refresh started for job ${this.currentJobId}`);
        }
    }

    /**
     * Stop auto-refresh timer
     */
    stopAutoRefresh() {
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
            this.refreshTimer = null;
        }
    }

    /**
     * Refresh job data
     * @param {string} jobId - Job ID to refresh
     */
    async refreshJobData(jobId) {
        try {
            await this.loadJobData(jobId);

            // Re-render if we're still on the same job
            if (this.currentJobId === jobId) {
                const container = document.querySelector('.job-detail-page').parentElement;
                await this.render(container, { jobId });
            }
        } catch (error) {
            console.error('📄 Failed to refresh job data:', error);
        }
    }

    /**
     * Render error state
     * @param {HTMLElement} container - Container element
     * @param {string} message - Error message
     */
    renderError(container, message) {
        container.innerHTML = `
            <div class="job-detail-page">
                <div class="container-fluid">
                    <div class="d-flex justify-content-between align-items-center mb-4">
                        <div>
                            <button class="btn btn-outline-secondary me-3" onclick="history.back()">
                                ← Back
                            </button>
                            <h1 class="h3 mb-0">Job Not Found</h1>
                        </div>
                        <div class="nav-links">
                            <a href="/dashboard" class="btn btn-outline-primary me-2">Dashboard</a>
                        </div>
                    </div>
                    
                    <div class="alert alert-danger">
                        <h4 class="alert-heading">❌ Error</h4>
                        <p class="mb-0">${message}</p>
                        <hr>
                        <a href="/dashboard" class="btn btn-primary">Return to Dashboard</a>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Handle page activation
     */
    activate(params) {
        console.log(`📄 JobDetail activated for job: ${params.jobId}`);
    }

    /**
     * Handle page deactivation
     */
    deactivate() {
        this.stopAutoRefresh();
        console.log('📄 JobDetail deactivated');
    }

    /**
     * Get status CSS class
     * @param {string} status - Job status
     * @returns {string} CSS class
     */
    getStatusClass(status) {
        const classes = {
            pending: 'bg-warning',
            processing: 'bg-info',
            completed: 'bg-success',
            failed: 'bg-danger',
            cancelled: 'bg-secondary'
        };
        return classes[status] || 'bg-secondary';
    }

    /**
     * Get status icon
     * @param {string} status - Job status
     * @returns {string} Icon
     */
    getStatusIcon(status) {
        const icons = {
            created: '➕',
            started: '▶️',
            pending: '⏳',
            processing: '🔄',
            completed: '✅',
            failed: '❌',
            cancelled: '⏹️'
        };
        return icons[status] || '📄';
    }

    /**
     * Get progress bar CSS class
     * @param {number} progress - Progress percentage
     * @returns {string} CSS class
     */
    getProgressClass(progress) {
        if (progress >= 100) {
            return 'bg-success';
        }
        if (progress >= 75) {
            return 'bg-info';
        }
        if (progress >= 50) {
            return 'bg-warning';
        }
        return 'bg-primary';
    }

    /**
     * Format date for display
     * @param {string} dateString - ISO date string
     * @returns {string} Formatted date
     */
    formatDate(dateString) {
        if (!dateString) {
            return 'N/A';
        }
        return new Date(dateString).toLocaleString();
    }

    /**
     * Calculate job duration
     * @param {Object} job - Job data
     * @returns {string} Duration string
     */
    calculateDuration(job) {
        if (!job.startedAt) {
            return 'Not started';
        }

        const start = new Date(job.startedAt);
        const end = job.completedAt ? new Date(job.completedAt) : new Date();
        const duration = end - start;

        return UIManager.formatDuration(duration);
    }

    /**
     * Cleanup resources
     */
    cleanup() {
        this.stopAutoRefresh();
        console.log('📄 JobDetail Page cleaned up');
    }
}

// Global functions for button actions (called from template)
window.cancelJob = async (jobId) => {
    if (confirm('Are you sure you want to cancel this job?')) {
        try {
            const result = await JobManager.cancelJob(jobId);
            if (result) {
                location.reload();
            }
        } catch (error) {
            alert(`Failed to cancel job: ${error.message}`);
        }
    }
};

window.retryJob = (_jobId) => {
    alert('Retry functionality not yet implemented');
};

window.refreshJobData = (_jobId) => {
    location.reload();
};

window.checkCreatomateStatus = async (creatomateId) => {
    try {
        const result = await APIService.getCreatomateStatus(creatomateId);
        if (result.success) {
            alert(`Creatomate Status: ${result.status}\nProgress: ${result.progress || 'N/A'}%`);
        } else {
            alert(`Error: ${result.message}`);
        }
    } catch (error) {
        alert(`Error checking status: ${error.message}`);
    }
};

window.copyToClipboard = async (text) => {
    try {
        await navigator.clipboard.writeText(text);
        alert('URL copied to clipboard!');
    } catch (error) {
        alert('Failed to copy URL');
    }
};

// Export singleton instance
export default new JobDetailPage();
