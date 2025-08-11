/**
 * Netlify Function: Queue Status
 * Returns demo queue status (no Redis integration)
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
        // Return demo queue status since we don't have Redis
        const stats = {
            pending: 0,
            processing: 0,
            completed: 0,
            failed: 0,
        };

        console.log("📊 Returning demo queue status");

        return {
            statusCode: 200,
            headers,
            body: JSON.stringify({
                success: true,
                stats: stats,
                note: "Demo queue status - Redis integration required for real queue management",
            }),
        };
    } catch (error) {
        console.error("❌ Error getting queue status:", error);

        return {
            statusCode: 500,
            headers,
            body: JSON.stringify({
                success: false,
                message: "Failed to get queue status",
                error: error.message,
            }),
        };
    }
};
