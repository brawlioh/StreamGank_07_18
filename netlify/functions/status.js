/**
 * Netlify Function: Check Job Status
 * Checks the status of a video generation job
 */

const headers = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "GET, OPTIONS",
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

    if (event.httpMethod !== "GET") {
        return {
            statusCode: 405,
            headers,
            body: JSON.stringify({ error: "Method not allowed" }),
        };
    }

    try {
        // Extract creatomate ID from path parameters
        const pathSegments = event.path.split("/");
        const creatomateId = pathSegments[pathSegments.length - 1];

        console.log(`🔍 Checking status for Creatomate ID: ${creatomateId}`);

        // TODO: Integrate with actual Creatomate API or your backend service
        // For now, return a simulated response

        // Simulate different status responses based on ID pattern
        let status = "processing";
        let videoUrl = "";

        if (creatomateId.includes("complete")) {
            status = "succeeded";
            videoUrl = `https://cdn.creatomate.com/renders/${creatomateId}.mp4`;
        } else if (creatomateId.includes("failed")) {
            status = "failed";
        }

        return {
            statusCode: 200,
            headers,
            body: JSON.stringify({
                success: true,
                status: status,
                videoUrl: videoUrl,
                creatomateId: creatomateId,
                note: "This is a demo response - backend integration required",
            }),
        };
    } catch (error) {
        console.error("❌ Error checking status:", error);

        return {
            statusCode: 500,
            headers,
            body: JSON.stringify({
                success: false,
                message: "Failed to check status",
                error: error.message,
            }),
        };
    }
};
