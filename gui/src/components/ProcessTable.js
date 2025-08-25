/**
 * ProcessTable - Manages the job process table display
 * Handles job status updates, table population, and job actions
 */

import APIService from '../services/APIService.js';
import UIManager from './UIManager.js';

class ProcessTable {
    constructor() {
        this.processData = new Map(); // Store job data
        this.isInitialized = false;
        this.updateInterval = null;
    }

    /**
     * Initialize the process table
     */
    async init() {
        if (this.isInitialized) {
            return;
        }

        console.log('🔧 ProcessTable initializing...');

        await this.loadRecentJobs();
        this.setupEventListeners();
        this.startPeriodicUpdates();

        this.isInitialized = true;
        console.log('✅ ProcessTable initialized');
    }

    /**
     * Setup event listeners for process table actions
     */
    setupEventListeners() {
        // View job button handler (delegated event with proper child element handling)
        document.addEventListener('click', (e) => {
            const viewButton = e.target.closest('.btn-view-job');
            if (viewButton) {
                e.preventDefault();
                const jobId = viewButton.dataset.jobId;
                console.log(`🎯 View button clicked for job: ${jobId}`);
                this.viewJob(jobId);
            }
        });

        // Cancel job button handler (delegated event with proper child element handling)
        document.addEventListener('click', (e) => {
            const cancelButton = e.target.closest('.btn-cancel-job');
            if (cancelButton) {
                e.preventDefault();
                const jobId = cancelButton.dataset.jobId;
                console.log(`🚫 Cancel button clicked for job: ${jobId}`);
                this.cancelJob(jobId);
            }
        });

        // Delete job button handler (delegated event with proper child element handling)
        document.addEventListener('click', (e) => {
            const deleteButton = e.target.closest('.btn-delete-job');
            if (deleteButton) {
                e.preventDefault();
                const jobId = deleteButton.dataset.jobId;
                console.log(`🗑️ Delete button clicked for job: ${jobId}`);
                this.deleteJob(jobId);
            }
        });
    }

    /**
     * Load recent jobs from API
     */
    async loadRecentJobs() {
        // ANTI-SPAM: Don't load if page is not visible
        if (document.hidden) {
            console.log('📋 ProcessTable: Skipping job load - page not visible (anti-spam)');
            return;
        }

        try {
            console.log('📋 ProcessTable: Loading jobs from /api/queue/jobs...');
            const response = await APIService.get('/api/queue/jobs');

            console.log('📋 ProcessTable: API response:', response);

            if (response.success && response.jobs) {
                console.log(`📋 ProcessTable: Received ${response.jobs.length} jobs`);
                console.log('📋 ProcessTable: Raw job data:', response.jobs[0]); // Debug first job

                // Clear existing process data
                this.processData.clear();

                // Add jobs to process data
                response.jobs.forEach((job) => {
                    console.log(`📋 Processing job:`, job); // Debug each job structure

                    const processedJob = {
                        id: job.id,
                        status: job.status || 'pending',
                        country: job.parameters?.country || job.country || 'Unknown',
                        platform: job.parameters?.platform || job.platform || 'Unknown',
                        genre: job.parameters?.genre || job.genre || 'Unknown',
                        contentType: job.parameters?.contentType || job.contentType || 'Unknown',
                        createdAt: job.createdAt || new Date().toISOString(),
                        startedAt: job.startedAt,
                        completedAt: job.completedAt,
                        failedAt: job.failedAt,
                        progress: job.progress || 0,
                        workerId: job.workerId,
                        error: job.error
                    };

                    console.log(`📋 Processed job data:`, processedJob);
                    this.processData.set(job.id, processedJob);
                });

                console.log(`📋 Loaded ${response.jobs.length} jobs into process table`);
                this.updateProcessTable();
            } else {
                console.log('📋 ProcessTable: No jobs received or API failed');
                // Still update table to show empty state
                this.updateProcessTable();
            }
        } catch (error) {
            console.error('❌ Failed to load recent jobs:', error);
            UIManager.addStatusMessage('error', '❌', 'Failed to load job history');
            // Still update table to show empty state
            this.updateProcessTable();
        }
    }

