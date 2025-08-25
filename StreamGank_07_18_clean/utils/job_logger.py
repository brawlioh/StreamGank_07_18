"""
Professional Job Logging System for StreamGank
Provides structured, persistent logging for all job processes with rotation and archiving
"""

import os
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Dict, List, Any, Optional


class JobLogger:
    """
    Professional logging system for job processes
    Features: File persistence, JSON structure, log rotation, search capabilities
    """
    
    def __init__(self, base_log_dir: str = "docker_volumes/logs"):
        """
        Initialize job logger with file persistence
        
        Args:
            base_log_dir (str): Base directory for log files
        """
        self.base_log_dir = Path(base_log_dir)
        self.base_log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        self.job_logs_dir = self.base_log_dir / "jobs"
        self.system_logs_dir = self.base_log_dir / "system"
        self.archived_logs_dir = self.base_log_dir / "archived"
        
        for dir_path in [self.job_logs_dir, self.system_logs_dir, self.archived_logs_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # Log rotation settings (must be set before _setup_system_logger)
        self.max_bytes = 10 * 1024 * 1024  # 10MB per log file
        self.backup_count = 5  # Keep 5 backup files
        
        # Configure system logger
        self.system_logger = self._setup_system_logger()
        
        # Active job loggers cache
        self.job_loggers = {}
        
        self.system_logger.info("JobLogger initialized successfully")
    
    def _setup_system_logger(self) -> logging.Logger:
        """Setup system-wide logger for the logging system itself"""
        logger = logging.getLogger("streamgank_job_logger")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = RotatingFileHandler(
                self.system_logs_dir / "job_logger_system.log",
                maxBytes=self.max_bytes,
                backupCount=self.backup_count
            )
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def get_job_logger(self, job_id: str) -> logging.Logger:
        """
        Get or create a dedicated logger for a specific job
        
        Args:
            job_id (str): Unique job identifier
            
        Returns:
            logging.Logger: Configured job logger
        """
        if job_id not in self.job_loggers:
            logger = logging.getLogger(f"job_{job_id}")
            logger.setLevel(logging.INFO)
            
            # Create log file for this job
            job_log_file = self.job_logs_dir / f"{job_id}.log"
            
            handler = RotatingFileHandler(
                job_log_file,
                maxBytes=self.max_bytes,
                backupCount=self.backup_count
            )
            
            # JSON formatter for structured logging
            formatter = logging.Formatter('%(message)s')
            handler.setFormatter(formatter)
            
            logger.addHandler(handler)
            self.job_loggers[job_id] = logger
            
            # Log job start
            self.log_job_event(job_id, "job_started", "Job logging initialized", {
                'log_file': str(job_log_file),
                'timestamp': datetime.utcnow().isoformat()
            })
        
        return self.job_loggers[job_id]
    
    def log_job_event(self, job_id: str, event_type: str, message: str, 
                     details: Dict[str, Any] = None, level: str = "info"):
        """
        Log a structured job event
        
        Args:
            job_id (str): Job identifier
            event_type (str): Type of event (step_start, step_complete, error, etc.)
            message (str): Human readable message
            details (Dict): Additional structured data
            level (str): Log level (info, warning, error, debug)
        """
        logger = self.get_job_logger(job_id)
        
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'job_id': job_id,
            'event_type': event_type,
            'level': level,
            'message': message,
            'details': details or {},
            'process_time': time.time()
        }
        
        # Log as JSON for structured parsing
        log_line = json.dumps(log_entry, ensure_ascii=False)
        
        # Log at appropriate level
        if level == "error":
            logger.error(log_line)
        elif level == "warning":
            logger.warning(log_line)
        elif level == "debug":
            logger.debug(log_line)
        else:
            logger.info(log_line)
        
        # Also log to system logger for monitoring
        self.system_logger.info(f"Job {job_id[-8:]}: {event_type} - {message}")
    
    def log_step_start(self, job_id: str, step_number: int, step_name: str, 
                      details: Dict[str, Any] = None):
        """Log workflow step start"""
        self.log_job_event(
            job_id, 
            "step_start",
            f"Step {step_number}/7 started: {step_name}",
            {
                'step_number': step_number,
                'step_name': step_name,
                'total_steps': 7,
                **(details or {})
            }
        )
    
    def log_step_complete(self, job_id: str, step_number: int, step_name: str,
                         duration: float, details: Dict[str, Any] = None):
        """Log workflow step completion"""
        self.log_job_event(
            job_id,
            "step_complete", 
            f"Step {step_number}/7 completed: {step_name} ({duration:.1f}s)",
            {
                'step_number': step_number,
                'step_name': step_name,
                'duration': duration,
                'total_steps': 7,
                **(details or {})
            },
            "info"
        )
    
    def log_step_error(self, job_id: str, step_number: int, step_name: str,
                      error: str, details: Dict[str, Any] = None):
        """Log workflow step error"""
        self.log_job_event(
            job_id,
            "step_error",
            f"Step {step_number}/7 failed: {step_name} - {error}",
            {
                'step_number': step_number,
                'step_name': step_name,
                'error': error,
                'total_steps': 7,
                **(details or {})
            },
            "error"
        )
    
    def log_workflow_complete(self, job_id: str, total_duration: float,
                             creatomate_id: str = None, details: Dict[str, Any] = None):
        """Log workflow completion"""
        self.log_job_event(
            job_id,
            "workflow_complete",
            f"Workflow completed successfully in {total_duration:.1f}s",
            {
                'total_duration': total_duration,
                'creatomate_id': creatomate_id,
                'steps_completed': 7,
                **(details or {})
            }
        )
    
    def log_workflow_failed(self, job_id: str, error: str, step_number: int = None,
                           details: Dict[str, Any] = None):
        """Log workflow failure"""
        self.log_job_event(
            job_id,
            "workflow_failed",
            f"Workflow failed: {error}",
            {
                'error': error,
                'failed_at_step': step_number,
                **(details or {})
            },
            "error"
        )
    
    def get_job_logs(self, job_id: str, limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Retrieve logs for a specific job
        
        Args:
            job_id (str): Job identifier
            limit (int): Maximum number of log entries to return
            
        Returns:
            List[Dict]: List of log entries
        """
        job_log_file = self.job_logs_dir / f"{job_id}.log"
        
        if not job_log_file.exists():
            return []
        
        logs = []
        try:
            with open(job_log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            log_entry = json.loads(line)
                            logs.append(log_entry)
                        except json.JSONDecodeError:
                            # Handle non-JSON log lines
                            logs.append({
                                'timestamp': datetime.utcnow().isoformat(),
                                'job_id': job_id,
                                'event_type': 'raw_log',
                                'level': 'info',
                                'message': line,
                                'details': {}
                            })
        except Exception as e:
            self.system_logger.error(f"Failed to read logs for job {job_id}: {str(e)}")
            return []
        
        # Return most recent logs first, limited
        return logs[-limit:]
    
    def search_logs(self, job_id: str = None, event_type: str = None, 
                   level: str = None, message_contains: str = None,
                   limit: int = 100) -> List[Dict[str, Any]]:
        """
        Search logs with filters
        
        Args:
            job_id (str): Filter by job ID
            event_type (str): Filter by event type
            level (str): Filter by log level
            message_contains (str): Filter by message content
            limit (int): Maximum results
            
        Returns:
            List[Dict]: Filtered log entries
        """
        if job_id:
            # Search specific job
            logs = self.get_job_logs(job_id)
        else:
            # Search all jobs (this could be expensive)
            logs = []
            for log_file in self.job_logs_dir.glob("*.log"):
                job_logs = self.get_job_logs(log_file.stem)
                logs.extend(job_logs)
        
        # Apply filters
        filtered_logs = []
        for log in logs:
            if event_type and log.get('event_type') != event_type:
                continue
            if level and log.get('level') != level:
                continue
            if message_contains and message_contains.lower() not in log.get('message', '').lower():
                continue
            
            filtered_logs.append(log)
        
        # Sort by timestamp (newest first) and limit
        filtered_logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return filtered_logs[:limit]
    
    def archive_job_logs(self, job_id: str) -> bool:
        """
        Archive completed job logs to reduce active log directory size
        
        Args:
            job_id (str): Job identifier
            
        Returns:
            bool: Success status
        """
        try:
            job_log_file = self.job_logs_dir / f"{job_id}.log"
            
            if not job_log_file.exists():
                return False
            
            # Create archive filename with timestamp
            archive_filename = f"{job_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.log"
            archive_path = self.archived_logs_dir / archive_filename
            
            # Move log file to archive
            job_log_file.rename(archive_path)
            
            # Remove from active loggers cache
            if job_id in self.job_loggers:
                # Close handler
                for handler in self.job_loggers[job_id].handlers:
                    handler.close()
                del self.job_loggers[job_id]
            
            self.system_logger.info(f"Archived logs for job {job_id} to {archive_filename}")
            return True
            
        except Exception as e:
            self.system_logger.error(f"Failed to archive logs for job {job_id}: {str(e)}")
            return False
    
    def get_log_stats(self) -> Dict[str, Any]:
        """Get logging system statistics"""
        return {
            'active_job_loggers': len(self.job_loggers),
            'active_log_files': len(list(self.job_logs_dir.glob("*.log"))),
            'archived_log_files': len(list(self.archived_logs_dir.glob("*.log"))),
            'total_log_size_mb': sum(f.stat().st_size for f in self.job_logs_dir.glob("*.log")) / (1024 * 1024),
            'base_log_dir': str(self.base_log_dir),
            'log_dirs': {
                'jobs': str(self.job_logs_dir),
                'system': str(self.system_logs_dir),
                'archived': str(self.archived_logs_dir)
            }
        }
    
    def cleanup_old_logs(self, days_old: int = 30):
        """
        Clean up old log files to prevent disk space issues
        
        Args:
            days_old (int): Delete logs older than this many days
        """
        cutoff_time = time.time() - (days_old * 24 * 60 * 60)
        
        deleted_count = 0
        for log_file in self.archived_logs_dir.glob("*.log"):
            if log_file.stat().st_mtime < cutoff_time:
                try:
                    log_file.unlink()
                    deleted_count += 1
                except Exception as e:
                    self.system_logger.error(f"Failed to delete old log file {log_file}: {str(e)}")
        
        if deleted_count > 0:
            self.system_logger.info(f"Cleaned up {deleted_count} old log files")


# Global job logger instance
_job_logger = None

def get_job_logger() -> JobLogger:
    """Get global job logger instance"""
    global _job_logger
    if _job_logger is None:
        _job_logger = JobLogger()
    return _job_logger


def log_job_event(job_id: str, event_type: str, message: str, 
                 details: Dict[str, Any] = None, level: str = "info"):
    """Convenience function for logging job events"""
    logger = get_job_logger()
    logger.log_job_event(job_id, event_type, message, details, level)
