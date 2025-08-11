/**
 * Netlify Function: Get Platforms by Country
 * Returns available streaming platforms for a specific country
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
        // Extract country from path parameters
        const pathSegments = event.path.split("/");
        const country = pathSegments[pathSegments.length - 1];

        console.log(`🌍 Fetching platforms for country: ${country}`);

        // Available platforms by country
        const availablePlatforms = {
            FR: ["Prime", "Apple TV+", "Disney+", "Max", "Netflix", "Free"],
            US: ["Prime", "Apple TV+", "Disney+", "Hulu", "Max", "Netflix"],
        };

        const platforms = availablePlatforms[country] || availablePlatforms["US"]; // Default to US if country not found

        console.log(`✅ Found ${platforms.length} platforms for ${country}:`, platforms);

        return {
            statusCode: 200,
            headers,
            body: JSON.stringify({
                success: true,
                country: country,
                platforms: platforms,
                source: "user_defined",
                count: platforms.length,
            }),
        };
    } catch (error) {
        console.error("❌ Error fetching platforms:", error);

        return {
            statusCode: 500,
            headers,
            body: JSON.stringify({
                success: false,
                message: "Failed to fetch platforms",
                error: error.message,
            }),
        };
    }
};
