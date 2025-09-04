/**
 * Realtime Service - Professional real-time communication service
 * Handles Server-Sent Events (SSE) and fallback polling for queue status updates
 */
import APIService from "./APIService";

interface PollingConfig {
    fast: number;
    normal: number;
    slow: number;
    slowest: number;
}

interface QueueStats {
    pending: number;
    processing: number;
    completed: number;
    failed: number;
    activeWorkers: number;
    availableWorkers: number;
    concurrentProcessing: boolean;
    _debug?: string;
}

export class RealtimeService extends EventTarget {
    private eventSource: EventSource | null = null;
    private isSSEEnabled: boolean = false;
    private sseRetryCount: number = 0;
    private maxSSERetries: number = 5;
    private reconnectAttempts: number = 0;
    private maxReconnectAttempts: number = 3;

    // ANTI-SPAM: Polling fallback configuration
    private pollingTimer: number | null = null;
    private isPolling: boolean = false;
    private pollingInterval: number = 60000; // 60 seconds default
    private adaptivePollingConfig: PollingConfig = {
        fast: 30000, // 30 seconds during active operations
        normal: 60000, // 60 seconds normal
        slow: 120000, // 2 minutes when idle
        slowest: 180000, // 3 minutes when very idle
    };

    // Connection state
    private isConnected: boolean = false;
    private lastUpdateTime: number = 0;
    private consecutiveErrors: number = 0;
    private maxConsecutiveErrors: number = 5;

    constructor() {
        super();
    }

    /**
     * Initialize Realtime Service
     */
    init(): void {
        this.setupEventListeners();
        this.initializeConnection();
    }

    /**
     * Setup event listeners
     */
    private setupEventListeners(): void {
        // Page visibility API for smart connection management
        document.addEventListener("visibilitychange", () => {
            if (document.hidden) {
                this.handlePageHidden();
            } else {
                this.handlePageVisible();
            }
        });

        // Connection recovery on network changes
        window.addEventListener("online", () => {
            console.log("📡 Network back online, attempting to reconnect...");
            this.reconnect();
        });

        window.addEventListener("offline", () => {
            console.log("📡 Network offline detected");
            this.disconnect();
        });

        // Cleanup on page unload
        window.addEventListener("beforeunload", () => {
            this.cleanup();
        });
    }

    /**
     * Initialize real-time connection (SSE preferred, polling fallback)
     */
    private initializeConnection(): void {
        if (this.canUseSSE()) {
            this.initializeSSE();
        } else {
            console.log("📡 SSE not supported, using polling fallback");
            this.startPolling("normal");
        }
    }

    /**
     * Check if Server-Sent Events are supported
     */
    private canUseSSE(): boolean {
        return (
            typeof EventSource !== "undefined" &&
            !navigator.userAgent.includes("Edge/") && // Edge has SSE issues
            this.sseRetryCount < this.maxSSERetries
        );
    }

    /**
     * Initialize Server-Sent Events connection
     */
    private initializeSSE(): void {
        if (this.eventSource || this.isSSEEnabled) {
            return;
        }

        try {
            console.log("📡 Initializing Server-Sent Events...");
            this.eventSource = new EventSource("/api/queue/status/stream");

            this.eventSource.onopen = () => {
                console.log("📡 SSE connection opened");
                this.isSSEEnabled = true;
                this.isConnected = true;
                this.sseRetryCount = 0;
                this.consecutiveErrors = 0;

                // Stop any active polling
                this.stopPolling();

                // Emit connection event
                this.dispatchEvent(new CustomEvent("connected", { detail: { type: "sse" } }));
                this.addStatusMessage("success", "📡", "Real-time updates enabled");
            };

            this.eventSource.onmessage = (event) => {
                this.handleSSEMessage(event);
            };

            // Handle specific event types
            this.eventSource.addEventListener("status", (event) => {
                this.handleSSEMessage(event as MessageEvent);
            });

            this.eventSource.addEventListener("heartbeat", () => {
                // Keep connection alive - just update last activity
                this.lastUpdateTime = Date.now();
            });

            this.eventSource.onerror = (event) => {
                this.handleSSEError(event);
            };
        } catch (error) {
            console.error("❌ Failed to initialize SSE:", error);
            this.fallbackToPolling();
        }
    }

