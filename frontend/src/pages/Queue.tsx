import { useState, useEffect, useCallback, useRef } from "react";
import { Link } from "react-router-dom";
import Navigation from "../components/Navigation";
import { addStatusMessage } from "../utils/statusMessages";
import APIService from "../services/APIService";
import RealtimeService from "../services/RealtimeService";
import type { Job } from "../types/job";
import type { QueueStats } from "../types/queue";

export default function Queue() {
    const [jobs, setJobs] = useState<Job[]>([]);
    const [queueStats, setQueueStats] = useState<QueueStats>({
        pending: 0,
        processing: 0,
        rendering: 0,
        completed: 0,
        failed: 0,
        activeWorkers: 0,
        availableWorkers: 3,
        concurrentProcessing: true,
    });
    const [currentFilter, setCurrentFilter] = useState<string>("all");
    const [searchQuery, setSearchQuery] = useState<string>("");
    const [connectionStatus, setConnectionStatus] = useState<"connected" | "disconnected" | "warning">("connected");

    // Request deduplication - prevent multiple simultaneous API calls
    const [isLoadingData, setIsLoadingData] = useState(false);

    // Throttle SSE updates to prevent spam
    const lastUpdateTime = useRef<number>(0);
    const UPDATE_THROTTLE_MS = 1000; // 1 second minimum between updates
    const [isLoading, setIsLoading] = useState(true);
    const [isQueueProcessing, setIsQueueProcessing] = useState(true);

    // Load queue data with deduplication
    const loadQueueData = useCallback(async () => {
        // Prevent multiple simultaneous API calls
        if (isLoadingData) {
            console.log("📋 Skipping duplicate loadQueueData call");
            return;
        }

        setIsLoadingData(true);
        try {
            console.log("📋 Loading queue data...");

            // Load all jobs first
            const jobsResponse = await APIService.getAllJobs();
            if (jobsResponse.success && Array.isArray(jobsResponse.jobs)) {
                const allJobs = jobsResponse.jobs as Job[];
                setJobs(allJobs);

                // Calculate statistics from actual jobs data
                const calculatedStats = {
                    pending: allJobs.filter((job: Job) => job.status === "pending").length,
                    processing: allJobs.filter((job: Job) => job.status === "processing" || job.status === "active").length,
                    rendering: allJobs.filter((job: Job) => job.status === "rendering").length,
                    completed: allJobs.filter((job: Job) => job.status === "completed").length,
                    failed: allJobs.filter((job: Job) => job.status === "failed" || job.status === "cancelled").length,
                    activeWorkers: 0,
                    availableWorkers: 3,
                    concurrentProcessing: true,
                };

                setQueueStats(calculatedStats);

                // 🔧 AUTO-DETECT: Check for potential sync issues
                const oldFailedCount = queueStats.failed;
                const newFailedCount = calculatedStats.failed;

                if (newFailedCount > oldFailedCount) {
                    addStatusMessage("warning", "⚠️", `${newFailedCount - oldFailedCount} new failed job(s) detected`);
                }

                // Check if queue is processing (infer from stats)
                const hasPendingJobs = calculatedStats.pending > 0;
                const hasProcessingJobs = calculatedStats.processing > 0;

                // If there are pending jobs but no processing jobs, queue might be stopped
                setIsQueueProcessing(!(hasPendingJobs && !hasProcessingJobs));
            }

            // Also try to load queue statistics from API (as backup)
            try {
                const statsResponse = await APIService.getQueueStatus();
                if (statsResponse.success && statsResponse.stats && typeof statsResponse.stats === "object") {
                    const stats = statsResponse.stats as { activeWorkers?: number; availableWorkers?: number; concurrentProcessing?: boolean };
                    // Merge API stats with calculated stats, preferring calculated for accuracy
                    setQueueStats((prev) => ({
                        ...prev,
                        activeWorkers: stats.activeWorkers || prev.activeWorkers,
                        availableWorkers: stats.availableWorkers || prev.availableWorkers,
                        concurrentProcessing: stats.concurrentProcessing ?? prev.concurrentProcessing,
                    }));
                }
            } catch {
                console.warn("📋 Could not load API stats, using calculated stats only");
            }

            console.log(`📋 Loaded ${Array.isArray(jobsResponse.jobs) ? jobsResponse.jobs.length : 0} jobs and calculated queue stats`);
        } catch (error) {
            console.error("📋 Failed to load queue data:", error);
            addStatusMessage("error", "❌", "Failed to load queue data");
        } finally {
            setIsLoading(false);
            setIsLoadingData(false); // Reset deduplication flag
        }
    }, [queueStats.failed, isLoadingData]);

    // Set page title and start auto-refresh
    useEffect(() => {
        document.title = "Queue Management - StreamGank Video Generator";

        // Auto-refresh every 30 seconds to catch failed jobs
        const autoRefreshInterval = setInterval(() => {
            loadQueueData();
        }, 30000); // 30 seconds

        return () => {
            clearInterval(autoRefreshInterval);
        };
    }, [loadQueueData]);

    // Initialize real-time updates
    useEffect(() => {
        // Load initial data
        loadQueueData();

        // Initialize realtime service
        RealtimeService.init();

        // Listen for queue updates - OPTIMIZED & THROTTLED VERSION
        const handleQueueUpdate = (event: CustomEvent) => {
            const now = Date.now();
            console.log("📊 Queue update received:", event.detail);

            if (event.detail.stats) {
                setQueueStats(event.detail.stats);
                console.log("📊 Queue stats updated from SSE");
            }

            // Only refresh jobs data if there's actual job changes AND enough time has passed
            if (event.detail.jobChanged || event.detail.source === "manual") {
                if (now - lastUpdateTime.current > UPDATE_THROTTLE_MS) {
                    console.log("🔄 Refreshing jobs data due to job changes");
                    lastUpdateTime.current = now;
                    loadQueueData();
                } else {
                    console.log("⏱️ Throttling job data refresh (too soon)");
                }
            }
        };

        const handleConnectionChange = (event: CustomEvent) => {
            setConnectionStatus(event.detail.type === "sse" ? "connected" : "warning");
        };

        const handleDisconnection = () => {
            setConnectionStatus("disconnected");
        };

        RealtimeService.addEventListener("queueUpdate", handleQueueUpdate as EventListener);
        RealtimeService.addEventListener("connected", handleConnectionChange as EventListener);
        RealtimeService.addEventListener("disconnected", handleDisconnection);

        return () => {
            RealtimeService.removeEventListener("queueUpdate", handleQueueUpdate as EventListener);
            RealtimeService.removeEventListener("connected", handleConnectionChange as EventListener);
            RealtimeService.removeEventListener("disconnected", handleDisconnection);
        };
    }, [loadQueueData]);

    // Filter jobs based on current filter and search
    const filteredJobs = jobs.filter((job) => {
        // Filter by status
        if (currentFilter !== "all" && job.status !== currentFilter) {
            return false;
        }

        // Filter by search query
        if (searchQuery) {
            const query = searchQuery.toLowerCase();
            const country = job.parameters?.country || job.country || "";
            const platform = job.parameters?.platform || job.platform || "";
            const genre = job.parameters?.genre || job.genre || "";
            const contentType = job.parameters?.contentType || job.contentType || "";

            return job.id.toLowerCase().includes(query) || country.toLowerCase().includes(query) || platform.toLowerCase().includes(query) || genre.toLowerCase().includes(query) || contentType.toLowerCase().includes(query);
        }

        return true;
    });

    const handleClearQueue = async () => {
        if (confirm("Are you sure you want to clear all completed and failed jobs?")) {
            try {
                const response = await APIService.clearQueue();
                if (response.success) {
                    addStatusMessage("success", "🧹", "Queue cleared successfully");
                    await loadQueueData();
                } else {
                    addStatusMessage("error", "❌", "Failed to clear queue");
                }
            } catch {
                addStatusMessage("error", "❌", "Failed to clear queue");
            }
        }
    };

    const handleToggleQueue = async () => {
        try {
            const response = await APIService.post("/api/queue/toggle");
            if (response.success) {
                const newStatus = response.data && typeof response.data === "object" && "isProcessing" in response.data ? (response.data as { isProcessing: boolean }).isProcessing : !isQueueProcessing;
                setIsQueueProcessing(newStatus);
                addStatusMessage("success", "⚡", `Queue processing ${newStatus ? "started" : "stopped"}`);
                await loadQueueData();
            }
        } catch {
            addStatusMessage("error", "❌", "Failed to toggle queue");
        }
    };

    const handleClearFailed = async () => {
        if (confirm("Clear all failed jobs?")) {
            try {
                const response = await APIService.post("/api/queue/clear-failed");
                if (response.success) {
                    addStatusMessage("success", "🧹", "Failed jobs cleared");
                    await loadQueueData();
                }
            } catch {
                addStatusMessage("error", "❌", "Failed to clear failed jobs");
            }
        }
    };

    // 🔧 NEW: Function to sync jobs with Docker/backend state
    const handleSyncJobs = async () => {
        try {
            addStatusMessage("info", "🔄", "Syncing jobs with Docker logs...");

            // Force a fresh load without cache
            const response = await APIService.post("/api/queue/cleanup");
            if (response.success) {
                addStatusMessage("success", "✅", "Job sync completed");
            }

            // Reload the queue data
            await loadQueueData();
        } catch {
            addStatusMessage("error", "❌", "Failed to sync jobs");
        }
    };

    const handleRetryJob = async (jobId: string) => {
        if (confirm("Retry this job?")) {
            try {
                const response = await APIService.retryJob(jobId);
                if (response.success) {
                    addStatusMessage("success", "🔄", "Job retry initiated");
                    await loadQueueData();
                }
            } catch {
                addStatusMessage("error", "❌", "Failed to retry job");
            }
        }
    };

    const handleCancelJob = async (jobId: string, jobStatus: string) => {
        const isPending = jobStatus === "pending";
        const confirmMessage = isPending ? "Cancel this pending job? It will be removed from the queue." : "Cancel this active job? The process will be stopped immediately.";

        if (confirm(confirmMessage)) {
            try {
                const response = await APIService.cancelJob(jobId);
                if (response.success) {
                    const message = isPending ? "Pending job removed from queue" : "Active job cancelled";
                    addStatusMessage("success", "⏹️", message);
                    await loadQueueData();
                }
            } catch {
                addStatusMessage("error", "❌", "Failed to cancel job");
            }
        }
    };

    const getStatusBadgeClass = (status: string) => {
        switch (status) {
            case "pending":
                return "process-status-badge pending";
            case "active":
            case "processing":
                return "process-status-badge processing";
            case "rendering":
                return "process-status-badge processing";
            case "completed":
                return "process-status-badge completed";
            case "failed":
                return "process-status-badge failed";
            case "cancelled":
                return "process-status-badge bg-gray-500 text-gray-200";
            default:
                return "process-status-badge bg-gray-500 text-gray-200";
        }
    };

    const formatDuration = (job: Job) => {
        if (!job.startedAt) return "--";

        const start = new Date(job.startedAt);
        const end = job.completedAt ? new Date(job.completedAt) : new Date();
        const duration = end.getTime() - start.getTime();

        const minutes = Math.floor(duration / 60000);
        const seconds = Math.floor((duration % 60000) / 1000);

        return minutes > 0 ? `${minutes}m ${seconds}s` : `${seconds}s`;
    };

    const totalQueueJobs = queueStats.pending + queueStats.processing;

    if (isLoading) {
        return (
            <div className="min-h-screen" style={{ backgroundColor: "var(--dark-bg)" }}>
                <Navigation queueCount={totalQueueJobs} connectionStatus={connectionStatus} />
                <div className="container-fluid pt-5">
                    <div className="text-center py-5">
                        <div className="spinner-border mb-3" style={{ color: "var(--primary-color)" }}>
                            <span className="sr-only">Loading...</span>
                        </div>
                        <p style={{ color: "var(--text-light)" }}>Loading queue data...</p>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen" style={{ backgroundColor: "var(--dark-bg)" }}>
            <Navigation queueCount={totalQueueJobs} connectionStatus={connectionStatus} onRefresh={loadQueueData} />

            <div className="container-fluid pt-5">
                {/* Header */}
                <div className="mb-4">
                    <h1 className="text-2xl font-bold mb-0 flex items-center" style={{ color: "var(--text-light)" }}>
                        <i className="fas fa-tasks mr-2"></i>
                        Queue Management
                    </h1>
                    <p className="mb-0" style={{ color: "var(--text-light)" }}>
                        Monitor and manage video generation jobs
                    </p>
                </div>

                {/* Queue Statistics */}
                <div className="grid grid-cols-5 gap-4 mb-6">
                    <div className="rounded-lg p-4 text-center border" style={{ backgroundColor: "var(--dark-panel)", borderColor: "var(--border-color)" }}>
                        <h6 className="font-semibold mb-2" style={{ color: "var(--text-light)" }}>
                            Pending
                            {!isQueueProcessing && queueStats.pending > 0 && (
                                <span className="ml-2 text-red-400" title="Queue processing is stopped">
                                    ⚠️
                                </span>
                            )}
                        </h6>
                        <div className="text-2xl font-bold text-yellow-400">{queueStats.pending || 0}</div>
                        {!isQueueProcessing && queueStats.pending > 0 && <div className="text-xs text-red-400 mt-1">Queue Stopped</div>}
                    </div>
                    <div className="rounded-lg p-4 text-center border" style={{ backgroundColor: "var(--dark-panel)", borderColor: "var(--border-color)" }}>
                        <h6 className="font-semibold mb-2" style={{ color: "var(--text-light)" }}>
                            Processing
                        </h6>
                        <div className="text-2xl font-bold text-blue-400">{queueStats.processing || 0}</div>
                    </div>
                    <div className="rounded-lg p-4 text-center border" style={{ backgroundColor: "var(--dark-panel)", borderColor: "var(--border-color)" }}>
                        <h6 className="font-semibold mb-2" style={{ color: "var(--text-light)" }}>
                            Rendering
                        </h6>
                        <div className="text-2xl font-bold text-purple-400">{queueStats.rendering || 0}</div>
                    </div>
                    <div className="rounded-lg p-4 text-center border" style={{ backgroundColor: "var(--dark-panel)", borderColor: "var(--border-color)" }}>
                        <h6 className="font-semibold mb-2" style={{ color: "var(--text-light)" }}>
                            Completed
                        </h6>
                        <div className="text-2xl font-bold text-green-400">{queueStats.completed || 0}</div>
                    </div>
                    <div className="rounded-lg p-4 text-center border" style={{ backgroundColor: "var(--dark-panel)", borderColor: "var(--border-color)" }}>
                        <h6 className="font-semibold mb-2" style={{ color: "var(--text-light)" }}>
                            Failed
                        </h6>
                        <div className="text-2xl font-bold text-red-400">{queueStats.failed || 0}</div>
                    </div>
                </div>

                {/* Queue Controls */}
                <div className="rounded-lg p-4 mb-6 border" style={{ backgroundColor: "var(--dark-panel)", borderColor: "var(--border-color)" }}>
                    <div className="flex justify-between items-center">
                        <div className="flex gap-2">
                            <div className="flex items-center gap-2">
                                <label className="text-sm" style={{ color: "var(--text-light)" }}>
                                    Filter:
                                </label>
                                <select value={currentFilter} onChange={(e) => setCurrentFilter(e.target.value)} className="form-select-custom">
                                    <option value="all">All Jobs</option>
                                    <option value="pending">Pending</option>
                                    <option value="processing">Processing</option>
                                    <option value="rendering">Rendering</option>
                                    <option value="completed">Completed</option>
                                    <option value="failed">Failed</option>
                                </select>
                            </div>
                            <div className="flex items-center gap-2">
                                <label className="text-sm" style={{ color: "var(--text-light)" }}>
                                    Search:
                                </label>
                                <input type="text" value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} placeholder="Job ID, platform, genre..." className="form-select-custom" />
                            </div>
                        </div>
                        <div className="flex gap-2">
                            <button onClick={loadQueueData} className="btn btn-outline-info btn-sm" title="Refresh job list from database">
                                <i className="fas fa-sync-alt mr-1"></i>
                                Refresh
                            </button>
                            <button onClick={handleSyncJobs} className="btn btn-outline-secondary btn-sm" title="Force sync with Docker logs and fix stuck jobs">
                                <i className="fas fa-tools mr-1"></i>
                                Sync Jobs
                            </button>
                            <button onClick={handleToggleQueue} className={`btn btn-sm ${isQueueProcessing ? "btn-outline-warning" : "btn-outline-success"}`} title={isQueueProcessing ? "Stop queue processing" : "Start queue processing"}>
                                <i className={`fas ${isQueueProcessing ? "fa-pause" : "fa-play"} mr-1`}></i>
                                {isQueueProcessing ? "Pause Queue" : "Start Queue"}
                            </button>
                            <button onClick={handleClearFailed} className="btn btn-outline-warning btn-sm">
                                <i className="fas fa-trash mr-1"></i>
                                Clear Failed
                            </button>
                            <button onClick={handleClearQueue} className="btn btn-outline-danger btn-sm">
                                <i className="fas fa-trash-alt mr-1"></i>
                                Clear Queue
                            </button>
                        </div>
                    </div>
                </div>

                {/* Jobs Table */}
                <div className="process-table-container">
                    <table className="process-table">
                        <thead>
                            <tr>
                                <th>Job ID</th>
                                <th>Status</th>
                                <th>Worker</th>
                                <th>Progress</th>
                                <th>Parameters</th>
                                <th>Started</th>
                                <th>Duration</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {filteredJobs.length === 0 ? (
                                <tr>
                                    <td colSpan={8} className="text-center py-8">
                                        <div className="empty-state">
                                            <div className="empty-icon">
                                                <i className="fas fa-inbox"></i>
                                            </div>
                                            <h6>No Jobs Found</h6>
                                            <p>{currentFilter === "all" ? "No jobs in the queue yet. Start by generating a video from the dashboard." : `No ${currentFilter} jobs found.`}</p>
                                        </div>
                                    </td>
                                </tr>
                            ) : (
                                filteredJobs.map((job) => (
                                    <tr key={job.id} className="hover:bg-white/5">
                                        <td>
                                            <span className="process-id">{job.id.slice(-8)}</span>
                                        </td>
                                        <td>
                                            <span className={getStatusBadgeClass(job.status)}>{job.status.charAt(0).toUpperCase() + job.status.slice(1)}</span>
                                        </td>
                                        <td>
                                            <span className="badge bg-info text-xs">{job.workerId ? job.workerId.slice(-4) : "--"}</span>
                                        </td>
                                        <td>
                                            <span className={`badge ${job.progress >= 100 ? "bg-success" : job.progress >= 50 ? "bg-warning" : "bg-secondary"}`}>{job.progress || 0}%</span>
                                        </td>
                                        <td>
                                            <div className="process-params">
                                                <div className="param-row">
                                                    <span className="param-flag">CTY</span>
                                                    <span className="param-value">{job.parameters?.country || job.country || "--"}</span>
                                                </div>
                                                <div className="param-row">
                                                    <span className="param-flag">PLT</span>
                                                    <span className="param-value">{job.parameters?.platform || job.platform || "--"}</span>
                                                </div>
                                                <div className="param-row">
                                                    <span className="param-flag">GNR</span>
                                                    <span className="param-value">{job.parameters?.genre || job.genre || "--"}</span>
                                                </div>
                                            </div>
                                        </td>
                                        <td>
                                            <span className="badge bg-light text-dark text-xs">{job.startedAt ? new Date(job.startedAt).toLocaleTimeString() : "--"}</span>
                                        </td>
                                        <td>
                                            <span className="badge bg-light text-dark text-xs">{formatDuration(job)}</span>
                                        </td>
                                        <td>
                                            <div className="process-actions-cell">
                                                <Link to={`/job/${job.id}`} className="process-action-btn view text-xs">
                                                    <i className="fas fa-eye"></i>
                                                    View
                                                </Link>
                                                {(job.status === "pending" || job.status === "active") && (
                                                    <button onClick={() => handleCancelJob(job.id, job.status)} className="process-action-btn cancel text-xs">
                                                        <i className="fas fa-stop"></i>
                                                        Cancel
                                                    </button>
                                                )}
                                                {job.status === "failed" && (
                                                    <button onClick={() => handleRetryJob(job.id)} className="process-action-btn text-xs" style={{ borderColor: "#3b82f6", color: "#60a5fa" }}>
                                                        <i className="fas fa-redo"></i>
                                                        Retry
                                                    </button>
                                                )}
                                            </div>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>

                {/* Queue Info Footer */}
                <div className="mt-6 rounded-lg p-4 border" style={{ backgroundColor: "var(--dark-panel)", borderColor: "var(--border-color)" }}>
                    <div className="flex justify-between items-center text-sm" style={{ color: "var(--text-secondary)" }}>
                        <div>
                            <strong style={{ color: "var(--text-light)" }}>{filteredJobs.length}</strong> jobs shown
                            {currentFilter !== "all" && ` (filtered by ${currentFilter})`}
                            {searchQuery && ` (search: "${searchQuery}")`}
                        </div>
                        <div>
                            Workers:{" "}
                            <strong style={{ color: "var(--text-light)" }}>
                                {queueStats.activeWorkers}/{queueStats.availableWorkers}
                            </strong>{" "}
                            active
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
