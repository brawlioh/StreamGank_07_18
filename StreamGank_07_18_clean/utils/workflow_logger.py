"""
StreamGank Professional Workflow Logger

This module provides structured, workflow-based logging for the StreamGank video generation system.
Designed for professional monitoring, debugging, and progress tracking.

Features:
- Workflow step tracking with timing
- Structured log formats for easy parsing
- Progress indicators and status updates
- Error correlation and context preservation
- Integration with monitoring systems
"""

import json
import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from pathlib import Path
import uuid

class WorkflowLogger:
    """
    Professional workflow logger for StreamGank video generation.
    
    Provides structured logging with workflow context, progress tracking,
    and professional formatting for monitoring and debugging.
    """
    
    def __init__(self, workflow_id: Optional[str] = None, job_id: Optional[str] = None):
        """
        Initialize workflow logger with unique identifiers.
        
        Args:
            workflow_id: Unique workflow identifier (auto-generated if None)
            job_id: Job identifier for queue management (optional)
        """
        self.workflow_id = workflow_id or f"wf_{uuid.uuid4().hex[:8]}"
        self.job_id = job_id
        self.start_time = time.time()
        self.current_step = None
        self.step_start_time = None
        self.total_steps = 7  # Default for full workflow
        self.completed_steps = 0
        
        # Configure structured logger
        self.logger = logging.getLogger(f"streamgank.workflow.{self.workflow_id}")
        
        # Workflow context for all logs
        self.base_context = {
            'workflow_id': self.workflow_id,
            'job_id': self.job_id,
            'timestamp': None,  # Will be set per log
            'workflow_duration': None  # Will be calculated per log
        }
    
    def _get_log_context(self, additional_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get complete log context with timing information."""
        current_time = time.time()
        context = self.base_context.copy()
        context.update({
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'workflow_duration': round(current_time - self.start_time, 2),
            'current_step': self.current_step,
            'progress_percentage': round((self.completed_steps / self.total_steps) * 100, 1) if self.total_steps > 0 else 0
        })
        
        if additional_context:
            context.update(additional_context)
            
        return context
    
    def workflow_start(self, parameters: Dict[str, Any]) -> None:
        """Log workflow start with parameters."""
        context = self._get_log_context({
            'event': 'workflow_start',
            'parameters': parameters,
            'total_steps': self.total_steps
        })
        
        self.logger.info("🚀 WORKFLOW STARTED", extra={'structured': context})
        self.logger.info("=" * 80)
        self.logger.info(f"📋 WORKFLOW CONFIGURATION:")
        for key, value in parameters.items():
            self.logger.info(f"   {key}: {value}")
        self.logger.info("=" * 80)
    
    def step_start(self, step_number: int, step_name: str, description: str = "") -> None:
        """Log the start of a workflow step."""
        self.current_step = step_name
        self.step_start_time = time.time()
        
        context = self._get_log_context({
            'event': 'step_start',
            'step_number': step_number,
            'step_name': step_name,
            'step_description': description
        })
        
        progress_bar = self._get_progress_bar()
        
        self.logger.info(f"\n📊 {progress_bar}")
        self.logger.info(f"🔄 STEP {step_number}/{self.total_steps}: {step_name.upper()}")
        if description:
            self.logger.info(f"   {description}")
        
        # Log structured data for monitoring systems
        self.logger.debug("Step started", extra={'structured': context})
    
    def step_progress(self, message: str, details: Dict[str, Any] = None) -> None:
        """Log progress within a step."""
        context = self._get_log_context({
            'event': 'step_progress',
            'message': message,
            'details': details or {}
        })
        
        self.logger.info(f"   ⏳ {message}")
        if details:
            for key, value in details.items():
                if isinstance(value, (list, dict)):
                    self.logger.info(f"      {key}: {len(value) if isinstance(value, list) else len(value.keys())} items")
                else:
                    self.logger.info(f"      {key}: {value}")
        
        self.logger.debug("Step progress", extra={'structured': context})
    
    def step_complete(self, step_number: int, step_name: str, results: Dict[str, Any] = None) -> None:
        """Log completion of a workflow step."""
        step_duration = time.time() - self.step_start_time if self.step_start_time else 0
        self.completed_steps = step_number
        
        context = self._get_log_context({
            'event': 'step_complete',
            'step_number': step_number,
            'step_name': step_name,
            'step_duration': round(step_duration, 2),
            'results': results or {}
        })
        
        self.logger.info(f"✅ STEP {step_number} COMPLETED in {step_duration:.1f}s")
        if results:
            for key, value in results.items():
                if isinstance(value, list):
                    self.logger.info(f"   📊 {key}: {len(value)} items")
                elif isinstance(value, dict):
                    self.logger.info(f"   📊 {key}: {len(value.keys())} items")
                else:
                    self.logger.info(f"   📊 {key}: {value}")
        
        self.logger.debug("Step completed", extra={'structured': context})
        
        # Reset step tracking
        self.current_step = None
        self.step_start_time = None
    
    def step_error(self, step_number: int, step_name: str, error: Exception, context_data: Dict[str, Any] = None) -> None:
        """Log a step error with full context."""
        step_duration = time.time() - self.step_start_time if self.step_start_time else 0
        
        context = self._get_log_context({
            'event': 'step_error',
            'step_number': step_number,
            'step_name': step_name,
            'step_duration': round(step_duration, 2),
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context_data': context_data or {}
        })
        
        self.logger.error(f"❌ STEP {step_number} FAILED: {step_name}")
        self.logger.error(f"   💥 Error: {type(error).__name__}: {str(error)}")
        self.logger.error(f"   ⏱️ Step duration before failure: {step_duration:.1f}s")
        
        if context_data:
            self.logger.error("   📋 Context data:")
            for key, value in context_data.items():
                self.logger.error(f"      {key}: {value}")
        
        self.logger.error("Step failed", extra={'structured': context})
    
    def workflow_complete(self, final_results: Dict[str, Any]) -> None:
        """Log successful workflow completion."""
        total_duration = time.time() - self.start_time
        
        context = self._get_log_context({
            'event': 'workflow_complete',
            'total_duration': round(total_duration, 2),
            'completed_steps': self.completed_steps,
            'final_results': final_results
        })
        
        self.logger.info("\n🎉 WORKFLOW COMPLETED SUCCESSFULLY!")
        self.logger.info("=" * 80)
        self.logger.info(f"⏰ Total Duration: {total_duration:.1f}s ({total_duration/60:.1f} minutes)")
        self.logger.info(f"📊 Steps Completed: {self.completed_steps}/{self.total_steps}")
        
        # Log key results
        if 'final_video_url' in final_results:
            self.logger.info(f"🎯 Final Video: {final_results['final_video_url']}")
        
        if 'assets_created' in final_results:
            assets = final_results['assets_created']
            self.logger.info("📦 Assets Generated:")
            for asset_type, asset_data in assets.items():
                if isinstance(asset_data, list):
                    self.logger.info(f"   {asset_type}: {len(asset_data)} items")
                else:
                    self.logger.info(f"   {asset_type}: ✅")
        
        self.logger.info("=" * 80)
        self.logger.info("Workflow completed", extra={'structured': context})
    
    def workflow_error(self, error: Exception, failed_step: int = None, context_data: Dict[str, Any] = None) -> None:
        """Log workflow failure with complete context."""
        total_duration = time.time() - self.start_time
        
        context = self._get_log_context({
            'event': 'workflow_error',
            'total_duration': round(total_duration, 2),
            'failed_step': failed_step,
            'completed_steps': self.completed_steps,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context_data': context_data or {}
        })
        
        self.logger.error("\n❌ WORKFLOW FAILED")
        self.logger.error("=" * 80)
        self.logger.error(f"💥 Error: {type(error).__name__}: {str(error)}")
        if failed_step:
            self.logger.error(f"📍 Failed at step: {failed_step}")
        self.logger.error(f"⏰ Duration before failure: {total_duration:.1f}s")
        self.logger.error(f"✅ Steps completed: {self.completed_steps}/{self.total_steps}")
        
        if context_data:
            self.logger.error("📋 Context data at time of failure:")
            for key, value in context_data.items():
                self.logger.error(f"   {key}: {value}")
        
        self.logger.error("=" * 80)
        self.logger.error("Workflow failed", extra={'structured': context})
    
    def log_asset_status(self, asset_type: str, assets: List[str], step_name: str = None) -> None:
        """Log the status of generated assets."""
        context = self._get_log_context({
            'event': 'asset_status',
            'asset_type': asset_type,
            'asset_count': len(assets),
            'step_name': step_name or self.current_step
        })
        
        self.logger.info(f"📦 {asset_type.upper()}: {len(assets)} items")
        for i, asset in enumerate(assets, 1):
            # Show just the filename or last part of URL for cleaner logs
            asset_name = asset.split('/')[-1] if '/' in asset else asset
            self.logger.info(f"   {i}. {asset_name}")
        
        self.logger.debug("Asset status logged", extra={'structured': context})
    
    def log_external_service_call(self, service: str, operation: str, duration: float = None, status: str = "success") -> None:
        """Log external service calls for monitoring."""
        context = self._get_log_context({
            'event': 'external_service_call',
            'service': service,
            'operation': operation,
            'duration': duration,
            'status': status
        })
        
        duration_text = f" ({duration:.2f}s)" if duration else ""
        status_emoji = "✅" if status == "success" else "❌" if status == "error" else "⏳"
        
        self.logger.info(f"   🔗 {service} {operation}: {status_emoji}{duration_text}")
        self.logger.debug("External service call", extra={'structured': context})
    
    def _get_progress_bar(self, width: int = 20) -> str:
        """Generate a visual progress bar."""
        if self.total_steps == 0:
            return "[████████████████████] 100%"
        
        progress = self.completed_steps / self.total_steps
        filled = int(width * progress)
        bar = "█" * filled + "░" * (width - filled)
        percentage = progress * 100
        
        return f"[{bar}] {percentage:.0f}% | Step {self.completed_steps + 1}/{self.total_steps}"

class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured logging with JSON output for monitoring systems."""
    
    def format(self, record):
        # Standard format for console
        formatted = super().format(record)
        
        # Add structured data if present
        if hasattr(record, 'structured'):
            # For file/monitoring output, add JSON
            structured_data = json.dumps(record.structured, indent=None, separators=(',', ':'))
            return f"{formatted} | STRUCTURED: {structured_data}"
        
        return formatted

def setup_workflow_logging(workflow_id: str = None, job_id: str = None, log_level: str = "INFO") -> WorkflowLogger:
    """
    Set up professional workflow logging for StreamGank.
    
    Args:
        workflow_id: Unique workflow identifier
        job_id: Job identifier for queue management
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    
    Returns:
        WorkflowLogger: Configured workflow logger instance
    """
    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger("streamgank")
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler with UTF-8 encoding support for emojis
    import sys
    import io
    
    # Fix Windows console encoding for emoji support
    if sys.platform.startswith('win'):
        try:
            # Try to set console to UTF-8 mode
            import os
            os.system('chcp 65001 >nul 2>&1')  # Set console to UTF-8
            
            # Reconfigure stdout to handle UTF-8
            if hasattr(sys.stdout, 'reconfigure'):
                sys.stdout.reconfigure(encoding='utf-8', errors='replace')
                sys.stderr.reconfigure(encoding='utf-8', errors='replace')
            else:
                # Fallback for older Python versions
                sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
                sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
        except Exception as e:
            # If UTF-8 setup fails, we'll continue with default encoding
            pass
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler with structured formatting
    workflow_id_clean = workflow_id or f"wf_{uuid.uuid4().hex[:8]}"
    log_file = log_dir / f"workflow_{workflow_id_clean}.log"
    
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_formatter = StructuredFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    # Create workflow logger
    workflow_logger = WorkflowLogger(workflow_id=workflow_id_clean, job_id=job_id)
    
    # Log setup completion
    workflow_logger.logger.info(f"📝 Workflow logging initialized: {log_file}")
    
    return workflow_logger

# Example usage and integration patterns
if __name__ == "__main__":
    # Example of professional workflow logging
    logger = setup_workflow_logging(workflow_id="example_001", job_id="gui_job_123")
    
    # Start workflow
    logger.workflow_start({
        'country': 'US',
        'genre': 'Horror',
        'platform': 'Netflix',
        'num_movies': 3
    })
    
    # Example steps
    logger.step_start(1, "database_extraction", "Extracting top movies from database")
    logger.step_progress("Connecting to Supabase database")
    logger.log_external_service_call("Supabase", "query", 1.2, "success")
    logger.step_progress("Processing query results", {'movies_found': 5})
    logger.step_complete(1, "database_extraction", {'movies_extracted': 3})
    
    # Example completion
    logger.workflow_complete({
        'final_video_url': 'https://example.com/video.mp4',
        'assets_created': {
            'posters': ['poster1.jpg', 'poster2.jpg', 'poster3.jpg'],
            'clips': ['clip1.mp4', 'clip2.mp4', 'clip3.mp4']
        }
    })