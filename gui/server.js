const express = require("express");
const { spawn } = require("child_process");
const path = require("path");
const VideoQueueManager = require("./queue-manager");

const app = express();
const port = process.env.PORT || 3000;

// Initialize Redis queue manager
const queueManager = new VideoQueueManager();

// Middleware for parsing JSON and serving static files
app.use(express.json());
app.use(express.static(path.join(__dirname)));

// Enable CORS
app.use((req, res, next) => {
    res.header("Access-Control-Allow-Origin", "*");
    res.header("Access-Control-Allow-Headers", "Origin, X-Requested-With, Content-Type, Accept");
    next();
});

// Route to serve the main HTML file
app.get("/", (req, res) => {
    res.sendFile(path.join(__dirname, "index.html"));
});

// Health check endpoint for Docker
app.get("/health", (req, res) => {
    res.status(200).json({
        status: "healthy",
        timestamp: new Date().toISOString(),
        service: "streamgank-gui",
    });
});

// Job detail page route
app.get("/job/:jobId", (req, res) => {
    res.sendFile(path.join(__dirname, "job-detail.html"));
});

// Job detail API route (enhanced with more details)
app.get("/api/job/:jobId/details", async (req, res) => {
    try {
        const { jobId } = req.params;
        const job = await queueManager.getJob(jobId);

        if (!job) {
            return res.status(404).json({
                success: false,
                message: "Job not found",
            });
        }

        // Enhanced job details with additional metadata
        const enhancedJob = {
            ...job,
            duration: job.startedAt ? Date.now() - new Date(job.startedAt).getTime() : null,
            detailsUrl: `/job/${jobId}`,
            isActive: ["pending", "processing"].includes(job.status),
        };

        res.json({
            success: true,
            job: enhancedJob,
        });
    } catch (error) {
        console.error("❌ Failed to get job details:", error);
        res.status(500).json({
            success: false,
            message: "Failed to get job details",
            error: error.message,
        });
    }
});

// Job logs API route
app.get("/api/job/:jobId/logs", async (req, res) => {
    try {
        const { jobId } = req.params;
        const logs = queueManager.getJobLogs(jobId);

        res.json({
            success: true,
            logs: logs,
            count: logs.length,
        });
    } catch (error) {
        console.error("❌ Failed to get job logs:", error);
        res.status(500).json({
            success: false,
            message: "Failed to get job logs",
            error: error.message,
        });
    }
});

// Platform mapping to match frontend values to Python script expectations
const platformMapping = {
    amazon: "Prime",
    apple: "Apple TV+",
    disney: "Disney+",
    hulu: "Hulu",
    max: "Max",
    netflix: "Netflix",
    free: "Free",
};

// Content type mapping
const contentTypeMapping = {
    Film: "Film",
    Serie: "Série",
    all: "Film", // Default to Film for 'all' option
};

// Helper function to execute Python script with async/await
async function executePythonScript(args, cwd = path.join(__dirname, ".."), timeoutMs = 30 * 60 * 1000) {
    return new Promise((resolve, reject) => {
        // Executing command (same as CLI)

        const pythonProcess = spawn("python", args, {
            cwd: cwd,
            env: {
                ...process.env,
                PYTHONIOENCODING: "utf-8",
                PYTHONUNBUFFERED: "1",
            },
        });

        let stdout = "";
        let stderr = "";
        let isResolved = false;

        // Set up timeout (30 minutes default)
        const timeout = setTimeout(() => {
            if (!isResolved) {
                isResolved = true;
                pythonProcess.kill("SIGTERM");
                reject({
                    code: -2,
                    error: "Python script execution timeout",
                    stdout,
                    stderr,
                });
            }
        }, timeoutMs);

        // Handle stdout data
        pythonProcess.stdout.on("data", (data) => {
            try {
                const output = data.toString("utf8");
                stdout += output;
                // Output exactly like CLI - no prefixes
                process.stdout.write(output);
            } catch (encodingError) {
                console.warn("Encoding error in stdout:", encodingError.message);
                const output = data.toString("latin1"); // Fallback encoding
                stdout += output;
                process.stdout.write(output);
            }
        });

        // Handle stderr data
        pythonProcess.stderr.on("data", (data) => {
            try {
                const output = data.toString("utf8");
                stderr += output;
                // Output exactly like CLI - no prefixes
                process.stderr.write(output);
            } catch (encodingError) {
                console.warn("Encoding error in stderr:", encodingError.message);
                const output = data.toString("latin1"); // Fallback encoding
                stderr += output;
                process.stderr.write(output);
            }
        });

        // Handle process completion
        pythonProcess.on("close", (code) => {
            if (!isResolved) {
                isResolved = true;
                clearTimeout(timeout);
                // Process completed (code logged internally only if needed)

                if (code !== 0) {
                    reject({
                        code,
                        error: stderr || "Python script failed with no error message",
                        stdout,
                    });
                } else {
                    resolve({
                        code,
                        stdout,
                        stderr,
                    });
                }
            }
        });

        // Handle process errors
        pythonProcess.on("error", (error) => {
            if (!isResolved) {
                isResolved = true;
                clearTimeout(timeout);
                console.error("Failed to start Python process:", error);
                reject({
                    code: -1,
                    error: error.message,
                    stdout: "",
                    stderr: "",
                });
            }
        });
    });
}

