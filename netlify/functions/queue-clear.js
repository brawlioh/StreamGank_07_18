/**
 * Netlify Function: Clear Queue
 * Simulates clearing the queue (demo response without Redis)
 */

const headers = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
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

    if (event.httpMethod !== "POST") {
        return {
            statusCode: 405,
            headers,
            body: JSON.stringify({ error: "Method not allowed" }),
        };
    }

    try {
        console.log("🗑️ Queue clear request received");

        return {
            statusCode: 200,
            headers,
            body: JSON.stringify({
                success: true,
                message: "Queue clear request received",
                note: "This is a demo response - Redis integration required for real queue clearing",
            }),
        };
    } catch (error) {
        console.error("❌ Error clearing queue:", error);

        return {
            statusCode: 500,
            headers,
            body: JSON.stringify({
                success: false,
                message: "Failed to clear queue",
                error: error.message,
            }),
        };
    }
};
