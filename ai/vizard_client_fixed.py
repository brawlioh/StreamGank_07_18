import os
import requests
import time
import json
from typing import Dict, List, Optional, Any

class VizardAIClient:
    """Client for interacting with Vizard AI API to extract video highlights"""
    # Current API endpoint based on latest documentation
    API_ENDPOINT = "https://elb-api.vizard.ai/hvizard-server-front/open-api/v1"
    # Additional endpoints to try if the primary fails
    FALLBACK_ENDPOINTS = [
        "https://api.vizard.ai/api/v1", 
        "https://api.vizardai.com/api/v1",
        "https://elb-api.vizard.ai/api/v1"
    ]
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("VIZARD_API_KEY")
        if not self.api_key:
            raise ValueError("Vizard AI API key not provided and not found in environment variables")
        
        # Store successful endpoints to reuse in subsequent calls
        self.successful_endpoints = {}
        self.project_endpoint_map = {}
    
    def create_project(self, video_url: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Create a new Vizard AI project for a video
        
        Args:
            video_url: URL of the video to process
            options: Additional options for project creation
            
        Returns:
            Dictionary with project details including ID
        """
        # Use the primary endpoint for project creation based on sample API
        endpoint = f"{self.API_ENDPOINT}/project/create"
        
        # Create URL patterns list with fallbacks
        url_patterns = [endpoint]
        for base_url in self.FALLBACK_ENDPOINTS:
            url_patterns.append(f"{base_url}/project/create")
        
        # Default options based on the sample API request format
        default_options = {
            "lang": "en",
            "preferLength": [2],  # Medium length
            "videoUrl": video_url,
            "videoType": 2,
            "ratioOfClip": 1,
            "templateId": 69147768,
            "removeSilenceSwitch": 0,
            "maxClipNumber": 3,  # Default to 3 clips
            "subtitleSwitch": 1,
            "headlineSwitch": 0,
            "ext": "1",
            "emojiSwitch": 0,
            "highlightSwitch": 0
        }
        
        # Map our simple options to the API format
        if options:
            if "clipCount" in options:
                default_options["maxClipNumber"] = options["clipCount"]
            if "minLength" in options and "maxLength" in options:
                # Convert min/max length to preferLength value
                # 1=short, 2=medium, 3=long
                if options["minLength"] <= 5 and options["maxLength"] <= 8:
                    default_options["preferLength"] = [1]  # Short
                elif options["minLength"] >= 8:
                    default_options["preferLength"] = [3]  # Long
                else:
                    default_options["preferLength"] = [2]  # Medium
        
        # Use the prepared options as the data payload
        data = default_options
            
        print(f"🔄 Creating Vizard AI project for video: {video_url}")
        print(f"   With options: {json.dumps(data, indent=2)}")
        
        # Setup authentication headers for Vizard API
        headers = {
            "VIZARDAI_API_KEY": self.api_key,
            "Content-Type": "application/json"
        }
        
        errors = []
        # If we have a successful endpoint for project creation from a previous call, try it first
        if "create_project" in self.successful_endpoints:
            primary_endpoint = self.successful_endpoints["create_project"]
            url_patterns = [primary_endpoint] + [e for e in url_patterns if e != primary_endpoint]
            print(f"   Using previously successful endpoint: {primary_endpoint}")
        
        # Try each endpoint until one works
        last_error = None
        for url in url_patterns:
            try:
                print(f"   Trying endpoint: {url}")
                response = requests.post(url, headers=headers, json=data)
                
                # Check if request was successful
                if response.status_code == 200:
                    try:
                        response_data = response.json()
                        project_id = response_data.get("projectId")
                        if project_id:
                            # Store the successful endpoint for future calls
                            self.successful_endpoints["create_project"] = url
                            
                            # Map this project ID to the successful endpoint
                            raw_id = str(project_id)
                            self.project_endpoint_map[raw_id] = url
                            
                            # Format project ID for consistency
                            formatted_id = f"open-api-{project_id}" if not str(project_id).startswith("open-api-") else project_id
                            print(f"   Formatted project ID: {formatted_id} (original: {project_id})")
                            print(f"✅ Project created successfully")
                            print(f"   Project ID: {project_id}")
                            
                            # Add additional useful information to the response
                            response_data["raw_response"] = response.text
                            response_data["formattedId"] = formatted_id
                            response_data["project-format-id"] = f"project-{project_id}" # Alternative format
                            response_data["success_endpoint"] = url
                            
                            return response_data
                        else:
                            print(f"   ⚠️ No project ID returned: {response.text}")
                    except Exception as e:
                        print(f"   ⚠️ Error parsing response: {str(e)}")
                else:
                    print(f"   ⚠️ Failed: Status code {response.status_code}")
            except requests.exceptions.RequestException as e:
                print(f"   ⚠️ Endpoint failed: {str(e)}")
                last_error = e
                continue
        
        # All endpoints failed
        print(f"❌ All endpoints failed to create project")
        error_msg = str(last_error) if last_error else "Unknown error occurred"
        return {"error": error_msg}
    
    def get_project_status(self, project_id: str) -> Dict[str, Any]:
        """Get the status of a Vizard AI project
        
        Args:
            project_id: ID of the project to check status for
            
        Returns:
            Dictionary with project status and details
        """
        # Convert project ID to string if needed
        project_id = str(project_id)
        
        # Store the raw project ID (without any prefixes)
        raw_project_id = project_id
        if project_id.startswith("project-"):
            raw_project_id = project_id.replace("project-", "")
        elif project_id.startswith("open-api-"):
            raw_project_id = project_id.replace("open-api-", "")
            
        # Format project IDs for different endpoints
        open_api_id = f"open-api-{raw_project_id}"
        project_format_id = f"project-{raw_project_id}"
        
        # Define potential API endpoints to try
        endpoints = []
        
        # Check if we have a successful endpoint for this project ID
        if raw_project_id in self.project_endpoint_map:
            # Use the base endpoint that worked for this project before
            base_endpoint = self.project_endpoint_map[raw_project_id]
            base_url = '/'.join(base_endpoint.split('/')[:-2])
            
            # Prioritize status endpoints using the successful base URL
            endpoints.extend([
                f"{base_url}/project/status?projectId={raw_project_id}",
                f"{base_url}/projects/{raw_project_id}"
            ])
            print(f"🔄 Using previously successful endpoint base for project {raw_project_id}: {base_url}")
        
        # Check if we have any general successful endpoint for status checks
        if "get_status" in self.successful_endpoints:
            status_endpoint = self.successful_endpoints["get_status"]
            if status_endpoint not in endpoints:
                endpoints.append(status_endpoint)
        
        # Add all standard endpoints as fallbacks
        standard_endpoints = [
            f"{self.API_ENDPOINT}/project/status?projectId={raw_project_id}",
            f"{self.API_ENDPOINT}/projects/{raw_project_id}",
            f"https://elb-api.vizard.ai/hvizard-server-front/open-api/v1/project/status?projectId={raw_project_id}",
            f"https://elb-api.vizard.ai/hvizard-server-front/open-api/v1/projects/{raw_project_id}",
            f"https://api.vizard.ai/api/v1/projects/{raw_project_id}",
            f"https://api.vizard.ai/api/v1/project/status?projectId={raw_project_id}",
            f"https://elb-api.vizard.ai/api/v1/projects/{raw_project_id}",
            f"https://elb-api.vizard.ai/api/v1/project/status?projectId={raw_project_id}"
        ]
        
        # Add endpoints using the full project ID as fallbacks
        full_id_endpoints = [
            f"{self.API_ENDPOINT}/project/status?projectId={project_id}",
            f"{self.API_ENDPOINT}/projects/{project_id}"
        ]
        
        # Add all endpoints without duplicates
        for endpoint in standard_endpoints + full_id_endpoints:
            if endpoint not in endpoints:
                endpoints.append(endpoint)
        
        # Setup authentication headers matching the sample API
        headers = {
            "VIZARDAI_API_KEY": self.api_key,
            "Content-Type": "application/json"
        }
        
        # Try each endpoint
        for url in endpoints:
            try:
                print(f"🔄 Trying endpoint: {url}")
                response = requests.get(url, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    print(f"✅ Success! Found working endpoint: {url}")
                    try:
                        # Store the successful endpoint for future use
                        self.successful_endpoints["get_status"] = url
                        
                        # Also map this project ID to the successful endpoint
                        if raw_project_id not in self.project_endpoint_map:
                            self.project_endpoint_map[raw_project_id] = url
                            
                        data = response.json()
                        # Add the successful endpoint to the response for debugging
                        if isinstance(data, dict):
                            data["success_endpoint"] = url
                        return data
                    except ValueError:
                        print(f"   ⚠️ Warning: Response is not valid JSON")
                        print(f"   Response: {response.text[:150]}...")
                else:
                    print(f"   ⚠️ Failed: Status code {response.status_code}")
            except Exception as e:
                print(f"   ⚠️ Error: {str(e)[:100]}")
        
        # All endpoints failed
        print("❌ All API endpoints failed to retrieve project status")
        return {"status": "UNKNOWN", "error": "Failed to access project status through any known endpoints"}

    def wait_for_completion(self, project_id: str, initial_delay: int = 20, max_retries: int = 120, retry_delay: int = 5) -> Dict[str, Any]:
        """
        Wait for a project to complete processing by polling its status
        
        Args:
            project_id: ID of the project to wait for
            initial_delay: Initial delay before first status check (seconds)
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries (seconds)
            
        Returns:
            Dictionary with final project status and details
        """
        # Convert to string if integer was passed
        project_id = str(project_id)
        
        # Handle either project-XXX or open-api-XXX format
        if not (project_id.startswith("project-") or project_id.startswith("open-api-")):
            # By default, use the open-api format as it seems to be the newer format
            project_id = f"open-api-{project_id}"
            print(f"🔄 Formatted project ID to open-api format: {project_id}")
        
        # For display purposes, show both formats
        if project_id.startswith("open-api-"):
            alt_format = project_id.replace("open-api-", "project-")
            print(f"   Alternative project ID format: {alt_format}")
        elif project_id.startswith("project-"):
            alt_format = project_id.replace("project-", "open-api-")
            print(f"   Alternative project ID format: {alt_format}")
        
        print(f"🕒 Waiting {initial_delay}s before first status check for project: {project_id}")
        print(f"⏳ This process can take several minutes. Maximum wait time: {max_retries * retry_delay / 60:.1f} minutes")
        time.sleep(initial_delay)
        
        consecutive_errors = 0
        max_consecutive_errors = 5
        backoff_factor = 1.5
        current_retry_delay = retry_delay
        progress_indicators = ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"]
        start_time = time.time()
        total_wait_time = 0
        
        for attempt in range(max_retries):
            progress_indicator = progress_indicators[attempt % len(progress_indicators)]
            elapsed_minutes = (time.time() - start_time) / 60
            
            try:
                print(f"\r{progress_indicator} Checking project status (attempt {attempt + 1}/{max_retries}) - Elapsed time: {elapsed_minutes:.1f} minutes", end="")
                status_response = self.get_project_status(project_id)
                print("\n", end="")  # New line after progress indicator
                
                # Check if we got a valid response
                if "error" in status_response and "status" in status_response and status_response["status"] == "UNKNOWN":
                    consecutive_errors += 1
                    print(f"⚠️ Error getting status (consecutive errors: {consecutive_errors}/{max_consecutive_errors})")
                    
                    # Implement exponential backoff
                    current_retry_delay = min(60, current_retry_delay * backoff_factor)  # Cap at 60 seconds
                    print(f"⏱️ Increasing retry delay to {current_retry_delay:.1f}s")
                    
                    # Stop after too many consecutive errors to avoid endless retries
                    if consecutive_errors >= max_consecutive_errors:
                        print(f"❌ Too many consecutive errors ({consecutive_errors}), stopping status checks")
                        return {"status": "ERROR", "error": f"Failed after {consecutive_errors} consecutive errors"}
                else:
                    # Reset consecutive error counter on success
                    consecutive_errors = 0
                    current_retry_delay = retry_delay  # Reset delay
                
                # Extract and show progress info if available
                progress_info = ""
                if isinstance(status_response, dict):
                    # Try to extract progress percentage if available
                    progress = status_response.get("progress", status_response.get("data", {}).get("progress"))
                    if progress:
                        progress_info = f" - Progress: {progress}%"
                    
                    # Extract status
                    status = ""
                    if "status" in status_response:
                        status = status_response.get("status", "").upper()
                    elif "data" in status_response and "status" in status_response["data"]:
                        status = status_response["data"]["status"].upper()
                    
                    print(f"📊 Current status: {status}{progress_info}")
                    
                    # Check if the project is complete
                    if status in ["COMPLETED", "DONE", "FINISHED", "SUCCESS"]:
                        total_time = (time.time() - start_time) / 60
                        print(f"✅ Project completed successfully in {total_time:.1f} minutes!")
                        return status_response
                    elif status in ["FAILED", "ERROR"]:
                        print(f"❌ Project failed with status: {status}")
                        return status_response
                    elif status in ["PROCESSING", "PENDING", "RUNNING"]:
                        # Still processing, continue waiting
                        print(f"   Project still processing... (Retry {attempt+1}/{max_retries})")
                else:
                    print(f"📊 Received non-dictionary response: {status_response[:100]}...")
                
                # Project still processing, wait and retry
                print(f"⏳ Project still processing, waiting {current_retry_delay:.1f}s before next check...")
                # Show waiting animation
                for i in range(int(current_retry_delay)):
                    if i % 5 == 0:  # Update animation every 5 seconds
                        indicator = progress_indicators[(attempt + i//5) % len(progress_indicators)]
                        print(f"\r{indicator} Waiting {current_retry_delay-i}s", end="")
                    time.sleep(1)
                print("\r                      ", end="\r")  # Clear the line
                total_wait_time += current_retry_delay
                
            except Exception as e:
                print("\n", end="")  # Ensure newline after progress indicator
                consecutive_errors += 1
                print(f"⚠️ Exception checking status: {str(e)} (consecutive errors: {consecutive_errors}/{max_consecutive_errors})")
                
                # Implement exponential backoff
                current_retry_delay = min(60, current_retry_delay * backoff_factor)
                print(f"⏱️ Increasing retry delay to {current_retry_delay:.1f}s")
                
                # Stop after too many consecutive errors to avoid endless retries
                if consecutive_errors >= max_consecutive_errors:
                    print(f"❌ Too many consecutive errors ({consecutive_errors}), stopping status checks")
                    return {"status": "ERROR", "error": f"Failed after {consecutive_errors} consecutive errors"}
                
                time.sleep(current_retry_delay)
                total_wait_time += current_retry_delay
        
        # Max retries reached
        total_time = (time.time() - start_time) / 60
        print(f"⚠️ Max retries ({max_retries}) reached after {total_time:.1f} minutes, project may still be processing")
        return {"status": "TIMEOUT", "error": f"Timed out after {max_retries} attempts ({total_time:.1f} minutes)"}
    
    def get_existing_project(self, project_id: str) -> Dict[str, Any]:
        """
        Get an existing project from the dashboard using its ID
        
        Args:
            project_id: Full project ID from dashboard (e.g., 'project-175586116364') 
            
        Returns:
            Dictionary with project details
        """
        # Ensure the project_id is properly formatted
        if not project_id.startswith("project-"):
            project_id = f"project-{project_id}"
            print(f"🔄 Formatted project ID: {project_id}")
        
        # Get the project details using the status endpoint
        project_details = self.get_project_status(project_id)
        
        if "error" in project_details:
            print(f"❌ Failed to get project details: {project_details['error']}")
            return project_details
        
        print(f"✅ Successfully retrieved project details for {project_id}")
        print(f"📊 Project details: {json.dumps(project_details, indent=2)}")
        
        return project_details
    
    def download_highlights(self, project_id: str, output_dir: str = "./test_vizard_clips") -> List[str]:
        """Download highlight clips from a completed project
        
        Args:
            project_id: ID of the project
            output_dir: Directory to save downloaded clips
            
        Returns:
            List of paths to downloaded clip files
        """
        print(f"💼 Downloading highlights for project ID: {project_id}")
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Convert to string if integer was passed
        project_id = str(project_id)
        
        # Extract raw project ID (without any prefixes)
        raw_project_id = project_id
        if project_id.startswith("project-"):
            raw_project_id = project_id.replace("project-", "")
        elif project_id.startswith("open-api-"):
            raw_project_id = project_id.replace("open-api-", "")
        
        print(f"🔄 Using raw project ID: {raw_project_id} (from {project_id})")
        
        # Setup authentication headers
        headers = {
            "VIZARDAI_API_KEY": self.api_key,
            "Content-Type": "application/json"
        }
        
        # Use the exact endpoint format from the API documentation
        query_endpoint = f"https://elb-api.vizard.ai/hvizard-server-front/open-api/v1/project/query/{raw_project_id}"
        
        print(f"🔍 Getting project details from: {query_endpoint}")
        
        # First, query the project to get clip details
        try:
            response = requests.get(query_endpoint, headers=headers, timeout=30)
            if response.status_code == 200:
                print(f"✅ Successfully retrieved project clips")
                project_details = response.json()
                # Store this successful endpoint
                self.successful_endpoints["query_clips"] = query_endpoint
            else:
                print(f"❌ Failed to query project: Status code {response.status_code}")
                return []
        except Exception as e:
            print(f"❌ Error querying project: {str(e)}")
            return []
        
        # Ensure the project is completed - check both direct status and data.status paths
        project_status = project_details.get("status", project_details.get("data", {}).get("status", "UNKNOWN"))
        if project_status.upper() not in ["COMPLETED", "SUCCESS", "DONE"]:
            print(f"❌ Cannot download clips: Project status is {project_status}")
            return []
            
        # Try to get the clips information from different possible response structures
        clips = []
        if "highlights" in project_details:
            clips = project_details["highlights"]
        elif "data" in project_details and "highlights" in project_details["data"]:
            clips = project_details["data"]["highlights"]
        elif "clips" in project_details:
            clips = project_details["clips"]
        elif "data" in project_details and "clips" in project_details["data"]:
            clips = project_details["data"]["clips"]
        elif "data" in project_details and "result" in project_details["data"] and "clips" in project_details["data"]["result"]:
            clips = project_details["data"]["result"]["clips"]
        
        if not clips:
            print("❌ No clips found in project details")
            print(f"Project details structure: {json.dumps(list(project_details.keys()), indent=2)}")
            if "data" in project_details:
                print(f"data keys: {json.dumps(list(project_details['data'].keys()), indent=2)}")
            return []
            
        # Extract clip URLs
        clip_urls = []
        for clip in clips:
            if "url" in clip:
                clip_urls.append(clip["url"])
        
        if not clip_urls:
            print("❌ No clip URLs found in project details")
            return []
            
        print(f"🎬 Found {len(clip_urls)} clip URLs in project details")
        
        # Download the clips
        movie_title = "Movie"  # Default title
        return self.download_clips_from_urls(clip_urls, movie_title, output_dir)
    
    def extract_from_existing_project(self, project_id: str, movie_title: str = "Movie", output_dir: str = "temp_clips") -> List[str]:
        """
        Extract highlight clips from an existing completed project in the dashboard
        
        Args:
            project_id: Full dashboard project ID (e.g., 'project-175586116364' or 'open-api-175586116364')
            movie_title: Title of the movie (for file naming)
            output_dir: Directory to save clips to
            
        Returns:
            List of paths to downloaded clip files
        """
        # Convert to string if integer was passed
        project_id = str(project_id)
        
        # Handle multiple project ID formats
        if not (project_id.startswith("project-") or project_id.startswith("open-api-")):
            # Try both formats with fallback
            project_id = f"open-api-{project_id}"
            print(f"🔄 Formatted project ID to open-api format: {project_id}")
        
        print(f"🔍 Extracting highlights from existing project: {project_id}")
        
        # Get project details
        project_details = self.get_existing_project(project_id)
        
        if "error" in project_details:
            print(f"❌ Cannot extract highlights: {project_details['error']}")
            return []
        
        # Extract clip URLs from project details
        clip_urls = []
        
        # Try different possible paths in the API response structure
        if "clips" in project_details:
            # Direct clips array
            for clip in project_details["clips"]:
                if "url" in clip:
                    clip_urls.append(clip["url"])
        elif "data" in project_details and "clips" in project_details["data"]:
            # Nested clips array
            for clip in project_details["data"]["clips"]:
                if "url" in clip:
                    clip_urls.append(clip["url"])
        
        if not clip_urls:
            print("❌ No clip URLs found in project details")
            return []
        
        print(f"🎬 Found {len(clip_urls)} clip URLs in project details")
        
        # Download the clips
        return self.download_clips_from_urls(clip_urls, movie_title, output_dir)
    
    def download_clips_from_urls(self, clip_urls: List[str], movie_title: str, output_dir: str = "temp_clips") -> List[str]:
        """
        Download clips from URLs
        
        Args:
            clip_urls: List of clip URLs to download
            movie_title: Title of the movie (for file naming)
            output_dir: Directory to save clips to
            
        Returns:
            List of paths to downloaded clip files
        """
        downloaded_files = []
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Download each clip
        for i, url in enumerate(clip_urls):
            try:
                # Generate a filename
                timestamp = int(time.time())
                safe_title = movie_title.replace(" ", "_").replace("/", "_").replace("\\", "_")
                filename = f"{safe_title}_highlight_{i+1}_{timestamp}.mp4"
                filepath = os.path.join(output_dir, filename)
                
                print(f"🔄 Downloading clip {i+1}/{len(clip_urls)} to {filepath}")
                
                # Download the file
                response = requests.get(url, stream=True)
                response.raise_for_status()
                
                with open(filepath, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                print(f"✅ Downloaded clip {i+1} successfully")
                downloaded_files.append(filepath)
            except Exception as e:
                print(f"❌ Error downloading clip {i+1}: {str(e)}")
        
        print(f"✅ Downloaded {len(downloaded_files)}/{len(clip_urls)} clips successfully")
        return downloaded_files
    
    def extract_highlights(self, youtube_url: str, num_clips: int = 1, clip_length: int = 1, output_dir: str = "temp_clips") -> List[str]:
        """
        Extract highlights from a YouTube video
        
        Args:
            youtube_url: URL of the YouTube video
            num_clips: Number of highlight clips to extract
            clip_length: Length of clips (1=short, 2=medium, 3=long)
            output_dir: Directory to save downloaded clips
            
        Returns:
            List of paths to downloaded highlight clips
        """
        # Map clip_length to min/max duration in seconds
        length_options = {
            1: {"minLength": 3, "maxLength": 8},    # Short clips
            2: {"minLength": 5, "maxLength": 12},   # Medium clips
            3: {"minLength": 8, "maxLength": 20}    # Long clips
        }
        
        # Set options for clip extraction
        options = {"clipCount": num_clips}
        options.update(length_options.get(clip_length, length_options[1]))
        
        try:
            # Create project for the video
            project_result = self.create_project(youtube_url, options)
            
            if "error" in project_result:
                print(f"❌ Failed to create project: {project_result['error']}")
                return []
            
            project_id = project_result.get("projectId")
            if project_id:
                print(f"✅ Created Vizard AI project {project_id}")
                
                # Wait for project to complete processing
                final_status = self.wait_for_completion(project_id)
                
                # Check if project completed successfully
                status = final_status.get("status")
                if status != "COMPLETED":
                    print(f"❌ Project processing failed with status: {status}")
                    return []
                
                # Download clips
                return self.download_highlights(project_id, output_dir)
                
        except Exception as e:
            print(f"❌ Error extracting highlights: {str(e)}")
            return []
        
        return []  # Default return in case nothing is returned above
