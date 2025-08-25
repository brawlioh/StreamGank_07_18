/**
 * Professional Job Detail Application
 * Real-time job monitoring with live progress updates, timeline, and logs
 */

import APIService from './services/APIService.js';
import RealtimeService from './services/RealtimeService.js';

export class JobDetailApp {
    constructor() {
        this.jobId = this.extractJobIdFromURL();
        this.jobData = null;
        this.refreshInterval = null;
        this.logUpdateInterval = null;
        this.autoScroll = true;
        this.isInitialized = false;
        this.lastRefreshTime = 0; // Track last refresh for smart intervals
        this.jobSSE = null; // Job-specific SSE connection
        this.currentActiveStep = null; // Track currently active step from webhooks

        // Timeline steps for video generation process - MATCHES ACTUAL WORKFLOW.PY
        this.processSteps = [
            { id: 'database_extraction', name: 'Database Extraction', description: 'Extracting movies from database' },
            { id: 'script_generation', name: 'Script Generation', description: 'Generating AI scripts for content' },
            {
                id: 'asset_preparation',
                name: 'Asset Preparation',
                description: 'Creating enhanced posters and movie clips'
            },
            { id: 'heygen_creation', name: 'HeyGen Video Creation', description: 'Generating AI avatar videos' },
            { id: 'heygen_processing', name: 'HeyGen Processing', description: 'Waiting for video completion' },
            {
                id: 'scroll_generation',
                name: 'Scroll Video Generation',
                description: 'Creating StreamGank scroll overlay'
            },
            { id: 'creatomate_assembly', name: 'Creatomate Assembly', description: 'Creating final video' }
        ];
    }

    /**
     * Initialize the application
     */
    async initialize() {
        try {
            console.log('🎬 Initializing Professional Job Detail App...');

            if (!this.jobId) {
                this.showError('Invalid job ID in URL');
                return;
            }

            // Set up event listeners
            this.setupEventListeners();

            // Load initial job data
            await this.loadJobData();

            // Start real-time updates
            this.startRealTimeUpdates();

            // Show main content
            this.showMainContent();

            console.log(`✅ Job Detail App initialized for job: ${this.jobId}`);
            this.isInitialized = true;
        } catch (error) {
            console.error('❌ Failed to initialize Job Detail App:', error);
            this.showError(`Failed to load job: ${error.message}`);
        }
    }

    /**
     * Extract job ID from current URL
     */
    extractJobIdFromURL() {
        const pathParts = window.location.pathname.split('/');
        const jobIndex = pathParts.indexOf('job');
        return jobIndex !== -1 && pathParts[jobIndex + 1] ? pathParts[jobIndex + 1] : null;
    }

    /**
     * Set up event listeners
     */
    setupEventListeners() {
        // Back button
        document.getElementById('back-btn')?.addEventListener('click', () => {
            window.history.back();
        });

        // Refresh button
        document.getElementById('refresh-btn')?.addEventListener('click', () => {
            this.refreshJobData();
        });

        // Clear logs button
        document.getElementById('clear-logs-btn')?.addEventListener('click', () => {
            this.clearLogs();
        });

        // Auto-scroll toggle
        document.getElementById('auto-scroll-btn')?.addEventListener('click', (e) => {
            this.toggleAutoScroll(e.target);
        });

        // Real-time service events
        RealtimeService.addEventListener('jobUpdate', (event) => {
            if (event.detail.jobId === this.jobId) {
                this.handleJobUpdate(event.detail);
            }
        });

        RealtimeService.addEventListener('jobLog', (event) => {
            if (event.detail.jobId === this.jobId) {
                // Log functionality removed
            }
        });
    }

    /**
     * Load job data from API
     */
    async loadJobData() {
        try {
            console.log(`📡 Loading job data for: ${this.jobId}`);

            const response = await APIService.getJobStatus(this.jobId);

            if (!response.success || !response.job) {
                throw new Error('Job not found');
            }

            this.jobData = response.job;
            this.lastRefreshTime = Date.now(); // Initialize refresh tracking
            this.updateUI();

            // Add page unload cleanup for SSE connections
            window.addEventListener('beforeunload', () => {
                this.closeJobSSE();
            });

            console.log('✅ Job data loaded successfully');
        } catch (error) {
            console.error('❌ Failed to load job data:', error);
            throw error;
        }
    }

    /**
     * Update the entire UI with current job data
     */
    updateUI() {
        if (!this.jobData) return;

        console.log('🔄 Updating UI with job data:', this.jobData);

        this.updateJobHeader();
        this.updateProgressSection();
        this.updateJobParameters();
        this.updateTimeline();
        this.updateQuickStats();
        this.updateActionButtons();
        this.updateErrorInfo();
        this.updateVideoResult();
    }

    /**
     * Update job header information
     */
    updateJobHeader() {
        const jobIdElement = document.getElementById('job-id');
        const statusBadge = document.getElementById('job-status-badge');
        const overviewCard = document.getElementById('job-overview-card');

        if (jobIdElement) {
            jobIdElement.textContent = this.jobData.id || 'Unknown';
        }

        if (statusBadge) {
            const status = this.jobData.status || 'unknown';
            statusBadge.textContent = status.charAt(0).toUpperCase() + status.slice(1);
            statusBadge.className = `badge ${this.getStatusBadgeClass(status)} ms-2`;
        }

        if (overviewCard) {
            overviewCard.className = `card bg-dark status-card mb-4 status-${this.jobData.status}`;
        }
    }

