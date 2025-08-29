"""
Webhook Client for Real-time Step Updates
Sends step completion notifications to Node.js server for real-time frontend updates
"""

import requests
import os
import time
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class WebhookClient:
    """Client for sending real-time webhook notifications during workflow execution"""
    
    def __init__(self, base_url: str = None, job_id: str = None):
        """
        Initialize webhook client
        
        Args:
            base_url (str): Base URL for webhook endpoints (default: from env or localhost:3000)
            job_id (str): Job ID for this workflow execution
        """
        self.base_url = base_url or os.getenv('WEBHOOK_BASE_URL', 'http://localhost:3000')
        self.job_id = job_id or os.getenv('JOB_ID')
        self.session = requests.Session()
        self.session.timeout = 5  # 5 second timeout for webhook calls
        
        # Remove trailing slash
        if self.base_url.endswith('/'):
            self.base_url = self.base_url[:-1]
    
    def send_step_update(self, 
                        step_number: int,
                        step_name: str, 
                        status: str = 'completed',
                        duration: float = None,
                        details: Dict[str, Any] = None) -> bool:
        """
        Send step completion update to Node.js server
        
        Args:
            step_number (int): Step number (1-7)
            step_name (str): Human readable step name
            status (str): Step status (completed, failed, started)
            duration (float): Step execution duration in seconds
            details (Dict): Additional step details
            
        Returns:
            bool: True if webhook sent successfully, False otherwise
        """
        if not self.job_id:
            logger.warning("No job_id set for webhook client - skipping webhook")
            return False
        
        webhook_url = f"{self.base_url}/api/webhooks/step-update"
        
        # Generate unique step tracking key for accuracy
        step_key = f"{self.job_id}_{step_number}_{status}_{int(time.time() * 1000)}"
        
        payload = {
            'job_id': self.job_id,
            'step_number': step_number,
            'step_name': step_name,
            'status': status,
            'duration': duration,
            'details': details or {},
            'timestamp': time.time(),
            'step_key': step_key,  # ✅ NEW: Unique tracking key
            'sequence': int(time.time() * 1000),  # ✅ NEW: Microsecond sequence for ordering
            'workflow_stage': f"step_{step_number}_{status}"  # ✅ NEW: Clear stage identifier
        }
        
        try:
            logger.info(f"📡 Sending webhook: Step {step_number} {status} for job {self.job_id}")
            
            response = self.session.post(
                webhook_url, 
                json=payload,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                logger.debug(f"✅ Webhook sent successfully: Step {step_number}")
                return True
            else:
                logger.warning(f"⚠️ Webhook returned status {response.status_code}: {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.warning(f"⚠️ Webhook failed for step {step_number}: {str(e)}")
            return False
        except Exception as e:
            logger.warning(f"⚠️ Unexpected webhook error for step {step_number}: {str(e)}")
            return False
    
    def send_workflow_started(self, total_steps: int = 7) -> bool:
        """Send workflow started notification"""
        return self.send_step_update(
            step_number=0,
            step_name="Workflow Started",
            status="started",
            details={'total_steps': total_steps}
        )
    
    def send_workflow_completed(self, total_duration: float, creatomate_id: str = None) -> bool:
        """Send workflow completion notification"""
        return self.send_step_update(
            step_number=8,
            step_name="Workflow Completed",
            status="completed",
            duration=total_duration,
            details={
                'creatomate_id': creatomate_id,
                'workflow_complete': True
            }
        )
    
    def send_workflow_failed(self, error: str, step_number: int = None) -> bool:
        """Send workflow failure notification"""
        return self.send_step_update(
            step_number=step_number or 0,
            step_name="Workflow Failed",
            status="failed",
            details={'error': error}
        )
    
    def send_creatomate_ready(self, creatomate_id: str, step_duration: float = 0) -> bool:
        """
        Send immediate notification that Creatomate ID is ready and monitoring should start
        
        Args:
            creatomate_id (str): The Creatomate render ID
            step_duration (float): Duration of step 7 completion
            
        Returns:
            bool: True if webhook sent successfully, False otherwise
        """
        logger.info(f"🎬 Sending immediate Creatomate ready notification: {creatomate_id}")
        
        return self.send_step_update(
            step_number=7,
            step_name="Creatomate Assembly",
            status="creatomate_ready",  # Special status for immediate monitoring trigger
            duration=step_duration,
            details={
                'creatomate_id': creatomate_id,
                'immediate_monitoring': True,
                'ready_for_rendering': True
            }
        )


def create_webhook_client(job_id: str = None) -> WebhookClient:
    """
    Create a webhook client instance
    
    Args:
        job_id (str): Job ID for webhook notifications
        
    Returns:
        WebhookClient: Configured webhook client
    """
    return WebhookClient(job_id=job_id)