    /**
     * Update the professional job dashboard with current job data
     */
    updateProcessTable() {
        const jobCardsContainer = document.getElementById('job-cards-container');
        const emptyState = document.getElementById('empty-jobs-state');
        const loadingState = document.getElementById('jobs-loading-state');
        const jobCountBadge = document.getElementById('job-count-badge');

        console.log('📊 JobDashboard: Updating dashboard...');
        console.log('📊 JobDashboard: Cards container found:', !!jobCardsContainer);
        console.log('📊 JobDashboard: Empty state found:', !!emptyState);

        if (!jobCardsContainer) {
            console.warn('⚠️ Job cards container not found');
            return;
        }

        // Hide loading state
        if (loadingState) {
            loadingState.style.display = 'none';
        }

        // Clear existing cards
        jobCardsContainer.innerHTML = '';

        console.log(`📊 JobDashboard: Processing ${this.processData.size} jobs`);

        // Update job count badge
        if (jobCountBadge) {
            jobCountBadge.textContent = this.processData.size;
        }

        if (this.processData.size === 0) {
            // Show empty state
            if (emptyState) {
                emptyState.style.display = 'block';
                console.log('📊 JobDashboard: Showing empty state');
            }
            return;
        }

        // Hide empty state
        if (emptyState) {
            emptyState.style.display = 'none';
        }

        // Create job cards
        const sortedJobs = Array.from(this.processData.values()).sort(
            (a, b) => new Date(b.createdAt) - new Date(a.createdAt)
        );

        sortedJobs.forEach((job) => {
            const jobCard = this.createJobCard(job);
            jobCardsContainer.appendChild(jobCard);
        });

        console.log(`📊 JobDashboard: Updated with ${sortedJobs.length} job cards`);
    }

