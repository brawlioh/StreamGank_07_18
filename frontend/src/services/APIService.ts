/**
 * API Service - Professional HTTP client for server communication
 * Handles all API requests with caching, error handling, and retry logic
 */
import axios from "axios";
import type { AxiosRequestConfig, AxiosResponse } from "axios";

interface CacheEntry {
    data: APIResponse;
    timestamp: number;
}

interface APIResponse {
    success: boolean;
    message?: string;
    error?: string;
    [key: string]: unknown;
}

export class APIService {
    private baseURL: string;
    private timeout: number;
    private cache: Map<string, CacheEntry>;
    private cacheTTL: number;
    private retryAttempts: number;
    private retryDelay: number;

    constructor() {
        // Debug: Check all available environment variables
        console.log("🔍 Debug - All import.meta.env:", import.meta.env);
        console.log("🔍 Debug - VITE_BACKEND_URL:", import.meta.env.VITE_BACKEND_URL);

        // Use VITE_BACKEND_URL from .env file - NO FALLBACKS, NO HARDCODING
        this.baseURL = import.meta.env.VITE_BACKEND_URL;

        if (!this.baseURL) {
            throw new Error("❌ VITE_BACKEND_URL is not set in .env file! This is required for API communication.");
        }

        // Log the URL from .env for debugging
        console.log(`🔗 APIService initialized with baseURL from .env: ${this.baseURL}`);

        this.timeout = 30000; // 30 second timeout
        this.cache = new Map();
        this.cacheTTL = 5000; // 5 second cache TTL
        this.retryAttempts = 3;
        this.retryDelay = 1000; // 1 second base delay
    }

