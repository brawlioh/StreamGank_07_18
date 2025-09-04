import { useState, useEffect, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import Navigation from "../components/Navigation";
import { addStatusMessage } from "../utils/statusMessages";
import APIService from "../services/APIService";
import type { Job } from "../types/job";

interface LogEntry {
    event_type: string;
    details?: {
        step_number: number;
        status: string;
        [key: string]: unknown;
    };
}

interface SSEMessage {
    job_id: string;
    type: string;
    step_number?: number;
    step_name?: string;
    status?: string;
    job_status?: string;
    progress?: number;
    currentStep?: string;
    failed?: boolean;
    error?: string;
    validated?: boolean;
    details?: {
        creatomate_id?: string;
        [key: string]: unknown;
    };
    videoUrl?: string;
    timestamp?: string;
}

interface ProcessStep {
    id: string;
    name: string;
    description: string;
}

export default function JobDetail() {
    const { jobId } = useParams<{ jobId: string }>();

    const [jobData, setJobData] = useState<Job | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [currentActiveStep, setCurrentActiveStep] = useState<number | null>(null);
    const [jobSSE, setJobSSE] = useState<EventSource | null>(null);

    // Timeline steps for video generation process
    const processSteps: ProcessStep[] = [
        { id: "database_extraction", name: "Database Extraction", description: "Extracting movies from database" },
        { id: "script_generation", name: "Script Generation", description: "Generating AI scripts for content" },
        { id: "asset_preparation", name: "Asset Preparation", description: "Creating enhanced posters and movie clips" },
        { id: "heygen_creation", name: "HeyGen Video Creation", description: "Generating AI avatar videos" },
        { id: "heygen_processing", name: "HeyGen Processing", description: "Waiting for video completion" },
        { id: "scroll_generation", name: "Scroll Video Generation", description: "Creating StreamGank scroll overlay" },
        { id: "creatomate_assembly", name: "Creatomate Assembly", description: "Creating final video" },
    ];

    // Helper function to match current step text with process steps
    const getCurrentStepIndex = (currentStepText: string): number => {
        const stepText = currentStepText.toLowerCase();

        // Map current step text to process step indices
        if (stepText.includes("extract") || stepText.includes("movies") || stepText.includes("step 1")) {
            return 0; // Database Extraction
        } else if (stepText.includes("script") || stepText.includes("generating") || stepText.includes("step 2")) {
            return 1; // Script Generation
        } else if (stepText.includes("asset") || stepText.includes("poster") || stepText.includes("step 3")) {
            return 2; // Asset Preparation
        } else if (stepText.includes("heygen") && (stepText.includes("creat") || stepText.includes("step 4"))) {
            return 3; // HeyGen Video Creation
        } else if (stepText.includes("heygen") && (stepText.includes("process") || stepText.includes("wait") || stepText.includes("step 5"))) {
            return 4; // HeyGen Processing
        } else if (stepText.includes("scroll") || stepText.includes("overlay") || stepText.includes("step 6")) {
            return 5; // Scroll Video Generation
        } else if (stepText.includes("creatomate") || stepText.includes("final") || stepText.includes("step 7") || stepText.includes("render")) {
            return 6; // Creatomate Assembly
        }

        return -1; // No match found
    };

    // Set page title
    useEffect(() => {
        document.title = `Job ${jobId} - StreamGank Video Generator`;
    }, [jobId]);

    // Load current active step from persistent logs
    const loadCurrentActiveStepFromLogs = useCallback(async () => {
        try {
            const response = await fetch(`/api/queue/job/${jobId}/logs/persistent?limit=50`);
            if (!response.ok) return;

            const result = await response.json();
            if (!result.success || !result.data.logs) return;

            const logs = result.data.logs;
            let activeStep: number | null = null;
            const stepStatus: Record<number, string> = {};

            // Process logs to find current active step
            logs.forEach((log: LogEntry) => {
                if (log.event_type === "webhook_received" && log.details) {
                    const stepNumber = log.details.step_number;
                    const status = log.details.status;

                    if (stepNumber >= 1 && stepNumber <= 7) {
                        if (status === "started") {
                            stepStatus[stepNumber] = "started";
                            activeStep = stepNumber;
                        } else if (status === "completed") {
                            stepStatus[stepNumber] = "completed";
                            if (activeStep === stepNumber) {
                                activeStep = null;
                            }
                        }
                    }
                }
            });

            setCurrentActiveStep(activeStep);
        } catch (error) {
            console.error("❌ Error loading persistent logs:", error);
        }
    }, [jobId]);

    // Load job data
    const loadJobData = useCallback(async () => {
        if (!jobId) return;

        try {
            setIsLoading(true);
            console.log(`📡 Loading job data for: ${jobId}`);

            const response = await APIService.getJobStatus(jobId);

            if (!response.success || !response.job) {
                throw new Error("Job not found");
            }

            setJobData(response.job as Job);
            setError(null);

            // Load current active step from logs
            await loadCurrentActiveStepFromLogs();

            console.log("✅ Job data loaded successfully");
        } catch (err: unknown) {
            console.error("❌ Failed to load job data:", err);
            setError(err instanceof Error ? err.message : "Unknown error occurred");
        } finally {
            setIsLoading(false);
        }
    }, [jobId, loadCurrentActiveStepFromLogs]);

    // Handle job-specific SSE messages
    const handleJobSSEMessage = useCallback(
        (data: SSEMessage) => {
            if (data.job_id !== jobId) return;

            switch (data.type) {
                case "step_update":
                    if (!data.validated) break;

                    console.log(`📡 Real-time step update: Step ${data.step_number} ${data.status}`);

                    // 🚨 CRITICAL: Handle failure status immediately
                    if (data.failed || data.job_status === "failed" || data.status === "failed") {
                        console.log(`🚨 Job ${jobId} failed via SSE update:`, data.error);
                        addStatusMessage("error", "❌", `Job failed: ${data.error || "Workflow error"}`);

                        setJobData((prev) =>
                            prev
                                ? {
                                      ...prev,
                                      status: "failed",
                                      error: data.error || "Workflow failed",
                                      currentStep: data.currentStep || `❌ Failed at ${data.step_name}`,
                                      progress: data.progress || prev.progress,
                                  }
                                : null
                        );

                        // Clear active step on failure
                        setCurrentActiveStep(null);
                        return;
                    }

                    if (jobData) {
                        if (data.status === "started" && data.step_number) {
                            setCurrentActiveStep(data.step_number);
                            setJobData((prev) =>
                                prev
                                    ? {
                                          ...prev,
                                          currentStep: `Step ${data.step_number}/7: ${data.step_name} (Processing...)`,
                                          progress: data.progress || prev.progress,
                                      }
                                    : null
                            );
                        } else if (data.status === "completed") {
                            if (currentActiveStep === data.step_number) {
                                setCurrentActiveStep(null);
                            }
                            setJobData((prev) =>
                                prev
                                    ? {
                                          ...prev,
                                          currentStep: `Step ${data.step_number}/7: ${data.step_name} ✅`,
                                          progress: data.progress || prev.progress,
                                      }
                                    : null
                            );

                            // Handle step 7 completion
                            if (data.step_number === 7 && data.details?.creatomate_id) {
                                setJobData((prev) =>
                                    prev
                                        ? {
                                              ...prev,
                                              creatomateId: data.details!.creatomate_id,
                                          }
                                        : null
                                );
                            }
                        }
                    }
                    break;

                case "render_completed":
                    console.log("🎬 INSTANT: Creatomate render completed via webhook!", data);
                    if (jobData) {
                        setJobData((prev) =>
                            prev
                                ? {
                                      ...prev,
                                      status: "completed",
                                      progress: 100,
                                      currentStep: "🎉 Video rendering completed successfully!",
                                      videoUrl: data.videoUrl,
                                      completedAt: data.timestamp,
                                  }
                                : null
                        );
                    }
                    break;

                case "render_failed":
                    console.log("❌ INSTANT: Creatomate render failed via webhook!", data);
                    if (jobData) {
                        setJobData((prev) =>
                            prev
                                ? {
                                      ...prev,
                                      status: "failed",
                                      currentStep: `❌ Video rendering failed: ${data.error}`,
                                      error: data.error,
                                  }
                                : null
                        );
                    }
                    break;
            }
        },
        [jobId, jobData, currentActiveStep]
    );

    // Initialize job-specific SSE
    const initializeJobSSE = useCallback(() => {
        if (jobSSE || !jobId) return;

        console.log(`📡 Connecting to job-specific real-time updates for ${jobId}`);

        try {
            const eventSource = new EventSource(`/api/job/${jobId}/stream`);

            eventSource.onopen = () => {
                console.log(`📡 Real-time connection established for job ${jobId}`);
            };

            eventSource.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    handleJobSSEMessage(data);
                } catch (error) {
                    console.error("❌ Failed to parse job SSE message:", error);
                }
            };

            eventSource.onerror = () => {
                console.warn(`⚠️ Job SSE connection error for ${jobId}`);
                setTimeout(() => {
                    if (eventSource.readyState === EventSource.CLOSED) {
                        setJobSSE(null);
                        initializeJobSSE();
                    }
                }, 5000);
            };

            setJobSSE(eventSource);
        } catch (error) {
            console.error(`❌ Failed to initialize job SSE for ${jobId}:`, error);
        }
    }, [jobSSE, jobId, handleJobSSEMessage]);

    // Initialize page
    useEffect(() => {
        if (!jobId) {
            setError("Invalid job ID");
            return;
        }

        loadJobData();
        initializeJobSSE();

        // Cleanup on unmount
        return () => {
            if (jobSSE) {
                jobSSE.close();
            }
        };
    }, [jobId, loadJobData, initializeJobSSE, jobSSE]);

    const handleCancelJob = async () => {
        if (!jobData) return;

        // Different confirmation messages based on job status
        let confirmMessage = "Are you sure you want to cancel this job?";
        if (jobData.status === "processing") {
            confirmMessage = "⚠️ This job is currently processing. Stopping it may result in incomplete work. Are you sure you want to stop this job?";
        } else if (jobData.status === "failed") {
            confirmMessage = "Are you sure you want to remove this failed job from the queue?";
        }

        if (!confirm(confirmMessage)) return;

        try {
            const response = await APIService.cancelJob(jobData.id);
            if (response.success) {
                await loadJobData();
                const statusMessage = jobData.status === "processing" ? "Job stopped successfully" : jobData.status === "failed" ? "Job removed successfully" : "Job cancelled successfully";
                addStatusMessage("success", "⏹️", statusMessage);
            }
        } catch {
            addStatusMessage("error", "❌", "Failed to cancel job");
        }
    };

    const handleRetryJob = async () => {
        if (!jobData || !confirm("Are you sure you want to retry this job?")) return;

        try {
            const response = await APIService.retryJob(jobData.id);
            if (response.success) {
                await loadJobData();
                addStatusMessage("success", "🔄", "Job retry initiated");
            }
        } catch {
            addStatusMessage("error", "❌", "Failed to retry job");
        }
    };

    const checkCreatomateStatus = async () => {
        if (!jobData?.creatomateId) return;

        try {
            const response = await fetch(`/api/status/${jobData.creatomateId}`);
            const result = await response.json();

            if (result.success && result.status === "succeeded" && result.videoUrl) {
                setJobData((prev) =>
                    prev
                        ? {
                              ...prev,
                              videoUrl: result.videoUrl,
                              status: "completed",
                              progress: 100,
                          }
                        : null
                );
                addStatusMessage("success", "🎬", "Video is ready!");
            } else {
                addStatusMessage("info", "⏳", `Video status: ${result.status || "Unknown"}`);
            }
        } catch {
            addStatusMessage("error", "❌", "Failed to check video status");
        }
    };

    const getStatusBadgeClass = (status: string) => {
        switch (status) {
            case "pending":
                return "bg-yellow-500 text-black";
            case "active":
            case "processing":
                return "bg-blue-500 text-white";
            case "rendering":
                return "bg-purple-500 text-white";
            case "completed":
                return "bg-green-500 text-white";
            case "failed":
                return "bg-red-500 text-white";
            case "cancelled":
                return "bg-gray-500 text-white";
            default:
                return "bg-gray-500 text-white";
        }
    };

    const getStepIcon = (stepId: string, iconClass: string) => {
        if (iconClass === "completed") return "✓";
        if (iconClass === "failed") return "✗";
        if (iconClass === "active") return "⟳";

        const stepIcons: Record<string, string> = {
            database_extraction: "🗄️",
            script_generation: "📝",
            asset_preparation: "🎨",
            heygen_creation: "🤖",
            heygen_processing: "⏳",
            scroll_generation: "📱",
            creatomate_assembly: "🎬",
        };

        return stepIcons[stepId] || "○";
    };

    const getStepIconClass = (_step: ProcessStep, index: number) => {
        const currentProgress = jobData?.progress || 0;
        const currentStep = jobData?.currentStep || "";
        const currentStepIndex = getCurrentStepIndex(currentStep);

        // Special handling for completed jobs - all steps should be completed
        if (jobData?.status === "completed") {
            return "completed";
        }

        // If job is failed, show appropriate status based on where it failed
        if (jobData?.status === "failed") {
            if (currentStepIndex >= 0) {
                if (index < currentStepIndex) {
                    return "completed";
                } else if (index === currentStepIndex) {
                    return "failed";
                } else {
                    return "pending";
                }
            } else {
                // Fallback to progress-based calculation
                const expectedProgressForStep = ((index + 1) / processSteps.length) * 100;
                if (currentProgress > expectedProgressForStep) {
                    return "completed";
                } else if (currentProgress >= expectedProgressForStep - 100 / processSteps.length) {
                    return "failed";
                } else {
                    return "pending";
                }
            }
        }

        // For active/processing jobs, use current step matching
        if (currentStepIndex >= 0) {
            if (index < currentStepIndex) {
                return "completed";
            } else if (index === currentStepIndex) {
                return "active";
            } else {
                return "pending";
            }
        }

        // Fallback to progress-based calculation
        const stepProgressThreshold = ((index + 1) / processSteps.length) * 100;

        if (currentProgress >= stepProgressThreshold) {
            return "completed";
        } else if (currentProgress >= stepProgressThreshold - 100 / processSteps.length) {
            return "active";
        } else {
            return "pending";
        }
    };

    const calculateDuration = () => {
        if (!jobData?.startedAt) return "--";

        const start = new Date(jobData.startedAt);
        const end = jobData.completedAt ? new Date(jobData.completedAt) : new Date();
        const duration = end.getTime() - start.getTime();

        const minutes = Math.floor(duration / 60000);
        const seconds = Math.floor((duration % 60000) / 1000);

        return minutes > 0 ? `${minutes}m ${seconds}s` : `${seconds}s`;
    };

    if (isLoading) {
        return (
            <div className="min-h-screen" style={{ backgroundColor: "var(--dark-bg)" }}>
                <Navigation />
                <div className="container-fluid pt-5">
                    <div className="text-center py-5">
                        <div className="spinner-border mb-3" style={{ color: "var(--primary-color)" }}></div>
                        <p style={{ color: "var(--text-light)" }}>Loading job details...</p>
                    </div>
                </div>
            </div>
        );
    }

    if (error || !jobData) {
        return (
            <div className="min-h-screen" style={{ backgroundColor: "var(--dark-bg)" }}>
                <Navigation />
                <div className="container-fluid pt-5">
                    <div className="text-center py-5">
                        <i className="fas fa-exclamation-triangle fa-3x text-red-500 mb-3"></i>
                        <h3 className="mb-2" style={{ color: "var(--text-light)" }}>
                            Job Not Found
                        </h3>
                        <p className="mb-4" style={{ color: "var(--text-secondary)" }}>
                            {error || "The requested job could not be found."}
                        </p>
                        <Link to="/dashboard" className="btn btn-primary">
                            <i className="fas fa-home mr-2"></i>
                            Back to Dashboard
                        </Link>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen" style={{ backgroundColor: "var(--dark-bg)" }}>
            <Navigation />

            <div className="container-fluid pt-5">
                {/* Header */}
                <div className="flex justify-between items-center mb-6">
                    <div>
                        <h1 className="text-2xl font-bold mb-2 flex items-center" style={{ color: "var(--text-light)" }}>
                            <i className="fas fa-cog mr-2"></i>
                            Job Details
                            <span className={`badge ${getStatusBadgeClass(jobData.status)} ml-3 px-3 py-1`}>{jobData.status.charAt(0).toUpperCase() + jobData.status.slice(1)}</span>
                        </h1>
                        <p style={{ color: "var(--text-secondary)" }}>Job ID: {jobData.id}</p>
                    </div>
                    <div className="flex gap-2">
                        <button onClick={() => window.location.reload()} className="btn btn-outline-primary btn-sm">
                            <i className="fas fa-sync-alt mr-1"></i>
                            Refresh
                        </button>
                        <Link to="/queue" className="btn btn-outline-secondary btn-sm">
                            <i className="fas fa-arrow-left mr-1"></i>
                            Back to Queue
                        </Link>
                    </div>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {/* Left Column - Job Overview & Progress */}
                    <div>
                        {/* Job Overview */}
                        <div className="rounded-lg p-4 mb-6 border" style={{ backgroundColor: "var(--dark-panel)", borderColor: "var(--border-color)" }}>
                            <h3 className="text-lg font-semibold mb-3" style={{ color: "var(--text-light)" }}>
                                Job Overview
                            </h3>

                            {/* Progress Bar */}
                            <div className="mb-3">
                                <div className="flex justify-between items-center mb-1">
                                    <span className="text-xs" style={{ color: "var(--text-secondary)" }}>
                                        Progress
                                    </span>
                                    <span className="text-sm font-semibold" style={{ color: "var(--text-light)" }}>
                                        {jobData.progress || 0}%
                                    </span>
                                </div>
                                <div className="w-full bg-gray-700 rounded-full h-2">
                                    <div
                                        className={`h-2 rounded-full transition-all duration-300 ${jobData.progress >= 100 ? "bg-green-500" : jobData.progress >= 75 ? "bg-blue-500" : jobData.progress >= 50 ? "bg-yellow-500" : "bg-green-500"} ${
                                            jobData.progress < 100 && ["active", "processing", "rendering"].includes(jobData.status) ? "animate-pulse" : ""
                                        }`}
                                        style={{ width: `${jobData.progress || 0}%` }}
                                    ></div>
                                </div>
                            </div>

                            {/* Current Step */}
                            <div className="mb-3">
                                <span className="text-xs" style={{ color: "var(--text-secondary)" }}>
                                    Current Step
                                </span>
                                <p className="text-sm font-medium" style={{ color: "var(--text-light)" }}>
                                    {jobData.currentStep || "Initializing..."}
                                </p>
                            </div>

                            {/* Job Details - Compact Grid */}
                            <div className="grid grid-cols-3 gap-2 text-xs mb-3">
                                <div>
                                    <span style={{ color: "var(--text-secondary)" }}>Country:</span>
                                    <div className="font-medium text-green-400">{jobData.parameters?.country || jobData.country || "N/A"}</div>
                                </div>
                                <div>
                                    <span style={{ color: "var(--text-secondary)" }}>Platform:</span>
                                    <div className="font-medium text-green-400">{jobData.parameters?.platform || jobData.platform || "N/A"}</div>
                                </div>
                                <div>
                                    <span style={{ color: "var(--text-secondary)" }}>Genre:</span>
                                    <div className="font-medium text-green-400">{jobData.parameters?.genre || jobData.genre || "N/A"}</div>
                                </div>
                                <div>
                                    <span style={{ color: "var(--text-secondary)" }}>Type:</span>
                                    <div className="font-medium" style={{ color: "var(--text-light)" }}>
                                        {jobData.parameters?.contentType || jobData.contentType || "N/A"}
                                    </div>
                                </div>
                                <div>
                                    <span style={{ color: "var(--text-secondary)" }}>Template:</span>
                                    <div className="font-medium" style={{ color: "var(--text-light)" }}>
                                        {jobData.parameters?.template || jobData.template || "Default"}
                                    </div>
                                </div>
                                <div>
                                    <span style={{ color: "var(--text-secondary)" }}>Worker:</span>
                                    <div className="font-medium" style={{ color: "var(--text-light)" }}>
                                        {jobData.workerId?.slice(-4) || "N/A"}
                                    </div>
                                </div>
                            </div>

                            {/* Job Timestamps */}
                            <div className="grid grid-cols-2 gap-2 text-xs pt-2 border-t" style={{ borderColor: "var(--border-color)" }}>
                                <div>
                                    <span style={{ color: "var(--text-secondary)" }}>Started:</span>
                                    <div className="font-medium" style={{ color: "var(--text-light)" }}>
                                        {jobData.startedAt ? new Date(jobData.startedAt).toLocaleString() : "N/A"}
                                    </div>
                                </div>
                                <div>
                                    <span style={{ color: "var(--text-secondary)" }}>Completed:</span>
                                    <div className="font-medium" style={{ color: "var(--text-light)" }}>
                                        {jobData.completedAt ? new Date(jobData.completedAt).toLocaleString() : jobData.status === "completed" ? "Recently" : "N/A"}
                                    </div>
                                </div>
                                <div>
                                    <span style={{ color: "var(--text-secondary)" }}>Duration:</span>
                                    <div className="font-medium" style={{ color: "var(--text-light)" }}>
                                        {calculateDuration()}
                                    </div>
                                </div>
                                <div>
                                    <span style={{ color: "var(--text-secondary)" }}>Status:</span>
                                    <div className="font-medium text-green-400">{jobData.status.charAt(0).toUpperCase() + jobData.status.slice(1)}</div>
                                </div>
                            </div>

                            {/* Quick Actions */}
                            <div className="flex gap-2 mt-3 pt-2 border-t" style={{ borderColor: "var(--border-color)" }}>
                                {jobData.status !== "completed" && (
                                    <button onClick={handleCancelJob} className={`btn btn-sm flex-1 ${jobData.status === "processing" ? "btn-warning" : "btn-outline-warning"}`}>
                                        <i className={`fas ${jobData.status === "processing" ? "fa-hand-paper" : "fa-stop-circle"} mr-1`}></i>
                                        {jobData.status === "processing" ? "Stop Process" : jobData.status === "failed" ? "Remove Job" : "Cancel"}
                                    </button>
                                )}
                                {jobData.status === "failed" && (
                                    <button onClick={handleRetryJob} className="btn btn-outline-primary btn-sm flex-1">
                                        <i className="fas fa-redo mr-1"></i>
                                        Retry
                                    </button>
                                )}
                                {jobData.creatomateId && !jobData.videoUrl && (
                                    <button onClick={checkCreatomateStatus} className="btn btn-outline-info btn-sm flex-1">
                                        <i className="fas fa-video mr-1"></i>
                                        Check Status
                                    </button>
                                )}
                            </div>
                        </div>

                        {/* Video Result Section */}
                        {jobData.videoUrl ? (
                            <div className="rounded-lg p-4 border" style={{ backgroundColor: "var(--dark-panel)", borderColor: "var(--border-color)" }}>
                                <h3 className="text-lg font-semibold mb-4 text-green-400">
                                    <i className="fas fa-video mr-2"></i>
                                    Video Result
                                </h3>
                                <div className="mb-4">
                                    <video controls className="w-full rounded-lg" style={{ maxHeight: "300px" }}>
                                        <source src={jobData.videoUrl} type="video/mp4" />
                                        Your browser does not support the video tag.
                                    </video>
                                </div>
                                <div className="grid grid-cols-3 gap-2">
                                    <a href={jobData.videoUrl} target="_blank" rel="noopener noreferrer" className="btn btn-success btn-sm">
                                        <i className="fas fa-external-link-alt mr-1"></i>
                                        Open in New Tab
                                    </a>
                                    <a href={jobData.videoUrl} download className="btn btn-outline-light btn-sm">
                                        <i className="fas fa-download mr-1"></i>
                                        Download Video
                                    </a>
                                    <button onClick={() => navigator.clipboard.writeText(jobData.videoUrl!)} className="btn btn-outline-info btn-sm">
                                        <i className="fas fa-copy mr-1"></i>
                                        Copy URL
                                    </button>
                                </div>
                            </div>
                        ) : (
                            <div className="rounded-lg p-4 border border-dashed" style={{ backgroundColor: "var(--dark-panel)", borderColor: "var(--border-color)" }}>
                                <div className="text-center py-8">
                                    <div className="text-4xl mb-3">🎬</div>
                                    <h3 className="text-lg font-semibold mb-2" style={{ color: "var(--text-light)" }}>
                                        Video Processing
                                    </h3>
                                    <p className="text-sm mb-3" style={{ color: "var(--text-secondary)" }}>
                                        {jobData.status === "completed" ? "Video processing completed. Video will appear here when ready." : jobData.status === "failed" ? "Video generation failed. Check error details below." : "Your video is being processed. This may take several minutes."}
                                    </p>
                                    {jobData.progress < 100 && (
                                        <div className="inline-flex items-center text-green-400">
                                            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-green-400 mr-2"></div>
                                            Processing...
                                        </div>
                                    )}
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Right Column - Process Timeline */}
                    <div>
                        {/* Process Timeline */}
                        <div className="rounded-lg p-6 border" style={{ backgroundColor: "var(--dark-panel)", borderColor: "var(--border-color)" }}>
                            <h3 className="text-lg font-semibold mb-4" style={{ color: "var(--text-light)" }}>
                                Process Timeline
                            </h3>

                            <div className="space-y-4">
                                {processSteps.map((step, index) => {
                                    const iconClass = getStepIconClass(step, index);

                                    return (
                                        <div key={step.id} className={`timeline-step ${iconClass} flex items-center p-3 rounded-lg transition-all duration-200`}>
                                            <div
                                                className={`step-icon w-8 h-8 rounded-full flex items-center justify-center mr-4 text-lg ${
                                                    iconClass === "completed" ? "bg-green-500 text-white" : iconClass === "active" ? "bg-blue-500 text-white animate-pulse" : iconClass === "failed" ? "bg-red-500 text-white" : "bg-gray-600 text-gray-300"
                                                }`}
                                            >
                                                {getStepIcon(step.id, iconClass)}
                                            </div>
                                            <div className="flex-1">
                                                <div className="step-title font-medium" style={{ color: "var(--text-light)" }}>
                                                    {step.name}
                                                </div>
                                                <div className="step-description text-sm" style={{ color: "var(--text-secondary)" }}>
                                                    {step.description}
                                                </div>
                                            </div>
                                            <div
                                                className={`step-status text-xs px-2 py-1 rounded ${
                                                    iconClass === "completed" ? "bg-green-500/20 text-green-400" : iconClass === "active" ? "bg-blue-500/20 text-blue-400" : iconClass === "failed" ? "bg-red-500/20 text-red-400" : "bg-gray-500/20 text-gray-400"
                                                }`}
                                            >
                                                {iconClass === "pending" ? "Waiting..." : iconClass === "active" ? "In Progress" : iconClass === "completed" ? "Completed" : iconClass === "failed" ? "Failed" : "Unknown"}
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>

                        {/* Error Information */}
                        {jobData.status === "failed" && jobData.error && (
                            <div className="rounded-lg p-6 mt-6 border border-red-500" style={{ backgroundColor: "var(--dark-panel)" }}>
                                <h3 className="text-lg font-semibold text-red-400 mb-4">
                                    <i className="fas fa-bug mr-2"></i>
                                    Error Details
                                </h3>
                                <div className="bg-black/50 p-4 rounded border border-red-500/50">
                                    <code className="text-red-300 text-sm">{jobData.error}</code>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
