/**
 * Professional Webhook Manager for StreamGank
 * Handles external service notifications with enterprise-level reliability
 *
 * Features:
 * - Configurable webhook endpoints
 * - Automatic retry with exponential backoff
 * - Security with HMAC signatures
 * - Rate limiting and error tracking
 * - Professional logging and monitoring
 */

const crypto = require("crypto");
const axios = require("axios").default;

class WebhookManager {
    constructor() {
        // Webhook configuration from environment
        this.webhookConfig = this.loadWebhookConfig();

        // Retry configuration
        this.maxRetries = parseInt(process.env.WEBHOOK_MAX_RETRIES) || 3;
        this.retryDelay = parseInt(process.env.WEBHOOK_RETRY_DELAY) || 1000; // Base delay in ms
        this.maxRetryDelay = parseInt(process.env.WEBHOOK_MAX_RETRY_DELAY) || 30000; // Max 30s

        // Rate limiting
        this.rateLimitWindow = parseInt(process.env.WEBHOOK_RATE_LIMIT_WINDOW) || 60000; // 1 minute
        this.rateLimitMax = parseInt(process.env.WEBHOOK_RATE_LIMIT_MAX) || 100; // Max requests per window
        this.requestCounts = new Map();

        // Error tracking
        this.errorStats = new Map();

        // Security
        this.secretKey = process.env.WEBHOOK_SECRET_KEY || this.generateSecretKey();

        console.log(`🔗 Webhook Manager initialized with ${this.webhookConfig.length} configured endpoints`);
    }

    /**
     * Load webhook configuration from environment variables
     * @returns {Array} Array of webhook configurations
     */
    loadWebhookConfig() {
        const webhooks = [];

        // Parse webhook URLs from environment (comma-separated)
        const webhookUrls = process.env.WEBHOOK_URLS ? process.env.WEBHOOK_URLS.split(",") : [];
        const webhookEvents = process.env.WEBHOOK_EVENTS ? process.env.WEBHOOK_EVENTS.split(",") : ["job.completed", "job.failed"];

        webhookUrls.forEach((url, index) => {
            const cleanUrl = url.trim();
            if (cleanUrl) {
                webhooks.push({
                    id: `webhook_${index + 1}`,
                    url: cleanUrl,
                    events: webhookEvents,
                    enabled: true,
                    timeout: parseInt(process.env.WEBHOOK_TIMEOUT) || 10000, // 10 second timeout
                    headers: this.parseWebhookHeaders(process.env.WEBHOOK_HEADERS),
                });
            }
        });

        return webhooks;
    }

    /**
     * Parse webhook headers from environment variable
     * @param {string} headersString - Headers in format "Header1:Value1,Header2:Value2"
     * @returns {Object} Headers object
     */
    parseWebhookHeaders(headersString) {
        const headers = {
            "Content-Type": "application/json",
            "User-Agent": "StreamGank-Webhook/1.0",
        };

        if (headersString) {
            headersString.split(",").forEach((header) => {
                const [key, value] = header.split(":").map((s) => s.trim());
                if (key && value) {
                    headers[key] = value;
                }
            });
        }

        return headers;
    }

    /**
     * Generate a secure secret key for webhook signatures
     * @returns {string} Generated secret key
     */
    generateSecretKey() {
        return crypto.randomBytes(32).toString("hex");
    }

    /**
     * Create HMAC signature for webhook payload
     * @param {Object} payload - Webhook payload
     * @param {string} secret - Secret key
     * @returns {string} HMAC signature
     */
    createSignature(payload, secret) {
        const payloadString = typeof payload === "string" ? payload : JSON.stringify(payload);
        return crypto.createHmac("sha256", secret).update(payloadString).digest("hex");
    }

    /**
     * Check rate limiting for a webhook endpoint
     * @param {string} webhookId - Webhook ID
     * @returns {boolean} Whether request is allowed
     */
    checkRateLimit(webhookId) {
        const now = Date.now();
        const windowStart = now - this.rateLimitWindow;

        // Get or create request count for this webhook
        let requestData = this.requestCounts.get(webhookId) || { count: 0, windowStart: now };

        // Reset window if expired
        if (requestData.windowStart < windowStart) {
            requestData = { count: 0, windowStart: now };
        }

        // Check rate limit
        if (requestData.count >= this.rateLimitMax) {
            console.warn(`⚠️ Rate limit exceeded for webhook ${webhookId}: ${requestData.count}/${this.rateLimitMax}`);
            return false;
        }

        // Update count
        requestData.count++;
        this.requestCounts.set(webhookId, requestData);

        return true;
    }

    /**
     * Send webhook notification with professional error handling
     * @param {string} event - Event name (e.g., 'job.completed')
     * @param {Object} data - Event data
     * @returns {Promise<Array>} Results from all webhook deliveries
     */
    async sendWebhookNotification(event, data) {
        if (!event || !data) {
            console.error("❌ Webhook notification requires event and data parameters");
            return [];
        }

        // Filter webhooks that should receive this event
        const relevantWebhooks = this.webhookConfig.filter((webhook) => webhook.enabled && webhook.events.includes(event));

        if (relevantWebhooks.length === 0) {
            console.log(`🔗 No webhooks configured for event: ${event}`);
            return [];
        }

        console.log(`🔗 Sending webhook notifications for event: ${event} to ${relevantWebhooks.length} endpoints`);

        // Send to all relevant webhooks in parallel
        const webhookPromises = relevantWebhooks.map((webhook) => this.deliverWebhook(webhook, event, data));

        const results = await Promise.allSettled(webhookPromises);

        // Log delivery summary
        const successful = results.filter((r) => r.status === "fulfilled").length;
        const failed = results.filter((r) => r.status === "rejected").length;

        console.log(`🔗 Webhook delivery complete: ${successful} successful, ${failed} failed`);

        return results;
    }

