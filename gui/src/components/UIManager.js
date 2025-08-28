/**
 * UI Manager - Professional user interface state management
 * Handles status messages, progress tracking, button states, and UI updates
 */
import DOMManager from '../core/DOMManager.js';

export class UIManager {
    constructor() {
        this.statusMessageId = 0;
        this.maxStatusMessages = 50;
        this.autoHideDelay = 5000; // 5 seconds
        this.completedVideos = [];
        this.videoReadyMessageShown = false;
    }

    /**
     * Initialize UI Manager
     */
    init() {
        this.setupEventListeners();
        this.initializeProgressTracking();
    }

    /**
     * Setup UI event listeners
     */
    setupEventListeners() {
        // Clear logs button
        const clearLogsBtn = DOMManager.get('clearLogsBtn');
        if (clearLogsBtn) {
            clearLogsBtn.addEventListener('click', () => this.clearStatusMessages());
        }

        // Generate button state management
        const generateButton = DOMManager.get('generateButton');
        if (generateButton) {
            generateButton.addEventListener('click', (e) => {
                if (generateButton.disabled) {
                    e.preventDefault();
                    this.addStatusMessage('warning', '⚠️', 'Please wait for current generation to complete');
                }
            });
        }
    }

    /**
     * Initialize progress tracking system
     */
    initializeProgressTracking() {
        DOMManager.hide('progressContainer');
    }

    // === Status Message Management ===

