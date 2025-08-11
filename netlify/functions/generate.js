/**
 * Netlify Function: Generate Video
 * Handles video generation requests from the frontend
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

    if (event.httpMethod !== "POST") {
        return {
            statusCode: 405,
            headers,
            body: JSON.stringify({ error: "Method not allowed" }),
        };
    }

    try {
        const { country, platform, genre, contentType, template, pauseAfterExtraction } = JSON.parse(event.body);

        console.log("📨 Received generation request:", { country, platform, genre, contentType, template, pauseAfterExtraction });

        if (!country || !platform || !genre || !contentType) {
            return {
                statusCode: 400,
                headers,
                body: JSON.stringify({
                    success: false,
                    message: "Missing required parameters",
                    received: { country, platform, genre, contentType, template },
                }),
            };
        }

        // Platform mapping to match Python script expectations
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

        const mappedPlatform = platformMapping[platform] || platform;
        const mappedContentType = contentTypeMapping[contentType] || contentType;

        // For Netlify deployment, we'll need to integrate with external services
        // This is a placeholder that would need to be connected to your backend infrastructure

        // Generate a unique job ID
        const jobId = `job_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

        console.log("🔄 Generated job ID:", jobId);
        console.log("🔄 Mapped values:", {
            country,
            platform: mappedPlatform,
            genre,
            contentType: mappedContentType,
            template: template || "auto",
            pauseAfterExtraction: pauseAfterExtraction || false,
        });

        // Call external Python backend API
        const backendUrl = process.env.BACKEND_API_URL || "http://localhost:8000";
        const response = await fetch(`${backendUrl}/generate`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                country,
                platform: mappedPlatform,
                genre,
                contentType: mappedContentType,
                template: template || "auto",
                pauseAfterExtraction: pauseAfterExtraction || false,
            }),
        });

        const result = await response.json();

        return {
            statusCode: response.ok ? 200 : 500,
            headers,
            body: JSON.stringify({
                success: response.ok,
                jobId: jobId,
                message: response.ok ? "Video generation started" : "Generation failed",
                data: result,
                parameters: {
                    country,
                    platform: mappedPlatform,
                    genre,
                    contentType: mappedContentType,
                    template: template || "auto",
                    pauseAfterExtraction: pauseAfterExtraction || false,
                },
            }),
        };
    } catch (error) {
        console.error("❌ Error in generate function:", error);

        return {
            statusCode: 500,
            headers,
            body: JSON.stringify({
                success: false,
                message: "Failed to process generation request",
                error: error.message,
            }),
        };
    }
};