    /**
     * Deliver webhook to a single endpoint with retry logic
     * @param {Object} webhook - Webhook configuration
     * @param {string} event - Event name
     * @param {Object} data - Event data
     * @returns {Promise<Object>} Delivery result
     */
    async deliverWebhook(webhook, event, data) {
        // Check rate limiting
        if (!this.checkRateLimit(webhook.id)) {
            throw new Error(`Rate limit exceeded for webhook ${webhook.id}`);
        }

        // Prepare payload
        const payload = {
            event,
            data,
            timestamp: new Date().toISOString(),
            webhook_id: webhook.id,
            source: "streamgank",
        };

        // Create signature
        const signature = this.createSignature(payload, this.secretKey);

        // Prepare headers
        const headers = {
            ...webhook.headers,
            "X-StreamGank-Signature": `sha256=${signature}`,
            "X-StreamGank-Event": event,
            "X-StreamGank-Delivery": crypto.randomUUID(),
        };

        // Delivery with retry logic
        let lastError;
        for (let attempt = 0; attempt <= this.maxRetries; attempt++) {
            try {
                const startTime = Date.now();

                const response = await axios.post(webhook.url, payload, {
                    headers,
                    timeout: webhook.timeout,
                    validateStatus: (status) => status >= 200 && status < 300,
                });

                const duration = Date.now() - startTime;

                console.log(`✅ Webhook delivered successfully: ${webhook.id} (${duration}ms, status: ${response.status})`);

                // Reset error count on success
                this.errorStats.delete(webhook.id);

                return {
                    webhookId: webhook.id,
                    success: true,
                    status: response.status,
                    duration,
                    attempt: attempt + 1,
                };
            } catch (error) {
                lastError = error;

                // Track errors
                const errorCount = (this.errorStats.get(webhook.id) || 0) + 1;
                this.errorStats.set(webhook.id, errorCount);

                const isLastAttempt = attempt === this.maxRetries;
                const delay = Math.min(this.retryDelay * Math.pow(2, attempt), this.maxRetryDelay);

                if (isLastAttempt) {
                    console.error(`❌ Webhook delivery failed after ${attempt + 1} attempts: ${webhook.id} - ${error.message}`);
                } else {
                    console.warn(`⚠️ Webhook delivery failed (attempt ${attempt + 1}/${this.maxRetries + 1}): ${webhook.id} - ${error.message}. Retrying in ${delay}ms...`);
                    await new Promise((resolve) => setTimeout(resolve, delay));
                }
            }
        }

        // All attempts failed
        throw new Error(`Webhook delivery failed after ${this.maxRetries + 1} attempts: ${lastError.message}`);
    }

    /**
     * Get webhook system status and statistics
     * @returns {Object} Webhook system status
     */
    getWebhookStatus() {
        const now = Date.now();
        const activeWebhooks = this.webhookConfig.filter((w) => w.enabled).length;
        const totalErrors = Array.from(this.errorStats.values()).reduce((sum, count) => sum + count, 0);

        // Calculate request rates
        const requestRates = {};
        for (const [webhookId, data] of this.requestCounts) {
            if (now - data.windowStart < this.rateLimitWindow) {
                requestRates[webhookId] = data.count;
            }
        }

        return {
            active_webhooks: activeWebhooks,
            total_webhooks: this.webhookConfig.length,
            total_errors: totalErrors,
            rate_limits: requestRates,
            error_counts: Object.fromEntries(this.errorStats),
            config: {
                max_retries: this.maxRetries,
                retry_delay: this.retryDelay,
                rate_limit: `${this.rateLimitMax}/${this.rateLimitWindow}ms`,
                secret_configured: !!this.secretKey,
            },
        };
    }

    /**
     * Validate webhook endpoint connectivity
     * @param {string} url - Webhook URL to test
     * @returns {Promise<Object>} Validation result
     */
    async validateWebhookEndpoint(url) {
        try {
            const testPayload = {
                event: "webhook.test",
                data: { message: "StreamGank webhook connectivity test" },
                timestamp: new Date().toISOString(),
                test: true,
            };

            const signature = this.createSignature(testPayload, this.secretKey);
            const headers = {
                "Content-Type": "application/json",
                "User-Agent": "StreamGank-Webhook/1.0",
                "X-StreamGank-Signature": `sha256=${signature}`,
                "X-StreamGank-Event": "webhook.test",
                "X-StreamGank-Test": "true",
            };

            const startTime = Date.now();
            const response = await axios.post(url, testPayload, {
                headers,
                timeout: 5000,
                validateStatus: (status) => status >= 200 && status < 500,
            });

            const duration = Date.now() - startTime;

            return {
                success: response.status >= 200 && response.status < 300,
                status: response.status,
                duration,
                url,
                message: response.status >= 200 && response.status < 300 ? "Webhook endpoint is reachable" : `HTTP ${response.status} response`,
            };
        } catch (error) {
            return {
                success: false,
                status: 0,
                duration: 0,
                url,
                message: error.message,
                error: error.code || "UNKNOWN_ERROR",
            };
        }
    }
}

module.exports = WebhookManager;
