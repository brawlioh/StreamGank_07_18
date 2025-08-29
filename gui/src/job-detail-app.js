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

        // Creatomate section event listeners
        this.setupCreatomateEventListeners();

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
     * Set up event listeners for Creatomate section buttons
     */
    setupCreatomateEventListeners() {
        // Use event delegation to handle dynamically created buttons
        document.addEventListener('click', (e) => {
            // Refresh Creatomate status button
            if (e.target && (e.target.id === 'refresh-creatomate-btn' || e.target.closest('#refresh-creatomate-btn'))) {
                e.preventDefault();
                console.log('🔄 Manual refresh button clicked - checking Creatomate status');
                this.checkCreatomateStatusAutomatically();
            }

            // Download video button
            if (e.target && (e.target.id === 'download-video-btn' || e.target.closest('#download-video-btn'))) {
                e.preventDefault();
                this.downloadVideo();
            }

            // Copy video URL button
            if (e.target && (e.target.id === 'copy-video-url-btn' || e.target.closest('#copy-video-url-btn'))) {
                e.preventDefault();
                this.copyVideoUrlFromCreatomate();
            }

            // Fullscreen preview button
            if (e.target && (e.target.id === 'preview-fullscreen-btn' || e.target.closest('#preview-fullscreen-btn'))) {
                e.preventDefault();
                this.previewFullscreen();
            }

            // Retry button for errors
            if (e.target && (e.target.id === 'retry-creatomate-btn' || e.target.closest('#retry-creatomate-btn'))) {
                e.preventDefault();
                this.checkCreatomateStatusAutomatically();
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

            // NEW: Load persistent logs to determine current active step on page reload
            await this.loadCurrentActiveStepFromLogs();

            this.updateUI();

            // Add page unload cleanup for SSE connections
            window.addEventListener('beforeunload', () => {
                this.closeJobSSE();
            });

            console.log('✅ Job data loaded successfully');

            // 🎬 AUTO-START MONITORING: Check if job needs Creatomate monitoring on page load
            setTimeout(async () => {
                if (
                    this.jobData.creatomateId &&
                    this.jobData.status !== 'rendering' &&
                    this.jobData.status !== 'completed' &&
                    !this.jobData.videoUrl
                ) {
                    console.log('🔍 AUTO-START: Job has creatomateId but no monitoring - starting automatically...');
                    await this.startCreatomateMonitoring();
                }
            }, 1000); // Small delay to ensure UI is loaded
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
        this.updateCreatomateSection(); // New: Handle Creatomate video result section
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

        // Removed Creatomate monitoring buttons - functionality moved to video section

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

        // Removed duplicate "Refresh Status" button - functionality moved to video section header

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
     * Update video result section
     */
    updateVideoResult() {
        const videoCard = document.getElementById('video-result-card');
        const videoContent = document.getElementById('video-content');

        // Check if elements exist (they were removed from HTML)
        if (!videoCard || !videoContent) {
            console.log('📝 Video result elements not found - functionality moved to video section');
            return;
        }

        if (this.jobData.status === 'completed' && this.jobData.videoUrl) {
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
        } else {
            videoCard.classList.add('d-none');
        }
    }

    /**
     * Update Creatomate video result section
     * Shows the new section below Process Timeline for Creatomate video status and result
     */
    updateCreatomateSection() {
        const creatomateSection = document.getElementById('creatomate-section');
        if (!creatomateSection) return;

        // Show Creatomate section when Step 7 starts (85%+) or if we have creatomateId
        // Don't wait for Step 7 to complete - show as soon as Creatomate processing begins
        const step7Started = this.jobData.progress >= 85 || this.jobData.stepDetails?.step_7;
        const workflowStepsComplete = step7Started || this.jobData.creatomateId;

        console.log(
            `🔍 Creatomate section check - CreatomateId: ${this.jobData.creatomateId}, Progress: ${this.jobData.progress}, StepDetails: ${JSON.stringify(this.jobData.stepDetails)}, WorkflowComplete: ${workflowStepsComplete}`
        );

        if (workflowStepsComplete) {
            console.log(
                `🎬 Step 7 started or completed, showing Creatomate section. ID: ${this.jobData.creatomateId || 'Pending...'}`
            );

            // Show the section
            creatomateSection.classList.remove('d-none');

            // Update Creatomate ID display
            const creatomateIdElement = document.getElementById('creatomate-id');
            if (creatomateIdElement) {
                creatomateIdElement.textContent = this.jobData.creatomateId || 'Processing Step 7...';
            }

            // Only check status if we have creatomateId and video processing
            if (this.jobData.creatomateId) {
                // Check if we already have video URL or need to fetch it
                if (this.jobData.videoUrl) {
                    console.log('🎬 Video URL already available, showing video result directly');
                    this.showCreatomateVideoResult();
                } else {
                    console.log('🔍 No video URL yet, checking Creatomate status automatically...');
                    // Always check Creatomate status to get the latest video info
                    this.checkCreatomateStatusAutomatically();
                }
            } else {
                // Step 7 is running but no creatomateId yet - show preparation status
                console.log('⏳ Step 7 in progress, waiting for Creatomate ID...');
                this.showCreatomatePreparationStatus();
            }
        } else {
            // Hide the section if conditions not met
            creatomateSection.classList.add('d-none');
            console.log('❌ Workflow not complete yet - hiding Creatomate section');
        }
    }

    /**
     * Automatically check Creatomate status when all steps are complete
     */
    async checkCreatomateStatusAutomatically() {
        console.log('🔄 Automatically checking Creatomate status for ID:', this.jobData.creatomateId);

        // Show rendering status initially
        this.showCreatomateRenderingStatus();

        try {
            const response = await fetch(`/api/status/${this.jobData.creatomateId}`);
            const result = await response.json();

            console.log('📡 Creatomate API response:', result);

            if (result.success) {
                // Update status badge
                this.updateCreatomateStatusBadge(result.status);

                if (result.status === 'succeeded' && result.videoUrl) {
                    console.log('✅ Video is ready!', result.videoUrl);

                    // Update job data with video info
                    this.jobData.videoUrl = result.videoUrl;
                    this.jobData.creatomateStatus = result.status;

                    // IMPORTANT: Update job status and progress when video is ready
                    this.jobData.status = 'completed';
                    this.jobData.progress = 100;
                    this.jobData.currentStep = '✅ Video creation completed';

                    console.log('💾 Updated job status to completed, progress to 100%');
                    console.log('💾 Updated jobData.videoUrl to:', this.jobData.videoUrl);

                    // Update UI elements immediately
                    this.updateJobHeader();
                    this.updateProgressSection();

                    console.log('🎬 About to call showCreatomateVideoResult()');
                    // Show video result
                    this.showCreatomateVideoResult();
                } else if (result.status === 'processing' || result.status === 'planned') {
                    console.log('⏳ Video still rendering, status:', result.status);
                    this.showCreatomateRenderingStatus(result.status);

                    // Auto-refresh after 30 seconds
                    setTimeout(() => {
                        if (this.jobData.creatomateId && !this.jobData.videoUrl) {
                            this.checkCreatomateStatusAutomatically();
                        }
                    }, 30000);
                } else if (result.status === 'failed' || result.status === 'error') {
                    console.log('❌ Video rendering failed');
                    this.showCreatomateError('Video rendering failed');
                } else {
                    console.log('❓ Unknown status:', result.status);
                    this.showCreatomateError(`Unknown status: ${result.status}`);
                }
            } else {
                console.error('❌ Creatomate API error:', result.error);
                this.showCreatomateError(result.error || 'Failed to check video status');
            }
        } catch (error) {
            console.error('❌ Error checking Creatomate status:', error);
            this.showCreatomateError(`Network error: ${error.message}`);
        }
    }

    /**
     * Show Creatomate video result when ready
     */
    showCreatomateVideoResult() {
        console.log('🎬 showCreatomateVideoResult called with videoUrl:', this.jobData.videoUrl);

        // Hide other status views
        document.getElementById('rendering-status')?.classList.add('d-none');
        document.getElementById('error-status')?.classList.add('d-none');
        document.getElementById('creatomate-progress')?.classList.add('d-none');

        // Show video result
        const videoResult = document.getElementById('video-result');
        if (videoResult && this.jobData.videoUrl) {
            console.log('🎬 Video result div found, setting up player with URL:', this.jobData.videoUrl);

            // CRITICAL: Show the video result div first
            videoResult.classList.remove('d-none');
            console.log('✅ Video result div is now visible');

            // Update video source and ensure it loads properly
            const resultVideo = document.getElementById('result-video');

            console.log('🔍 Looking for video element with ID "result-video"');
            console.log('🎬 Video element found:', !!resultVideo);
            console.log('🎬 Current video URL in jobData:', this.jobData.videoUrl);

            if (resultVideo) {
                console.log('🎬 Video element found, setting up player with URL:', this.jobData.videoUrl);

                // Set up video player with multiple fallback options
                this.setupVideoPlayer(resultVideo, this.jobData.videoUrl);
            } else {
                console.error('❌ Video element not found with ID "result-video"!');

                // Debug: List all video elements on page
                const allVideos = document.querySelectorAll('video');
                console.log(
                    '🔍 Found',
                    allVideos.length,
                    'video elements on page:',
                    Array.from(allVideos).map((v) => v.id || 'no-id')
                );
            }

            // Update status badge to success
            this.updateCreatomateStatusBadge('succeeded');

            console.log('🎉 Video result displayed successfully!');
        } else {
            console.error('❌ Video result setup failed:', {
                videoResult: !!videoResult,
                videoUrl: this.jobData.videoUrl
            });
        }
    }

    /**
     * Show preparation status while Step 7 is running but no creatomateId yet
     */
    showCreatomatePreparationStatus() {
        // Hide other views
        document.getElementById('video-result')?.classList.add('d-none');
        document.getElementById('error-status')?.classList.add('d-none');

        // Show progress indicator
        const creatomateProgress = document.getElementById('creatomate-progress');
        const renderingStatus = document.getElementById('rendering-status');

        if (creatomateProgress) {
            const statusText = document.getElementById('creatomate-status-text');
            const progressBar = document.getElementById('creatomate-progress-bar');

            if (statusText) {
                statusText.textContent = 'Preparing video for rendering...';
            }

            if (progressBar) {
                progressBar.style.width = '80%';
                progressBar.classList.add('progress-bar-animated');
            }

            creatomateProgress.classList.remove('d-none');
        }

        if (renderingStatus) {
            renderingStatus.classList.remove('d-none');
        }

        // Update status badge to show preparation
        this.updateCreatomateStatusBadge('preparing');
    }

    /**
     * Show rendering status while video is being processed
     */
    showCreatomateRenderingStatus(status = 'processing') {
        // Hide other views
        document.getElementById('video-result')?.classList.add('d-none');
        document.getElementById('error-status')?.classList.add('d-none');

        // Show progress indicator
        const creatomateProgress = document.getElementById('creatomate-progress');
        const renderingStatus = document.getElementById('rendering-status');

        if (creatomateProgress) {
            const statusText = document.getElementById('creatomate-status-text');
            const progressBar = document.getElementById('creatomate-progress-bar');

            if (statusText) {
                const statusMessages = {
                    planned: 'Video queued for processing...',
                    processing: 'Video is being rendered...',
                    rendering: 'Video is being rendered...',
                    waiting: 'Video is being rendered...',
                    transcribing: 'Video is being rendered...'
                };
                statusText.textContent = statusMessages[status] || 'Checking video status...';
            }

            if (progressBar) {
                // Show specific progress based on status
                const progressMap = {
                    planned: '85%',
                    waiting: '87%',
                    transcribing: '88%',
                    rendering: '90%',
                    processing: '75%'
                };
                progressBar.style.width = progressMap[status] || '25%';
                progressBar.classList.add('progress-bar-animated');
            }

            creatomateProgress.classList.remove('d-none');
        }

        if (renderingStatus) {
            renderingStatus.classList.remove('d-none');
        }
    }

    /**
     * Show error status for Creatomate failures
     */
    showCreatomateError(errorMessage) {
        // Hide other views
        document.getElementById('video-result')?.classList.add('d-none');
        document.getElementById('rendering-status')?.classList.add('d-none');
        document.getElementById('creatomate-progress')?.classList.add('d-none');

        // Show error status
        const errorStatus = document.getElementById('error-status');
        const errorMessageElement = document.getElementById('error-message');

        if (errorStatus) {
            if (errorMessageElement) {
                errorMessageElement.textContent = errorMessage || 'An error occurred while processing the video';
            }
            errorStatus.classList.remove('d-none');
        }

        // Update status badge to failed
        this.updateCreatomateStatusBadge('failed');
    }

    /**
     * Update Creatomate status badge
     */
    updateCreatomateStatusBadge(status) {
        const badge = document.getElementById('creatomate-status-badge');
        if (badge) {
            const statusMap = {
                succeeded: { text: 'Ready', class: 'bg-success' },
                processing: { text: 'Rendering', class: 'bg-warning' },
                planned: { text: 'Queued', class: 'bg-info' },
                waiting: { text: 'Rendering', class: 'bg-warning' },
                transcribing: { text: 'Rendering', class: 'bg-warning' },
                rendering: { text: 'Rendering', class: 'bg-warning' },
                preparing: { text: 'Preparing', class: 'bg-primary' },
                failed: { text: 'Failed', class: 'bg-danger' },
                error: { text: 'Error', class: 'bg-danger' }
            };

            const statusInfo = statusMap[status] || { text: status, class: 'bg-secondary' };
            badge.textContent = statusInfo.text;
            badge.className = `badge ${statusInfo.class} ms-2 fs-6`;
        }
    }

    /**
     * Download video from Creatomate result section
     */
    downloadVideo() {
        if (this.jobData.videoUrl) {
            console.log('📥 Downloading video from:', this.jobData.videoUrl);

            // Create a temporary download link
            const link = document.createElement('a');
            link.href = this.jobData.videoUrl;
            link.download = `streamgank_video_${this.jobData.id || 'unknown'}.mp4`;
            link.target = '_blank';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);

            console.log('✅ Download initiated');
        } else {
            console.error('❌ No video URL available for download');
        }
    }

    /**
     * Copy video URL to clipboard from Creatomate section
     */
    async copyVideoUrlFromCreatomate() {
        if (this.jobData.videoUrl) {
            try {
                await navigator.clipboard.writeText(this.jobData.videoUrl);
                console.log('📋 Video URL copied to clipboard');

                // Provide user feedback
                const button = document.getElementById('copy-video-url-btn');
                if (button) {
                    const originalText = button.innerHTML;
                    button.innerHTML = '<i class="fas fa-check me-1"></i>Copied!';
                    button.classList.add('btn-success');
                    button.classList.remove('btn-outline-info');

                    setTimeout(() => {
                        button.innerHTML = originalText;
                        button.classList.remove('btn-success');
                        button.classList.add('btn-outline-info');
                    }, 2000);
                }
            } catch (error) {
                console.error('❌ Failed to copy URL:', error);
                // Fallback for older browsers
                this.fallbackCopyToClipboard(this.jobData.videoUrl);
            }
        } else {
            console.error('❌ No video URL available to copy');
        }
    }

    /**
     * Open video in fullscreen preview
     */
    previewFullscreen() {
        if (this.jobData.videoUrl) {
            console.log('🖥️ Opening fullscreen preview');

            const video = document.getElementById('result-video');
            if (video) {
                if (video.requestFullscreen) {
                    video.requestFullscreen();
                } else if (video.webkitRequestFullscreen) {
                    video.webkitRequestFullscreen();
                } else if (video.msRequestFullscreen) {
                    video.msRequestFullscreen();
                }

                // Start playing the video in fullscreen
                video.play().catch((e) => console.warn('Video autoplay prevented:', e));
            }
        } else {
            console.error('❌ No video available for preview');
        }
    }

    /**
     * Fallback method to copy text to clipboard for older browsers
     */
    fallbackCopyToClipboard(text) {
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.left = '-999999px';
        textArea.style.top = '-999999px';
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();

        try {
            const successful = document.execCommand('copy');
            if (successful) {
                console.log('📋 URL copied using fallback method');
            }
        } catch (err) {
            console.error('❌ Fallback copy failed:', err);
        }

        document.body.removeChild(textArea);
    }

    /**
     * Setup simple video player using <source> element
     */
    setupVideoPlayer(videoElement, videoUrl) {
        console.log('🎬 Setting up video player with <source> element for:', videoUrl);
        console.log('🎬 Video element found:', !!videoElement);
        console.log('🎬 Video URL provided:', videoUrl);

        if (!videoElement) {
            console.error('❌ Video element is null or undefined!');
            return;
        }

        if (!videoUrl) {
            console.error('❌ Video URL is null or undefined!');
            return;
        }

        // Show loading indicator
        const videoLoading = document.getElementById('video-loading');
        if (videoLoading) {
            videoLoading.style.display = 'block';
            console.log('🔄 Video loading indicator shown');
        } else {
            console.warn('⚠️ Video loading indicator not found');
        }

        // Show video element
        videoElement.classList.remove('d-none');

        // Find and set the source element
        const videoSource = document.getElementById('video-source');
        if (videoSource) {
            videoSource.src = videoUrl;
            videoSource.type = 'video/mp4';
            console.log('🎬 Video source element found and src set to:', videoSource.src);
            console.log('🎬 Video source element type:', videoSource.type);
        } else {
            console.warn('⚠️ Video source element not found, setting video src directly as fallback');
            videoElement.src = videoUrl;
        }

        // Also set video element src as backup (both methods)
        videoElement.src = videoUrl;
        console.log('🎬 Video element src also set to:', videoElement.src);

        // Add event listeners for debugging and UI updates
        videoElement.addEventListener('loadstart', () => {
            console.log('🔄 Video loading started');
        });

        videoElement.addEventListener('loadedmetadata', () => {
            console.log('✅ Video metadata loaded');
            console.log('📐 Video dimensions:', videoElement.videoWidth, 'x', videoElement.videoHeight);
            console.log('⏱️ Video duration:', videoElement.duration, 'seconds');

            // Hide loading indicator
            if (videoLoading) {
                videoLoading.style.display = 'none';
            }
        });

        videoElement.addEventListener('canplay', () => {
            console.log('✅ Video can start playing - success!');
            console.log('📊 Video ready state:', videoElement.readyState);

            // Hide loading indicator
            if (videoLoading) {
                videoLoading.style.display = 'none';
            }
        });

        videoElement.addEventListener('error', (e) => {
            console.error('❌ Video loading error:', e);
            console.error('❌ Video error code:', videoElement.error?.code);
            console.error('❌ Video error message:', videoElement.error?.message);

            // Hide loading indicator and show error
            if (videoLoading) {
                videoLoading.innerHTML = `
                    <div class="text-center">
                        <i class="fas fa-exclamation-triangle text-warning mb-2" style="font-size: 2rem;"></i>
                        <div class="text-light small">Error loading video</div>
                        <div class="text-muted small">Code: ${videoElement.error?.code}</div>
                    </div>
                `;
            }
        });

        videoElement.addEventListener('progress', () => {
            console.log(
                '📊 Video loading progress:',
                videoElement.buffered.length > 0
                    ? Math.round((videoElement.buffered.end(0) / videoElement.duration) * 100) + '%'
                    : '0%'
            );
        });

        // Force reload the video with source element
        videoElement.load();

        console.log('🎬 Video player configured with loading indicator and enhanced debugging');
        console.log('🔍 Video element details:', {
            src: videoElement.src,
            currentSrc: videoElement.currentSrc,
            readyState: videoElement.readyState,
            networkState: videoElement.networkState
        });
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

        // Start fetching real job logs from the server (also reduced frequency)
        this.startLogUpdates();
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
     * Load current active step from persistent logs (for page reload)
     */
    async loadCurrentActiveStepFromLogs() {
        try {
            console.log(`📋 Loading persistent logs to determine current active step for ${this.jobId}`);

            const response = await fetch(`/api/queue/job/${this.jobId}/logs/persistent?limit=50`);
            if (!response.ok) {
                console.warn('⚠️ Could not load persistent logs, using job data only');
                return;
            }

            const result = await response.json();
            if (!result.success || !result.data.logs) {
                console.warn('⚠️ No persistent logs available');
                return;
            }

            const logs = result.data.logs;
            console.log(`📋 Loaded ${logs.length} persistent log entries`);

            // Find the most recent "started" event that doesn't have a corresponding "completed" event
            let currentActiveStep = null;
            const stepStatus = {}; // Track started/completed status for each step

            // Process logs in chronological order to track step states
            logs.forEach((log) => {
                if (log.event_type === 'webhook_received' && log.details) {
                    const step_number = log.details.step_number;
                    const status = log.details.status;

                    if (step_number >= 1 && step_number <= 7) {
                        if (status === 'started') {
                            stepStatus[step_number] = 'started';
                            currentActiveStep = step_number; // This step is now active
                        } else if (status === 'completed') {
                            stepStatus[step_number] = 'completed';
                            if (currentActiveStep === step_number) {
                                currentActiveStep = null; // Step is no longer active
                            }
                        }
                    }
                }
            });

            // Set the current active step based on log analysis
            this.currentActiveStep = currentActiveStep;

            if (currentActiveStep) {
                console.log(`📍 Determined from logs: Step ${currentActiveStep} is currently active`);
            } else {
                console.log(`📍 No active step found in logs - workflow may be complete or not started`);
            }
        } catch (error) {
            console.error('❌ Error loading persistent logs:', error);
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
                console.log(`   🔑 Step Key: ${data.step_key || 'N/A'}`);
                console.log(`   📊 Sequence: ${data.sequence || 'N/A'}`);
                console.log(`   ✅ Validated: ${data.validated || false}`);

                // ✅ FRONTEND VALIDATION: Check if update should be processed
                if (!data.validated) {
                    console.warn(`⚠️ REJECTED: Non-validated step update for ${data.step_number} ${data.status}`);
                    break;
                }

                // Check sequence order to prevent processing old updates
                const lastSequence = this.lastStepSequence || 0;
                const currentSequence = data.sequence || Date.now();

                if (currentSequence < lastSequence) {
                    console.warn(`⚠️ REJECTED: Out-of-order frontend update`);
                    console.warn(`   Current: ${currentSequence}, Last: ${lastSequence}`);
                    break;
                }

                // Update last sequence
                this.lastStepSequence = currentSequence;

                console.log(`✅ FRONTEND VALIDATED: Processing step ${data.step_number} ${data.status}`);

                // Update job data with real-time info
                if (this.jobData) {
                    // Handle both "started" and "completed" status
                    if (data.status === 'started') {
                        // Step is starting - track as currently active step
                        this.currentActiveStep = data.step_number;
                        this.jobData.currentStep = `Step ${data.step_number}/7: ${data.step_name} (Processing...)`;
                        // ✅ FIXED: Use backend progress calculation, don't override
                        this.jobData.progress = data.progress || this.jobData.progress;
                        console.log(
                            `📋 Step ${data.step_number} started: ${data.step_name} (${this.jobData.progress}%)`
                        );
                    } else if (data.status === 'completed' || data.status === 'creatomate_ready') {
                        // Step completed - no longer active, update progress
                        if (this.currentActiveStep === data.step_number) {
                            this.currentActiveStep = null; // Step no longer active
                        }
                        this.jobData.currentStep = `Step ${data.step_number}/7: ${data.step_name} ✅`;
                        // ✅ FIXED: Use backend progress calculation, don't override
                        this.jobData.progress = data.progress || this.jobData.progress;
                        console.log(
                            `✅ Step ${data.step_number} completed: ${data.step_name} (${this.jobData.progress}%)`
                        );

                        // 🎯 FIX: When step 7 completes or creatomate_ready, extract Creatomate ID immediately
                        if (data.step_number === 7 || data.status === 'creatomate_ready') {
                            console.log(`🎬 Step 7 ${data.status} - checking for immediate Creatomate ID...`);
                            
                            // 🚀 IMMEDIATE UPDATE: Check if creatomate_id is in the webhook details
                            const creatomateId = data.details?.creatomate_id;
                            if (creatomateId) {
                                console.log(`🎬 IMMEDIATE: Got Creatomate ID from Step 7 webhook: ${creatomateId}`);
                                this.jobData.creatomateId = creatomateId;
                                
                                // Immediately update Creatomate section with the new ID
                                this.updateCreatomateSection();
                                
                                // Start monitoring if not already started
                                console.log('🚀 Starting Creatomate monitoring with immediate ID...');
                                setTimeout(() => {
                                    this.startCreatomateMonitoring();
                                }, 100);
                            }
                            setTimeout(async () => {
                                try {
                                    await this.refreshJobData();
                                    console.log('🎬 Job data refreshed after step 7 - triggering video display');

                                    // 🎬 BACKUP CHECK: If job has creatomateId but status is not 'rendering', start monitoring
                                    if (
                                        this.jobData.creatomateId &&
                                        this.jobData.status !== 'rendering' &&
                                        !this.jobData.videoUrl
                                    ) {
                                        console.log(
                                            '🔍 BACKUP: Job has creatomateId but monitoring may not have started - triggering monitoring...'
                                        );
                                        await this.startCreatomateMonitoring();
                                    }

                                    this.updateUI(); // This will trigger updateCreatomateSection with fresh data
                                } catch (error) {
                                    console.error('❌ Failed to refresh job data after step 7:', error);
                                }
                            }, 2000); // Increased delay to 2 seconds to ensure webhook processing completes
                        }
                    }

                    // Update UI immediately
                    this.updateProgressSection();
                    this.updateTimeline();
                }
                break;

            case 'render_completed':
                console.log('🎬 INSTANT: Creatomate render completed via webhook!', data);

                // Update job data immediately with video URL
                if (this.jobData) {
                    this.jobData.status = 'completed';
                    this.jobData.progress = 100;
                    this.jobData.currentStep = '🎉 Video rendering completed successfully!';
                    this.jobData.videoUrl = data.videoUrl;
                    this.jobData.completedAt = data.timestamp;

                    console.log('✅ Job data updated with video URL:', data.videoUrl);

                    // Update UI immediately to show video
                    this.updateUI();
                    this.showCreatomateVideoResult();

                    // Stop all polling since video is ready
                    this.stopRealTimeUpdates();

                    console.log('🎬 Video displayed instantly via webhook!');
                }
                break;

            case 'render_failed':
                console.log('❌ INSTANT: Creatomate render failed via webhook!', data);

                // Update job data immediately with error
                if (this.jobData) {
                    this.jobData.status = 'failed';
                    this.jobData.currentStep = `❌ Video rendering failed: ${data.error}`;
                    this.jobData.error = data.error;

                    console.log('❌ Job marked as failed:', data.error);

                    // Update UI to show failure
                    this.updateUI();

                    // Stop polling
                    this.stopRealTimeUpdates();
                }
                break;

            case 'render_planned':
                console.log('📋 REAL-TIME: Video queued for processing via webhook!', data);

                // Update job data with queued status
                if (this.jobData) {
                    this.jobData.status = 'rendering';
                    this.jobData.progress = 85;
                    this.jobData.currentStep = '📋 Video queued for processing...';

                    console.log('📋 Video queued for processing');

                    // Update UI to show queued status
                    this.updateUI();
                    this.updateProgressSection();

                    // Update Creatomate section specifically
                    this.updateCreatomateStatusBadge('planned');
                    this.showCreatomateRenderingStatus('planned');
                }
                break;

            case 'render_waiting':
                console.log('⏳ REAL-TIME: Video waiting for processing via webhook!', data);

                // Update job data with waiting status
                if (this.jobData) {
                    this.jobData.status = 'rendering';
                    this.jobData.progress = 87;
                    this.jobData.currentStep = '⏳ Video is being rendered...';

                    console.log('⏳ Video is being rendered (waiting)');

                    // Update UI to show waiting status
                    this.updateUI();
                    this.updateProgressSection();

                    // Update Creatomate section specifically
                    this.updateCreatomateStatusBadge('processing');
                    this.showCreatomateRenderingStatus('processing');
                }
                break;

            case 'render_transcribing':
                console.log('💬 REAL-TIME: Video transcribing via webhook!', data);

                // Update job data with transcribing status
                if (this.jobData) {
                    this.jobData.status = 'rendering';
                    this.jobData.progress = 88;
                    this.jobData.currentStep = '💬 Video is being rendered...';

                    console.log('💬 Video is being rendered (transcribing)');

                    // Update UI to show transcribing status
                    this.updateUI();
                    this.updateProgressSection();

                    // Update Creatomate section specifically
                    this.updateCreatomateStatusBadge('processing');
                    this.showCreatomateRenderingStatus('processing');
                }
                break;

            case 'render_rendering':
                console.log('🎬 REAL-TIME: Video actively rendering via webhook!', data);

                // Update job data with rendering status
                if (this.jobData) {
                    this.jobData.status = 'rendering';
                    this.jobData.progress = 90;
                    this.jobData.currentStep = '🎬 Video is being rendered...';

                    console.log('🎬 Video is being rendered (actively)');

                    // Update UI to show active rendering status
                    this.updateUI();
                    this.updateProgressSection();

                    // Update Creatomate section specifically
                    this.updateCreatomateStatusBadge('processing');
                    this.showCreatomateRenderingStatus('rendering');
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
     * Start Creatomate monitoring for the current job (backup mechanism)
     */
    async startCreatomateMonitoring() {
        if (!this.jobData.creatomateId) {
            console.error('❌ Cannot start Creatomate monitoring: No creatomateId found');
            return;
        }

        try {
            console.log(`🎬 Starting Creatomate monitoring for job ${this.jobId} (ID: ${this.jobData.creatomateId})`);

            const response = await fetch(`/api/queue/job/${this.jobId}/monitor-creatomate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                const result = await response.json();
                console.log('✅ Creatomate monitoring started successfully:', result);

                // Update job status to rendering
                if (this.jobData.status !== 'rendering') {
                    this.jobData.status = 'rendering';
                    this.jobData.currentStep = '🎬 Video rendering in progress with Creatomate...';
                    this.updateUI();
                }
            } else {
                const error = await response.json();
                console.error('❌ Failed to start Creatomate monitoring:', error);
            }
        } catch (error) {
            console.error('❌ Error starting Creatomate monitoring:', error);
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
