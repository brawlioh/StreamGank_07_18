/**
 * Netlify Function: Job Status
 * Handles job-related operations (demo responses without Redis)
 */

const headers = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Content-Type": "application/json",
};

exports.handler = async (event, context) => {
    // Handle CORS preflight
    if (event.httpMethod === "OPTIONS") {
        return {
            statusCode: 200,
            headers,
            body: "",
        };
    }

    try {
        // Extract job ID and action from path
        const pathSegments = event.path.split("/");
        const jobId = pathSegments[pathSegments.length - 2] || pathSegments[pathSegments.length - 1];
        const action = pathSegments[pathSegments.length - 1];

        console.log(`📋 Job request - ID: ${jobId}, Action: ${action}, Method: ${event.httpMethod}`);

        if (event.httpMethod === "GET") {
            // Get job status
            return {
                statusCode: 200,
                headers,
                body: JSON.stringify({
                    success: true,
                    job: {
                        id: jobId,
                        status: "completed",
                        progress: 100,
                        currentStep: "Demo job completed",
                        createdAt: new Date().toISOString(),
                        completedAt: new Date().toISOString(),
                        videoUrl: "",
                        note: "This is a demo response - backend integration required for real job tracking",
                    },
                }),
            };
        }

        if (event.httpMethod === "POST") {
            if (action === "cancel") {
                // Cancel job
                return {
                    statusCode: 200,
                    headers,
                    body: JSON.stringify({
                        success: true,
                        message: "Job cancellation request received",
                        job: {
                            id: jobId,
                            status: "cancelled",
                            note: "This is a demo response - backend integration required for real job cancellation",
                        },
                    }),
                };
            }

            if (action === "complete") {
                // Complete job
                const { videoUrl } = JSON.parse(event.body || "{}");

                return {
                    statusCode: 200,
                    headers,
                    body: JSON.stringify({
                        success: true,
                        message: "Job completion request received",
                        job: {
                            id: jobId,
                            status: "completed",
                            videoUrl: videoUrl || "",
                            completedAt: new Date().toISOString(),
                            note: "This is a demo response - backend integration required for real job completion",
                        },
                    }),
                };
            }
        }

        return {
            statusCode: 400,
            headers,
            body: JSON.stringify({
                success: false,
                message: "Invalid job operation",
            }),
        };
    } catch (error) {
        console.error("❌ Error in job function:", error);

        return {
            statusCode: 500,
            headers,
            body: JSON.stringify({
                success: false,
                message: "Failed to process job request",
                error: error.message,
            }),
        };
    }
};