// API endpoint to add video to Redis queue
app.post("/api/generate", async (req, res) => {
    try {
        const { country, platform, genre, contentType, template, pauseAfterExtraction } = req.body;

        console.log("📨 Received queue request:", { country, platform, genre, contentType, template, pauseAfterExtraction });

        if (!country || !platform || !genre || !contentType) {
            return res.status(400).json({
                success: false,
                message: "Missing required parameters",
                received: { country, platform, genre, contentType, template },
            });
        }

        // Map platform and content type to match Python script expectations
        const mappedPlatform = platformMapping[platform] || platform;
        const mappedContentType = contentTypeMapping[contentType] || contentType;

        console.log("🔄 Mapped values:", {
            country,
            platform: mappedPlatform,
            genre,
            contentType: mappedContentType,
            template: template || "auto", // Default to 'auto' if not provided
            pauseAfterExtraction: pauseAfterExtraction || false,
        });

        // Add job to Redis queue
        const job = await queueManager.addJob({
            country,
            platform: mappedPlatform,
            genre,
            contentType: mappedContentType,
            template: template || "auto", // Include template parameter
            pauseAfterExtraction: pauseAfterExtraction || false, // Include pause flag
        });

        // Get current queue status
        const queueStatus = await queueManager.getQueueStatus();

        // Return job info and queue status
        res.json({
            success: true,
            jobId: job.id,
            message: "Video added to queue successfully",
            queuePosition: queueStatus.pending + queueStatus.processing,
            queueStatus: queueStatus,
            job: job,
        });
    } catch (error) {
        console.error("❌ Failed to add job to queue:", error);

        res.status(500).json({
            success: false,
            message: "Failed to add video to queue",
            error: error.message,
        });
    }
});

// API endpoint to check Creatomate status
app.get("/api/status/:creatomateId", async (req, res) => {
    try {
        const { creatomateId } = req.params;

        const scriptPath = path.join(__dirname, "../main.py");
        const args = [scriptPath, "--check-creatomate", creatomateId];

        // Execute Python script with async/await
        const result = await executePythonScript(args);
        const { stdout } = result;

        // Parse status from output
        let status = "unknown";
        let videoUrl = "";

        const statusMatch = stdout.match(/Render Status[:\s]+(\w+)/i);
        if (statusMatch && statusMatch[1]) {
            status = statusMatch[1];
        }

        const urlMatch = stdout.match(/Video URL[:\s]+(https:\/\/[^\s\n]+)/i);
        if (urlMatch && urlMatch[1]) {
            videoUrl = urlMatch[1];
        }

        res.json({
            success: true,
            status: status,
            videoUrl: videoUrl,
            creatomateId: creatomateId,
        });
    } catch (error) {
        console.error("Status check failed:", error);

        res.status(500).json({
            success: false,
            message: "Failed to check status",
            error: error.error || error.message,
        });
    }
});

// API endpoint to test Python script and database connection
app.get("/api/test", async (req, res) => {
    try {
        console.log("Testing Python script and database connection...");

        const scriptPath = path.join(__dirname, "../main.py");
        const args = [scriptPath, "--country", "FR", "--platform", "Netflix", "--genre", "Horror", "--content-type", "Film"];

        // Execute with shorter timeout for testing
        const result = await executePythonScript(args, path.join(__dirname, ".."), 5 * 60 * 1000);

        res.json({
            success: true,
            message: "Python script test completed",
            hasOutput: result.stdout.length > 0,
            outputLength: result.stdout.length,
            preview: result.stdout.substring(0, 500) + (result.stdout.length > 500 ? "..." : ""),
        });
    } catch (error) {
        console.error("Python script test failed:", error);

        res.json({
            success: false,
            message: "Python script test failed",
            error: error.error || error.message,
            code: error.code,
            stdout: error.stdout ? error.stdout.substring(0, 500) : "",
            stderr: error.stderr ? error.stderr.substring(0, 500) : "",
        });
    }
});

