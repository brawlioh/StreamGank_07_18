"""
StreamGank Constants Configuration

This module contains fixed values, mappings, and constants used throughout
the StreamGank system including platform colors, genre mappings, and 
supported configurations.
"""

from typing import Dict, List, Tuple

# =============================================================================
# PLATFORM COLOR SCHEMES
# =============================================================================

PLATFORM_COLORS = {
    # Netflix
    'Netflix': {
        'primary': (229, 9, 20),     # Netflix red
        'secondary': (139, 0, 0),    # Dark red
        'accent': (255, 255, 255),   # White text
        'background': (0, 0, 0)      # Black background
    },
    
    # Max (formerly HBO Max)
    'Max': {
        'primary': (0, 229, 255),    # Max blue
        'secondary': (0, 100, 139),  # Dark blue
        'accent': (255, 255, 255),   # White text
        'background': (18, 18, 18)   # Dark gray
    },
    
    # Prime Video
    'Prime Video': {
        'primary': (0, 168, 225),    # Prime blue
        'secondary': (0, 80, 120),   # Darker blue
        'accent': (255, 255, 255),   # White text
        'background': (35, 47, 52)   # Dark blue-gray
    },
    
    # Disney+
    'Disney+': {
        'primary': (17, 60, 207),    # Disney blue
        'secondary': (10, 30, 100),  # Dark blue
        'accent': (255, 255, 255),   # White text
        'background': (26, 29, 41)   # Dark navy
    },
    
    # Hulu
    'Hulu': {
        'primary': (28, 231, 131),   # Hulu green
        'secondary': (10, 120, 60),  # Dark green
        'accent': (255, 255, 255),   # White text
        'background': (11, 22, 34)   # Dark blue
    },
    
    # Apple TV+
    'Apple TV+': {
        'primary': (27, 27, 27),     # Apple dark gray
        'secondary': (60, 60, 60),   # Medium gray
        'accent': (255, 255, 255),   # White text
        'background': (0, 0, 0)      # Black
    },
    
    # Paramount+
    'Paramount+': {
        'primary': (0, 102, 204),    # Paramount blue
        'secondary': (0, 51, 102),   # Dark blue
        'accent': (255, 255, 255),   # White text
        'background': (23, 23, 23)   # Dark gray
    }
}

# =============================================================================
# GENRE COLOR SCHEMES
# =============================================================================

GENRE_COLORS = {
    # Horror/Thriller
    'Horror': {
        'primary': (139, 0, 0),      # Dark red
        'secondary': (60, 0, 0),     # Darker red
        'accent': (255, 255, 255),   # White text
        'mood': 'intense'
    },
    'Horreur': {  # French
        'primary': (139, 0, 0),
        'secondary': (60, 0, 0),
        'accent': (255, 255, 255),
        'mood': 'intense'
    },
    'Thriller': {
        'primary': (75, 0, 130),     # Indigo
        'secondary': (30, 0, 60),    # Dark indigo
        'accent': (255, 255, 255),
        'mood': 'suspenseful'
    },
    'Mystery & Thriller': {
        'primary': (75, 0, 130),
        'secondary': (30, 0, 60),
        'accent': (255, 255, 255),  
        'mood': 'mysterious'
    },
    
    # Action/Adventure
    'Action': {
        'primary': (255, 69, 0),     # Orange red
        'secondary': (180, 30, 0),   # Dark orange
        'accent': (255, 255, 255),
        'mood': 'energetic'
    },
    'Action & Adventure': {
        'primary': (255, 69, 0),
        'secondary': (180, 30, 0),
        'accent': (255, 255, 255),
        'mood': 'adventurous'
    },
    'Action & Aventure': {  # French
        'primary': (255, 69, 0),
        'secondary': (180, 30, 0),
        'accent': (255, 255, 255),
        'mood': 'adventurous'
    },
    
    # Comedy
    'Comedy': {
        'primary': (255, 165, 0),    # Orange
        'secondary': (200, 100, 0),  # Dark orange
        'accent': (255, 255, 255),
        'mood': 'cheerful'
    },
    'Comédie': {  # French
        'primary': (255, 165, 0),
        'secondary': (200, 100, 0),
        'accent': (255, 255, 255),
        'mood': 'cheerful'
    },
    
    # Drama
    'Drama': {
        'primary': (25, 25, 112),    # Dark blue
        'secondary': (10, 10, 50),   # Darker blue
        'accent': (255, 255, 255),
        'mood': 'emotional'
    },
    'Drame': {  # French
        'primary': (25, 25, 112),
        'secondary': (10, 10, 50),
        'accent': (255, 255, 255),
        'mood': 'emotional'
    },
    
    # Fantasy/Sci-Fi
    'Fantasy': {
        'primary': (148, 0, 211),    # Dark violet
        'secondary': (80, 0, 120),   # Darker violet
        'accent': (255, 255, 255),
        'mood': 'magical'
    },
    'Fantastique': {  # French
        'primary': (148, 0, 211),
        'secondary': (80, 0, 120),
        'accent': (255, 255, 255),
        'mood': 'magical'
    },
    'Science-Fiction': {
        'primary': (0, 191, 255),    # Deep sky blue
        'secondary': (0, 100, 150),  # Dark blue
        'accent': (255, 255, 255),
        'mood': 'futuristic'
    },
    
    # Romance
    'Romance': {
        'primary': (255, 20, 147),   # Deep pink
        'secondary': (139, 10, 80),  # Dark pink
        'accent': (255, 255, 255),
        'mood': 'romantic'
    },
    
    # Documentary
    'Documentary': {
        'primary': (70, 130, 180),   # Steel blue
        'secondary': (30, 60, 90),   # Dark steel blue
        'accent': (255, 255, 255),
        'mood': 'informative'
    },
    'Documentaire': {  # French
        'primary': (70, 130, 180),
        'secondary': (30, 60, 90),
        'accent': (255, 255, 255),
        'mood': 'informative'
    }
}