    /**
     * Create a professional job card
     * @param {Object} job - Job data
     * @returns {HTMLElement} Job card element
     */
    createJobCard(job) {
        const cardCol = document.createElement('div');
        cardCol.className = 'col-lg-6 col-xl-4';

        const statusClass = this.getStatusClass(job.status);
        const statusIcon = this.getStatusIcon(job.status);
        const shortId = job.id ? job.id.slice(-8) : 'Unknown';

        // Calculate duration and time information
        let duration = 'Not started';
        let startedTime = 'Not started';
        let timeClass = 'text-muted';

        if (job.startedAt) {
            const startTime = new Date(job.startedAt);
            startedTime = startTime.toLocaleString();

            const endTime = job.completedAt || job.failedAt || new Date();
            const durationMs = new Date(endTime) - startTime;
            const durationMinutes = Math.floor(durationMs / 60000);
            const durationSeconds = Math.floor((durationMs % 60000) / 1000);

            if (durationMinutes > 0) {
                duration = `${durationMinutes}m ${durationSeconds}s`;
            } else {
                duration = `${durationSeconds}s`;
            }
            timeClass = 'text-info';
        } else if (job.createdAt) {
            startedTime = `Created: ${new Date(job.createdAt).toLocaleString()}`;
            timeClass = 'text-warning';
        }

        // Progress calculation for visual appeal
        const progress = job.progress || 0;
        const progressColor = progress >= 100 ? 'bg-success' : progress >= 50 ? 'bg-info' : 'bg-warning';

        // Status-specific styling
        let cardBorderClass = 'border-secondary';
        let statusBgClass = 'bg-secondary';

        switch (job.status) {
            case 'pending':
                cardBorderClass = 'border-warning';
                statusBgClass = 'bg-warning';
                break;
            case 'active':
            case 'processing':
                cardBorderClass = 'border-info';
                statusBgClass = 'bg-info';
                break;
            case 'completed':
                cardBorderClass = 'border-success';
                statusBgClass = 'bg-success';
                break;
            case 'failed':
                cardBorderClass = 'border-danger';
                statusBgClass = 'bg-danger';
                break;
            case 'cancelled':
                cardBorderClass = 'border-dark';
                statusBgClass = 'bg-dark';
                break;
        }

        cardCol.innerHTML = `
            <div class="card bg-dark ${cardBorderClass} h-100" style="border-radius: 12px; border-width: 2px;">
                <!-- Card Header -->
                <div class="card-header ${statusBgClass} text-white d-flex justify-content-between align-items-center" style="border-radius: 10px 10px 0 0;">
                    <div class="d-flex align-items-center">
                        <span class="me-2" style="font-size: 1.2em;">${statusIcon}</span>
                        <div>
                            <h6 class="mb-0">Job ${shortId}</h6>
                            <small style="opacity: 0.9;">${job.status.charAt(0).toUpperCase() + job.status.slice(1)}</small>
                        </div>
                    </div>
                    <div class="text-end">
                        <div class="btn-group" role="group">
                            <button class="btn btn-sm btn-outline-light btn-view-job" 
                                    data-job-id="${job.id}" title="View Details">
                                <i class="fas fa-eye"></i>
                            </button>
                            ${
                                job.status === 'pending' || job.status === 'active'
                                    ? `
                            <button class="btn btn-sm btn-outline-light btn-cancel-job" 
                                    data-job-id="${job.id}" title="Cancel Job">
                                <i class="fas fa-times"></i>
                            </button>
                            `
                                    : ''
                            }
                            ${
                                job.status === 'failed' || job.status === 'completed' || job.status === 'cancelled'
                                    ? `
                            <button class="btn btn-sm btn-danger btn-delete-job" 
                                    data-job-id="${job.id}" title="Delete Job Permanently"
                                    style="border: 1px solid #dc3545; background-color: #dc3545; color: white;">
                                <i class="fas fa-trash"></i>
                            </button>
                            `
                                    : ''
                            }
                        </div>
                    </div>
                </div>

                <!-- Card Body -->
                <div class="card-body">
                    <!-- Progress Section -->
                    <div class="mb-3">
                        <div class="d-flex justify-content-between align-items-center mb-2">
                            <small class="text-light fw-bold">Progress</small>
                            <small class="text-light">${progress}%</small>
                        </div>
                        <div class="progress" style="height: 8px; background-color: #495057; border-radius: 10px;">
                            <div class="progress-bar ${progressColor}" role="progressbar" 
                                 style="width: ${progress}%; border-radius: 10px;" 
                                 aria-valuenow="${progress}" aria-valuemin="0" aria-valuemax="100">
                            </div>
                        </div>
                        ${
                            job.currentStep
                                ? `
                        <small class="text-muted mt-1 d-block" style="font-size: 0.75em;">
                            ${job.currentStep}
                        </small>
                        `
                                : ''
                        }
                    </div>

                    <!-- Job Parameters -->
                    <div class="row g-2 mb-3">
                        <div class="col-6">
                            <div class="bg-secondary bg-opacity-25 p-2 rounded">
                                <small class="text-muted d-block">Country</small>
                                <small class="text-light fw-bold">${job.country || 'Unknown'}</small>
                            </div>
                        </div>
                        <div class="col-6">
                            <div class="bg-secondary bg-opacity-25 p-2 rounded">
                                <small class="text-muted d-block">Platform</small>
                                <small class="text-info fw-bold">${job.platform || 'Unknown'}</small>
                            </div>
                        </div>
                        <div class="col-6">
                            <div class="bg-secondary bg-opacity-25 p-2 rounded">
                                <small class="text-muted d-block">Genre</small>
                                <small class="text-warning fw-bold">${job.genre || 'Unknown'}</small>
                            </div>
                        </div>
                        <div class="col-6">
                            <div class="bg-secondary bg-opacity-25 p-2 rounded">
                                <small class="text-muted d-block">Type</small>
                                <small class="text-light fw-bold">${job.contentType || 'Unknown'}</small>
                            </div>
                        </div>
                    </div>

                    <!-- Time Information -->
                    <div class="text-center">
                        <small class="${timeClass}">
                            <i class="fas fa-clock me-1"></i>
                            ${startedTime}
                        </small>
                        ${
                            duration !== 'Not started'
                                ? `
                        <br><small class="text-muted">
                            <i class="fas fa-stopwatch me-1"></i>
                            Duration: ${duration}
                        </small>
                        `
                                : ''
                        }
                        ${
                            job.workerId
                                ? `
                        <br><small class="text-muted">
                            <i class="fas fa-user me-1"></i>
                            Worker: ${job.workerId.slice(-8)}
                        </small>
                        `
                                : ''
                        }
                    </div>

                    ${
                        job.status === 'failed' && job.error
                            ? `
                    <!-- Error Information -->
                    <div class="mt-3 p-2 bg-danger bg-opacity-25 rounded border border-danger">
                        <small class="text-danger fw-bold">
                            <i class="fas fa-exclamation-triangle me-1"></i>
                            Error
                        </small>
                        <small class="text-light d-block mt-1" style="font-size: 0.75em;">
                            ${job.error.length > 60 ? job.error.substring(0, 60) + '...' : job.error}
                        </small>
                    </div>
                    `
                            : ''
                    }
                </div>
            </div>
        `;

        return cardCol;
    }

    /**
     * Get CSS class for job status
     * @param {string} status - Job status
     * @returns {string} CSS class
     */
    getStatusClass(status) {
        const statusMap = {
            pending: 'bg-warning',
            active: 'bg-info',
            completed: 'bg-success',
            failed: 'bg-danger',
            cancelled: 'bg-secondary'
        };
        return statusMap[status] || 'bg-secondary';
    }