    /**
     * Make HTTP request with professional error handling and caching
     */
    async request(method: string, endpoint: string, data: unknown = null, options: AxiosRequestConfig = {}): Promise<APIResponse> {
        const url = `${this.baseURL}${endpoint}`;
        const cacheKey = `${method}:${endpoint}:${JSON.stringify(data)}`;

        // Check cache for GET requests
        if (method === "GET" && this.cache.has(cacheKey)) {
            const cached = this.cache.get(cacheKey)!;
            if (Date.now() - cached.timestamp < this.cacheTTL) {
                console.log(`📋 Cache hit: ${endpoint}`);
                return cached.data;
            } else {
                this.cache.delete(cacheKey);
            }
        }

        // Axios request configuration
        const axiosConfig: AxiosRequestConfig = {
            method: method.toLowerCase() as "get" | "post" | "put" | "delete",
            url: url,
            timeout: this.timeout,
            headers: {
                "Content-Type": "application/json",
                ...options.headers,
            },
            ...options,
        };

        if (data && method !== "GET") {
            axiosConfig.data = data;
        }

        let lastError: unknown;

        // Retry logic
        for (let attempt = 1; attempt <= this.retryAttempts; attempt++) {
            try {
                const startTime = Date.now();
                const response: AxiosResponse = await axios(axiosConfig);
                const duration = Date.now() - startTime;

                // Log slow requests
                if (duration > 2000) {
                    console.warn(`⚠️ Slow API request: ${endpoint} (${duration}ms)`);
                }

                const responseData = response.data;

                // Cache successful GET requests
                if (method === "GET" && responseData.success) {
                    this.cache.set(cacheKey, {
                        data: responseData,
                        timestamp: Date.now(),
                    });
                }

                return responseData;
            } catch (error: unknown) {
                lastError = error;

                // Handle axios timeout and network errors
                if (error && typeof error === "object" && "code" in error && error.code === "ECONNABORTED") {
                    throw new Error(`Request timeout: ${endpoint}`);
                }
                if (error && typeof error === "object" && "message" in error && typeof error.message === "string" && error.message.includes("timeout")) {
                    throw new Error(`Request timeout: ${endpoint}`);
                }

                // Handle HTTP error responses
                let errorMessage = "Unknown error";
                if (error && typeof error === "object") {
                    if ("response" in error && error.response && typeof error.response === "object") {
                        const response = error.response as { status: number; statusText: string };
                        errorMessage = `HTTP ${response.status}: ${response.statusText}`;
                    } else if ("message" in error && typeof error.message === "string") {
                        errorMessage = error.message;
                    }
                }

                if (attempt < this.retryAttempts) {
                    const delay = this.retryDelay * Math.pow(2, attempt - 1); // Exponential backoff
                    console.warn(`⚠️ Request failed (attempt ${attempt}/${this.retryAttempts}), retrying in ${delay}ms:`, errorMessage);
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
     */
    async get(endpoint: string, options: AxiosRequestConfig = {}): Promise<APIResponse> {
        return this.request("GET", endpoint, null, options);
    }

    /**
     * POST request
     */
    async post(endpoint: string, data: unknown = {}, options: AxiosRequestConfig = {}): Promise<APIResponse> {
        return this.request("POST", endpoint, data, options);
    }

    /**
     * PUT request
     */
    async put(endpoint: string, data: unknown = {}, options: AxiosRequestConfig = {}): Promise<APIResponse> {
        return this.request("PUT", endpoint, data, options);
    }

    /**
     * DELETE request
     */
    async delete(endpoint: string, options: AxiosRequestConfig = {}): Promise<APIResponse> {
        return this.request("DELETE", endpoint, null, options);
    }

    // === StreamGank Specific API Methods ===

    /**
     * Generate video request
     */
    async generateVideo(params: unknown): Promise<APIResponse> {
        return this.post("/api/generate", params);
    }

    /**
     * Get job status
     */
    async getJobStatus(jobId: string): Promise<APIResponse> {
        return this.get(`/api/job/${jobId}`);
    }

    /**
     * Get queue status with optimized caching
     */
    async getQueueStatus(): Promise<APIResponse> {
        return this.get("/api/queue/status");
    }

    /**
     * Get all jobs in queue
     */
    async getAllJobs(): Promise<APIResponse> {
        return this.get("/api/queue/jobs");
    }

    /**
     * Clear queue
     */
    async clearQueue(): Promise<APIResponse> {
        return this.post("/api/queue/clear");
    }

    /**
     * Cancel specific job
     */
    async cancelJob(jobId: string): Promise<APIResponse> {
        return this.post(`/api/job/${jobId}/cancel`);
    }

    /**
     * Retry failed job
     */
    async retryJob(jobId: string): Promise<APIResponse> {
        return this.post(`/api/job/${jobId}/retry`);
    }

    /**
     * Validate StreamGank URL
     */
    async validateUrl(url: string): Promise<APIResponse> {
        return this.post("/api/validate-url", { url });
    }

    /**
     * Get Creatomate render status
     */
    async getCreatomateStatus(renderId: string): Promise<APIResponse> {
        return this.get(`/api/status/${renderId}`);
    }

    /**
     * Get platforms for country
     */
    async getPlatforms(country: string): Promise<APIResponse> {
        return this.get(`/api/platforms/${country}`);
    }

    /**
     * Get genres for platform
     */
    async getGenres(country: string, platform?: string): Promise<APIResponse> {
        if (platform) {
            const encodedPlatform = encodeURIComponent(platform);
            return this.get(`/api/genres/${country}?platform=${encodedPlatform}`);
        }
        return this.get(`/api/genres/${country}`);
    }

    // === Webhook API Methods ===

    /**
     * Get webhook system status
     */
    async getWebhookStatus(): Promise<APIResponse> {
        return this.get("/api/webhooks/status");
    }

    /**
     * Test webhook endpoint
     */
    async testWebhook(url: string): Promise<APIResponse> {
        return this.post("/api/webhooks/test", { url });
    }

    /**
     * Trigger webhook manually
     */
    async triggerWebhook(event: string, data: unknown): Promise<APIResponse> {
        return this.post("/api/webhooks/trigger", { event, data });
    }

    /**
     * Get available templates
     */
    async getTemplates(): Promise<APIResponse> {
        console.log("📋 Fetching available templates");
        return this.get("/api/templates");
    }

    /**
     * Get movie preview
     */
    async getMoviePreview(params: { country: string; platforms: string[]; genres: string[]; contentType?: string }): Promise<APIResponse> {
        console.log("🎬 Fetching movie preview", params);
        return this.post("/api/movies/preview", params);
    }

    // === Utility Methods ===

    /**
     * Clear API cache
     */
    clearCache(): void {
        this.cache.clear();
        console.log("🧹 API cache cleared");
    }

    /**
     * Get cache statistics
     */
    getCacheStats(): { total: number; valid: number; expired: number; hitRate: number } {
        const now = Date.now();
        let validEntries = 0;
        let expiredEntries = 0;

        this.cache.forEach((entry) => {
            if (now - entry.timestamp < this.cacheTTL) {
                validEntries++;
            } else {
                expiredEntries++;
            }
        });

        return {
            total: this.cache.size,
            valid: validEntries,
            expired: expiredEntries,
            hitRate: validEntries / (validEntries + expiredEntries) || 0,
        };
    }
}

// Export singleton instance
export default new APIService();