    /**
     * Handle SSE message
     */
    private handleSSEMessage(event: MessageEvent): void {
        try {
            const data = JSON.parse(event.data);

            if (data.success && data.stats) {
                this.lastUpdateTime = Date.now();
                this.consecutiveErrors = 0;

                // Emit update event for other components
                this.dispatchEvent(
                    new CustomEvent("queueUpdate", {
                        detail: { stats: data.stats, source: "sse" },
                    })
                );

                // Log debugging info
                if (data.stats._debug) {
                    console.log(`📊 SSE queue update: ${data.stats._debug}`);
                }
            }
        } catch (error) {
            console.error("❌ Failed to parse SSE message:", error);
            this.consecutiveErrors++;

            if (this.consecutiveErrors >= this.maxConsecutiveErrors) {
                console.warn("⚠️ Too many consecutive SSE parsing errors, falling back to polling");
                this.fallbackToPolling();
            }
        }
    }

    /**
     * Handle SSE connection errors
     */
    private handleSSEError(event: Event): void {
        console.warn("⚠️ SSE connection error, attempting fallback");
        this.isSSEEnabled = false;
        this.isConnected = false;
        this.sseRetryCount++;

        // Close existing connection
        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
        }

        // Emit disconnection event
        this.dispatchEvent(new CustomEvent("disconnected", { detail: { type: "sse", error: event } }));

        // Fallback to polling
        this.fallbackToPolling();

