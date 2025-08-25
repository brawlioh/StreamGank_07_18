/**
 * API Service - Professional HTTP client for server communication
 * Handles all API requests with caching, error handling, and retry logic
 */
import axios from 'axios';

export class APIService {
    constructor() {
        this.baseURL = window.location.origin;
        this.timeout = 30000; // 30 second timeout
        this.cache = new Map();
        this.cacheTTL = 5000; // 5 second cache TTL
        this.retryAttempts = 3;
        this.retryDelay = 1000; // 1 second base delay
    }

    /**
     * Make HTTP request with professional error handling and caching
     * @param {string} method - HTTP method
     * @param {string} endpoint - API endpoint
     * @param {Object} data - Request data
     * @param {Object} options - Additional options
     * @returns {Promise<Object>} Response data
     */
    async request(method, endpoint, data = null, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const cacheKey = `${method}:${endpoint}:${JSON.stringify(data)}`;

        // Check cache for GET requests
        if (method === 'GET' && this.cache.has(cacheKey)) {
            const cached = this.cache.get(cacheKey);
            if (Date.now() - cached.timestamp < this.cacheTTL) {
                console.log(`📋 Cache hit: ${endpoint}`);
                return cached.data;
            } else {
                this.cache.delete(cacheKey);
            }
        }

        // Axios request configuration
        const axiosConfig = {
            method: method.toLowerCase(),
            url: url,
            timeout: this.timeout,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        };

        if (data && method !== 'GET') {
            axiosConfig.data = data;
        }

        let lastError;

        // Retry logic
        for (let attempt = 1; attempt <= this.retryAttempts; attempt++) {
            try {
                const startTime = Date.now();
                const response = await axios(axiosConfig);
                const duration = Date.now() - startTime;

                // Log slow requests
                if (duration > 2000) {
                    console.warn(`⚠️ Slow API request: ${endpoint} (${duration}ms)`);
                }

                const responseData = response.data;

                // Cache successful GET requests
                if (method === 'GET' && responseData.success) {
                    this.cache.set(cacheKey, {
                        data: responseData,
                        timestamp: Date.now()
                    });
                }

                return responseData;
            } catch (error) {
                lastError = error;

                // Handle axios timeout and network errors
                if (error.code === 'ECONNABORTED' || error.message.includes('timeout')) {
                    throw new Error(`Request timeout: ${endpoint}`);
                }

                // Handle HTTP error responses
                const errorMessage = error.response
                    ? `HTTP ${error.response.status}: ${error.response.statusText}`
                    : error.message;

                if (attempt < this.retryAttempts) {
                    const delay = this.retryDelay * Math.pow(2, attempt - 1); // Exponential backoff
                    console.warn(
                        `⚠️ Request failed (attempt ${attempt}/${this.retryAttempts}), retrying in ${delay}ms:`,
                        errorMessage
                    );
                    await new Promise((resolve) => setTimeout(resolve, delay));
                } else {
                    console.error(`❌ API Error after ${this.retryAttempts} attempts (${method} ${endpoint}):`, error);
                }
            }
        }

        throw lastError;
    }

    /**
     * GET request
     * @param {string} endpoint - API endpoint
     * @param {Object} options - Request options
     * @returns {Promise<Object>} Response data
     */
    async get(endpoint, options = {}) {
        return this.request('GET', endpoint, null, options);
    }

    /**
     * POST request
     * @param {string} endpoint - API endpoint
     * @param {Object} data - Request data
     * @param {Object} options - Request options
     * @returns {Promise<Object>} Response data
     */
    async post(endpoint, data = {}, options = {}) {
        return this.request('POST', endpoint, data, options);
    }

    /**
     * PUT request
     * @param {string} endpoint - API endpoint
     * @param {Object} data - Request data
     * @param {Object} options - Request options
     * @returns {Promise<Object>} Response data
     */
    async put(endpoint, data = {}, options = {}) {
        return this.request('PUT', endpoint, data, options);
    }

    /**
     * DELETE request
     * @param {string} endpoint - API endpoint
     * @param {Object} options - Request options
     * @returns {Promise<Object>} Response data
     */
    async delete(endpoint, options = {}) {
        return this.request('DELETE', endpoint, null, options);
    }

