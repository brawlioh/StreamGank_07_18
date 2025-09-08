import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import APIService from "../services/APIService";
import Navigation from "../components/Navigation";

interface FormState {
    country: string;
    platforms: string[];
    genres: string[];
    template: string;
    contentType: string;
}

interface Movie {
    title: string;
    year: string;
    platform: string;
    genre: string;
    poster_url: string;
    description: string;
}

interface StatusMessage {
    type: "info" | "success" | "error" | "warning";
    icon: string;
    message: string;
    timestamp: number;
}

export default function Dashboard() {
    const navigate = useNavigate();
    const [formState, setFormState] = useState<FormState>({
        country: "US",
        platforms: [],
        genres: [],
        template: "auto",
        contentType: "Film",
    });

    const [moviePreview, setMoviePreview] = useState<Movie[]>([]);
    const [isLoadingPreview, setIsLoadingPreview] = useState(false);
    const [statusMessages, setStatusMessages] = useState<StatusMessage[]>([
        {
            type: "warning",
            icon: "⚠",
            message: "Ready to generate video. Click the Generate button to start.",
            timestamp: Date.now(),
        },
    ]);
    const [availablePlatforms, setAvailablePlatforms] = useState<string[]>([]);
    const [availableGenres, setAvailableGenres] = useState<string[]>([]);
    const [availableTemplates, setAvailableTemplates] = useState<{ id: string; name: string }[]>([]);

    const addStatusMessage = (type: StatusMessage["type"], icon: string, message: string) => {
        const newMessage: StatusMessage = {
            type,
            icon,
            message,
            timestamp: Date.now(),
        };
        setStatusMessages((prev) => [newMessage, ...prev.slice(0, 4)]); // Keep only 5 messages
    };

    const loadInitialData = useCallback(async () => {
        try {
            // Load available platforms and genres
            const platformsResponse = await APIService.getPlatforms(formState.country);
            const genresResponse = await APIService.getGenres(formState.country);
            const templatesResponse = await APIService.getTemplates();

            if (platformsResponse.success && Array.isArray(platformsResponse.platforms)) {
                setAvailablePlatforms(platformsResponse.platforms as string[]);
            }
            if (genresResponse.success && Array.isArray(genresResponse.genres)) {
                setAvailableGenres(genresResponse.genres as string[]);
            }
            if (templatesResponse.success && Array.isArray(templatesResponse.templates)) {
                setAvailableTemplates(templatesResponse.templates as { id: string; name: string }[]);
            }
        } catch (error) {
            console.error("Failed to load initial data:", error);
            addStatusMessage("error", "❌", "Failed to load platform and genre data");
        }
    }, [formState.country]);

    const loadMoviePreview = useCallback(async () => {
        if (formState.platforms.length === 0 || formState.genres.length === 0) return;

        setIsLoadingPreview(true);
        try {
            const response = await APIService.getMoviePreview({
                country: formState.country,
                platforms: formState.platforms,
                genres: formState.genres,
                contentType: formState.contentType === "All" ? undefined : formState.contentType,
            });

            if (response.success && Array.isArray(response.movies)) {
                setMoviePreview(response.movies as Movie[]);
            } else {
                setMoviePreview([]);
            }
        } catch (error) {
            console.error("Failed to load movie preview:", error);
            setMoviePreview([]);
        } finally {
            setIsLoadingPreview(false);
        }
    }, [formState.country, formState.platforms, formState.genres, formState.contentType]);

    useEffect(() => {
        document.title = "Dashboard - StreamGank Video Generator";
        loadInitialData();
    }, [loadInitialData]);

    useEffect(() => {
        // Update preview when form state changes
        if (formState.platforms.length > 0 && formState.genres.length > 0) {
            loadMoviePreview();
        }
    }, [formState.platforms, formState.genres, formState.contentType, loadMoviePreview]);

    const generateTargetURL = () => {
        if (formState.platforms.length === 0 || formState.genres.length === 0) {
            return "Select all parameters to generate URL";
        }

        const params = new URLSearchParams();
        params.set("country", formState.country);
        params.set("platform", formState.platforms.join(","));
        params.set("genre", formState.genres.join(","));
        if (formState.contentType !== "All") {
            params.set("type", formState.contentType);
        }

        return `https://streaming.com/?${params.toString()}`;
    };

    const isGenerateEnabled = () => {
        // Must have platforms and genres selected
        if (formState.platforms.length === 0 || formState.genres.length === 0) {
            return false;
        }

        // Must have movies found (unless still loading)
        if (!isLoadingPreview && moviePreview.length === 0) {
            return false;
        }

        return true;
    };

    const handlePlatformChange = (platform: string) => {
        setFormState((prev) => ({
            ...prev,
            platforms: prev.platforms.includes(platform) ? prev.platforms.filter((p) => p !== platform) : [...prev.platforms, platform],
        }));
    };

    const handleGenreChange = (genre: string) => {
        setFormState((prev) => ({
            ...prev,
            genres: prev.genres.includes(genre) ? prev.genres.filter((g) => g !== genre) : [...prev.genres, genre],
        }));
    };

    const handleGenerate = async () => {
        // Validation
        if (formState.platforms.length === 0) {
            addStatusMessage("error", "❌", "Please select at least one platform");
            return;
        }
        if (formState.genres.length === 0) {
            addStatusMessage("error", "❌", "Please select at least one genre");
            return;
        }

        addStatusMessage("info", "🎬", "Starting video generation...");

        try {
            const response = await APIService.generateVideo({
                country: formState.country,
                platform: formState.platforms.join(","),
                genre: formState.genres.join(","),
                contentType: formState.contentType === "All" ? undefined : formState.contentType,
                template: formState.template === "auto" ? undefined : formState.template,
            });

            if (response.success) {
                const jobId = response.job && typeof response.job === "object" && "id" in response.job ? (response.job as { id: string }).id : "Unknown";
                addStatusMessage("success", "✅", `Video generation started! Job ID: ${jobId}`);

                if (jobId !== "Unknown") {
                    // Connect to job-specific SSE for real-time updates
                    import("../services/RealtimeService").then((module) => {
                        const RealtimeService = module.default;
                        RealtimeService.connectToJob(jobId);
                        console.log(`📡 Connected to job-specific SSE for job: ${jobId}`);
                    });

                    // Navigate to job detail page after a short delay
                    setTimeout(() => {
                        navigate(`/job/${jobId}`);
                    }, 2000);
                }
            } else {
                addStatusMessage("error", "❌", `Failed to start video generation: ${response.message || "Unknown error"}`);
            }
        } catch (error: unknown) {
            console.error("Video generation error:", error);
            addStatusMessage("error", "❌", `Video generation failed: ${error instanceof Error ? error.message : "Unknown error"}`);
        }
    };

    return (
        <div className="min-h-screen" style={{ backgroundColor: "var(--dark-bg)", color: "var(--text-light)" }}>
            {/* Navigation */}
            <Navigation queueCount={0} connectionStatus="connected" onRefresh={() => window.location.reload()} />

            {/* Status Messages */}
            {statusMessages.length > 0 && (
                <div style={{ backgroundColor: "var(--dark-bg)", borderBottom: "1px solid var(--border-color)" }}>
                    <div className="px-6 py-4">
                        {statusMessages.slice(0, 1).map((message) => (
                            <div
                                key={message.timestamp}
                                className={`flex items-center space-x-3 p-3 rounded-lg ${
                                    message.type === "success"
                                        ? "bg-green-900/30 border border-green-600/50"
                                        : message.type === "error"
                                        ? "bg-red-900/30 border border-red-600/50"
                                        : message.type === "warning"
                                        ? "bg-yellow-900/30 border border-yellow-600/50"
                                        : "bg-blue-900/30 border border-blue-600/50"
                                }`}
                            >
                                <span className="text-lg">{message.icon}</span>
                                <span className={`text-sm ${message.type === "success" ? "text-green-400" : message.type === "error" ? "text-red-400" : message.type === "warning" ? "text-yellow-400" : "text-blue-400"}`}>{message.message}</span>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Main Content */}
            <div className="flex min-h-screen">
                {/* Left Panel - Video Generator */}
                <div className="w-1/4 p-6" style={{ backgroundColor: "var(--dark-panel)", borderRight: "1px solid var(--border-color)" }}>
                    <h2 className="text-lg font-semibold mb-4 text-green-400">VIDEO GENERATOR</h2>

                    {/* Streaming Country */}
                    <div className="mb-6">
                        <label className="block text-sm font-medium mb-2">Streaming Country</label>
                        <select className="w-full rounded px-3 py-2" style={{ backgroundColor: "var(--dark-bg)", border: "1px solid var(--border-color)", color: "var(--text-light)" }} value={formState.country} onChange={(e) => setFormState((prev) => ({ ...prev, country: e.target.value }))}>
                            <option value="US">United States (US)</option>
                        </select>
                    </div>

                    {/* Platform */}
                    <div className="mb-6">
                        <label className="block text-sm font-medium mb-2">Platform</label>
                        <div className="grid grid-cols-2 gap-2 text-sm">
                            {availablePlatforms.length > 0 ? (
                                availablePlatforms.map((platform) => (
                                    <label key={platform} className="flex items-center space-x-2">
                                        <input type="checkbox" className="rounded text-blue-600 bg-gray-700 border-gray-600 focus:ring-blue-500" checked={formState.platforms.includes(platform)} onChange={() => handlePlatformChange(platform)} />
                                        <span className="text-gray-300">{platform}</span>
                                    </label>
                                ))
                            ) : (
                                <div className="col-span-2 text-gray-400 text-sm flex items-center">
                                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500 mr-2"></div>
                                    Loading platforms...
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Genre */}
                    <div className="mb-6">
                        <label className="block text-sm font-medium mb-2">Genre</label>
                        <div className="grid grid-cols-2 gap-2 text-sm">
                            {availableGenres.length > 0 ? (
                                availableGenres.map((genre) => (
                                    <label key={genre} className="flex items-center space-x-2">
                                        <input type="checkbox" className="rounded text-blue-600 bg-gray-700 border-gray-600 focus:ring-blue-500" checked={formState.genres.includes(genre)} onChange={() => handleGenreChange(genre)} />
                                        <span className="text-gray-300">{genre}</span>
                                    </label>
                                ))
                            ) : (
                                <div className="col-span-2 text-gray-400 text-sm flex items-center">
                                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500 mr-2"></div>
                                    Loading genres...
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Video Template */}
                    <div className="mb-6">
                        <label className="block text-sm font-medium mb-2">Video Template</label>
                        <select className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500" value={formState.template} onChange={(e) => setFormState((prev) => ({ ...prev, template: e.target.value }))}>
                            <option value="auto">Default Template</option>
                            {availableTemplates.map((template) => (
                                <option key={template.id} value={template.id}>
                                    {template.name}
                                </option>
                            ))}
                        </select>
                    </div>

                    {/* Content Type */}
                    <div className="mb-6">
                        <label className="block text-sm font-medium mb-2">Content Type</label>
                        <div className="space-y-2">
                            <label className="flex items-center space-x-2">
                                <input type="radio" name="contentType" className="rounded" checked={formState.contentType === "All"} onChange={() => setFormState((prev) => ({ ...prev, contentType: "All" }))} />
                                <span>All</span>
                            </label>
                            <label className="flex items-center space-x-2">
                                <input type="radio" name="contentType" className="rounded" checked={formState.contentType === "Film"} onChange={() => setFormState((prev) => ({ ...prev, contentType: "Film" }))} />
                                <span>Movies</span>
                            </label>
                            <label className="flex items-center space-x-2">
                                <input type="radio" name="contentType" className="rounded" checked={formState.contentType === "Série"} onChange={() => setFormState((prev) => ({ ...prev, contentType: "Série" }))} />
                                <span>TV Shows</span>
                            </label>
                        </div>
                    </div>

                    {/* Generate Button */}
                    <button onClick={handleGenerate} disabled={!isGenerateEnabled()} className={`w-full py-3 rounded font-medium transition-colors ${isGenerateEnabled() ? "bg-green-600 hover:bg-green-700 text-white cursor-pointer" : "bg-gray-600 text-gray-400 cursor-not-allowed"}`}>
                        📹 Generate Video
                    </button>
                </div>

                {/* Right Panel */}
                <div className="flex-1 p-6">
                    {/* Preview Configuration */}
                    <div className="preview-container rounded-lg p-4 mb-6">
                        <h3 className="text-lg font-semibold mb-4 text-green-400">Preview Configuration</h3>
                        <div className="grid grid-cols-3 gap-4 text-sm">
                            <div>
                                <span style={{ color: "var(--text-secondary)" }}>Country:</span>
                                <span className="ml-2 text-green-400">{formState.country === "US" ? "United States (US)" : formState.country}</span>
                            </div>
                            <div>
                                <span style={{ color: "var(--text-secondary)" }}>Platform:</span>
                                <span className="ml-2 text-green-400">{formState.platforms.length > 0 ? formState.platforms.join(", ") : "None selected"}</span>
                            </div>
                            <div>
                                <span style={{ color: "var(--text-secondary)" }}>Genre:</span>
                                <span className="ml-2 text-green-400">{formState.genres.length > 0 ? formState.genres.join(", ") : "None selected"}</span>
                            </div>
                            <div>
                                <span style={{ color: "var(--text-secondary)" }}>Template:</span>
                                <span className="ml-2 text-green-400">{availableTemplates.find((t) => t.id === formState.template)?.name || formState.template || "Default Template"}</span>
                            </div>
                            <div>
                                <span style={{ color: "var(--text-secondary)" }}>Type:</span>
                                <span className="ml-2 text-green-400">{formState.contentType === "Film" ? "Movies" : formState.contentType === "Série" ? "TV Shows" : formState.contentType}</span>
                            </div>
                        </div>
                        <div className="mt-3">
                            <span style={{ color: "var(--text-secondary)" }}>Target URL:</span>
                            <span className="ml-2 text-green-400 text-xs">{generateTargetURL()}</span>
                        </div>
                    </div>

                    {/* Movie Preview */}
                    <div className="movie-preview-container rounded-lg p-4 mb-6">
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-lg font-semibold text-green-400">Movie Preview</h3>
                            <button onClick={loadMoviePreview} disabled={isLoadingPreview} className="bg-green-600 hover:bg-green-700 disabled:bg-gray-600 text-white px-3 py-1 rounded text-sm flex items-center">
                                {isLoadingPreview ? <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div> : "🔄 "}
                                Refresh
                            </button>
                        </div>

                        {/* Loading State */}
                        {isLoadingPreview && (
                            <div className="text-center py-8">
                                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-500 mx-auto mb-4"></div>
                                <p style={{ color: "var(--text-secondary)" }} className="text-sm">
                                    Loading movie preview...
                                </p>
                            </div>
                        )}

                        {/* No Selection State */}
                        {!isLoadingPreview && (formState.platforms.length === 0 || formState.genres.length === 0) && (
                            <div className="text-center py-8">
                                <div className="text-6xl mb-4">🎬</div>
                                <p style={{ color: "var(--text-secondary)" }} className="text-sm">
                                    Select platforms and genres to preview movies
                                </p>
                            </div>
                        )}

                        {/* Movies Display */}
                        {!isLoadingPreview && formState.platforms.length > 0 && formState.genres.length > 0 && (
                            <>
                                <p className="text-gray-400 text-sm mb-4">Found {moviePreview.length} movies matching your criteria:</p>

                                {moviePreview.length > 0 ? (
                                    <div className="grid grid-cols-3 gap-4">
                                        {moviePreview.slice(0, 3).map((movie, index) => (
                                            <div key={index} className="text-center">
                                                <div className="w-full h-40 bg-gray-700 rounded mb-2 flex items-center justify-center overflow-hidden">
                                                    {movie.poster_url ? (
                                                        <img
                                                            src={movie.poster_url}
                                                            alt={movie.title}
                                                            className="w-full h-full object-cover"
                                                            onError={(e) => {
                                                                const target = e.target as HTMLImageElement;
                                                                target.style.display = "none";
                                                                target.nextElementSibling!.classList.remove("hidden");
                                                            }}
                                                        />
                                                    ) : null}
                                                    <span className={`text-gray-400 text-xs px-2 text-center ${movie.poster_url ? "hidden" : ""}`}>{movie.title}</span>
                                                </div>
                                                <h4 className="text-white font-medium text-sm truncate" title={movie.title}>
                                                    {movie.title}
                                                </h4>
                                                <p className="text-gray-400 text-xs">
                                                    {movie.year} • {movie.platform}
                                                </p>
                                            </div>
                                        ))}
                                    </div>
                                ) : (
                                    <div className="text-center py-8">
                                        <div className="text-4xl mb-4">🔍</div>
                                        <p style={{ color: "var(--text-secondary)" }} className="text-sm">
                                            No movies found for selected criteria
                                        </p>
                                        <p style={{ color: "var(--text-secondary)" }} className="text-xs mt-2 opacity-75">
                                            Try different platform or genre combinations
                                        </p>
                                    </div>
                                )}
                            </>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
