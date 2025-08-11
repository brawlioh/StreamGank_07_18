/**
 * Netlify Function: Validate URL
 * Validates StreamGank URLs (simplified version for Netlify)
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
        const { url } = JSON.parse(event.body);

        if (!url) {
            return {
                statusCode: 400,
                headers,
                body: JSON.stringify({
                    success: false,
                    message: "URL is required",
                }),
            };
        }

        console.log(`🔍 Validating URL: ${url}`);

        // For Netlify deployment, we'll do a simple validation
        // In a full implementation, this would check the actual StreamGank site
        const isStreamGankUrl = url.includes("streamgank.com");

        return {
            statusCode: 200,
            headers,
            body: JSON.stringify({
                success: true,
                valid: true, // Always return true for demo purposes
                reason: isStreamGankUrl ? "StreamGank URL detected" : "URL validation passed (simplified)",
                details: `URL validation completed for: ${url}`,
                note: "This is a simplified validation for Netlify deployment",
            }),
        };
    } catch (error) {
        console.error("❌ Error validating URL:", error);

        return {
            statusCode: 500,
            headers,
            body: JSON.stringify({
                success: false,
                message: "Failed to validate URL",
                error: error.message,
            }),
        };
    }
};
