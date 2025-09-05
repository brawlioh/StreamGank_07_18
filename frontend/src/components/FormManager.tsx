import { useState, useEffect, useCallback } from "react";
import APIService from "../services/APIService";

interface FormState {
    country: string;
    platforms: string[];
    genres: string[];
    template: string;
    contentType: string;
    pauseAfterExtraction: boolean;
}

interface Movie {
    title: string;
    year: string;
    platform: string;
    genre: string;
    poster_url: string;
    description: string;
}

interface FormManagerProps {
    onFormStateChange?: (formState: FormState) => void;
    onMoviePreviewUpdate?: (movies: Movie[]) => void;
    onGenerate?: (formData: FormState) => void;
}

// Genre mappings by country - moved outside component to avoid recreation on every render
const genresByCountry = {
    US: {
        "Action & Adventure": "Action & Adventure",
        Animation: "Animation",
        Comedy: "Comedy",
        Crime: "Crime",
        Documentary: "Documentary",
        Drama: "Drama",
        Fantasy: "Fantasy",
        History: "History",
        Horror: "Horror",
        "Kids & Family": "Kids & Family",
        "Made in Europe": "Made in Europe",
        "Music & Musical": "Music & Musical",
        "Mystery & Thriller": "Mystery & Thriller",
        "Reality TV": "Reality TV",
        Romance: "Romance",
        "Science-Fiction": "Science-Fiction",
        Sport: "Sport",
        "War & Military": "War & Military",
        Western: "Western",
    },
};

