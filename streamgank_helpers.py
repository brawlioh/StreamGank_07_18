#!/usr/bin/env python3
"""
StreamGank Helper Functions
===========================

This module contains helper functions for mapping database values to StreamGank URL parameters
based on country-specific localization requirements.

Author: StreamGank Video Generator
Created: 2025
"""


def get_genre_mapping_by_country(country_code):
    """
    Get genre mapping dictionary based on country code for StreamGank URL parameters
    
    Args:
        country_code (str): Country code (e.g., 'FR', 'US', 'DE', etc.)
        
    Returns:
        dict: Mapping from database genre names to StreamGank URL genre parameters
        
    Example:
        >>> mapping = get_genre_mapping_by_country('FR')
        >>> mapping.get('Horreur')  # Returns 'Horreur'
        >>> mapping.get('Horror')   # Returns 'Horreur' (cross-language support)
    """
    
    # Base English genre mapping (default for most countries)
    english_genres = {
        'Action & Adventure': 'Action%20%26%20Adventure',
        'Action': 'Action%20%26%20Adventure', 
        'Adventure': 'Action%20%26%20Adventure',
        'Animation': 'Animation',
        'Comedy': 'Comedy',
        'Crime': 'Crime',
        'Documentary': 'Documentary',
        'Drama': 'Drama',
        'Drame': 'Drama',  # Handle French input
        'Fantasy': 'Fantasy',
        'Fantastique': 'Fantasy',  # Handle French input
        'History': 'History',
        'Histoire': 'History',  # Handle French input
        'Horror': 'Horror',
        'Horreur': 'Horror',  # Handle French input
        'Kids & Family': 'Kids%20%26%20Family',
        'Family': 'Kids%20%26%20Family',
        'Made in Europe': 'Made%20in%20Europe',
        'Music & Musical': 'Music%20%26%20Musical',
        'Musical': 'Music%20%26%20Musical',
        'Mystery & Thriller': 'Mystery%20%26%20Thriller',
        'Mystery': 'Mystery%20%26%20Thriller',
        'Thriller': 'Mystery%20%26%20Thriller',
        'Reality TV': 'Reality%20TV',
        'Romance': 'Romance',
        'Science-Fiction': 'Science-Fiction',
        'Sci-Fi': 'Science-Fiction',
        'Sport': 'Sport',
        'War & Military': 'War%20%26%20Military',
        'War': 'War%20%26%20Military',
        'Military': 'War%20%26%20Military',
        'Western': 'Western'
    }
    
    # French genre mapping for StreamGank France
    french_genres = {
        # French database genres → French StreamGank URL parameters
        'Action & Aventure': 'Action%20%26%20Aventure',
        'Action': 'Action%20%26%20Aventure',
        'Aventure': 'Action%20%26%20Aventure',
        'Animation': 'Animation',
        'Comédie': 'Comédie',
        'Comedy': 'Comédie',  # Handle English input
        'Comédie Romantique': 'Comédie%20Romantique',
        'Romantic Comedy': 'Comédie%20Romantique',
        'Crime & Thriller': 'Crime%20%26%20Thriller',
        'Crime': 'Crime%20%26%20Thriller',
        'Thriller': 'Crime%20%26%20Thriller',
        'Documentaire': 'Documentaire',
        'Documentary': 'Documentaire',  # Handle English input
        'Drame': 'Drame',
        'Drama': 'Drame',  # Handle English input
        'Fantastique': 'Fantastique',
        'Fantasy': 'Fantastique',  # Handle English input
        'Film de guerre': 'Film%20de%20guerre',
        'War': 'Film%20de%20guerre',
        'War & Military': 'Film%20de%20guerre',
        'Histoire': 'Histoire',
        'History': 'Histoire',  # Handle English input
        'Horreur': 'Horreur',
        'Horror': 'Horreur',  # Handle English input
        'Musique & Comédie Musicale': 'Musique%20%26%20Comédie%20Musicale',
        'Music & Musical': 'Musique%20%26%20Comédie%20Musicale',
        'Musical': 'Musique%20%26%20Comédie%20Musicale',
        'Mystère & Thriller': 'Mystère%20%26%20Thriller',
        'Mystery & Thriller': 'Mystère%20%26%20Thriller',
        'Mystery': 'Mystère%20%26%20Thriller',
        'Pour enfants': 'Pour%20enfants',
        'Kids & Family': 'Pour%20enfants',
        'Family': 'Pour%20enfants',
        'Reality TV': 'Reality%20TV',
        'Romance': 'Romance',
        'Réalisé en Europe': 'Réalisé%20en%20Europe',
        'Made in Europe': 'Réalisé%20en%20Europe',
        'Science-Fiction': 'Science-Fiction',
        'Sci-Fi': 'Science-Fiction',
        'Sport & Fitness': 'Sport%20%26%20Fitness',
        'Sport': 'Sport%20%26%20Fitness',
        'Fitness': 'Sport%20%26%20Fitness',
        'Western': 'Western'
    }
    
    # Country-specific genre mappings
    country_mappings = {
        'FR': french_genres,
        'US': english_genres,
        'GB': english_genres,
        'UK': english_genres,
        'CA': english_genres,
        'AU': english_genres,
        # Add more countries as needed
        # 'DE': german_genres,  # Could add German mapping later
        # 'ES': spanish_genres,  # Could add Spanish mapping later
        # 'IT': italian_genres,  # Could add Italian mapping later
    }
    
    # Return country-specific mapping or default to English
    return country_mappings.get(country_code, english_genres)