    /**
     * Get icon for job status
     * @param {string} status - Job status
     * @returns {string} Status icon
     */
    getStatusIcon(status) {
        const iconMap = {
            pending: '⏳',
            active: '⚡',
            completed: '✅',
            failed: '❌',
            cancelled: '🚫'
        };
        return iconMap[status] || '❓';
    }

    /**
     * View job details (redirects to job detail page)
     * @param {string} jobId - Job ID
     */
    async viewJob(jobId) {
        try {
            console.log(`👁️ Redirecting to job details page: ${jobId}`);

            // Redirect to the job detail page
            window.location.href = `/job/${jobId}`;
        } catch (error) {
            console.error('❌ Failed to redirect to job details:', error);
            UIManager.addStatusMessage('error', '❌', 'Failed to open job details');
        }
    }

    /**
     * Cancel a job
     * @param {string} jobId - Job ID
     */
    async cancelJob(jobId) {
        if (!confirm(`Cancel job ${jobId.slice(-8)}?`)) {
            return;
        }

        try {
            const response = await APIService.delete(`/api/queue/job/${jobId}`);

            if (response.success) {
                UIManager.addStatusMessage('success', '✅', 'Job cancelled successfully');

                // Update job status in local data
                const job = this.processData.get(jobId);
                if (job) {
                    job.status = 'cancelled';
                    this.updateProcessTable();
                }
            } else {
                throw new Error(response.error || 'Failed to cancel job');
            }
        } catch (error) {
            console.error('❌ Failed to cancel job:', error);
            UIManager.addStatusMessage('error', '❌', `Failed to cancel job: ${error.message}`);
        }
    }

    /**
     * Delete a completed or failed job permanently
     * @param {string} jobId - Job ID
     */
    async deleteJob(jobId) {
        const job = this.processData.get(jobId);
        const jobShortId = jobId.slice(-8);
        const statusText = job ? job.status : 'Unknown';

        if (!confirm(`⚠️ Permanently delete ${statusText} job ${jobShortId}?\n\nThis action cannot be undone!`)) {
            return;
        }

        try {
            const response = await APIService.delete(`/api/queue/job/${jobId}/delete`);

            if (response.success) {
                UIManager.addStatusMessage('success', '🗑️', `Job ${jobShortId} deleted successfully`);

                // Remove job from local data completely
                this.processData.delete(jobId);
                this.updateProcessTable();
            } else {
                throw new Error(response.error || 'Failed to delete job');
            }
        } catch (error) {
            console.error('❌ Failed to delete job:', error);
            UIManager.addStatusMessage('error', '❌', `Failed to delete job: ${error.message}`);
        }
    }

    /**
     * Update job status (called from real-time updates)
     * @param {Object} jobUpdate - Job update data
     */
    updateJobStatus(jobUpdate) {
        const job = this.processData.get(jobUpdate.id);
        if (job) {
            // Update job data
            Object.assign(job, jobUpdate);

            // Update table if needed
            this.updateProcessTable();
        }
    }

    /**
     * Add new job to table
     * @param {Object} jobData - New job data
     */
    addJob(jobData) {
        this.processData.set(jobData.id, jobData);
        this.updateProcessTable();
    }

    /**
     * Start periodic updates for job status
     */
    startPeriodicUpdates() {
        // Clear any existing interval to prevent duplicates
        this.stopPeriodicUpdates();

        // ANTI-SPAM: Much longer intervals - webhooks provide real-time updates
        this.updateInterval = setInterval(() => {
            console.log('📋 ProcessTable: Periodic backup refresh (anti-spam mode)');
            this.loadRecentJobs();
        }, 600000); // 10 minutes backup only - webhooks do the real work

        console.log('📋 ProcessTable: Started 10-minute backup polling (anti-spam)');
    }

    /**
     * Stop periodic updates
     */
    stopPeriodicUpdates() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
            this.updateInterval = null;
        }
    }

    /**
     * Get current process data
     * @returns {Map} Process data map
     */
    getProcessData() {
        return this.processData;
    }

    /**
     * Cleanup resources
     */
    cleanup() {
        this.stopPeriodicUpdates();
        this.processData.clear();
        this.isInitialized = false;
    }
}

// Export singleton instance
const processTableInstance = new ProcessTable();

// Make globally available for immediate dashboard updates
window.ProcessTable = processTableInstance;

export default processTableInstance;
