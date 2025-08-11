/**
 * Netlify Function: Get Genres by Country
 * Returns available movie/show genres for a specific country
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

        console.log(`🎭 Fetching genres for country: ${country}`);

        // Available genres by country - Updated to match StreamGank
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

        return {
            statusCode: 200,
            headers,
            body: JSON.stringify({
                success: true,
                country: country,
                genres: genres,
                source: "user_defined",
                count: genres.length,
            }),
        };
    } catch (error) {
        console.error("❌ Error fetching genres:", error);

        return {
            statusCode: 500,
            headers,
            body: JSON.stringify({
                success: false,
                message: "Failed to fetch genres",
                error: error.message,
            }),
        };
    }
};
