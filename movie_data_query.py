#!/usr/bin/env python3
"""
Movie Data Query Tool for StreamGank

This script provides functionality to query movie data from the Supabase database
with various filtering options such as country, genre, platform, and content type.

Usage:
    python3 movie_data_query.py --country=US --genre="Action" --platform="Netflix" --content_type="Movie"
    
    # Interactive mode:
    python3 movie_data_query.py
"""

import os
import sys
import json
import logging
import argparse
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
from supabase import create_client

# =============================================================================
# CONFIGURATION
# =============================================================================

# Load environment variables
load_dotenv()

# Logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# =============================================================================
# DATABASE OPERATIONS
# =============================================================================

def test_supabase_connection():
    """
    Test Supabase connection and return status
    
    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        if not SUPABASE_URL or not SUPABASE_KEY:
            logger.error("❌ Supabase URL or key not found in environment variables")
            return False
        sample = supabase.table("movies").select("*").limit(1).execute()
        return hasattr(sample, 'data') and len(sample.data) >= 0
    except Exception as e:
        logger.error(f"❌ Supabase connection failed: {str(e)}")
        return False


def extract_movie_data(num_movies=3, country=None, genre=None, platform=None, content_type=None, debug=False):
    """
    Extract top movies by IMDB score from Supabase with filtering
    
    Args:
        num_movies (int): Number of movies to extract
        country (str): Country code for filtering
        genre (str): Genre to filter by
        platform (str): Platform to filter by
        content_type (str): Content type to filter by
        debug (bool): Enable debug output
        
    Returns:
        list: List of movie data dictionaries or None if failed
    """
    logger.info(f"🎬 Extracting {num_movies} movies from database")
    logger.info(f"   Filters: {country}, {genre}, {platform}, {content_type}")
    
    # Test connection first
    if not test_supabase_connection():
        logger.error("❌ Database connection failed")
        return None
    
    try:
        # Build query with joins and filters
        query = supabase.from_("movies").select("""
            movie_id,
            content_type,
            imdb_score,
            imdb_votes,
            runtime,
            release_year,
            movie_localizations!inner(
                title,
                country_code,
                platform_name,
                poster_url,
                cloudinary_poster_url,
                trailer_url,
                streaming_url
            ),
            movie_genres!inner(
                genre
            )
        """)
        
        # Apply filters if provided
        if content_type:
            query = query.eq("content_type", content_type)
        if country:
            query = query.eq("movie_localizations.country_code", country)
        if platform:
            query = query.eq("movie_localizations.platform_name", platform)
        if genre:
            query = query.eq("movie_genres.genre", genre)
        
        # Execute query
        response = query.order("imdb_score", desc=True).limit(num_movies).execute()
        
        if not hasattr(response, 'data') or len(response.data) == 0:
            logger.error("❌ No movies found matching criteria")
            return None
        
        # Process results
        movie_data = []
        processed_titles = set()  # Track processed titles to prevent duplicates
        
        for movie in response.data:
            try:
                localization = movie.get('movie_localizations', [])
                if isinstance(localization, list) and len(localization) > 0:
                    localization = localization[0]
                
                # Get title and check for duplicates
                title = localization.get('title', 'Unknown Title')
                if title in processed_titles:
                    logger.info(f"Skipping duplicate movie: {title} (ID: {movie.get('movie_id')})")
                    continue
                
                genres_data = movie.get('movie_genres', [])
                if isinstance(genres_data, list):
                    genres = [g.get('genre') for g in genres_data if g.get('genre')]
                else:
                    genres = [genres_data.get('genre')] if genres_data.get('genre') else []
                
                movie_info = {
                    'id': movie.get('movie_id'),
                    'title': title,
                    'year': movie.get('release_year', 'Unknown'),
                    'imdb': f"{movie.get('imdb_score', 0)}/10 ({movie.get('imdb_votes', 0)} votes)",
                    'imdb_score': movie.get('imdb_score', 0),
                    'imdb_votes': movie.get('imdb_votes', 0),
                    'runtime': f"{movie.get('runtime', 0)} min",
                    'platform': localization.get('platform_name', platform or 'Unknown'),
                    'poster_url': localization.get('poster_url', ''),
                    'cloudinary_poster_url': localization.get('cloudinary_poster_url', ''),
                    'trailer_url': localization.get('trailer_url', ''),
                    'streaming_url': localization.get('streaming_url', ''),
                    'genres': genres,
                    'content_type': movie.get('content_type', content_type or 'Unknown')
                }
                
                movie_data.append(movie_info)
                processed_titles.add(title)  # Add title to processed set
                
            except Exception as e:
                logger.error(f"Error processing movie {movie.get('movie_id', 'unknown')}: {str(e)}")
                continue
        
        movie_data.sort(key=lambda x: x.get('imdb_score', 0), reverse=True)
        
        if movie_data:
            logger.info(f"✅ Successfully extracted {len(movie_data)} movies")
            logger.info(f"   Top movie: {movie_data[0]['title']} - IMDB: {movie_data[0]['imdb']}")
            if debug:
                logger.info(f"Movie data: {json.dumps(movie_data, indent=2)}")
            return movie_data
        else:
            logger.error("❌ No movies could be processed")
            return None
            
    except Exception as e:
        logger.error(f"❌ Database query failed: {str(e)}")
        return None


def get_available_countries():
    """Get list of available countries from the database"""
    try:
        if not test_supabase_connection():
            return []
            
        response = supabase.from_("movie_localizations").select("country_code").execute()
        if not hasattr(response, 'data') or len(response.data) == 0:
            return []
            
        countries = set()
        for item in response.data:
            if item.get('country_code'):
                countries.add(item.get('country_code'))
                
        return sorted(list(countries))
    except Exception as e:
        logger.error(f"❌ Failed to retrieve countries: {str(e)}")
        return []


def get_available_platforms(country=None, min_movies=3):
    """Get list of available platforms with at least min_movies for a specific country"""
    try:
        if not test_supabase_connection():
            return []
            
        # First get all platforms
        query = supabase.from_("movie_localizations").select("platform_name")
        if country:
            query = query.eq("country_code", country)
            
        response = query.execute()
        if not hasattr(response, 'data') or len(response.data) == 0:
            return []
            
        # Count movies for each platform
        platform_counts = {}
        for item in response.data:
            platform = item.get('platform_name')
            if platform:
                platform_counts[platform] = platform_counts.get(platform, 0) + 1
                
        # Filter platforms with at least min_movies
        valid_platforms = [platform for platform, count in platform_counts.items() if count >= min_movies]
        return sorted(valid_platforms)
    except Exception as e:
        logger.error(f"❌ Failed to retrieve platforms: {str(e)}")
        return []


def get_available_genres(country=None, platform=None, min_movies=3):
    """Get list of available genres with at least min_movies for specific country and platform"""
    try:
        if not test_supabase_connection():
            return []
            
        # This query requires joining tables
        query = supabase.from_("movies").select("""
            movie_genres!inner(genre),
            movie_localizations!inner(country_code, platform_name)
        """)
        
        if country:
            query = query.eq("movie_localizations.country_code", country)
        if platform:
            query = query.eq("movie_localizations.platform_name", platform)
            
        response = query.execute()
        if not hasattr(response, 'data') or len(response.data) == 0:
            return []
            
        # Count movies for each genre
        genre_counts = {}
        for item in response.data:
            genres_data = item.get('movie_genres', [])
            if isinstance(genres_data, list):
                for g in genres_data:
                    if g.get('genre'):
                        genre = g.get('genre')
                        genre_counts[genre] = genre_counts.get(genre, 0) + 1
            elif genres_data.get('genre'):
                genre = genres_data.get('genre')
                genre_counts[genre] = genre_counts.get(genre, 0) + 1
                
        # Filter genres with at least min_movies
        valid_genres = [genre for genre, count in genre_counts.items() if count >= min_movies]
        return sorted(valid_genres)
    except Exception as e:
        logger.error(f"❌ Failed to retrieve genres: {str(e)}")
        return []


def get_available_content_types(country=None, platform=None, genre=None, min_movies=3):
    """
    Get list of available content types with at least min_movies for specific filters
    
    Args:
        country (str): Country code to filter by
        platform (str): Platform name to filter by
        genre (str): Genre to filter by
        min_movies (int): Minimum number of movies required for a content type to be included
        
    Returns:
        list: Sorted list of content types with at least min_movies
    """
    try:
        if not test_supabase_connection():
            return []
            
        # Build query to count movies per content type
        query_str = """
        SELECT m.content_type, COUNT(DISTINCT m.movie_id) as count
        FROM movies m
        JOIN movie_localizations ml ON m.movie_id = ml.movie_id
        """
        
        if genre:
            query_str += " JOIN movie_genres mg ON m.movie_id = mg.movie_id"
            
        conditions = []
        if country:
            conditions.append(f"ml.country_code = '{country}'")
        if platform:
            conditions.append(f"ml.platform_name = '{platform}'")
        if genre:
            conditions.append(f"mg.genre = '{genre}'")
            
        if conditions:
            query_str += " WHERE " + " AND ".join(conditions)
            
        query_str += " GROUP BY m.content_type"
        
        # Execute the raw SQL query
        response = supabase.rpc('run_sql', {'query': query_str}).execute()
        
        if not hasattr(response, 'data') or len(response.data) == 0:
            return []
            
        # Filter content types with at least min_movies
        valid_content_types = []
        content_type_counts = {}
        for item in response.data:
            if item.get('count', 0) >= min_movies and item.get('content_type'):
                valid_content_types.append(item.get('content_type'))
                content_type_counts[item.get('content_type')] = item.get('count')
                
        return sorted(valid_content_types), content_type_counts
    except Exception as e:
        logger.error(f"❌ Failed to retrieve content types: {str(e)}")
        # Fallback to standard API if raw SQL fails
        return _get_content_types_fallback(country, platform, genre, min_movies)

def _get_content_types_fallback(country=None, platform=None, genre=None, min_movies=3):
    """Fallback method for getting content types if raw SQL fails"""
    try:
        query = supabase.from_("movies").select("""
            content_type,
            movie_localizations!inner(country_code, platform_name),
            movie_genres!inner(genre)
        """)
        
        if country:
            query = query.eq("movie_localizations.country_code", country)
        if platform:
            query = query.eq("movie_localizations.platform_name", platform)
        if genre:
            query = query.eq("movie_genres.genre", genre)
            
        response = query.execute()
        
        content_type_counts = {}
        for item in response.data:
            content_type = item.get('content_type')
            if content_type:
                content_type_counts[content_type] = content_type_counts.get(content_type, 0) + 1
                
        valid_content_types = [ct for ct, count in content_type_counts.items() if count >= min_movies]
        return sorted(valid_content_types), content_type_counts
    except Exception as e:
        logger.error(f"❌ Fallback content type retrieval failed: {str(e)}")
        return [], {}

def display_menu_options(options, prompt, show_min_msg=True, counts=None, show_counts=False):
    """Display numbered menu options and get user selection
    
    Args:
        options: List of options to display
        prompt: Prompt text to show
        show_min_msg: Whether to show the minimum movies message
        counts: Optional dictionary of item counts to display
        show_counts: Whether to display counts next to options
    """
    if not options:
        if show_min_msg:
            print(f"No {prompt.lower()} options available with at least 3 movies for the current filters.")
        else:
            print(f"No {prompt.lower()} options available with current filters.")
        return None
        
    print(f"\n{prompt}:")
    print("0. [Skip/Any]")
    for i, option in enumerate(options, 1):
        if show_counts and counts and option in counts:
            print(f"{i}. {option} ({counts[option]} movies)")
        else:
            print(f"{i}. {option}")
        
    while True:
        selection = input("Enter your choice (number): ").strip()
        if not selection:
            return None
            
        try:
            choice = int(selection)
            if choice == 0:
                return None
            if 1 <= choice <= len(options):
                return options[choice-1]
            print(f"Please enter a number between 0 and {len(options)}.")
        except ValueError:
            # If they entered the actual value instead of a number
            if selection in options:
                return selection
            print("Please enter a valid number or exact option name.")


def query_movies_interactive():
    """Interactive mode for querying movies"""
    print("\n===== StreamGank Movie Data Query Tool =====\n")
    print("Fetching available options from database...")
    print("Note: Only showing filter options with at least 3 movies available\n")
    
    # Get available countries
    countries = get_available_countries()
    country = display_menu_options(countries, "Select Country", show_min_msg=False)
    print(f"Selected country: {country or 'Any'}")
    
    # Get available platforms for selected country with at least 3 movies
    platforms = get_available_platforms(country, min_movies=3)
    platform = display_menu_options(platforms, "Select Platform", show_min_msg=True)
    print(f"Selected platform: {platform or 'Any'}")
    
    # Get available genres for selected country and platform with at least 3 movies
    genres = get_available_genres(country, platform, min_movies=3)
    genre = display_menu_options(genres, "Select Genre", show_min_msg=True)
    print(f"Selected genre: {genre or 'Any'}")
    
    # Get available content types for selected filters with at least 3 movies
    content_types, content_counts = get_available_content_types(country, platform, genre, min_movies=3)
    content_type = display_menu_options(content_types, "Select Content Type", 
                                       show_min_msg=True, 
                                       counts=content_counts,
                                       show_counts=True)
    print(f"Selected content type: {content_type or 'Any'}")
    
    # Get number of movies
    while True:
        try:
            num_input = input("\nNumber of movies to retrieve (default: 3): ").strip()
            num_movies = int(num_input) if num_input else 3
            if num_movies > 0:
                break
            print("Please enter a positive number.")
        except ValueError:
            print("Please enter a valid number.")
    
    print("\nQuerying database with selected filters...")
    print(f"Country: {country or 'Any'}")
    print(f"Platform: {platform or 'Any'}")
    print(f"Genre: {genre or 'Any'}")
    print(f"Content Type: {content_type or 'Any'}")
    print(f"Number of movies: {num_movies}")
    
    # Query movies
    movies = extract_movie_data(
        num_movies=num_movies,
        country=country,
        platform=platform,
        genre=genre,
        content_type=content_type,
        debug=True
    )
    
    # Display results
    if movies:
        print("\n===== Results =====")
        print(f"Found {len(movies)} movies matching your filter criteria:")
        print(f"- Country: {country or 'Any'}")
        print(f"- Platform: {platform or 'Any'}")
        print(f"- Genre: {genre or 'Any'}")
        print(f"- Content Type: {content_type or 'Any'}")
        print(f"- Number requested: {num_movies}")
        
        for i, movie in enumerate(movies, 1):
            print(f"\n----- Movie {i} of {len(movies)} -----")
            print(f"Title: {movie['title']} ({movie['year']})")
            print(f"IMDB: {movie['imdb']}")
            print(f"Platform: {movie['platform']}")
            print(f"Genres: {', '.join(movie['genres'])}")
            print(f"Content Type: {movie['content_type']}")
            print(f"Runtime: {movie['runtime']}")
            if movie['poster_url']:
                print(f"Poster: {movie['poster_url']}")
    else:
        print("\nNo movies found matching your criteria or database error occurred.")


def main():
    """Main function to run script"""
    parser = argparse.ArgumentParser(description="Query movie data from StreamGank database")
    parser.add_argument("--country", help="Country code filter (e.g., US, UK)")
    parser.add_argument("--platform", help="Platform filter (e.g., Netflix, Prime)")
    parser.add_argument("--genre", help="Genre filter (e.g., Action, Comedy)")
    parser.add_argument("--content_type", help="Content type filter (Movie or Series)")
    parser.add_argument("--num_movies", type=int, default=3, help="Number of movies to retrieve")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    parser.add_argument("--output", help="Output file path for JSON results")
    
    args = parser.parse_args()
    
    # Check if any arguments provided
    if len(sys.argv) > 1:
        # Command line mode
        movies = extract_movie_data(
            num_movies=args.num_movies,
            country=args.country,
            platform=args.platform,
            genre=args.genre,
            content_type=args.content_type,
            debug=args.debug
        )
        
        if movies:
            if args.output:
                with open(args.output, 'w') as f:
                    json.dump(movies, f, indent=2)
                print(f"Results saved to {args.output}")
            else:
                print(json.dumps(movies, indent=2))
        else:
            print("No movies found or database error occurred. Please check your database connection and try again.")
            return 1
    else:
        # Interactive mode
        query_movies_interactive()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
