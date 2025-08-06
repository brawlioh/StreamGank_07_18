"""
StreamGank Movie Data Extractor

This module handles movie data extraction from the Supabase database,
including filtering, processing, and data transformation for video generation.
"""

import logging
import random
from typing import List, Dict, Any, Optional
from database.connection import DatabaseConnection
from database.filters import build_movie_query, apply_filters
from database.validators import validate_extraction_params, validate_movie_response, process_movie_data

logger = logging.getLogger(__name__)

# =============================================================================
# MAIN EXTRACTION FUNCTIONS
# =============================================================================

def extract_movie_data(num_movies: int = 3, 
                      country: Optional[str] = None, 
                      genre: Optional[str] = None, 
                      platform: Optional[str] = None, 
                      content_type: Optional[str] = None, 
                      debug: bool = False) -> Optional[List[Dict[str, Any]]]:
    """
    Extract top movies by IMDB score from Supabase with filtering.
    
    This is the main entry point for movie data extraction. It handles
    database connection, query building, filtering, and data processing.
    
    Args:
        num_movies (int): Number of movies to extract
        country (str): Country code for filtering (e.g., 'US', 'FR')
        genre (str): Genre to filter by (e.g., 'Horror', 'Comedy')
        platform (str): Platform to filter by (e.g., 'Netflix', 'Max')
        content_type (str): Content type to filter by (e.g., 'Film', 'Série')
        debug (bool): Enable debug output and logging
        
    Returns:
        list: List of movie data dictionaries sorted by IMDB score, or None if failed
        
    Example:
        >>> movies = extract_movie_data(3, 'US', 'Horror', 'Netflix', 'Film')
        >>> print(len(movies))  # 3
        >>> print(movies[0]['title'])  # 'Top Horror Movie Title'
    """
    logger.info(f"🎬 Extracting {num_movies} movies from database")
    logger.info(f"   Filters: country={country}, genre={genre}, platform={platform}, content_type={content_type}")
    
    # Validate input parameters
    validation_result = validate_extraction_params(num_movies, country, genre, platform, content_type)
    if not validation_result['is_valid']:
        logger.error(f"❌ Invalid extraction parameters: {validation_result['errors']}")
        return None
    
    # Use database connection context manager
    with DatabaseConnection() as db:
        if not db.is_connected():
            logger.error("❌ Database connection failed")
            return None
        
        try:
            # Build query with joins and filters
            query = build_movie_query(db.get_client())
            
            # Apply filters if provided
            query = apply_filters(query, content_type, country, platform, genre)
            
            # Execute query with ordering and limit
            logger.debug(f"🔍 Executing database query with {num_movies} limit")
            response = query.order("imdb_score", desc=True).limit(num_movies).execute()
            
            # Validate response
            response_validation = validate_movie_response(response)
            if not response_validation['is_valid']:
                logger.error(f"❌ Database response validation failed: {response_validation['errors']}")
                return None
            
            # Process movie data
            movie_data = process_movie_data(response.data, debug=debug)
            
            if movie_data:
                # Sort by IMDB score (highest first)
                movie_data.sort(key=lambda x: x.get('imdb_score', 0), reverse=True)
                
                logger.info(f"✅ Successfully extracted {len(movie_data)} movies")
                if movie_data:
                    top_movie = movie_data[0]
                    logger.info(f"   Top movie: {top_movie['title']} - IMDB: {top_movie['imdb']}")
                
                if debug:
                    logger.debug("🔍 Extracted movie details:")
                    for i, movie in enumerate(movie_data[:3]):  # Show first 3
                        logger.debug(f"   {i+1}. {movie['title']} ({movie['year']}) - {movie['imdb']}")
                
                return movie_data
            else:
                logger.error("❌ No movies could be processed from database response")
                return None
                
        except Exception as e:
            logger.error(f"❌ Database query failed: {str(e)}")
            if debug:
                import traceback
                logger.debug(f"Full traceback: {traceback.format_exc()}")
            return None


