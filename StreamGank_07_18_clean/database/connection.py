"""
StreamGank Database Connection Management

This module handles Supabase database connections, configuration validation,
and connection testing for the StreamGang video generation system.
"""

import os
import logging
from typing import Optional, Dict, Any
from supabase import create_client, Client

logger = logging.getLogger(__name__)

# =============================================================================
# GLOBAL CONNECTION MANAGEMENT
# =============================================================================

_supabase_client: Optional[Client] = None

def get_supabase_client(force_recreate: bool = False) -> Optional[Client]:
    """
    Get or create Supabase client instance.
    
    Args:
        force_recreate (bool): Force recreation of client instance
        
    Returns:
        Client: Supabase client instance or None if configuration invalid
    """
    global _supabase_client
    
    if _supabase_client is None or force_recreate:
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            logger.error("❌ Missing Supabase configuration (SUPABASE_URL, SUPABASE_KEY)")
            return None
        
        try:
            _supabase_client = create_client(supabase_url, supabase_key)
            logger.debug("✅ Supabase client created successfully")
        except Exception as e:
            logger.error(f"❌ Failed to create Supabase client: {str(e)}")
            return None
    
    return _supabase_client


def test_supabase_connection() -> bool:
    """
    Test Supabase database connection.
    
    Returns:
        bool: True if connection is successful
    """
    logger.info("🔍 Testing Supabase database connection...")
    
    try:
        supabase = get_supabase_client()
        if not supabase:
            logger.error("❌ Could not create Supabase client")
            return False
        
        # Test with a simple query to movies table
        response = supabase.table("movies").select("*").limit(1).execute()
        
        if hasattr(response, 'data') and response.data is not None:
            logger.info(f"✅ Database connection successful ({len(response.data)} test records)")
            return True
        else:
            logger.error("❌ Database query returned invalid response")
            return False
            
    except Exception as e:
        logger.error(f"❌ Database connection failed: {str(e)}")
        return False


def validate_database_config() -> Dict[str, Any]:
    """
    Validate database configuration and environment variables.
    
    Returns:
        dict: Validation results with status and missing variables
    """
    validation_result = {
        'is_valid': True,
        'missing_vars': [],
        'connection_test': False,
        'error_details': []
    }
    
    # Check required environment variables
    required_vars = ['SUPABASE_URL', 'SUPABASE_KEY']
    
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            validation_result['missing_vars'].append(var)
            validation_result['is_valid'] = False
        elif not value.strip():
            validation_result['missing_vars'].append(f"{var} (empty)")
            validation_result['is_valid'] = False
    
    # Test connection if config is valid
    if validation_result['is_valid']:
        try:
            validation_result['connection_test'] = test_supabase_connection()
            if not validation_result['connection_test']:
                validation_result['is_valid'] = False
                validation_result['error_details'].append("Connection test failed")
        except Exception as e:
            validation_result['is_valid'] = False
            validation_result['connection_test'] = False
            validation_result['error_details'].append(f"Connection test error: {str(e)}")
    
    logger.info(f"🔧 Database config validation: {'✅ Valid' if validation_result['is_valid'] else '❌ Invalid'}")
    
    if not validation_result['is_valid']:
        if validation_result['missing_vars']:
            logger.error(f"❌ Missing variables: {', '.join(validation_result['missing_vars'])}")
        if validation_result['error_details']:
            logger.error(f"❌ Errors: {'; '.join(validation_result['error_details'])}")
    
    return validation_result


def get_database_info() -> Dict[str, Any]:
    """
    Get database connection information and statistics.
    
    Returns:
        dict: Database information and connection stats
    """
    info = {
        'connected': False,
        'url_configured': bool(os.getenv("SUPABASE_URL")),
        'key_configured': bool(os.getenv("SUPABASE_KEY")),
        'movies_count': 0,
        'tables_accessible': [],
        'connection_error': None
    }
    
    try:
        supabase = get_supabase_client()
        if supabase:
            info['connected'] = True
            
            # Test movies table access
            try:
                movies_response = supabase.table("movies").select("movie_id").execute()
                if hasattr(movies_response, 'data'):
                    info['movies_count'] = len(movies_response.data)
                    info['tables_accessible'].append('movies')
            except Exception as e:
                logger.warning(f"Movies table access failed: {str(e)}")
            
            # Test other tables
            test_tables = ['movie_localizations', 'movie_genres']
            for table in test_tables:
                try:
                    test_response = supabase.table(table).select("*").limit(1).execute()
                    if hasattr(test_response, 'data'):
                        info['tables_accessible'].append(table)
                except Exception as e:
                    logger.debug(f"Table {table} access test failed: {str(e)}")
    
    except Exception as e:
        info['connection_error'] = str(e)
        logger.error(f"Database info gathering failed: {str(e)}")
    
    return info


def reset_connection() -> bool:
    """
    Reset the database connection by forcing client recreation.
    
    Returns:
        bool: True if reset and reconnection successful
    """
    global _supabase_client
    
    logger.info("🔄 Resetting database connection...")
    
    _supabase_client = None
    
    # Test new connection
    return test_supabase_connection()

# =============================================================================
# CONNECTION CONTEXT MANAGER
# =============================================================================

class DatabaseConnection:
    """
    Context manager for database operations with automatic connection handling.
    
    Usage:
        with DatabaseConnection() as db:
            if db.is_connected():
                response = db.client.table("movies").select("*").execute()
    """
    
    def __init__(self, auto_retry: bool = True):
        """
        Initialize database connection context.
        
        Args:
            auto_retry (bool): Automatically retry connection on failure
        """
        self.auto_retry = auto_retry
        self.client = None
        self._connected = False
    
    def __enter__(self):
        """Enter context and establish connection."""
        self.client = get_supabase_client()
        
        if self.client:
            self._connected = test_supabase_connection()
            
            if not self._connected and self.auto_retry:
                logger.info("🔄 Auto-retrying database connection...")
                self.client = get_supabase_client(force_recreate=True)
                self._connected = test_supabase_connection()
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context (no cleanup needed for Supabase client)."""
        if exc_type:
            logger.error(f"Database operation failed: {exc_val}")
        
        # Supabase client doesn't require explicit closing
        pass
    
    def is_connected(self) -> bool:
        """Check if database connection is active."""
        return self._connected and self.client is not None
    
    def get_client(self) -> Optional[Client]:
        """Get the database client instance."""
        return self.client if self.is_connected() else None