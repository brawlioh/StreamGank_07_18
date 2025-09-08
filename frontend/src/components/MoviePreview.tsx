import { useState } from "react";

interface Movie {
    title: string;
    year: string;
    platform: string;
    genre: string;
    poster_url: string;
    description: string;
}

interface MoviePreviewProps {
    movies: Movie[];
    isLoading: boolean;
    onRefresh?: () => void;
}

export default function MoviePreview({ movies, isLoading, onRefresh }: MoviePreviewProps) {
    const [imageErrors, setImageErrors] = useState<Set<string>>(new Set());

    const handleImageError = (posterUrl: string) => {
        setImageErrors((prev) => new Set([...prev, posterUrl]));
    };

    const getImageSrc = (posterUrl: string) => {
        if (imageErrors.has(posterUrl)) {
            return "https://via.placeholder.com/300x450/1a1a1a/16c784?text=No+Image";
        }
        return posterUrl;
    };

    if (movies.length === 0 && !isLoading) {
        return null; // Don't show preview container when no movies
    }

    return (
        <div className="movie-preview-container" style={{ display: movies.length > 0 || isLoading ? "block" : "none" }}>
            <div className="flex justify-between items-center mb-2">
                <h4 className="mb-0 font-semibold" style={{ color: "var(--text-light)" }}>
                    Available Movies
                </h4>
                <button onClick={onRefresh} className="btn btn-outline-light btn-sm">
                    <i className="fas fa-sync-alt"></i>
                </button>
            </div>

            {/* Loading State */}
            {isLoading && (
                <div className="text-center py-2">
                    <div className="spinner-border spinner-border-sm" style={{ color: "var(--primary-color)" }}></div>
                    <small className="ml-2" style={{ color: "var(--text-secondary)" }}>
                        Loading...
                    </small>
                </div>
            )}

            {/* Movies Grid */}
            {!isLoading && movies.length > 0 && (
                <div className="flex flex-row gap-3 overflow-auto p-3 rounded" style={{ background: "rgba(18, 18, 18, 0.25)" }}>
                    {movies.map((movie, index) => (
                        <div key={`${movie.title}-${index}`} className="movie-card flex-shrink-0" style={{ width: "200px" }}>
                            <div className="movie-poster-container">
                                <img src={getImageSrc(movie.poster_url)} alt={movie.title} className="movie-poster" onError={() => handleImageError(movie.poster_url)} />
                            </div>
                            <div className="movie-info">
                                <h5 className="movie-title">{movie.title}</h5>
                                <div className="movie-meta">
                                    <span className="movie-badge movie-platform">{movie.platform}</span>
                                    <span className="movie-badge movie-year">{movie.year}</span>
                                    <span className="movie-badge movie-genre">{movie.genre}</span>
                                </div>
                                {movie.description && (
                                    <p className="text-xs mt-2" style={{ color: "var(--text-secondary)" }}>
                                        {movie.description.length > 100 ? `${movie.description.substring(0, 100)}...` : movie.description}
                                    </p>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* No Results State */}
            {!isLoading && movies.length === 0 && (
                <div className="text-center py-3">
                    <i className="fas fa-film fa-2x mb-2" style={{ color: "var(--text-secondary)" }}></i>
                    <div style={{ color: "var(--text-light)" }}>No Movies Found</div>
                    <small style={{ color: "var(--text-secondary)" }}>Try different filters</small>
                </div>
            )}
        </div>
    );
}