export default function FormManager({ onFormStateChange, onMoviePreviewUpdate, onGenerate }: FormManagerProps) {
    const [formState, setFormState] = useState<FormState>({
        country: "US",
        platforms: [],
        genres: [],
        template: "auto",
        contentType: "Série",
        pauseAfterExtraction: false,
    });

    const [availablePlatforms, setAvailablePlatforms] = useState<string[]>([]);
    const [availableGenres, setAvailableGenres] = useState<string[]>([]);
    const [isGenerating, setIsGenerating] = useState(false);

    // Template mappings
    const templates = {
        cc6718c5363e42b282a123f99b94b335: { name: "Default Template", genres: ["default"] },
        ed21a309a5c84b0d873fde68642adea3: { name: "Horror", genres: ["Horror"] },
        "7f8db20ddcd94a33a1235599aa8bf473": { name: "Action Adventure", genres: ["Action & Adventure"] },
        bc62f68a6b074406b571df42bdc6b71a: { name: "Romance", genres: ["Romance"] },
    };

    // Load platforms for country
    const loadPlatforms = useCallback(async (country: string) => {
        try {
            const response = await APIService.getPlatforms(country);
            if (response.success && Array.isArray(response.platforms)) {
                setAvailablePlatforms(response.platforms as string[]);
            }
        } catch (error) {
            console.error("Failed to load platforms:", error);
        }
    }, []);

    // Load genres for country
    const loadGenres = useCallback((country: string) => {
        const countryGenres = genresByCountry[country as keyof typeof genresByCountry] || genresByCountry.US;
        setAvailableGenres(Object.keys(countryGenres));
    }, []);

    // Load movie preview
    const loadMoviePreview = useCallback(async () => {
        if (!formState.country || formState.platforms.length === 0 || formState.genres.length === 0) {
            onMoviePreviewUpdate?.([]);
            return;
        }

        try {
            // Use VITE_BACKEND_URL from .env - NO HARDCODED PATHS
            const backendUrl = import.meta.env.VITE_BACKEND_URL;
            if (!backendUrl) {
                throw new Error("❌ VITE_BACKEND_URL not set in .env file!");
            }

            const response = await fetch(`${backendUrl}/api/movies/preview`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    country: formState.country,
                    platforms: formState.platforms,
                    genre: formState.genres,
                    contentType: formState.contentType === "All" ? null : formState.contentType,
                }),
            });

            const data = await response.json();
            if (data.success && data.movies && data.movies.length > 0) {
                onMoviePreviewUpdate?.(data.movies);
            } else {
                onMoviePreviewUpdate?.([]);
            }
        } catch (error) {
            console.error("Failed to load movie preview:", error);
            onMoviePreviewUpdate?.([]);
        }
    }, [formState, onMoviePreviewUpdate]);

    // Initialize form data
    useEffect(() => {
        loadPlatforms(formState.country);
        loadGenres(formState.country);
    }, [formState.country, loadPlatforms, loadGenres]);

    // Update preview when form changes
    useEffect(() => {
        const debounceTimer = setTimeout(() => {
            loadMoviePreview();
        }, 500);

        return () => clearTimeout(debounceTimer);
    }, [loadMoviePreview]);

    // Notify parent of form state changes
    useEffect(() => {
        onFormStateChange?.(formState);
    }, [formState, onFormStateChange]);

    const handleCountryChange = (country: string) => {
        setFormState((prev) => ({
            ...prev,
            country,
            platforms: [],
            genres: [],
        }));
    };

    const handlePlatformChange = (platform: string, checked: boolean) => {
        setFormState((prev) => ({
            ...prev,
            platforms: checked ? [...prev.platforms, platform] : prev.platforms.filter((p) => p !== platform),
        }));
    };

    const handleGenreChange = (genre: string, checked: boolean) => {
        setFormState((prev) => ({
            ...prev,
            genres: checked ? [...prev.genres, genre] : prev.genres.filter((g) => g !== genre),
        }));
    };

    const handleGenerate = async () => {
        if (!formState.country || formState.platforms.length === 0 || formState.genres.length === 0) {
            alert("Please select country, at least one platform, and at least one genre.");
            return;
        }

        setIsGenerating(true);
        try {
            onGenerate?.(formState);
        } finally {
            setIsGenerating(false);
        }
    };

    return (
        <div className="filter-panel">
            <h2 className="panel-title">VIDEO GENERATOR</h2>

            {/* Streaming Country */}
            <div className="filter-group">
                <h3>Streaming Country</h3>
                <div className="form-group">
                    <select value={formState.country} onChange={(e) => handleCountryChange(e.target.value)} className="form-select-custom">
                        <option value="US">United States (US)</option>
                    </select>
                </div>
            </div>

            {/* Platform */}
            <div className="filter-group">
                <h3>Platform</h3>
                <div className="checkbox-group">
                    {availablePlatforms.map((platform) => (
                        <div key={platform} className="checkbox-item">
                            <input type="checkbox" id={`platform-${platform}`} checked={formState.platforms.includes(platform)} onChange={(e) => handlePlatformChange(platform, e.target.checked)} />
                            <label htmlFor={`platform-${platform}`}>{platform}</label>
                        </div>
                    ))}
                </div>
            </div>

            {/* Genre */}
            <div className="filter-group">
                <h3>Genre</h3>
                <div className="checkbox-group">
                    {availableGenres.map((genre) => (
                        <div key={genre} className="checkbox-item">
                            <input type="checkbox" id={`genre-${genre}`} checked={formState.genres.includes(genre)} onChange={(e) => handleGenreChange(genre, e.target.checked)} />
                            <label htmlFor={`genre-${genre}`}>{genre}</label>
                        </div>
                    ))}
                </div>
            </div>

            {/* Video Template */}
            <div className="filter-group">
                <h3>Video Template</h3>
                <div className="form-group">
                    <select value={formState.template} onChange={(e) => setFormState((prev) => ({ ...prev, template: e.target.value }))} className="form-select-custom">
                        <option value="auto">Auto (Based on Genre)</option>
                        {Object.entries(templates).map(([id, template]) => (
                            <option key={id} value={id}>
                                {template.name}
                            </option>
                        ))}
                    </select>
                </div>
            </div>

            {/* Content Type */}
            <div className="filter-group">
                <h3>Content Type</h3>
                <div className="type-selector">
                    <div className="form-group">
                        <div className="form-check">
                            <input type="radio" name="contentType" id="all" value="All" checked={formState.contentType === "All"} onChange={(e) => setFormState((prev) => ({ ...prev, contentType: e.target.value }))} className="form-check-input" />
                            <label htmlFor="all" className="form-check-label">
                                All
                            </label>
                        </div>
                        <div className="form-check">
                            <input type="radio" name="contentType" id="movie" value="Film" checked={formState.contentType === "Film"} onChange={(e) => setFormState((prev) => ({ ...prev, contentType: e.target.value }))} className="form-check-input" />
                            <label htmlFor="movie" className="form-check-label">
                                Movies
                            </label>
                        </div>
                        <div className="form-check">
                            <input type="radio" name="contentType" id="serie" value="Série" checked={formState.contentType === "Série"} onChange={(e) => setFormState((prev) => ({ ...prev, contentType: e.target.value }))} className="form-check-input" />
                            <label htmlFor="serie" className="form-check-label">
                                TV Shows
                            </label>
                        </div>
                    </div>
                </div>
            </div>

            {/* Generation Options */}
            <div className="filter-group">
                <h3>Generation Options</h3>
                <div className="form-group">
                    <div className="form-check">
                        <input
                            type="checkbox"
                            id="pauseAfterExtraction"
                            checked={formState.pauseAfterExtraction}
                            onChange={(e) =>
                                setFormState((prev) => ({
                                    ...prev,
                                    pauseAfterExtraction: e.target.checked,
                                }))
                            }
                            className="form-check-input"
                        />
                        <label htmlFor="pauseAfterExtraction" className="form-check-label">
                            <strong>Pause after movie extraction</strong>
                            <br />
                            <small style={{ color: "var(--text-secondary)" }}>Stop process after finding 3 movies to review before video generation</small>
                        </label>
                    </div>
                </div>
            </div>

            {/* Generate Button */}
            <button onClick={handleGenerate} disabled={isGenerating || formState.platforms.length === 0 || formState.genres.length === 0} className="generate-btn mt-4">
                <span className="mr-2">🎬</span>
                {isGenerating ? "Generating..." : "Generate Video"}
            </button>
        </div>
    );
}