def extract_movies_by_filters(filters: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    """
    Extract movies using a filters dictionary.
    
    Args:
        filters (dict): Dictionary containing extraction parameters
            - num_movies (int): Number of movies to extract
            - country (str): Country filter
            - genre (str): Genre filter
            - platform (str): Platform filter
            - content_type (str): Content type filter
            - debug (bool): Debug mode
            
    Returns:
        list: Movie data or None if failed
    """
    logger.info(f"🎬 Extracting movies with filters: {filters}")
    
    return extract_movie_data(
        num_movies=filters.get('num_movies', 3),
        country=filters.get('country'),
        genre=filters.get('genre'),
        platform=filters.get('platform'),
        content_type=filters.get('content_type'),
        debug=filters.get('debug', False)
    )


def get_movie_details(movie_id: int) -> Optional[Dict[str, Any]]:
    """
    Get detailed information for a specific movie by ID.
    
    Args:
        movie_id (int): Movie ID to fetch
        
    Returns:
        dict: Movie details or None if not found
    """
    logger.info(f"🔍 Fetching details for movie ID: {movie_id}")
    
    with DatabaseConnection() as db:
        if not db.is_connected():
            logger.error("❌ Database connection failed")
            return None
        
        try:
            # Build detailed query for single movie
            query = build_movie_query(db.get_client())
            
            # Filter by movie ID
            response = query.eq("movie_id", movie_id).execute()
            
            if not hasattr(response, 'data') or len(response.data) == 0:
                logger.warning(f"⚠️ No movie found with ID: {movie_id}")
                return None
            
            # Process the single movie
            movie_data = process_movie_data(response.data, debug=True)
            
            if movie_data:
                movie_details = movie_data[0]
                logger.info(f"✅ Found movie: {movie_details['title']} ({movie_details['year']})")
                return movie_details
            else:
                logger.error(f"❌ Failed to process movie data for ID: {movie_id}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Failed to fetch movie details for ID {movie_id}: {str(e)}")
            return None

# =============================================================================
# SIMULATION AND FALLBACK DATA
# =============================================================================

def simulate_movie_data(num_movies: int = 3, genre: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Generate simulated movie data when database is unavailable.
    
    This function provides fallback data for testing and development
    when the database connection is not available.
    
    Args:
        num_movies (int): Number of movies to simulate
        genre (str): Genre preference for simulation (affects selection)
        
    Returns:
        list: List of simulated movie data dictionaries
    """
    logger.warning(f"⚠️ Generating {num_movies} simulated movies (database unavailable)")
    
    # Base movie templates organized by genre
    movie_templates = {
        'Horror': [
            {
                "id": 1001,
                "title": "It",
                "platform": "Netflix",
                "year": "2017",
                "imdb": "7.3/10 (500000 votes)",
                "imdb_score": 7.3,
                "imdb_votes": 500000,
                "runtime": "135 min",
                "trailer_url": "https://www.youtube.com/watch?v=FnCdOQsX5kc",
                "poster_url": "https://streamgank.com/images/it.jpg",
                "cloudinary_poster_url": "",
                "streaming_url": "https://netflix.com/title/80017573",
                "genres": ["Horror", "Mystery & Thriller"],
                "content_type": "Film"
            },
            {
                "id": 1002,
                "title": "The Conjuring",
                "platform": "Max",
                "year": "2013",
                "imdb": "7.5/10 (450000 votes)",
                "imdb_score": 7.5,
                "imdb_votes": 450000,
                "runtime": "112 min",
                "trailer_url": "https://www.youtube.com/watch?v=k10ETZ41q5o",
                "poster_url": "https://streamgank.com/images/conjuring.jpg",
                "cloudinary_poster_url": "",
                "streaming_url": "https://max.com/movies/the-conjuring",
                "genres": ["Horror", "Mystery & Thriller"],
                "content_type": "Film"
            },
            {
                "id": 1003,
                "title": "Stranger Things",
                "platform": "Netflix",
                "year": "2016",
                "imdb": "8.7/10 (1000000 votes)",
                "imdb_score": 8.7,
                "imdb_votes": 1000000,
                "runtime": "51 min",
                "trailer_url": "https://www.youtube.com/watch?v=b9EkMc79ZSU",
                "poster_url": "https://streamgank.com/images/strangerthings.jpg",
                "cloudinary_poster_url": "",
                "streaming_url": "https://netflix.com/title/80057281",
                "genres": ["Horror", "Sci-Fi", "Drama"],
                "content_type": "Série"
            }
        ],
        'Comedy': [
            {
                "id": 2001,
                "title": "The Office",
                "platform": "Netflix",
                "year": "2005",
                "imdb": "9.0/10 (600000 votes)",
                "imdb_score": 9.0,
                "imdb_votes": 600000,
                "runtime": "22 min",
                "trailer_url": "https://www.youtube.com/watch?v=LHOtME2DL4g",
                "poster_url": "https://streamgank.com/images/office.jpg",
                "cloudinary_poster_url": "",
                "streaming_url": "https://netflix.com/title/70136120",
                "genres": ["Comedy"],
                "content_type": "Série"
            },
            {
                "id": 2002,
                "title": "Deadpool",
                "platform": "Disney+",
                "year": "2016",
                "imdb": "8.0/10 (850000 votes)",
                "imdb_score": 8.0,
                "imdb_votes": 850000,
                "runtime": "108 min",
                "trailer_url": "https://www.youtube.com/watch?v=9X-7GrS0KI4",
                "poster_url": "https://streamgank.com/images/deadpool.jpg",
                "cloudinary_poster_url": "",
                "streaming_url": "https://disneyplus.com/movies/deadpool",
                "genres": ["Comedy", "Action"],
                "content_type": "Film"
            }
        ],
        'Action': [
            {
                "id": 3001,
                "title": "Top Gun: Maverick",
                "platform": "Prime Video",
                "year": "2022",
                "imdb": "8.3/10 (700000 votes)",
                "imdb_score": 8.3,
                "imdb_votes": 700000,
                "runtime": "130 min",
                "trailer_url": "https://www.youtube.com/watch?v=qSqVVswa420",
                "poster_url": "https://streamgank.com/images/topgun.jpg",
                "cloudinary_poster_url": "",
                "streaming_url": "https://amazon.com/dp/B09XVQCDNG",
                "genres": ["Action", "Drama"],
                "content_type": "Film"
            }
        ]
    }
    
    # Select movies based on genre preference
    if genre and genre in movie_templates:
        available_movies = movie_templates[genre].copy()
        logger.info(f"🎭 Using genre-specific templates for: {genre}")
    else:
        # Combine all genres
        available_movies = []
        for genre_movies in movie_templates.values():
            available_movies.extend(genre_movies)
        logger.info(f"🎭 Using mixed genre templates")
    
    # Randomize and select requested number
    random.shuffle(available_movies)
    selected_movies = available_movies[:num_movies]
    
    # Fill with duplicates if not enough movies
    while len(selected_movies) < num_movies:
        if available_movies:
            selected_movies.append(random.choice(available_movies))
        else:
            # Create generic movie if no templates
            selected_movies.append({
                "id": 9000 + len(selected_movies),
                "title": f"Movie {len(selected_movies) + 1}",
                "platform": "Netflix",
                "year": "2023",
                "imdb": "7.0/10 (100000 votes)",
                "imdb_score": 7.0,
                "imdb_votes": 100000,
                "runtime": "120 min",
                "trailer_url": "",
                "poster_url": "",
                "cloudinary_poster_url": "",
                "streaming_url": "",
                "genres": ["Drama"],
                "content_type": "Film"
            })
    
    logger.info(f"✅ Generated {len(selected_movies)} simulated movies")
    for i, movie in enumerate(selected_movies):
        logger.info(f"   {i+1}. {movie['title']} ({movie['year']}) - {movie['imdb']}")
    
    return selected_movies


def get_movies_sample(limit: int = 5) -> Optional[List[Dict[str, Any]]]:
    """
    Get a random sample of movies from the database for testing.
    
    Args:
        limit (int): Maximum number of movies to return
        
    Returns:
        list: Sample of movie data or None if failed
    """
    logger.info(f"🎲 Getting random sample of {limit} movies")
    
    with DatabaseConnection() as db:
        if not db.is_connected():
            logger.warning("⚠️ Database unavailable, returning simulated sample")
            return simulate_movie_data(limit)
        
        try:
            # Get random sample using offset
            import random
            offset = random.randint(0, 100)  # Random starting point
            
            query = build_movie_query(db.get_client())
            response = query.range(offset, offset + limit - 1).execute()
            
            if hasattr(response, 'data') and response.data:
                movie_data = process_movie_data(response.data)
                logger.info(f"✅ Retrieved {len(movie_data)} sample movies")
                return movie_data
            else:
                logger.warning("⚠️ No sample data available, using simulation")
                return simulate_movie_data(limit)
                
        except Exception as e:
            logger.error(f"❌ Failed to get movie sample: {str(e)}")
            logger.warning("⚠️ Falling back to simulated data")
            return simulate_movie_data(limit)