    /**
     * Update progress section
     */
    updateProgressSection() {
        const progressBar = document.getElementById('progress-bar');
        const progressPercentage = document.getElementById('progress-percentage');
        const currentStep = document.getElementById('current-step');

        // PRODUCTION FIX: Always show 100% for completed jobs with video URL
        let progress = this.jobData.progress || 0;

        // Override progress for truly completed jobs
        if (this.jobData.status === 'completed' && this.jobData.videoUrl) {
            progress = 100;
        }
        // Show actual progress for completed jobs without video (still rendering)
        else if (this.jobData.status === 'completed' && !this.jobData.videoUrl) {
            // Keep the actual progress to show it's not truly done yet
            progress = this.jobData.progress || 0;
        }
        // Also ensure failed/cancelled jobs show their actual progress, not stuck at partial
        else if (this.jobData.status === 'failed' || this.jobData.status === 'cancelled') {
            // Keep original progress for failed/cancelled to show where it stopped
            progress = this.jobData.progress || 0;
        }

        if (progressBar) {
            progressBar.style.width = `${progress}%`;
            progressBar.className = `progress-bar ${this.getProgressBarClass(progress)} progress-bar-striped ${progress < 100 && ['active', 'processing', 'rendering'].includes(this.jobData.status) ? 'progress-bar-animated' : ''}`;
        }

        if (progressPercentage) {
            progressPercentage.textContent = `${progress}%`;
        }

        if (currentStep) {
            currentStep.textContent = this.jobData.currentStep || this.getStepFromProgress(progress);
        }
    }

    /**
     * Update job parameters display
     */
    updateJobParameters() {
        const parametersContainer = document.getElementById('job-parameters');
        if (!parametersContainer) return;

        const params = [
            { label: 'Country', value: this.jobData.country, icon: 'fas fa-globe' },
            { label: 'Platform', value: this.jobData.platform, icon: 'fas fa-tv' },
            { label: 'Genre', value: this.jobData.genre, icon: 'fas fa-tags' },
            { label: 'Content Type', value: this.jobData.contentType, icon: 'fas fa-film' },
            { label: 'Template', value: this.jobData.template || 'Default', icon: 'fas fa-palette' },
            { label: 'Worker ID', value: this.jobData.workerId || 'Unassigned', icon: 'fas fa-user' }
        ];

        // Add Creatomate ID if available
        if (this.jobData.creatomateId) {
            params.push({
                label: 'Creatomate ID',
                value: this.jobData.creatomateId,
                icon: 'fas fa-video'
            });
        }

        parametersContainer.innerHTML = params
            .map(
                (param) => `
            <div class="param-badge">
                <i class="${param.icon}"></i>
                <span class="label">${param.label}:</span>
                <span class="value">${param.value || 'Unknown'}</span>
            </div>
        `
            )
            .join('');
    }

    /**
     * Update process timeline
     */
    updateTimeline() {
        const timelineContainer = document.getElementById('job-timeline');
        if (!timelineContainer) return;

        const currentProgress = this.jobData.progress || 0;
        const status = this.jobData.status;

        timelineContainer.innerHTML = this.processSteps
            .map((step, index) => {
                let iconClass = 'pending';
                let timestamp = '';

                // NEW: Use real-time webhook data to determine active step
                const stepNumber = index + 1;
                
                if (this.currentActiveStep === stepNumber) {
                    // This step is currently active (received "started" webhook)
                    iconClass = 'active';
                } else if (status === 'failed' && this.getProgressForStep(step.id) <= currentProgress) {
                    iconClass = 'failed';
                } else if (this.getProgressForStep(step.id) < currentProgress) {
                    // Step is completed (progress has moved past it)
                    iconClass = 'completed';
                    timestamp = this.getStepTimestamp(step.id);
                } else {
                    // Step is pending
                    iconClass = 'pending';
                }

                return `
                <div class="timeline-step ${iconClass}">
                    <div class="step-icon">
                        ${this.getStepIcon(step.id, iconClass)}
                    </div>
                    <div class="step-title">${step.name}</div>
                    <div class="step-status text-muted">${this.getStepStatusText(iconClass, timestamp)}</div>
                </div>
            `;
            })
            .join('');
    }

    /**
     * Update quick stats
     */
    updateQuickStats() {
        const duration = this.calculateDuration();
        const steps = this.getCurrentStepNumber();
        const worker = this.jobData.workerId ? this.jobData.workerId.slice(-4) : '--';
        const priority = this.jobData.priority || 'Normal';

        document.getElementById('stat-duration').textContent = duration;
        document.getElementById('stat-steps').textContent = steps;
        document.getElementById('stat-worker').textContent = worker;
        document.getElementById('stat-priority').textContent = priority;
    }

