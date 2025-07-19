#!/usr/bin/env python3
"""
Automated Video Generator for StreamGank - Concise Version

This script automates the end-to-end process of generating promotional videos for movies:
1. Capturing screenshots from StreamGank
2. Extracting movie data from Supabase
3. Generating avatar video scripts
4. Creating videos with HeyGen

Usage:
    python3 automated_video_generator_concise.py
"""

import os
import json
import time
import logging
import requests
import datetime
from pathlib import Path
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
import cloudinary
import cloudinary.uploader
from supabase import create_client
import openai

# Logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configuration (use default values from original script)
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME", "dodod8s0v")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY", "589374432754798")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET", "iwOZJxSJ9SIE47BwVBsvQdYAfsg")

cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET
)

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# OpenAI configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

# HeyGen API Key
HEYGEN_API_KEY = os.getenv("HEYGEN_API_KEY")

# Ensure output directories exist
screenshots_dir = Path("screenshots")
videos_dir = Path("videos")
screenshots_dir.mkdir(exist_ok=True)
videos_dir.mkdir(exist_ok=True)

def capture_streamgank_screenshots(url="https://streamgank.com/?country=FR&genres=Horreur&platforms=netflix&type=Film"):
    """Capture screenshots of StreamGank in mobile format"""
    output_dir = "screenshots"
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    screenshot_paths = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        device = p.devices["iPhone 12 Pro Max"]
        context = browser.new_context(**device, locale='fr-FR', timezone_id='Europe/Paris')
        page = context.new_page()
        
        logger.info(f"Accessing page: {url}")
        page.goto(url)
        page.wait_for_selector("text=RESULTS", timeout=30000)
        
        # Take screenshot
        screenshot_path = f"{output_dir}/streamgank_{timestamp}.png"
        page.screenshot(path=screenshot_path)
        screenshot_paths.append(screenshot_path)
        
        logger.info(f"Captured screenshot: {screenshot_path}")
    return screenshot_paths

def upload_to_cloudinary(file_paths):
    """Upload images to Cloudinary and return the URLs"""
    cloudinary_urls = []
    
    for file_path in file_paths:
        try:
            logger.info(f"Uploading {file_path} to Cloudinary")
            upload_result = cloudinary.uploader.upload(file_path)
            cloudinary_urls.append(upload_result["secure_url"])
            logger.info(f"Uploaded successfully, URL: {upload_result['secure_url']}")
        except Exception as e:
            logger.error(f"Error uploading to Cloudinary: {str(e)}")
    
    return cloudinary_urls

def extract_movie_data(num_movies=3, country="FR", genre="Horreur", platform="netflix", content_type="Film"):
    """Extract movie data from Supabase with filters"""
    try:
        # First, let's check the table structure to understand the available columns
        logger.info("Checking database schema...")
        response = supabase.table("movies").select("*").limit(1).execute()
        
        # Get the column names from the first item, if any
        columns = []
        if response.data and len(response.data) > 0:
            columns = response.data[0].keys()
            logger.info(f"Available columns: {', '.join(columns)}")
        
        # Build the query based on available columns
        query = supabase.table("movies").select("*")
        
        # Apply filters only for columns that exist
        if "country_code" in columns and country:
            query = query.eq("country_code", country)  # Use country_code instead of country
        elif "country" in columns and country:
            query = query.eq("country", country)
            
        if "genres" in columns and genre:  # Might be an array or JSON field
            # Handle differently depending on the field type
            query = query.ilike("genres", f"%{genre}%")  # Simple text search
        elif "genre" in columns and genre:
            query = query.eq("genre", genre)
            
        if "platform" in columns and platform:
            query = query.eq("platform", platform)
            
        if "content_type" in columns and content_type:
            query = query.eq("content_type", content_type)
        elif "type" in columns and content_type:
            query = query.eq("type", content_type)
        
        # Limit results and execute query
        response = query.limit(num_movies).execute()
        
        logger.info(f"Found {len(response.data)} movies in database")
        
        # Map the database schema to our expected format
        # This is a critical step to handle the actual schema we discovered
        mapped_movies = []
        for movie in response.data:
            # Create a standardized movie object with fallback values
            mapped_movie = {
                "title": f"Movie {movie.get('movie_id', 'Unknown')}",  # Generate a title since it's missing
                "platform": platform or "Netflix",  # Use the platform filter or default
                "year": str(movie.get('release_year', 'Unknown')),
                "imdb": f"{movie.get('imdb_score', '?')}/10",
                "description": f"A {content_type or 'Film'} with a runtime of {movie.get('runtime', '?')} minutes.",
                "original_data": movie  # Keep the original data for reference
            }
            mapped_movies.append(mapped_movie)
        
        logger.info(f"Mapped {len(mapped_movies)} movies to standard format")
        return mapped_movies
    except Exception as e:
        logger.error(f"Error extracting movie data: {str(e)}")
        # Return empty list on error
        return []
    except Exception as e:
        logger.error(f"Error extracting movie data: {str(e)}")
        return []