    // === StreamGank Specific API Methods ===

    /**
     * Generate video request
     * @param {Object} params - Video generation parameters
     * @returns {Promise<Object>} Job response
     */
    async generateVideo(params) {
        return this.post('/api/generate', params);
    }

    /**
     * Get job status
     * @param {string} jobId - Job ID
     * @returns {Promise<Object>} Job status
     */
    async getJobStatus(jobId) {
        return this.get(`/api/job/${jobId}`);
    }

    /**
     * Get queue status with optimized caching
     * @returns {Promise<Object>} Queue statistics
     */
    async getQueueStatus() {
        return this.get('/api/queue/status');
    }

    /**
     * Get all jobs in queue
     * @returns {Promise<Object>} All jobs data
     */
    async getAllJobs() {
        return this.get('/api/queue/jobs');
    }

    /**
     * Clear queue
     * @returns {Promise<Object>} Clear operation result
     */
    async clearQueue() {
        return this.post('/api/queue/clear');
    }

    /**
     * Cancel specific job
     * @param {string} jobId - Job ID to cancel
     * @returns {Promise<Object>} Cancel operation result
     */
    async cancelJob(jobId) {
        return this.post(`/api/job/${jobId}/cancel`);
    }

    /**
     * Retry failed job
     * @param {string} jobId - Job ID to retry
     * @returns {Promise<Object>} Retry operation result
     */
    async retryJob(jobId) {
        return this.post(`/api/job/${jobId}/retry`);
    }

    /**
     * Validate StreamGank URL
     * @param {string} url - URL to validate
     * @returns {Promise<Object>} Validation result
     */
    async validateUrl(url) {
        return this.post('/api/validate-url', { url });
    }

    /**
     * Get Creatomate render status
     * @param {string} renderId - Render ID
     * @returns {Promise<Object>} Render status
     */
    async getCreatomateStatus(renderId) {
        return this.get(`/api/status/${renderId}`);
    }

    /**
     * Get platforms for country
     * @param {string} country - Country code
     * @returns {Promise<Object>} Platform list
     */
    async getPlatforms(country) {
        return this.get(`/api/platforms/${country}`);
    }

    /**
     * Get genres for platform
     * @param {string} country - Country code
     * @param {string} platform - Platform name
     * @returns {Promise<Object>} Genre list
     */
    async getGenres(country, platform) {
        // If platform is provided, filter genres by platform
        if (platform) {
            return this.get(`/api/genres/${country}?platform=${platform}`);
        }
        // Otherwise get all genres for country
        return this.get(`/api/genres/${country}`);
    }

    // === Webhook API Methods ===

    /**
     * Get webhook system status
     * @returns {Promise<Object>} Webhook status
     */
    async getWebhookStatus() {
        return this.get('/api/webhooks/status');
    }

    /**
     * Test webhook endpoint
     * @param {string} url - Webhook URL to test
     * @returns {Promise<Object>} Test result
     */
    async testWebhook(url) {
        return this.post('/api/webhooks/test', { url });
    }

    /**
     * Trigger webhook manually
     * @param {string} event - Event name
     * @param {Object} data - Event data
     * @returns {Promise<Object>} Trigger result
     */
    async triggerWebhook(event, data) {
        return this.post('/api/webhooks/trigger', { event, data });
    }

    // === Utility Methods ===

    /**
     * Clear API cache
     */
    clearCache() {
        this.cache.clear();
        console.log('🧹 API cache cleared');
    }

    /**
     * Get cache statistics
     * @returns {Object} Cache stats
     */
    getCacheStats() {
        const now = Date.now();
        let validEntries = 0;
        let expiredEntries = 0;

        for (const [key, entry] of this.cache) {
            if (now - entry.timestamp < this.cacheTTL) {
                validEntries++;
            } else {
                expiredEntries++;
            }
        }

        return {
            total: this.cache.size,
            valid: validEntries,
            expired: expiredEntries,
            hitRate: validEntries / (validEntries + expiredEntries) || 0
        };
    }
}

// Export singleton instance
export default new APIService();