    /**
     * Update action buttons
     */
    updateActionButtons() {
        const actionsContainer = document.getElementById('job-actions');
        if (!actionsContainer) return;

        const status = this.jobData.status;
        let buttons = [];

        if (status === 'pending' || status === 'active') {
            buttons.push(`
                <button class="btn btn-outline-warning" onclick="jobDetailApp.cancelJob()">
                    <i class="fas fa-stop-circle me-1"></i> Cancel Job
                </button>
            `);
        }

        if (status === 'failed') {
            buttons.push(`
                <button class="btn btn-outline-primary" onclick="jobDetailApp.retryJob()">
                    <i class="fas fa-redo me-1"></i> Retry Job
                </button>
            `);
        }

        // Show monitoring button for jobs with Creatomate ID but no video URL
        if ((status === 'completed' || status === 'rendering') && this.jobData.creatomateId && !this.jobData.videoUrl) {
            if (this.jobData.workflowIncomplete) {
                // Workflow was incomplete - show warning button with different action
                buttons.push(`
                    <button class="btn btn-outline-danger" onclick="jobDetailApp.showWorkflowWarning()">
                        <i class="fas fa-exclamation-triangle me-1"></i> Workflow Issue
                    </button>
                `);
            } else {
                // Normal case - show monitoring button (works for both completed and rendering status)
                const buttonText = status === 'rendering' ? 'Check Render Status' : 'Check Video Status';
                buttons.push(`
                    <button class="btn btn-outline-warning" onclick="jobDetailApp.monitorCreatomate()">
                        <i class="fas fa-eye me-1"></i> ${buttonText}
                    </button>
                `);
            }
        }

        // Clean interface - log management buttons removed

        if (this.jobData.videoUrl) {
            buttons.push(`
                <a href="${this.jobData.videoUrl}" target="_blank" class="btn btn-success">
                    <i class="fas fa-play me-1"></i> Watch Video
                </a>
                <a href="${this.jobData.videoUrl}" download class="btn btn-outline-success">
                    <i class="fas fa-download me-1"></i> Download
                </a>
            `);
        }

        // Always show refresh button
        buttons.push(`
            <button class="btn btn-outline-info" onclick="jobDetailApp.refreshJobData()">
                <i class="fas fa-sync-alt me-1"></i> Refresh Status
            </button>
        `);

        actionsContainer.innerHTML = buttons.join('');
    }

    /**
     * Update error information
     */
    updateErrorInfo() {
        const errorCard = document.getElementById('error-card');
        const errorContent = document.getElementById('error-content');

        if (this.jobData.status === 'failed' && this.jobData.error) {
            errorContent.innerHTML = `
                <h6 class="text-danger mb-2">
                    <i class="fas fa-bug me-1"></i> Error Details
                </h6>
                <div class="bg-dark p-3 rounded border border-danger">
                    <code class="text-light">${this.jobData.error}</code>
                </div>
                ${
                    this.jobData.errorTimestamp
                        ? `
                <small class="text-muted d-block mt-2">
                    <i class="fas fa-clock me-1"></i> 
                    Error occurred: ${new Date(this.jobData.errorTimestamp).toLocaleString()}
                </small>
                `
                        : ''
                }
            `;
            errorCard.classList.remove('d-none');
        } else {
            errorCard.classList.add('d-none');
        }
    }