# =============================================================================
# CONTENT TYPE MAPPINGS
# =============================================================================

CONTENT_TYPES = {
    # English
    'Film': 'movie',
    'Movie': 'movie', 
    'Series': 'series',
    'TV Show': 'series',
    'Show': 'series',
    
    # French
    'Série': 'series',
    'Film': 'movie',
    
    # German
    'Serie': 'series',
    'Serien': 'series',
    
    # Spanish
    'Película': 'movie',
    'Serie': 'series',
    
    # Portuguese
    'Filme': 'movie',
    'Série': 'series'
}

# =============================================================================
# SUPPORTED COUNTRIES AND REGIONS
# =============================================================================

SUPPORTED_COUNTRIES = {
    'US': {
        'name': 'United States',
        'language': 'en',
        'currency': 'USD',
        'timezone': 'America/New_York',
        'content_rating_system': 'MPAA'
    },
    'FR': {
        'name': 'France',
        'language': 'fr', 
        'currency': 'EUR',
        'timezone': 'Europe/Paris',
        'content_rating_system': 'CSA'
    },
    'DE': {
        'name': 'Germany',
        'language': 'de',
        'currency': 'EUR', 
        'timezone': 'Europe/Berlin',
        'content_rating_system': 'FSK'
    },
    'IT': {
        'name': 'Italy',
        'language': 'it',
        'currency': 'EUR',
        'timezone': 'Europe/Rome',
        'content_rating_system': 'ANICA'
    },
    'ES': {
        'name': 'Spain',
        'language': 'es',
        'currency': 'EUR',
        'timezone': 'Europe/Madrid',
        'content_rating_system': 'ICAA'
    },
    'PT': {
        'name': 'Portugal',
        'language': 'pt',
        'currency': 'EUR',
        'timezone': 'Europe/Lisbon',
        'content_rating_system': 'IGAC'
    },
    'GB': {
        'name': 'United Kingdom',
        'language': 'en',
        'currency': 'GBP',
        'timezone': 'Europe/London', 
        'content_rating_system': 'BBFC'
    },
    'CA': {
        'name': 'Canada',
        'language': 'en',
        'currency': 'CAD',
        'timezone': 'America/Toronto',
        'content_rating_system': 'CRTC'
    }
}

# =============================================================================
# GENRE MAPPINGS BY COUNTRY (US-ONLY SIMPLIFIED)
# =============================================================================

US_GENRE_MAPPING = {
    "Action & Adventure": "Action & Adventure",
    "Animation": "Animation", 
    "Comedy": "Comedy",
    "Crime": "Crime",
    "Documentary": "Documentary",
    "Drama": "Drama", 
    "Fantasy": "Fantasy",
    "History": "History",
    "Horror": "Horror",
    "Kids & Family": "Kids & Family",
    "Made in Europe": "Made in Europe",
    "Music & Musical": "Music & Musical", 
    "Mystery & Thriller": "Mystery & Thriller",
    "Reality TV": "Reality TV",
    "Romance": "Romance",
    "Science-Fiction": "Science-Fiction",
    "Sport": "Sport",
    "War & Military": "War & Military",
    "Western": "Western"
}