def get_platform_mapping_by_country(country_code):
    """
    Get platform mapping dictionary based on country code for StreamGank URL parameters
    
    Args:
        country_code (str): Country code (e.g., 'FR', 'US', 'DE', etc.)
        
    Returns:
        dict: Mapping from database platform names to StreamGank URL platform parameters
        
    Example:
        >>> mapping = get_platform_mapping_by_country('FR')
        >>> mapping.get('Canal+')  # Returns 'canal' (French-specific)
        >>> mapping.get('Netflix') # Returns 'netflix' (universal)
    """
    
    # Base platform mapping (consistent across most countries)
    base_platforms = {
        'Netflix': 'netflix',
        'Disney+': 'disney',
        'Disney Plus': 'disney',
        'Amazon Prime': 'amazon',
        'Prime Video': 'amazon',
        'Amazon Prime Video': 'amazon',
        'HBO Max': 'hbo',
        'HBO': 'hbo',
        'Apple TV+': 'apple',
        'Apple TV': 'apple',
        'Hulu': 'hulu',
        'Paramount+': 'paramount',
        'Paramount Plus': 'paramount'
    }
    
    # Country-specific platform mappings (can extend for localized platform names)
    french_platforms = {
        **base_platforms,
        # Add French-specific platform names
        'Canal+': 'canal',
        'France TV': 'francetv',
        'MyCanal': 'canal'
    }
    
    country_mappings = {
        'FR': french_platforms,
        'US': base_platforms,
        'GB': base_platforms,
        'UK': base_platforms,
        'CA': base_platforms,
        'AU': base_platforms,
    }
    
    return country_mappings.get(country_code, base_platforms)


def get_content_type_mapping_by_country(country_code):
    """
    Get content type mapping dictionary based on country code for StreamGank URL parameters
    
    Args:
        country_code (str): Country code (e.g., 'FR', 'US', 'DE', etc.)
        
    Returns:
        dict: Mapping from database content types to StreamGank URL type parameters
        
    Example:
        >>> mapping = get_content_type_mapping_by_country('FR')
        >>> mapping.get('Série')    # Returns 'Serie'
        >>> mapping.get('Émission') # Returns 'Serie' (French TV show term)
    """
    
    # Base content type mapping
    english_types = {
        'Film': 'Film',
        'Movie': 'Film',
        'Série': 'Serie',
        'Series': 'Serie',
        'TV Show': 'Serie',
        'TV Series': 'Serie'
    }
    
    # French content type mapping
    french_types = {
        'Film': 'Film',
        'Movie': 'Film',
        'Série': 'Serie',
        'Series': 'Serie',
        'TV Show': 'Serie',
        'TV Series': 'Serie',
        'Émission': 'Serie'  # French TV show term
    }
    
    country_mappings = {
        'FR': french_types,
        'US': english_types,
        'GB': english_types,
        'UK': english_types,
        'CA': english_types,
        'AU': english_types,
    }
    
    return country_mappings.get(country_code, english_types)