// API endpoint to get job status by ID
app.get("/api/job/:jobId", async (req, res) => {
    try {
        const { jobId } = req.params;
        const job = await queueManager.getJob(jobId);

        if (!job) {
            return res.status(404).json({
                success: false,
                message: "Job not found",
            });
        }

        res.json({
            success: true,
            job: job,
        });
    } catch (error) {
        console.error("❌ Failed to get job:", error);
        res.status(500).json({
            success: false,
            message: "Failed to get job status",
            error: error.message,
        });
    }
});

// API endpoint to get queue status
app.get("/api/queue/status", async (req, res) => {
    try {
        // Optimized for performance - removed expensive cleanup operations
        // Cleanup now runs periodically in background every 5 minutes
        const stats = await queueManager.getQueueStats();
        res.json({
            success: true,
            stats: stats,
        });
    } catch (error) {
        console.error("❌ Failed to get queue status:", error);
        res.status(500).json({
            success: false,
            message: "Failed to get queue status",
            error: error.message,
        });
    }
});

// API endpoint to get all jobs
app.get("/api/queue/jobs", async (req, res) => {
    try {
        const jobs = await queueManager.getAllJobs();
        res.json({
            success: true,
            jobs: jobs,
        });
    } catch (error) {
        console.error("❌ Failed to get all jobs:", error);
        res.status(500).json({
            success: false,
            message: "Failed to get jobs",
            error: error.message,
        });
    }
});

// API endpoint to clear queue (admin only)
app.post("/api/queue/clear", async (req, res) => {
    try {
        await queueManager.clearAllQueues();
        res.json({
            success: true,
            message: "All queues cleared successfully",
        });
    } catch (error) {
        console.error("❌ Failed to clear queues:", error);
        res.status(500).json({
            success: false,
            message: "Failed to clear queues",
            error: error.message,
        });
    }
});

// API endpoint to clean up stuck processing jobs
app.post("/api/queue/cleanup", async (req, res) => {
    try {
        await queueManager.cleanupProcessingQueue();
        res.json({
            success: true,
            message: "Processing queue cleaned up successfully",
        });
    } catch (error) {
        console.error("❌ Failed to cleanup processing queue:", error);
        res.status(500).json({
            success: false,
            message: "Failed to cleanup processing queue",
            error: error.message,
        });
    }
});

// API endpoint to update job with video URL after Creatomate completion
app.post("/api/job/:jobId/complete", async (req, res) => {
    try {
        const { jobId } = req.params;
        const { videoUrl } = req.body;

        if (!videoUrl) {
            return res.status(400).json({
                success: false,
                message: "Video URL is required",
            });
        }

        const job = await queueManager.getJob(jobId);
        if (!job) {
            return res.status(404).json({
                success: false,
                message: "Job not found",
            });
        }

        // Update job with final video URL
        job.videoUrl = videoUrl;
        job.progress = 100;
        job.completedAt = new Date().toISOString();
        job.currentStep = "Video rendering completed!";

        await queueManager.updateJob(job);

        res.json({
            success: true,
            message: "Job updated with video URL",
            job: job,
        });
    } catch (error) {
        console.error("❌ Failed to update job:", error);
        res.status(500).json({
            success: false,
            message: "Failed to update job",
            error: error.message,
        });
    }
});

// API endpoint to cancel a job
app.post("/api/job/:jobId/cancel", async (req, res) => {
    try {
        const { jobId } = req.params;
        console.log(`🛑 Cancelling job: ${jobId}`);

        // Use the queue manager's cancelJob method which handles process killing
        const job = await queueManager.cancelJob(jobId);

        res.json({
            success: true,
            message: "Job cancelled successfully",
            job: job,
        });
    } catch (error) {
        console.error("❌ Failed to cancel job:", error);
        res.status(500).json({
            success: false,
            message: "Failed to cancel job",
            error: error.message,
        });
    }
});

// API endpoint to get available platforms by region from database
app.get("/api/platforms/:country", async (req, res) => {
    try {
        const { country } = req.params;
        console.log(`🌍 Fetching platforms for country: ${country}`);

        // Use the exact platform data provided by the user
        const availablePlatforms = {
            FR: ["Prime", "Apple TV+", "Disney+", "Max", "Netflix", "Free"],
            US: ["Prime", "Apple TV+", "Disney+", "Hulu", "Max", "Netflix", "Free"],
        };

        const platforms = availablePlatforms[country] || availablePlatforms["US"]; // Default to US if country not found

        console.log(`✅ Found ${platforms.length} platforms for ${country}:`, platforms);

        res.json({
            success: true,
            country: country,
            platforms: platforms,
            source: "user_defined",
            count: platforms.length,
        });
    } catch (error) {
        console.error("❌ Error fetching platforms:", error);
        res.status(500).json({
            success: false,
            message: "Failed to fetch platforms",
            error: error.message,
        });
    }
});