    /**
     * Update video result section - Always shows video section, displays either processing status or completed video
     */
    updateVideoResult() {
        const videoCard = document.getElementById('video-result-card');
        const videoContent = document.getElementById('video-content');
        
        // Video preview section (replaces live logs completely)
        const videoPreviewSection = document.getElementById('video-preview-section');
        const videoPreviewContent = document.getElementById('video-preview-content');
        const videoSectionTitle = document.getElementById('video-section-title');
        const videoStatusBadge = document.getElementById('video-status-badge');
        const currentProcessingStep = document.getElementById('current-processing-step');

        // Always show the video section
        if (videoPreviewSection) {
            videoPreviewSection.classList.remove('d-none');
        }

        if (this.jobData.status === 'completed' && this.jobData.videoUrl) {
            // Video is completed - show video player and download options
            if (videoSectionTitle) videoSectionTitle.textContent = 'Video Preview';
            if (videoStatusBadge) {
                videoStatusBadge.textContent = 'Completed';
                videoStatusBadge.className = 'badge bg-success ms-2';
            }

            if (videoPreviewContent) {
                videoPreviewContent.innerHTML = `
                    <div class="row">
                        <div class="col-lg-8">
                            <div class="mb-3">
                                <video controls class="w-100 rounded" style="max-height: 400px;">
                                    <source src="${this.jobData.videoUrl}" type="video/mp4">
                                    Your browser does not support the video tag.
                                </video>
                            </div>
                        </div>
                        <div class="col-lg-4">
                            <div class="d-grid gap-2">
                                <a href="${this.jobData.videoUrl}" target="_blank" class="btn btn-success">
                                    <i class="fas fa-external-link-alt me-1"></i> Open in New Tab
                                </a>
                                <a href="${this.jobData.videoUrl}" download class="btn btn-outline-light">
                                    <i class="fas fa-download me-1"></i> Download Video
                                </a>
                                <button class="btn btn-outline-info" onclick="jobDetailApp.copyVideoUrl()">
                                    <i class="fas fa-copy me-1"></i> Copy URL
                                </button>
                            </div>
                            <div class="mt-3">
                                <h6 class="text-light mb-2">
                                    <i class="fas fa-info-circle me-1"></i> Video Details
                                </h6>
                                <div class="text-muted small">
                                    <div><strong>Status:</strong> Ready</div>
                                    <div><strong>Duration:</strong> ${this.calculateDuration()}</div>
                                    <div><strong>Completed:</strong> ${new Date(this.jobData.completedAt || Date.now()).toLocaleString()}</div>
                                    ${this.jobData.creatomateId ? `<div><strong>Render ID:</strong> ${this.jobData.creatomateId}</div>` : ''}
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            }

            // Also populate the old video result card (if still used elsewhere)
            if (videoContent) {
                videoContent.innerHTML = `
                    <div class="mb-3">
                        <video controls class="w-100 rounded" style="max-height: 300px;">
                            <source src="${this.jobData.videoUrl}" type="video/mp4">
                            Your browser does not support the video tag.
                        </video>
                    </div>
                    <div class="d-grid gap-2">
                        <a href="${this.jobData.videoUrl}" target="_blank" class="btn btn-success">
                            <i class="fas fa-external-link-alt me-1"></i> Open in New Tab
                        </a>
                        <a href="${this.jobData.videoUrl}" download class="btn btn-outline-light">
                            <i class="fas fa-download me-1"></i> Download Video
                        </a>
                        <button class="btn btn-outline-info" onclick="jobDetailApp.copyVideoUrl()">
                            <i class="fas fa-copy me-1"></i> Copy URL
                        </button>
                    </div>
                `;
                videoCard.classList.remove('d-none');
            }
        } else {
            // Video not ready - show processing status
            const status = this.jobData.status || 'pending';
            const currentStep = this.jobData.currentStep || 'Initializing...';
            
            if (videoSectionTitle) videoSectionTitle.textContent = 'Video Processing';
            if (videoStatusBadge) {
                if (status === 'failed') {
                    videoStatusBadge.textContent = 'Failed';
                    videoStatusBadge.className = 'badge bg-danger ms-2';
                } else if (status === 'cancelled') {
                    videoStatusBadge.textContent = 'Cancelled';
                    videoStatusBadge.className = 'badge bg-secondary ms-2';
                } else if (status === 'active' || status === 'processing') {
                    videoStatusBadge.textContent = 'Processing';
                    videoStatusBadge.className = 'badge bg-info ms-2';
                } else {
                    videoStatusBadge.textContent = 'Pending';
                    videoStatusBadge.className = 'badge bg-warning ms-2';
                }
            }

            if (currentProcessingStep) {
                currentProcessingStep.textContent = currentStep;
            }

            if (videoPreviewContent) {
                let statusIcon = 'fas fa-circle-notch fa-spin';
                let statusTitle = 'Video Processing in Progress';
                let statusMessage = 'Your video is being generated. This usually takes 2-5 minutes.';
                
                if (status === 'failed') {
                    statusIcon = 'fas fa-exclamation-triangle text-danger';
                    statusTitle = 'Video Processing Failed';
                    statusMessage = 'There was an error generating your video. Please try again.';
                } else if (status === 'cancelled') {
                    statusIcon = 'fas fa-ban text-secondary';
                    statusTitle = 'Video Processing Cancelled';
                    statusMessage = 'Video generation was cancelled by user request.';
                } else if (status === 'pending') {
                    statusIcon = 'fas fa-clock text-warning';
                    statusTitle = 'Video Processing Queued';
                    statusMessage = 'Your video is in the queue and will start processing shortly.';
                }

                videoPreviewContent.innerHTML = `
                    <div id="processing-status" class="text-center py-4">
                        <div class="mb-3">
                            <i class="${statusIcon}" style="font-size: 3rem;"></i>
                        </div>
                        <h6 class="text-light mb-2">${statusTitle}</h6>
                        <p class="text-muted">${statusMessage}</p>
                        <div class="mt-3">
                            <small class="text-muted">Current step: <span id="current-processing-step">${currentStep}</span></small>
                        </div>
                        ${status === 'active' || status === 'processing' ? `
                        <div class="mt-3">
                            <div class="progress" style="height: 8px;">
                                <div class="progress-bar progress-bar-striped progress-bar-animated" 
                                     style="width: ${this.jobData.progress || 0}%"></div>
                            </div>
                            <small class="text-muted mt-1 d-block">${this.jobData.progress || 0}% complete</small>
                        </div>
                        ` : ''}
                    </div>
                `;
            }
            
            if (videoCard) {
                videoCard.classList.add('d-none');
            }
        }
    }

    /**
     * Start real-time updates
     */
    startRealTimeUpdates() {
        console.log('🔄 Starting webhook-optimized updates (reduced polling)...');

        // Initialize job-specific real-time updates
        this.initializeJobSSE();

        // WEBHOOK-OPTIMIZED: Much longer intervals since webhooks provide real-time updates
        this.refreshInterval = setInterval(() => {
            // WEBHOOK-ONLY: Minimal polling - webhooks handle ALL real-time updates
            // Only check for final video URL on completed jobs

            if (['completed', 'rendering'].includes(this.jobData?.status) && !this.jobData?.videoUrl) {
                // Check for final video URL once job is completed
                this.refreshJobData();
                console.log('🔄 Checking for final video URL');
            } else if (this.jobData?.videoUrl || ['failed', 'cancelled'].includes(this.jobData?.status)) {
                // Job fully complete or failed - stop all polling
                console.log('🛑 Job complete, stopping all polling');
                this.stopRealTimeUpdates();
                return;
            }

            // No polling for active jobs - webhooks provide all updates
        }, 600000); // Check every 10 minutes ONLY for final video URL

        // Log updates disabled - using video preview section instead
        // this.startLogUpdates();
    }

    /**
     * Stop real-time updates when job is finished
     */
    stopRealTimeUpdates() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
            console.log('🛑 Stopped job refresh interval');
        }

        if (this.logUpdateInterval) {
            clearInterval(this.logUpdateInterval);
            this.logUpdateInterval = null;
            console.log('🛑 Stopped log update interval');
        }

        // Close job-specific SSE connection
        this.closeJobSSE();
    }

    /**
     * Load essential logs once - webhooks handle real-time updates
     */
    startLogUpdates() {
        // Initial log fetch only - no more polling spam
        console.log('📋 Loading initial logs - webhooks provide real-time updates');
        this.fetchRealLogs();

        // NO POLLING INTERVAL - webhooks handle all real-time updates
        // This eliminates request spam while maintaining real-time functionality through webhooks
    }

    /**
     * Fetch real logs from server (persistent + in-memory)
     */
    async fetchRealLogs() {
        try {
            // First try to get persistent logs (survives server restarts)
            let persistentLogs = [];
            try {
                const persistentResponse = await fetch(`/api/queue/job/${this.jobId}/logs/persistent?limit=500`);
                if (persistentResponse.ok) {
                    const persistentResult = await persistentResponse.json();
                    if (persistentResult.success && persistentResult.data.logs) {
                        persistentLogs = persistentResult.data.logs;
                        console.log(`📋 Loaded ${persistentLogs.length} persistent logs for job ${this.jobId}`);
                    }
                }
            } catch (persistentError) {
                console.warn('⚠️ Persistent logs not available:', persistentError.message);
            }

            // Then get in-memory logs (real-time updates)
            let memoryLogs = [];
            try {
                const memoryResponse = await fetch(`/api/queue/job/${this.jobId}/logs`);
                if (memoryResponse.ok) {
                    const memoryResult = await memoryResponse.json();
                    if (memoryResult.success && memoryResult.data.logs) {
                        memoryLogs = memoryResult.data.logs;
                        console.log(`📋 Loaded ${memoryLogs.length} in-memory logs for job ${this.jobId}`);
                    }
                }
            } catch (memoryError) {
                console.warn('⚠️ In-memory logs not available:', memoryError.message);
            }

            // Combine and filter for essential logs only (clean timeline view)
            const allLogs = this.combineLogs(persistentLogs, memoryLogs);

            // Filter to show only essential workflow messages (CLEAN TIMELINE)
            const essentialLogs = allLogs.filter((log) => {
                const message = log.message.toLowerCase();
                return (
                    message.includes('workflow initiated') ||
                    // CLEAN TIMELINE: Only show "completed" steps, NOT "started"
                    (message.includes('step') && message.includes('completed')) ||
                    message.includes('workflow completed') ||
                    message.includes('video is ready') ||
                    message.includes('error') ||
                    message.includes('failed')
                );
            });

            if (essentialLogs.length > 0) {
                this.updateLogDisplay(essentialLogs);
            } else {
                // Show clean message - focus on timeline
                // Log functionality removed - showing timeline only
            }
        } catch (error) {
            console.error('❌ Failed to fetch job logs:', error);
            // Log functionality removed - errors only in console
        }
    }

    /**
     * Combine persistent and in-memory logs, removing duplicates
     */
    combineLogs(persistentLogs, memoryLogs) {
        const logMap = new Map();

        // Add persistent logs first (they're the authoritative source)
        persistentLogs.forEach((log) => {
            const key = `${log.timestamp}_${log.message}_${log.level}`;
            logMap.set(key, {
                ...log,
                source: 'persistent',
                type: log.level || 'info' // Convert level to type for compatibility
            });
        });

        // Add memory logs that aren't already in persistent logs
        memoryLogs.forEach((log) => {
            const key = `${log.timestamp}_${log.message}_${log.type}`;
            if (!logMap.has(key)) {
                logMap.set(key, {
                    ...log,
                    source: 'memory'
                });
            }
        });

        // Convert back to array and sort by timestamp (newest first)
        return Array.from(logMap.values()).sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
    }

    /**
     * Update log display with real logs from server
     */
    updateLogDisplay(logs) {
        const logViewer = document.getElementById('log-viewer');
        if (!logViewer) return;

        // Clear existing logs first
        logViewer.innerHTML = '';

        if (logs.length === 0) {
            logViewer.innerHTML = `
                <div class="log-entry level-info">
                    <div class="log-icon">
                        <i class="fas fa-info-circle"></i>
                    </div>
                    <div class="log-timestamp">--:--:--</div>
                    <div class="log-content">
                        <strong>No logs available yet</strong><br>
                        Job processing hasn't started or logs are still being initialized.
                    </div>
                </div>
            `;
            return;
        }

        // Clean timeline view - no source indicators needed

        // Add all logs
        logs.forEach((logData) => {
            // Log functionality removed
        });

        // Auto-scroll to bottom if enabled
        if (this.autoScroll) {
            logViewer.scrollTop = logViewer.scrollHeight;
        }
    }

    /**
     * Get icon for log level
     */
    getLogIcon(level) {
        const icons = {
            info: 'fas fa-info-circle',
            success: 'fas fa-check-circle',
            warning: 'fas fa-exclamation-triangle',
            error: 'fas fa-times-circle',
            step: 'fas fa-cog fa-spin',
            debug: 'fas fa-bug'
        };
        return icons[level] || icons.info;
    }

    /**
     * Format log message for better readability
     */
    formatLogMessage(message) {
        if (!message || typeof message !== 'string') return '';

        // Clean up the message
        let formattedMessage = message
            .trim()
            .replace(/\r\n/g, '\n') // Normalize line endings
            .replace(/\r/g, '\n') // Handle remaining \r
            .replace(/\n{3,}/g, '\n\n'); // Limit consecutive newlines

        // Highlight important patterns
        formattedMessage = formattedMessage
            // Highlight file paths and URLs
            .replace(/(\/[^\s]+\.(py|js|json|mp4|jpg|png|webp))/g, '<code>$1</code>')
            // Highlight URLs
            .replace(/(https?:\/\/[^\s]+)/g, '<code>$1</code>')
            // Highlight step indicators
            .replace(/Step (\d+)\/(\d+):/g, '<strong>Step $1/$2:</strong>')
            // Highlight success indicators
            .replace(/(✅|✓|SUCCESS|COMPLETED|DONE)/gi, '<strong style="color: #3fb950;">$1</strong>')
            // Highlight error indicators
            .replace(/(❌|✗|ERROR|FAILED|FAILURE)/gi, '<strong style="color: #f85149;">$1</strong>')
            // Highlight warning indicators
            .replace(/(⚠️|WARNING|WARN)/gi, '<strong style="color: #d29922;">$1</strong>')
            // Highlight processing indicators
            .replace(/(🎬|📝|🎨|🤖|⏳|📱)/g, '<strong>$1</strong>')
            // Highlight file sizes and durations
            .replace(/(\d+(?:\.\d+)?\s*(?:MB|KB|GB|s|ms|minutes?|seconds?))/gi, '<strong>$1</strong>')
            // Highlight percentages
            .replace(/(\d+(?:\.\d+)?%)/g, '<strong>$1</strong>');

        return formattedMessage;
    }

    /**
     * Refresh job data
     */
    async refreshJobData() {
        try {
            console.log('🔄 Refreshing job data...');

            // Store previous status to detect completion
            const previousStatus = this.jobData?.status;

            await this.loadJobData();
            this.lastRefreshTime = Date.now(); // Track refresh time for smart intervals
            console.log('✅ Job data refreshed');

            // Stop real-time updates if job just completed with video URL
            if (
                previousStatus &&
                ['active', 'pending', 'processing', 'rendering'].includes(previousStatus) &&
                this.jobData?.status === 'completed' &&
                this.jobData?.videoUrl
            ) {
                console.log('🏁 Job completed during refresh, stopping real-time updates');
                this.stopRealTimeUpdates();
            }
        } catch (error) {
            console.error('❌ Failed to refresh job data:', error);
            // Log functionality removed - errors only in console
        }
    }

    /**
     * Handle job update from real-time service
     */
    handleJobUpdate(updateData) {
        console.log('📡 Received job update:', updateData);

        // Store previous status to detect completion
        const previousStatus = this.jobData?.status;

        // Merge update data with current job data
        this.jobData = { ...this.jobData, ...updateData };

        // Update UI
        this.updateUI();

        // Stop real-time updates if job just completed with video
        if (
            previousStatus &&
            ['active', 'pending', 'processing', 'rendering'].includes(previousStatus) &&
            this.jobData.status === 'completed' &&
            this.jobData.videoUrl
        ) {
            console.log('🏁 Job completed with video, stopping real-time updates');
            this.stopRealTimeUpdates();
        }

        // Add log entry about the update
        // Log functionality removed - status updates shown in timeline
    }

    /**
     * Show main content and hide loading
     */
    showMainContent() {
        document.getElementById('loading-state').classList.add('d-none');
        document.getElementById('main-content').classList.remove('d-none');
    }

    /**
     * Show error state
     */
    showError(message) {
        document.getElementById('loading-state').classList.add('d-none');
        document.getElementById('main-content').classList.add('d-none');
        document.getElementById('error-state').classList.remove('d-none');
        document.getElementById('error-message').textContent = message;
    }

    /**
     * Clear log viewer
     */
    clearLogs() {
        const logViewer = document.getElementById('log-viewer');
        if (logViewer) {
            const timestamp = new Date().toLocaleTimeString('en-US', {
                hour12: false,
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });

            logViewer.innerHTML = `
                <div class="log-entry level-info">
                    <div class="log-icon">
                        <i class="fas fa-broom"></i>
                    </div>
                    <div class="log-timestamp">${timestamp}</div>
                    <div class="log-content">
                        <strong>Log viewer cleared</strong><br>
                        Previous log entries have been removed from display.
                    </div>
                </div>
            `;
        }
    }

    /**
     * Toggle auto-scroll
     */
    toggleAutoScroll(button) {
        this.autoScroll = !this.autoScroll;
        button.classList.toggle('active', this.autoScroll);

        if (this.autoScroll) {
            const logViewer = document.getElementById('log-viewer');
            if (logViewer) {
                logViewer.scrollTop = logViewer.scrollHeight;
            }
        }
    }

    /**
     * Cancel job
     */
    async cancelJob() {
        if (confirm('Are you sure you want to cancel this job?')) {
            try {
                const response = await APIService.cancelJob(this.jobId);
                if (response.success) {
                    // Job cancellation logged in console only
                    await this.refreshJobData();
                } else {
                    throw new Error(response.message || 'Failed to cancel job');
                }
            } catch (error) {
                console.error('❌ Failed to cancel job:', error);
                // Error logged in console only
            }
        }
    }

    /**
     * Retry job
     */
    async retryJob() {
        if (confirm('Are you sure you want to retry this job?')) {
            try {
                const response = await APIService.retryJob(this.jobId);
                if (response.success) {
                    // Job retry logged in console only
                    await this.refreshJobData();
                } else {
                    throw new Error(response.message || 'Failed to retry job');
                }
            } catch (error) {
                console.error('❌ Failed to retry job:', error);
                // Error logged in console only
            }
        }
    }

    /**
     * Initialize job-specific Server-Sent Events for real-time updates
     */
    initializeJobSSE() {
        if (this.jobSSE) {
            return; // Already initialized
        }

        console.log(`📡 Connecting to job-specific real-time updates for ${this.jobId}`);

        try {
            this.jobSSE = new EventSource(`/api/job/${this.jobId}/stream`);

            this.jobSSE.onopen = () => {
                console.log(`📡 Real-time connection established for job ${this.jobId}`);
            };

            this.jobSSE.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleJobSSEMessage(data);
                } catch (error) {
                    console.error('❌ Failed to parse job SSE message:', error);
                }
            };

            this.jobSSE.onerror = (error) => {
                console.warn(`⚠️ Job SSE connection error for ${this.jobId}:`, error);
                // Reconnect after a delay
                setTimeout(() => {
                    if (this.jobSSE && this.jobSSE.readyState === EventSource.CLOSED) {
                        console.log(`🔄 Reconnecting job SSE for ${this.jobId}`);
                        this.closeJobSSE();
                        this.initializeJobSSE();
                    }
                }, 5000);
            };
        } catch (error) {
            console.error(`❌ Failed to initialize job SSE for ${this.jobId}:`, error);
        }
    }

    /**
     * Handle job-specific SSE messages (real-time webhook updates)
     */
    handleJobSSEMessage(data) {
        if (data.job_id !== this.jobId) {
            return; // Not for this job
        }

        switch (data.type) {
            case 'connected':
                console.log(`✅ Job ${this.jobId} real-time updates connected`);
                break;

            case 'step_update':
                console.log(`📡 Real-time step update: Step ${data.step_number} ${data.status}`);

                // Update job data with real-time info  
                if (this.jobData) {
                    // Handle both "started" and "completed" status
                    if (data.status === 'started') {
                        // Step is starting - track as currently active step
                        this.currentActiveStep = data.step_number;
                        this.jobData.currentStep = `Step ${data.step_number}/7: ${data.step_name} (Processing...)`;
                        this.jobData.progress = Math.max((data.step_number - 1) / 7 * 100, 0);
                        console.log(`📋 Step ${data.step_number} started: ${data.step_name}`);
                    } else if (data.status === 'completed') {
                        // Step completed - no longer active, update progress
                        if (this.currentActiveStep === data.step_number) {
                            this.currentActiveStep = null; // Step no longer active
                        }
                        this.jobData.currentStep = `Step ${data.step_number}/7: ${data.step_name} ✅`;
                        this.jobData.progress = Math.min(data.step_number / 7 * 100, 100);
                        console.log(`✅ Step ${data.step_number} completed: ${data.step_name}`);
                    }
                    
                    // Update UI immediately
                    this.updateProgressSection();
                    this.updateTimeline();
                }
                break;

            case 'heartbeat':
                // Keep connection alive - no action needed
                break;

            default:
                console.log(`📡 Job SSE message:`, data);
        }
    }

    /**
     * Close job-specific SSE connection
     */
    closeJobSSE() {
        if (this.jobSSE) {
            this.jobSSE.close();
            this.jobSSE = null;
            console.log(`📡 Closed job SSE connection for ${this.jobId}`);
        }
    }

    /**
     * Copy video URL to clipboard
     */
    async copyVideoUrl() {
        try {
            await navigator.clipboard.writeText(this.jobData.videoUrl);
            // Success logged in console only
        } catch (error) {
            console.error('Failed to copy URL:', error);
            // Error logged in console only
        }
    }

    /**
     * Manually trigger Creatomate monitoring for this job
     */
    async monitorCreatomate() {
        try {
            console.log(`🎬 Direct Creatomate status check for job ${this.jobId}`);

            if (!this.jobData.creatomateId) {
                this.addLogEntry({
                    level: 'error',
                    message: 'No Creatomate ID found for this job'
                });
                return;
            }

            this.addLogEntry({
                level: 'info',
                message: `Checking render status for Creatomate ID: ${this.jobData.creatomateId}`
            });

            // Direct Creatomate API check
            const response = await fetch(`/api/status/${this.jobData.creatomateId}`);
            const result = await response.json();

            if (result.success) {
                if (result.videoUrl && result.status === 'completed') {
                    // Video is ready!
                    this.addLogEntry({
                        level: 'success',
                        message: `🎉 Video is ready! URL: ${result.videoUrl}`
                    });

                    // Update job data to show video
                    this.jobData.videoUrl = result.videoUrl;
                    this.jobData.status = 'completed';
                    this.jobData.progress = 100;
                    this.jobData.currentStep = 'Video completed and ready for viewing!';

                    // Refresh the UI to show the video
                    this.updateUI();
                } else if (result.status) {
                    // Still rendering
                    const status = result.status.charAt(0).toUpperCase() + result.status.slice(1);
                    this.addLogEntry({
                        level: 'info',
                        message: `Render status: ${status} - Video not ready yet`
                    });

                    if (result.status !== 'completed') {
                        this.addLogEntry({
                            level: 'info',
                            message: 'Video is still rendering - check back in a few minutes'
                        });
                    }
                } else {
                    this.addLogEntry({
                        level: 'warning',
                        message: 'No status information available from Creatomate'
                    });
                }
            } else {
                this.addLogEntry({
                    level: 'error',
                    message: `Failed to check status: ${result.error || result.message}`
                });
            }
        } catch (error) {
            console.error('❌ Failed to check Creatomate status:', error);
            this.addLogEntry({
                level: 'error',
                message: `Failed to check status: ${error.message}`
            });
        }
    }

    /**
     * Show workflow warning information
     */
    showWorkflowWarning() {
        this.addLogEntry({
            level: 'warning',
            message: '⚠️ Workflow Incomplete - The Python script did not complete all 7 steps properly'
        });

        this.addLogEntry({
            level: 'info',
            message: 'This job has a Creatomate ID but the workflow may not have submitted the video correctly.'
        });

        if (this.jobData.creatomateId) {
            this.addLogEntry({
                level: 'info',
                message: `Manual check: python main.py --check-creatomate ${this.jobData.creatomateId}`
            });
        }

        this.addLogEntry({
            level: 'info',
            message: 'Consider retrying this job to ensure all 7 workflow steps complete properly.'
        });
    }

    // Helper methods
    getStatusBadgeClass(status) {
        const classes = {
            pending: 'bg-warning text-dark',
            active: 'bg-info text-dark',
            processing: 'bg-info text-dark',
            rendering: 'bg-primary', // New rendering status
            completed: 'bg-success',
            failed: 'bg-danger',
            cancelled: 'bg-secondary'
        };
        return classes[status] || 'bg-secondary';
    }

    getProgressBarClass(progress) {
        if (progress >= 100) return 'bg-success';
        if (progress >= 75) return 'bg-info';
        if (progress >= 50) return 'bg-warning';
        return 'bg-primary';
    }

    getStepFromProgress(progress) {
        const stepSize = 100 / this.processSteps.length; // Dynamic step size
        const step = Math.floor(progress / stepSize);
        return this.processSteps[Math.min(step, this.processSteps.length - 1)]?.description || 'Processing...';
    }

    getStepStatusText(iconClass, timestamp) {
        const statusTexts = {
            pending: 'Waiting...',
            active: 'In Progress',
            completed: timestamp ? `Done ${timestamp}` : 'Completed',
            failed: 'Failed'
        };
        return statusTexts[iconClass] || 'Unknown';
    }

    getProgressForStep(stepId) {
        const index = this.processSteps.findIndex((step) => step.id === stepId);
        return index !== -1 ? (index / this.processSteps.length) * 100 : 0;
    }

    getStepIcon(stepId, iconClass) {
        // Status-based icons
        if (iconClass === 'completed') return '✓';
        if (iconClass === 'failed') return '✗';
        if (iconClass === 'active') return '⟳';

        // Step-specific icons for pending state
        const stepIcons = {
            database_extraction: '🗄️',
            script_generation: '📝',
            asset_preparation: '🎨',
            heygen_creation: '🤖',
            heygen_processing: '⏳',
            scroll_generation: '📱',
            creatomate_assembly: '🎬'
        };

        return stepIcons[stepId] || '○';
    }

    getStepTimestamp(stepId) {
        // In a real implementation, this would return actual timestamps
        return new Date().toLocaleString();
    }

    getCurrentStepNumber() {
        const progress = this.jobData?.progress || 0;
        const stepNumber = Math.min(
            Math.floor(progress / (100 / this.processSteps.length)) + 1,
            this.processSteps.length
        );
        return `${stepNumber}/${this.processSteps.length}`;
    }

    calculateDuration() {
        if (!this.jobData?.startedAt) return '--';

        const start = new Date(this.jobData.startedAt);

        // For completed, failed, or cancelled jobs, use completedAt timestamp
        // Otherwise use current time for active jobs
        let end;
        if (['completed', 'failed', 'cancelled'].includes(this.jobData.status)) {
            end = this.jobData.completedAt ? new Date(this.jobData.completedAt) : new Date(this.jobData.startedAt);
        } else {
            end = new Date(); // Keep timer running for active jobs
        }

        const duration = end - start;

        const minutes = Math.floor(duration / 60000);
        const seconds = Math.floor((duration % 60000) / 1000);

        if (minutes > 0) {
            return `${minutes}m ${seconds}s`;
        }
        return `${seconds}s`;
    }

    /**
     * Cleanup resources
     */
    cleanup() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
        if (this.logUpdateInterval) {
            clearInterval(this.logUpdateInterval);
        }

        RealtimeService.cleanup();
        console.log('🧹 Job Detail App cleaned up');
    }
}

// Create global instance for button callbacks
window.jobDetailApp = new JobDetailApp();

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.jobDetailApp.initialize();
    });
} else {
    window.jobDetailApp.initialize();
}

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    window.jobDetailApp.cleanup();
});