# =============================================================================
# PLATFORM MAPPINGS
# =============================================================================

PLATFORM_MAPPING = {
    "Netflix": "Netflix",
    "Prime Video": "Prime Video", 
    "Disney+": "Disney+",
    "Max": "Max",
    "Hulu": "Hulu",
    "Apple TV+": "Apple TV+",
    "Paramount+": "Paramount+",
    "Peacock": "Peacock",
    "HBO Max": "Max",  # Legacy mapping
    "Amazon Prime": "Prime Video"  # Alternative name
}

# =============================================================================
# SPECIAL TITLE THEMES
# =============================================================================

TITLE_SPECIFIC_COLORS = {
    # Popular series with distinctive branding
    'Wednesday': {
        'primary': (139, 0, 139),    # Dark magenta
        'secondary': (70, 0, 70),    # Darker magenta
        'accent': (255, 255, 255),
        'mood': 'gothic'
    },
    'Stranger Things': {
        'primary': (220, 20, 60),    # Crimson
        'secondary': (120, 10, 30),  # Dark crimson
        'accent': (255, 255, 255),
        'mood': '80s_nostalgia'
    },
    'The Last of Us': {
        'primary': (85, 107, 47),    # Olive drab
        'secondary': (40, 50, 20),   # Dark olive
        'accent': (255, 255, 255),
        'mood': 'post_apocalyptic'
    },
    'The Witcher': {
        'primary': (105, 105, 105),  # Dim gray
        'secondary': (47, 79, 79),   # Dark slate gray
        'accent': (255, 215, 0),     # Gold accent
        'mood': 'medieval_fantasy'
    },
    'House of the Dragon': {
        'primary': (139, 0, 0),      # Dark red
        'secondary': (0, 0, 0),      # Black
        'accent': (255, 215, 0),     # Gold accent
        'mood': 'epic_fantasy'
    }
}

# =============================================================================
# RATING SYSTEMS
# =============================================================================

RATING_MAPPINGS = {
    'MPAA': ['G', 'PG', 'PG-13', 'R', 'NC-17'],
    'CSA': ['Tous publics', '-12', '-16', '-18'],
    'FSK': ['0', '6', '12', '16', '18'],
    'BBFC': ['U', 'PG', '12', '12A', '15', '18'],
    'CRTC': ['G', 'PG', '14A', '18A', 'R']
}

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_platform_colors(platform: str) -> Dict[str, Tuple[int, int, int]]:
    """Get color scheme for a specific platform."""
    return PLATFORM_COLORS.get(platform, PLATFORM_COLORS['Netflix'])


def get_genre_colors(genre: str) -> Dict[str, Tuple[int, int, int]]:
    """Get color scheme for a specific genre."""
    # Check title-specific themes first
    for title, colors in TITLE_SPECIFIC_COLORS.items():
        if title.lower() in genre.lower():
            return colors
    
    # Then check genre colors
    return GENRE_COLORS.get(genre, {
        'primary': (60, 60, 100),
        'secondary': (30, 30, 50), 
        'accent': (255, 255, 255),
        'mood': 'neutral'
    })


def get_thematic_colors(platform: str, genres: List[str], title: str = None) -> Dict[str, Tuple[int, int, int]]:
    """
    Get thematic colors based on platform, genres, and title.
    Priority: Title > Genre > Platform
    """
    # Check title-specific themes first
    if title:
        for title_key, colors in TITLE_SPECIFIC_COLORS.items():
            if title_key.lower() in title.lower():
                return colors
    
    # Check genre colors
    if genres:
        for genre in genres:
            if genre in GENRE_COLORS:
                return GENRE_COLORS[genre]
    
    # Fall back to platform colors
    return get_platform_colors(platform)


def normalize_content_type(content_type: str) -> str:
    """Normalize content type to standard values."""
    return CONTENT_TYPES.get(content_type, 'movie')


def get_country_info(country_code: str) -> Dict[str, str]:
    """Get country information by country code."""
    return SUPPORTED_COUNTRIES.get(country_code, SUPPORTED_COUNTRIES['US'])


def is_supported_country(country_code: str) -> bool:
    """Check if a country is supported."""
    return country_code in SUPPORTED_COUNTRIES


def get_supported_platforms() -> List[str]:
    """Get list of all supported platforms."""
    return list(PLATFORM_MAPPING.keys())


def get_supported_genres() -> List[str]:
    """Get list of all supported genres."""
    return list(US_GENRE_MAPPING.keys())