def enrich_movie_data(movie_data):
    """Enrich movie data with ChatGPT for more engaging descriptions"""
    enriched_data = []
    
    for movie in movie_data:
        try:
            # Check if OpenAI is properly configured
            if not OPENAI_API_KEY:
                logger.warning("OpenAI API key not set, skipping enrichment")
                enriched_data.append(movie)
                continue
                
            # Create client using the updated API format
            client = openai.OpenAI(api_key=OPENAI_API_KEY)
            
            # Prepare prompt with fallbacks for missing fields
            title = movie.get('title', 'A movie')
            description = movie.get('description', 'No description available')
            prompt = f"Create a more engaging and dramatic description for this movie:\nTitle: {title}\nOriginal Description: {description}\nKeep it under 200 characters and make it captivating."
            
            # Use the new API format
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",  # Using GPT-3.5 instead of GPT-4 for cost/availability
                messages=[
                    {"role": "system", "content": "You are a professional copywriter specializing in movie descriptions."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150
            )
            
            # Extract the enhanced description using the new API format
            enhanced_description = response.choices[0].message.content.strip()
            
            # Create an enriched movie data entry
            enriched_movie = movie.copy()
            enriched_movie["enhanced_description"] = enhanced_description
            enriched_data.append(enriched_movie)
            logger.info(f"Successfully enriched description for {title}")
            
        except Exception as e:
            logger.error(f"Error enriching movie data: {str(e)}")
            # Add movie without enrichment
            movie["enhanced_description"] = movie.get('description', 'An intriguing film worth watching')
            enriched_data.append(movie)
    
    return enriched_data

def generate_script(enriched_movies, cloudinary_urls):
    """Generate scripts for the avatar video"""
    scripts = {}
    
    # Check if we have any movies
    if not enriched_movies or len(enriched_movies) == 0:
        logger.warning("No movie data available for script generation")
        # Create a generic script if no movies available
        scripts["generic"] = """Hey movie lovers! I don't have specific movie recommendations right now, 
but check out StreamGank for the latest movies and TV shows across all your streaming platforms."""
        return "No movies available", "videos/script.txt", scripts
    
    # Intro + Movie 1 script
    try:
        # Make sure we have all required fields
        movie = enriched_movies[0]
        title = movie.get('title', 'this movie')
        description = movie.get('enhanced_description', movie.get('description', 'An interesting movie'))
        imdb = movie.get('imdb', 'highly rated')
        platform = movie.get('platform', 'your favorite streaming service')
        
        intro_script = f"""Hey movie lovers! I found some awesome films for you to check out. 
Let me tell you about {title}. {description}. 
It's rated {imdb} on IMDB and you can watch it on {platform}."""
    except Exception as e:
        logger.error(f"Error creating intro script: {str(e)}")
        intro_script = "Hey movie lovers! I found some awesome films for you to check out on StreamGank."
    
    scripts["intro_movie1"] = intro_script
    
    # Movie 2 script
    if len(enriched_movies) > 1:
        try:
            movie = enriched_movies[1]
            title = movie.get('title', 'another great movie')
            description = movie.get('enhanced_description', movie.get('description', 'An exciting film'))
            imdb = movie.get('imdb', 'well-rated')
            
            movie2_script = f"""Next up is {title}. {description}. 
It's rated {imdb} on IMDB."""
            scripts["movie2"] = movie2_script
        except Exception as e:
            logger.error(f"Error creating movie2 script: {str(e)}")
    
    # Movie 3 script
    if len(enriched_movies) > 2:
        try:
            movie = enriched_movies[2]
            title = movie.get('title', 'one more recommendation')
            description = movie.get('enhanced_description', movie.get('description', 'A must-watch film'))
            imdb = movie.get('imdb', 'positively reviewed')
            
            movie3_script = f"""Finally, don't miss {title}. {description}. 
It's rated {imdb} on IMDB."""
            scripts["movie3"] = movie3_script
        except Exception as e:
            logger.error(f"Error creating movie3 script: {str(e)}")
    
    # Combined script for reference
    combined_script = "\n\n".join(scripts.values())
    
    # Save scripts to file
    script_path = "videos/script.txt"
    os.makedirs(os.path.dirname(script_path), exist_ok=True)
    
    with open(script_path, "w") as f:
        f.write(combined_script)
    
    return combined_script, script_path, scripts

def create_heygen_video(scripts):
    """Create HeyGen videos from scripts
    Directly based on the original implementation from automated_video_generator.py
    """
    video_ids = {}
    
    # Check if HeyGen API key is configured
    if not HEYGEN_API_KEY:
        logger.warning("HEYGEN_API_KEY not set, skipping video creation")
        return {key: f"placeholder_{key}" for key in scripts.keys()}
    
    # Log a masked version of the key for debugging
    masked_key = HEYGEN_API_KEY[:4] + "..." + HEYGEN_API_KEY[-4:] if len(HEYGEN_API_KEY) > 8 else "[KEY TOO SHORT]"
    logger.info(f"Using HeyGen API key: {masked_key}")
    
    # Process each script in the dictionary
    for key, script_text in scripts.items():
        logger.info(f"Creating video for {key}...")
        
        # Create payload for the standard V2 API approach (matching original)
        payload = {
            "video_type": "talking_head",  # Type for avatar videos
            "test": False,
            "auto_match": True,
            "talking_head": {
                "voice": {
                    "type": "text",
                    "source": {
                        "type": "text",
                        "text": script_text
                    },
                    "voice_id": "11labs.lucrehung"  # Use a reliable voice ID
                },
                "character": {
                    "type": "avatar",
                    "avatar_id": "dc171ef48c0549f79bc3f607c8e554fe"  # Use a reliable avatar ID
                },
                "background": {
                    "type": "color",
                    "value": "#010101"  # Dark background
                }
            },
            "ratio": "16:9"
        }
        
        # Call the send_heygen_request function which is identical to the original
        video_id = send_heygen_request(payload)
        
        if video_id:
            video_ids[key] = video_id
            logger.info(f"Successfully created HeyGen video with ID: {video_id}")
        else:
            logger.warning(f"Failed to create HeyGen video for {key}, using placeholder")
            video_ids[key] = f"placeholder_{key}"
    
    return video_ids

def send_heygen_request(payload):
    """
    Helper function to send requests to HeyGen API
    Directly copied from the original automated_video_generator.py implementation
    
    Args:
        payload: API request payload
    
    Returns:
        Video ID if successful, None otherwise
    """
    logger.info("Sending request to HeyGen API...")
    logger.info(f"Request payload: {json.dumps(payload, indent=2)}")
    
    # Use the HEYGEN_API_KEY from environment (already imported)
    if not HEYGEN_API_KEY:
        logger.error("HEYGEN_API_KEY not found in environment variables")
        return None
    
    # Set up headers with X-Api-Key as per official documentation
    headers = {
        "X-Api-Key": HEYGEN_API_KEY,
        "Content-Type": "application/json"
    }
    
    try:
        # Determine which API endpoint to use based on payload structure
        is_template_request = "template_id" in payload
        
        if is_template_request:
            # Template-based approach
            template_id = payload.pop("template_id")
            url = f"https://api.heygen.com/v2/template/{template_id}/generate"
        else:
            # Standard approach
            url = "https://api.heygen.com/v2/video/generate"
        
        # Make the API request
        logger.info(f"Using API endpoint: {url}")
        response = requests.post(url, headers=headers, json=payload)
        
        # Log the complete response for debugging
        logger.info(f"Raw response: {response.text}")
        
        if response.status_code in [200, 201]:
            data = response.json()
            
            # Handle different response formats based on API type
            if is_template_request:
                # Template API response format
                video_id = data.get("data", {}).get("video_id")
            else:
                # Standard API response format
                video_id = data.get("data", {}).get("video_id")
            
            if video_id:
                logger.info(f"Video generation in progress. ID: {video_id}")
                return video_id
            else:
                logger.error(f"No video_id found in response: {data}")
                return None
        else:
            logger.error(f"Error creating video: {response.status_code}")
            logger.error(f"Details: {response.text}")
            return None
    except Exception as e:
        logger.error(f"Exception during video creation: {str(e)}")
        return None

def check_heygen_video_status(video_id):
    """Check the processing status of a HeyGen video"""
    try:
        api_url = f"https://api.heygen.com/v1/video.status?video_id={video_id}"
        
        headers = {
            "x-api-key": HEYGEN_API_KEY,
            "Content-Type": "application/json"
        }
        
        response = requests.get(api_url, headers=headers)
        response_data = response.json()
        
        if response.status_code == 200 and "data" in response_data and "status" in response_data["data"]:
            return response_data["data"]["status"]
        else:
            logger.error(f"Error checking video status: {response.text}")
            return "unknown"
            
    except Exception as e:
        logger.error(f"Exception checking video status: {str(e)}")
        return "unknown"

def wait_for_heygen_video(video_id, max_attempts=30, interval=10):
    """Wait for a HeyGen video to complete processing"""
    for attempt in range(max_attempts):
        status = check_heygen_video_status(video_id)
        
        if status == "completed":
            logger.info(f"Video {video_id} is ready!")
            return True
            
        elif status == "failed":
            logger.error(f"Video {video_id} processing failed")
            return False
            
        else:
            logger.info(f"Video {video_id} is {status}. Checking again in {interval} seconds...")
            time.sleep(interval)
    
    logger.warning(f"Timeout waiting for video {video_id}")
    return False

def download_heygen_video(video_id):
    """Download a HeyGen video by its ID and upload to Cloudinary"""
    try:
        # Get video URL from HeyGen
        api_url = f"https://api.heygen.com/v1/video.get?video_id={video_id}"
        
        headers = {
            "x-api-key": HEYGEN_API_KEY,
            "Content-Type": "application/json"
        }
        
        response = requests.get(api_url, headers=headers)
        response_data = response.json()
        
        if response.status_code == 200 and "data" in response_data and "video_url" in response_data["data"]:
            video_url = response_data["data"]["video_url"]
            
            # Download the video
            logger.info(f"Downloading video from {video_url}")
            video_response = requests.get(video_url)
            
            if video_response.status_code == 200:
                # Save video locally
                video_path = f"videos/{video_id}.mp4"
                with open(video_path, "wb") as f:
                    f.write(video_response.content)
                
                # Upload to Cloudinary
                logger.info(f"Uploading video {video_id} to Cloudinary")
                upload_result = cloudinary.uploader.upload(
                    video_path,
                    resource_type="video",
                    folder="heygen_videos"
                )
                
                return upload_result["secure_url"]
            else:
                logger.error(f"Error downloading video: {video_response.status_code}")
                return None
        else:
            logger.error(f"Error getting video URL: {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"Exception downloading video: {str(e)}")
        return None

def run_workflow(num_movies=3, country="FR", genre="Horreur", platform="netflix", content_type="Film"):
    """Run the complete video generation workflow"""
    results = {}
    
    try:
        # Step 1: Capture screenshots from StreamGank
        logger.info("Step 1: Capturing screenshots from StreamGank")
        screenshot_paths = capture_streamgank_screenshots()
        results['screenshots'] = screenshot_paths
        
        # Step 2: Upload screenshots to Cloudinary
        logger.info("Step 2: Uploading screenshots to Cloudinary")
        cloudinary_urls = upload_to_cloudinary(screenshot_paths)
        results['cloudinary_urls'] = {f"screenshot_{i}": url for i, url in enumerate(cloudinary_urls)}
        
        # Step 3: Extract movie data from Supabase and enrich with ChatGPT
        logger.info("Step 3: Extracting and enriching movie data")
        movies = extract_movie_data(num_movies, country, genre, platform, content_type)
        
        if not movies or len(movies) == 0:
            logger.warning("No movies found with the specified criteria. Using fallback data.")
            # Fallback to some default movie data for demonstration purposes
            movies = [{
                "title": "Example Movie",
                "platform": "Netflix",
                "year": "2023",
                "imdb": "8.5/10",
                "description": "This is an example movie description for demonstration purposes.",
            }]
        
        # Ensure we have exactly num_movies movies
        movies = movies[:num_movies] if len(movies) >= num_movies else movies
        
        # Enrich movie data with ChatGPT
        try:
            enriched_movies = enrich_movie_data(movies)
        except Exception as e:
            logger.error(f"Error enriching movies: {str(e)}")
            # If enrichment fails, just use the original movie data
            enriched_movies = movies
            
        results['enriched_movies'] = enriched_movies
            
        # Save enriched data for reference
        with open("videos/enriched_data.json", "w") as f:
            json.dump(enriched_movies, f, indent=2)
        
        # Step 4: Generate script for the avatar
        logger.info("Step 4: Generating script for the avatar")
        combined_script, script_path, scripts = generate_script(enriched_movies, results['cloudinary_urls'])
        results['script'] = combined_script
        
        # Step 5: Create HeyGen videos
        logger.info("Step 5: Creating HeyGen videos")
        heygen_video_ids = create_heygen_video(scripts)
        results['video_ids'] = heygen_video_ids
        
        # Wait for HeyGen videos to complete and download them
        logger.info("Waiting for HeyGen videos to complete...")
        cloudinary_video_urls = {}
        
        for key, video_id in heygen_video_ids.items():
            if video_id:
                if wait_for_heygen_video(video_id):
                    cloudinary_url = download_heygen_video(video_id)
                    if cloudinary_url:
                        cloudinary_video_urls[key] = cloudinary_url
        
        results['heygen_cloudinary_urls'] = cloudinary_video_urls
        
        logger.info("Full workflow completed successfully!")
        return results
        
    except Exception as e:
        logger.error(f"Error in workflow execution: {str(e)}")
        import traceback
        traceback.print_exc()
        return results

if __name__ == "__main__":
    # Print startup info
    print(f"StreamGank Video Generator - Concise Version")
    print(f"Running with environment variables: SUPABASE_URL={bool(SUPABASE_URL)}, SUPABASE_KEY={bool(SUPABASE_KEY)}")
    print(f"Cloudinary config: {bool(CLOUDINARY_CLOUD_NAME)}, {bool(CLOUDINARY_API_KEY)}, {bool(CLOUDINARY_API_SECRET)}")
    print(f"Running with: Country: FR, Genre: Horreur, Platform: netflix, Content Type: Film")
    
    # Run the workflow
    results = run_workflow()
    
    if results:
        print("\n📊 Results Summary:")
        if 'enriched_movies' in results:
            movies = results['enriched_movies']
            print(f"📽️  Movies processed: {len(movies)}")
            for i, movie in enumerate(movies, 1):
                # Safely print movie information with fallbacks
                title = movie.get('title', f'Movie {i}')
                year = movie.get('year', 'Unknown year')
                imdb = movie.get('imdb', 'Unrated')
                print(f"  {i}. {title} ({year}) - IMDB: {imdb}")
                
                # If we have original data, print some additional info
                if 'original_data' in movie:
                    original = movie['original_data']
                    runtime = original.get('runtime', '?')
                    print(f"     Runtime: {runtime} minutes, ID: {original.get('movie_id', '?')}")
                
        if 'video_ids' in results:
            print(f"🎥 HeyGen videos created: {len(results['video_ids'])}")
            
        if 'heygen_cloudinary_urls' in results:
            print(f"🎬 Final videos: {len(results['heygen_cloudinary_urls'])}")