def build_streamgank_url(country=None, genre=None, platform=None, content_type=None):
    """
    Build a complete StreamGank URL with localized parameters based on country
    
    Args:
        country (str): Country code for localization
        genre (str): Genre to filter by
        platform (str): Platform to filter by  
        content_type (str): Content type to filter by
        
    Returns:
        str: Complete StreamGank URL with properly encoded parameters
        
    Example:
        >>> url = build_streamgank_url('FR', 'Horreur', 'Netflix', 'Série')
        >>> print(url)
        https://streamgank.com/?country=FR&genres=Horreur&platforms=netflix&type=Serie
    """
    
    base_url = "https://streamgank.com/?"
    url_params = []
    
    if country:
        url_params.append(f"country={country}")
    
    if genre:
        # Use country-specific genre mapping
        genre_mapping = get_genre_mapping_by_country(country)
        streamgank_genre = genre_mapping.get(genre, genre)
        url_params.append(f"genres={streamgank_genre}")
    
    if platform:
        # Use country-specific platform mapping
        platform_mapping = get_platform_mapping_by_country(country)
        streamgank_platform = platform_mapping.get(platform, platform.lower())
        url_params.append(f"platforms={streamgank_platform}")
    
    if content_type:
        # Use country-specific content type mapping
        type_mapping = get_content_type_mapping_by_country(country)
        streamgank_type = type_mapping.get(content_type, content_type)
        url_params.append(f"type={streamgank_type}")
    
    # Construct final URL
    if url_params:
        return base_url + "&".join(url_params)
    else:
        return "https://streamgank.com/"  # Default homepage if no params


def get_supported_countries():
    """
    Get list of supported country codes
    
    Returns:
        list: List of supported country codes
        
    Example:
        >>> countries = get_supported_countries()
        >>> print(countries)
        ['FR', 'US', 'GB', 'UK', 'CA', 'AU']
    """
    
    return ['FR', 'US', 'GB', 'UK', 'CA', 'AU']


def get_available_genres_for_country(country_code):
    """
    Get all available genres for a specific country
    
    Args:
        country_code (str): Country code
        
    Returns:
        list: List of available genre names for the country
        
    Example:
        >>> genres = get_available_genres_for_country('FR')
        >>> print(len(genres))  # Should show French + English genre names
    """
    
    mapping = get_genre_mapping_by_country(country_code)
    return list(mapping.keys())


def get_available_platforms_for_country(country_code):
    """
    Get all available platforms for a specific country
    
    Args:
        country_code (str): Country code
        
    Returns:
        list: List of available platform names for the country
    """
    
    mapping = get_platform_mapping_by_country(country_code)
    return list(mapping.keys())


# For backward compatibility and convenience
def get_all_mappings_for_country(country_code):
    """
    Get all mappings (genres, platforms, content types) for a country in one call
    
    Args:
        country_code (str): Country code
        
    Returns:
        dict: Dictionary containing all mappings
        
    Example:
        >>> mappings = get_all_mappings_for_country('FR')
        >>> print(mappings.keys())
        dict_keys(['genres', 'platforms', 'content_types'])
    """
    
    return {
        'genres': get_genre_mapping_by_country(country_code),
        'platforms': get_platform_mapping_by_country(country_code),
        'content_types': get_content_type_mapping_by_country(country_code)
    } 