        // Try to reconnect SSE later with exponential backoff
        if (this.sseRetryCount < this.maxSSERetries) {
            const retryDelay = Math.min(1000 * Math.pow(2, this.sseRetryCount), 30000);
            console.log(`📡 Retrying SSE connection in ${retryDelay}ms (attempt ${this.sseRetryCount + 1}/${this.maxSSERetries})`);

            setTimeout(() => {
                if (!this.isSSEEnabled && this.canUseSSE()) {
                    this.initializeSSE();
                }
            }, retryDelay);
        } else {
            this.addStatusMessage("warning", "⚠️", "Real-time updates unavailable, using fallback polling");
        }
    }

    /**
     * Fallback to polling when SSE fails
     */
    private fallbackToPolling(): void {
        if (this.isPolling) {
            return; // Already polling
        }

        console.log("📡 Falling back to adaptive polling");
        this.startPolling("fast"); // Use fast polling as fallback
    }

    /**
     * Start adaptive polling based on activity level
     */
    private startPolling(mode: keyof PollingConfig = "normal"): void {
        if (this.pollingTimer) {
            this.stopPolling();
        }

        this.isPolling = true;
        this.pollingInterval = this.adaptivePollingConfig[mode] || this.adaptivePollingConfig.normal;

        console.log(`📡 Starting ${mode} polling (${this.pollingInterval}ms interval)`);

        // Initial poll
        this.pollQueueStatus();

        // Setup polling timer
        this.pollingTimer = window.setInterval(() => {
            this.pollQueueStatus();
        }, this.pollingInterval);

        // Emit polling started event
        this.dispatchEvent(
            new CustomEvent("pollingStarted", {
                detail: { mode, interval: this.pollingInterval },
            })
        );
    }

    /**
     * Stop polling
     */
    private stopPolling(): void {
        if (this.pollingTimer) {
            clearInterval(this.pollingTimer);
            this.pollingTimer = null;
            this.isPolling = false;
            console.log("📡 Polling stopped");
        }
    }

    /**
     * Poll queue status via API
     */
    private async pollQueueStatus(): Promise<void> {
        try {
            const startTime = Date.now();
            const result = await APIService.getQueueStatus();
            const duration = Date.now() - startTime;

            if (result.success && result.stats) {
                this.lastUpdateTime = Date.now();
                this.consecutiveErrors = 0;

                // Emit update event
                this.dispatchEvent(
                    new CustomEvent("queueUpdate", {
                        detail: {
                            stats: result.stats,
                            source: "polling",
                            duration,
                        },
                    })
                );

                // Adaptive polling based on response time and activity
                this.adjustPollingInterval(duration, result.stats);
            } else {
                this.consecutiveErrors++;
                console.warn("⚠️ Polling received invalid response");
            }
        } catch (error) {
            this.consecutiveErrors++;
            console.error("❌ Polling error:", error);

            // Slow down polling if too many errors
            if (this.consecutiveErrors >= this.maxConsecutiveErrors) {
                console.warn("⚠️ Too many polling errors, slowing down interval");
                this.startPolling("slowest");
            }
        }
    }

    /**
     * Adjust polling interval based on server performance and activity
     */
    private adjustPollingInterval(responseTime: number, stats: QueueStats): void {
        let newMode: keyof PollingConfig = "normal";

        // Fast polling during active processing
        if (stats.processing > 0 || stats.pending > 0) {
            newMode = "fast";
        }
        // Slow polling when server is slow or idle
        else if (responseTime > 2000) {
            newMode = "slow";
        }
        // Very slow polling when completely idle
        else if (stats.processing === 0 && stats.pending === 0 && Date.now() - this.lastUpdateTime > 60000) {
            newMode = "slowest";
        }

        // Update polling if mode changed
        const newInterval = this.adaptivePollingConfig[newMode];
        if (newInterval !== this.pollingInterval) {
            console.log(`📡 Adjusting polling: ${newMode} (${newInterval}ms)`);
            this.startPolling(newMode);
        }
    }

    /**
     * Handle page becoming hidden
     */
    private handlePageHidden(): void {
        console.log("📡 Page hidden, reducing update frequency");

        if (this.isPolling) {
            this.startPolling("slowest");
        }
    }

    /**
     * Handle page becoming visible
     */
    private handlePageVisible(): void {
        console.log("📡 Page visible, resuming normal updates");

        if (this.isPolling) {
            this.startPolling("normal");
        } else if (!this.isSSEEnabled && this.canUseSSE()) {
            // Try to re-establish SSE when page becomes active
            this.initializeSSE();
        }

        // Immediate update when page becomes visible
        if (this.isPolling) {
            this.pollQueueStatus();
        }
    }

    /**
     * Manually trigger queue status refresh
     */
    async refreshStatus(): Promise<void> {
        console.log("📡 Manual status refresh requested");

        try {
            const result = await APIService.getQueueStatus();

            if (result.success && result.stats) {
                this.dispatchEvent(
                    new CustomEvent("queueUpdate", {
                        detail: {
                            stats: result.stats,
                            source: "manual",
                        },
                    })
                );

                this.addStatusMessage("success", "🔄", "Status refreshed successfully");
            }
        } catch (error) {
            console.error("❌ Manual refresh failed:", error);
            this.addStatusMessage("error", "❌", "Failed to refresh status");
        }
    }

    /**
     * Reconnect to real-time updates
     */
    private reconnect(): void {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.warn("⚠️ Max reconnection attempts reached");
            return;
        }

        this.reconnectAttempts++;
        console.log(`📡 Reconnecting... (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);

        // Clean up existing connections
        this.disconnect();

        // Wait a moment then reinitialize
        setTimeout(() => {
            this.initializeConnection();
        }, 2000);
    }

    /**
     * Disconnect from real-time updates
     */
    disconnect(): void {
        // Close SSE connection
        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
        }

        // Stop polling
        this.stopPolling();

        // Update state
        this.isSSEEnabled = false;
        this.isConnected = false;
        this.isPolling = false;

        console.log("📡 Disconnected from real-time updates");
    }

    /**
     * Get connection status
     */
    getConnectionStatus(): any {
        return {
            isConnected: this.isConnected,
            connectionType: this.isSSEEnabled ? "sse" : this.isPolling ? "polling" : "none",
            isSSEEnabled: this.isSSEEnabled,
            isPolling: this.isPolling,
            pollingInterval: this.pollingInterval,
            sseRetryCount: this.sseRetryCount,
            consecutiveErrors: this.consecutiveErrors,
            lastUpdateTime: this.lastUpdateTime,
            timeSinceLastUpdate: Date.now() - this.lastUpdateTime,
        };
    }

    /**
     * Force reconnection with clean state
     */
    forceReconnect(): void {
        console.log("📡 Forcing reconnection...");

        this.sseRetryCount = 0;
        this.reconnectAttempts = 0;
        this.consecutiveErrors = 0;

        this.disconnect();

        setTimeout(() => {
            this.initializeConnection();
        }, 1000);
    }

    /**
     * Cleanup resources
     */
    cleanup(): void {
        this.disconnect();
        console.log("🧹 Realtime Service cleaned up");
    }

    // UI Update methods (emit events for components to handle)
    private addStatusMessage(type: string, icon: string, message: string): void {
        window.dispatchEvent(
            new CustomEvent("add-status-message", {
                detail: { type, icon, message },
            })
        );
    }
}

// Export singleton instance
export default new RealtimeService();