    /**
     * Add professional status message to UI
     * @param {string} type - Message type (success, error, info, warning)
     * @param {string} emoji - Emoji icon
     * @param {string} message - Message text
     * @param {boolean} autoHide - Whether to auto-hide message
     */
    addStatusMessage(type, emoji, message, autoHide = true) {
        const statusMessages = DOMManager.get('statusMessages');
        if (!statusMessages) {
            console.warn('⚠️ Status messages container not found');
            return;
        }

        this.statusMessageId++;
        const messageId = `status-msg-${this.statusMessageId}`;
        const timestamp = new Date().toLocaleTimeString();

        // Create message element
        const messageElement = document.createElement('div');
        messageElement.id = messageId;
        messageElement.className = `alert alert-${this.getBootstrapClass(type)} alert-dismissible fade show`;

        messageElement.innerHTML = `
            <div class="d-flex align-items-center">
                <span class="me-2" style="font-size: 1.2em;">${emoji}</span>
                <div class="flex-grow-1">
                    <strong>${message}</strong>
                    <small class="text-muted d-block">
                        <i class="fas fa-clock me-1"></i>${timestamp}
                    </small>
                </div>
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;

        // Add to container (newest at top)
        statusMessages.insertBefore(messageElement, statusMessages.firstChild);

        // Auto-hide if enabled
        if (autoHide && type !== 'error') {
            setTimeout(() => {
                this.removeStatusMessage(messageId);
            }, this.autoHideDelay);
        }

        // Limit number of messages
        this.limitStatusMessages();

        // Scroll to show new message
        messageElement.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

        console.log(`📝 Status: ${type} - ${message}`);
    }

    /**
     * Get Bootstrap CSS class for message type
     * @param {string} type - Message type
     * @returns {string} Bootstrap class
     */
    getBootstrapClass(type) {
        const classMap = {
            success: 'success',
            error: 'danger',
            warning: 'warning',
            info: 'info',
            primary: 'primary'
        };
        return classMap[type] || 'info';
    }

    /**
     * Remove status message by ID
     * @param {string} messageId - Message ID to remove
     */
    removeStatusMessage(messageId) {
        const element = document.getElementById(messageId);
        if (element) {
            element.classList.add('fade');
            setTimeout(() => {
                if (element.parentNode) {
                    element.parentNode.removeChild(element);
                }
            }, 150);
        }
    }

    /**
     * Clear all status messages
     */
    clearStatusMessages() {
        const statusMessages = DOMManager.get('statusMessages');
        if (statusMessages) {
            statusMessages.innerHTML = '';
            this.statusMessageId = 0;
            console.log('🧹 Status messages cleared');
        }
    }

    /**
     * Limit number of status messages
     */
    limitStatusMessages() {
        const statusMessages = DOMManager.get('statusMessages');
        if (!statusMessages) return;

        const messages = statusMessages.children;
        while (messages.length > this.maxStatusMessages) {
            statusMessages.removeChild(messages[messages.length - 1]);
        }
    }

    // === Progress Bar Management ===

    /**
     * Show progress bar
     */
    showProgress() {
        DOMManager.show('progressContainer');
        this.updateProgress(0, 'Initializing...');
    }

    /**
     * Hide progress bar
     */
    hideProgress() {
        DOMManager.hide('progressContainer');
    }

    /**
     * Update progress bar with percentage and message
     * @param {number} percentage - Progress percentage (0-100)
     * @param {string} message - Progress message
     */
    updateProgress(percentage, message = '') {
        const progressBar = DOMManager.get('progressBar');
        if (progressBar) {
            progressBar.style.width = `${percentage}%`;
            progressBar.setAttribute('aria-valuenow', percentage);

            // Update progress text
            if (message) {
                progressBar.textContent = `${Math.round(percentage)}% - ${message}`;
            } else {
                progressBar.textContent = `${Math.round(percentage)}%`;
            }

            // Update progress bar color based on percentage
            progressBar.className =
                'progress-bar progress-bar-striped progress-bar-animated ' + this.getProgressBarClass(percentage);
        }
    }

    /**
     * Get progress bar CSS class based on percentage
     * @param {number} percentage - Progress percentage
     * @returns {string} CSS class
     */
    getProgressBarClass(percentage) {
        if (percentage >= 100) return 'bg-success';
        if (percentage >= 75) return 'bg-info';
        if (percentage >= 50) return 'bg-warning';
        return 'bg-primary';
    }

    // === Button State Management ===

    /**
     * Enable generate button
     */
    enableGenerateButton() {
        const button = DOMManager.get('generateButton');
        if (button) {
            button.disabled = false;
            button.innerHTML = '<i class="fas fa-play me-2"></i>Generate Video';
            button.classList.remove('btn-secondary');
            button.classList.add('btn-primary');
        }
    }

    /**
     * Disable generate button with custom message
     * @param {string} message - Button message during disabled state
     */
    disableGenerateButton(message = 'Processing...') {
        const button = DOMManager.get('generateButton');
        if (button) {
            button.disabled = true;
            button.innerHTML = `<i class="fas fa-spinner fa-spin me-2"></i>${message}`;
            button.classList.remove('btn-primary');
            button.classList.add('btn-secondary');
        }
    }

    // === Queue Status Display ===

    /**
     * Update queue statistics in UI
     * @param {Object} stats - Queue statistics from server
     */
    updateQueueStats(stats) {
        // Update basic queue stats
        DOMManager.setText('queue-pending', stats.pending || 0);
        DOMManager.setText('queue-processing', stats.processing || 0);
        DOMManager.setText('queue-completed', stats.completed || 0);
        DOMManager.setText('queue-failed', stats.failed || 0);

        // Update worker information
        this.updateWorkerStats(stats);

        // Show debug info if available
        if (stats._debug || stats._poolUsed || stats._fallback) {
            const debugInfo = [];
            if (stats._debug) debugInfo.push(`API: ${stats._debug.duration}`);
            if (stats._poolUsed) debugInfo.push('Pool: ✓');
            if (stats._fallback) debugInfo.push('Fallback: ✓');
            if (stats._error) debugInfo.push(`Errors: ${stats._errorCount || 0}`);

            console.log('📊 Queue update:', { ...stats, debug: debugInfo.join(', ') });
        }
    }

    /**
     * Update worker statistics display
     * @param {Object} stats - Queue statistics
     */
    updateWorkerStats(stats) {
        const elements = {
            'queue-active-workers': stats.activeWorkers || 0,
            'queue-available-workers': stats.availableWorkers || stats.maxWorkers || 3,
            'queue-max-workers': stats.maxWorkers || 3
        };

        Object.entries(elements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = value;
            }
        });

        // Update concurrent processing status
        const concurrentElement = document.getElementById('queue-concurrent-enabled');
        if (concurrentElement) {
            const isEnabled = stats.concurrentProcessing;
            concurrentElement.textContent = isEnabled ? 'Yes' : 'No';
            concurrentElement.className = `badge ${isEnabled ? 'bg-info' : 'bg-secondary'}`;
        }
    }

    // === Form Preview Management ===

    /**
     * Update form preview display
     */
    updateFormPreview() {
        const formData = DOMManager.getFormData();

        // Get display names for dropdowns - using correct element names
        const countryText =
            DOMManager.get('countrySelect')?.options[DOMManager.get('countrySelect')?.selectedIndex]?.text || '-';
        const platformText =
            DOMManager.get('platformSelect')?.options[DOMManager.get('platformSelect')?.selectedIndex]?.text || '-';
        const genreText =
            DOMManager.get('genreSelect')?.options[DOMManager.get('genreSelect')?.selectedIndex]?.text || '-';
        const templateText =
            DOMManager.get('templateSelect')?.options[DOMManager.get('templateSelect')?.selectedIndex]?.text || '-';

        // Update preview elements
        DOMManager.setText('previewCountry', countryText);
        DOMManager.setText('previewPlatform', platformText);
        DOMManager.setText('previewGenre', genreText);
        DOMManager.setText('previewTemplate', templateText);
        DOMManager.setText('previewType', formData.contentType || '-');

        // Generate and display preview URL
        const previewUrl = this.generateStreamGankUrl(formData);
        DOMManager.setText('previewUrl', previewUrl);
    }

    /**
     * Update form preview using FormManager state directly (more reliable)
     * @param {Object} formState - Current form state from FormManager
     */
    updateFormPreviewFromState(formState) {
        // Get display text from DOM elements for proper labels
        const countryText = this.getSelectDisplayText('countrySelect', formState.country) || '-';

        // Handle multiple platforms - show selected platforms as comma-separated list
        const platformText = this.getSelectedCheckboxText('platforms') || '-';

        // Handle multiple genres - show selected genres as comma-separated list
        const genreText = this.getSelectedCheckboxText('genres') || '-';

        const templateText = this.getSelectDisplayText('templateSelect', formState.template) || '-';

        // Map contentType values to display text
        const contentTypeMap = {
            Film: 'Movies',
            Série: 'TV Shows',
            All: 'All'
        };
        const typeText = contentTypeMap[formState.contentType] || formState.contentType || '-';

        // Update preview elements
        DOMManager.setText('previewCountry', countryText);
        DOMManager.setText('previewPlatform', platformText);
        DOMManager.setText('previewGenre', genreText);
        DOMManager.setText('previewTemplate', templateText);
        DOMManager.setText('previewType', typeText);

        // Generate and display preview URL using form state
        const previewUrl = this.generateStreamGankUrl(formState);
        DOMManager.setText('previewUrl', previewUrl);
    }

    /**
     * Get display text for a select element option
     * @param {string} elementId - Select element ID
     * @param {string} value - Option value to find
     * @returns {string} Display text or value if not found
     */
    getSelectDisplayText(elementId, value) {
        if (!value) return '';

        const selectElement = DOMManager.get(elementId);
        if (selectElement) {
            const option = Array.from(selectElement.options).find((opt) => opt.value === value);
            return option ? option.text : value;
        }
        return value;
    }

    /**
     * Get selected checkbox text as comma-separated string
     * @param {string} checkboxName - Name attribute of checkboxes
     * @returns {string} Comma-separated list of selected checkbox labels
     */
    getSelectedCheckboxText(checkboxName) {
        const checkboxes = document.querySelectorAll(`input[name="${checkboxName}"]:checked`);
        if (checkboxes.length === 0) return '';

        const selectedTexts = Array.from(checkboxes).map((checkbox) => {
            const label = document.querySelector(`label[for="${checkbox.id}"]`);
            return label ? label.textContent : checkbox.value;
        });

        return selectedTexts.join(', ');
    }

    /**
     * Generate StreamGang URL from form data
     * @param {Object} formData - Form data object
     * @returns {string} Generated URL
     */
    generateStreamGankUrl(formData) {
        if (!formData.country || !formData.platforms || formData.platforms.length === 0 || !formData.contentType) {
            return 'Select all parameters to generate URL';
        }

        const baseUrl = 'https://streamgank.com';
        const params = new URLSearchParams();

        // Use exact format: country, platforms (plural), genres (plural), type
        if (formData.country) params.set('country', formData.country);

        // Handle multiple platforms - properly encoded
        if (formData.platforms && formData.platforms.length > 0) {
            const platformsString = formData.platforms.join(',');
            params.set('platforms', platformsString);
        }

        // Handle multiple genres - properly encoded
        if (formData.genres && formData.genres.length > 0) {
            const genresString = formData.genres.join(',');
            params.set('genres', genresString);
        }

        // Only add content type if not 'all' - use actual selected value
        if (formData.contentType && formData.contentType !== 'All') {
            params.set('type', formData.contentType);
        }

        const finalUrl = `${baseUrl}?${params.toString()}`;

        // Ensure the URL is properly encoded for browser use
        const encodedUrl = encodeURI(finalUrl);
        console.log('🔗 Generated URL (encoded):', encodedUrl);
        return encodedUrl;
    }

    // === Video Results Management ===

    /**
     * Show video results section
     */
    showVideoResults() {
        DOMManager.show('videoResults');
    }

    /**
     * Hide video results section
     */
    hideVideoResults() {
        DOMManager.hide('videoResults');
    }

    /**
     * Display completed video in gallery
     * @param {Object} videoData - Video data object
     */
    displayVideo(videoData) {
        const videoGallery = DOMManager.get('videoGallery');
        if (!videoGallery) return;

        const videoElement = this.createVideoElement(videoData);
        videoGallery.appendChild(videoElement);

        this.completedVideos.push(videoData);
        this.updateVideoCount();
        this.showVideoResults();

        this.addStatusMessage('success', '🎬', 'Video is ready for viewing!');
    }

    /**
     * Create video element for gallery
     * @param {Object} videoData - Video data
     * @returns {HTMLElement} Video element
     */
    createVideoElement(videoData) {
        const videoElement = document.createElement('div');
        videoElement.className = 'video-item mb-3';
        videoElement.setAttribute('data-job-id', videoData.jobId || 'unknown');

        const timestamp = new Date().toLocaleString();
        const formData = DOMManager.getFormData();

        videoElement.innerHTML = `
            <div class="card">
                <div class="card-body">
                    <h6 class="card-title">
                        <i class="fas fa-video me-2"></i>Video ${this.completedVideos.length + 1}
                        <span class="badge bg-success ms-2">${videoData.jobId || 'N/A'}</span>
                        <small class="text-muted ms-2">${timestamp}</small>
                    </h6>
                    <div class="video-info mb-2">
                        <small class="text-muted">
                            ${formData.country || 'Unknown'} • ${formData.platform || 'Unknown'} • 
                            ${formData.genre || 'Unknown'} • ${formData.contentType || 'Unknown'}
                            ${videoData.creatomateId ? ` • ID: ${videoData.creatomateId}` : ''}
                        </small>
                    </div>
                    <video controls class="w-100 mb-3" style="max-height: 400px;" preload="metadata">
                        <source src="${videoData.videoUrl}" type="video/mp4">
                        Your browser does not support the video tag.
                    </video>
                    <div class="d-flex gap-2 flex-wrap">
                        <a href="${videoData.videoUrl}" target="_blank" class="btn btn-primary btn-sm">
                            <i class="fas fa-external-link-alt me-1"></i>Open Video
                        </a>
                        <a href="${videoData.videoUrl}" download class="btn btn-outline-secondary btn-sm">
                            <i class="fas fa-download me-1"></i>Download
                        </a>
                        <button class="btn btn-outline-info btn-sm copy-url-btn" data-url="${videoData.videoUrl}">
                            <i class="fas fa-copy me-1"></i>Copy URL
                        </button>
                        <button class="btn btn-outline-danger btn-sm remove-video-btn" data-job-id="${videoData.jobId}">
                            <i class="fas fa-trash me-1"></i>Remove
                        </button>
                    </div>
                </div>
            </div>
        `;

        // Setup video element event listeners
        this.setupVideoEventHandlers(videoElement);

        return videoElement;
    }

    /**
     * Setup event handlers for video element
     * @param {HTMLElement} videoElement - Video element
     */
    setupVideoEventHandlers(videoElement) {
        const video = videoElement.querySelector('video');
        const copyBtn = videoElement.querySelector('.copy-url-btn');
        const removeBtn = videoElement.querySelector('.remove-video-btn');

        // Video event handlers
        if (video) {
            video.addEventListener('loadstart', () => {
                if (!this.videoReadyMessageShown) {
                    this.addStatusMessage('info', '📥', 'Video started loading...');
                }
            });

            video.addEventListener('canplay', () => {
                if (!this.videoReadyMessageShown) {
                    this.addStatusMessage('success', '🎬', 'Video is ready to play!');
                    this.videoReadyMessageShown = true;
                }
            });

            video.addEventListener('error', (e) => {
                this.addStatusMessage('error', '❌', 'Video failed to load. Please try the direct link.');
                console.error('Video load error:', e);
            });
        }

        // Copy URL button
        if (copyBtn) {
            copyBtn.addEventListener('click', () => {
                const url = copyBtn.getAttribute('data-url');
                navigator.clipboard
                    .writeText(url)
                    .then(() => {
                        this.addStatusMessage('success', '📋', 'Video URL copied to clipboard!');
                    })
                    .catch(() => {
                        this.addStatusMessage('error', '❌', 'Failed to copy URL to clipboard');
                    });
            });
        }

        // Remove video button
        if (removeBtn) {
            removeBtn.addEventListener('click', () => {
                if (confirm('Remove this video from the gallery?')) {
                    videoElement.remove();
                    const jobId = removeBtn.getAttribute('data-job-id');
                    this.completedVideos = this.completedVideos.filter((v) => v.jobId !== jobId);
                    this.updateVideoCount();
                    this.addStatusMessage('info', '🗑️', 'Video removed from gallery');
                }
            });
        }
    }

    /**
     * Update video count display
     */
    updateVideoCount() {
        const count = this.completedVideos.length;
        DOMManager.setText('videosCount', count);

        const badge = DOMManager.get('videoCountBadge');
        if (badge) {
            badge.textContent = count;
            badge.style.display = count > 0 ? 'inline' : 'none';
        }
    }

    /**
     * Clear all video results
     */
    clearVideoResults() {
        const videoGallery = DOMManager.get('videoGallery');
        if (videoGallery) {
            videoGallery.innerHTML = '';
        }

        this.completedVideos = [];
        this.updateVideoCount();
        this.hideVideoResults();
        this.videoReadyMessageShown = false;
    }

    // === Utility Methods ===

    /**
     * Format duration from milliseconds
     * @param {number} ms - Duration in milliseconds
     * @returns {string} Formatted duration
     */
    formatDuration(ms) {
        if (!ms || ms < 0) return '-';

        const seconds = Math.floor(ms / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);

        if (hours > 0) {
            return `${hours}h ${minutes % 60}m ${seconds % 60}s`;
        } else if (minutes > 0) {
            return `${minutes}m ${seconds % 60}s`;
        } else {
            return `${seconds}s`;
        }
    }

    /**
     * Get current UI state for debugging
     * @returns {Object} Current UI state
     */
    getState() {
        return {
            completedVideos: this.completedVideos.length,
            statusMessages: this.statusMessageId,
            videoReadyMessageShown: this.videoReadyMessageShown
        };
    }
}

// Export singleton instance
export default new UIManager();