// API endpoint to get available genres by region
app.get("/api/genres/:country", async (req, res) => {
    try {
        const { country } = req.params;
        console.log(`🎭 Fetching genres for country: ${country}`);

        // Use the exact genre data for the system - Updated to match StreamGank
        const availableGenres = {
            FR: [
                "Action & Aventure",
                "Animation",
                "Comédie",
                "Comédie Romantique",
                "Crime & Thriller",
                "Documentaire",
                "Drame",
                "Fantastique",
                "Film de guerre",
                "Histoire",
                "Horreur",
                "Musique & Comédie Musicale",
                "Mystère & Thriller",
                "Pour enfants",
                "Reality TV",
                "Réalisé en Europe",
                "Science-Fiction",
                "Sport & Fitness",
                "Western",
            ],
            US: ["Action & Adventure", "Animation", "Comedy", "Crime", "Documentary", "Drama", "Fantasy", "History", "Horror", "Kids & Family", "Made in Europe", "Music & Musical", "Mystery & Thriller", "Reality TV", "Romance", "Science-Fiction", "Sport", "War & Military", "Western"],
        };

        const genres = availableGenres[country] || availableGenres["US"];

        console.log(`✅ Found ${genres.length} genres for ${country}:`, genres);

        res.json({
            success: true,
            country: country,
            genres: genres,
            source: "user_defined",
            count: genres.length,
        });
    } catch (error) {
        console.error("❌ Error fetching genres:", error);
        res.status(500).json({
            success: false,
            message: "Failed to fetch genres",
            error: error.message,
        });
    }
});

// API endpoint to validate StreamGank URL
app.post("/api/validate-url", async (req, res) => {
    try {
        const { url } = req.body;

        if (!url) {
            return res.status(400).json({
                success: false,
                message: "URL is required",
            });
        }

        console.log(`🔍 Validating URL: ${url}`);

        // Use node's built-in fetch or a library like axios to check the URL
        const https = require("https");
        const http = require("http");
        const urlParsed = new URL(url);

        const client = urlParsed.protocol === "https:" ? https : http;

        const validation = await new Promise((resolve, reject) => {
            const request = client.get(
                url,
                {
                    headers: {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                    },
                    timeout: 10000,
                },
                (response) => {
                    let data = "";

                    response.on("data", (chunk) => {
                        data += chunk;
                    });

                    response.on("end", () => {
                        // Simplified validation - check basic HTTP response success
                        console.log(`🔍 Simplified validation for: ${url} - Status Code: ${response.statusCode}`);

                        // Log first 200 characters of content for debugging
                        console.log(`📄 First 200 chars of page content: ${data.substring(0, 200)}`);

                        // Always return valid=true since no movies validation is removed
                        resolve({
                            valid: true,
                            reason: "URL validation passed - no movies check removed",
                            details: `Page loaded successfully with ${data.length} bytes of content`,
                        });
                    });
                }
            );

            request.on("error", (error) => {
                console.error("Validation request error:", error);
                reject(error);
            });

            request.on("timeout", () => {
                request.destroy();
                reject(new Error("Request timeout"));
            });
        });

        console.log(`✅ Validation result: ${validation.valid ? "Valid" : "Invalid"} - ${validation.reason}`);

        res.json({
            success: true,
            ...validation,
        });
    } catch (error) {
        console.error("❌ Error validating URL:", error);

        // If validation fails, return valid=true to continue (fail-safe approach)
        res.json({
            success: true,
            valid: true,
            reason: "Validation failed, proceeding anyway",
            details: `Validation error: ${error.message}`,
        });
    }
});

// Initialize Redis connection and start server
async function startServer() {
    try {
        // Connect to Redis
        await queueManager.connect();
        console.log("🔗 Redis queue manager connected");

        // Start the server
        app.listen(port, '0.0.0.0', () => {
            console.log(`🚀 StreamGank Video Generator GUI server running at http://0.0.0.0:${port}`);
            console.log(`📋 Redis queue system active`);
            console.log(`🗂️ Platform mappings loaded: ${Object.keys(platformMapping).length} platforms`);
            console.log(`📝 Content type mappings: ${Object.keys(contentTypeMapping).join(", ")}`);
        });
    } catch (error) {
        console.error("❌ Failed to start server:", error);
        process.exit(1);
    }
}

// Handle graceful shutdown
process.on("SIGINT", async () => {
    console.log("\n🛑 Shutting down server...");
    await queueManager.close();
    process.exit(0);
});

process.on("SIGTERM", async () => {
    console.log("\n🛑 Shutting down server...");
    await queueManager.close();
    process.exit(0);
});

// Start the server
startServer();
