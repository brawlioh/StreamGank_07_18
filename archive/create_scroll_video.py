#!/usr/bin/env python3
"""
Script to create a scrolling video of StreamGank in responsive (mobile) mode. The script captures a series of images during the scroll and assembles them into a video.
"""

import os
import time
import logging
import subprocess
from playwright.sync_api import sync_playwright
# Import StreamGank helper function for URL building
from streamgank_helpers import build_streamgank_url

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_scroll_video(
    country="FR",
    genre="Horreur", 
    platform="Netflix",
    content_type="Série",
    num_frames=72,  # 72 images for 12 seconds at 6 FPS (more frames for smoother scrolling)
    output_video="streamgank_scroll_readable.mp4",
    scroll_height=3000,  # Increased to ensure more content is shown
    device_name="iPhone 12 Pro Max"
):
    """
    Create a scrolling video of StreamGank in responsive (mobile) mode. The script captures a series of images during the scroll and assembles them into a video.
    """
    # Créer les dossiers pour les captures et la vidéo
    frames_dir = "scroll_frames"
    os.makedirs(frames_dir, exist_ok=True)
    
    # Use either filtered URL or homepage based on parameter combination
    # If we're using specific filters that might result in no content, let's use the homepage instead
    # This ensures we always have content to scroll through
    url = build_streamgank_url(country=country, genre=None, platform=None, content_type=None)
    logger.info(f"Starting screenshot capture for {url} in {device_name} mode")
    
    # Also log the filtered URL for reference
    filtered_url = build_streamgank_url(country, genre, platform, content_type)
    logger.info(f"Note: Full filter would be: {filtered_url}")
    
    # Nettoyer les anciennes images
    for file in os.listdir(frames_dir):
        if file.endswith(".png"):
            os.remove(os.path.join(frames_dir, file))
    
    with sync_playwright() as p:
        # Lancer le navigateur en mode mobile
        browser = p.chromium.launch(headless=False)
        
        # Utiliser un dispositif mobile prédéfini
        device = p.devices[device_name]
        context = browser.new_context(
            **device,
            locale='fr-FR',
            timezone_id='Europe/Paris',
        )
        
        # Ouvrir une nouvelle page
        page = context.new_page()
        
        # Accessing page
        logger.info(f"Accessing page: {url}")
        page.goto(url)
        
        # Wait for page to fully load
        try:
            page.wait_for_selector("text=RESULTS", timeout=10000)
        except Exception as e:
            logger.info(f"Waiting for homepage content instead: {str(e)}")
            page.wait_for_selector("text=StreamGank", timeout=10000)
            
        logger.info("Page loaded successfully")
        
        # Wait for content to be visible
        time.sleep(2)
        
        # Handle cookie banner if present
        try:
            cookie_banner = page.wait_for_selector("text=We use cookies", timeout=5000)
            if cookie_banner:
                logger.info("Cookie banner detected")
                essential_button = page.wait_for_selector("button:has-text('Essential Only')", timeout=3000)
                if essential_button:
                    logger.info("Clicking 'Essential Only' button")
                    essential_button.click()
                    time.sleep(2)
        except Exception as e:
            logger.info(f"No cookie banner or error: {str(e)}")
        
        # Remove any remaining cookie elements
        page.evaluate("""() => {
            const elements = document.querySelectorAll('*');
            for (const el of elements) {
                if (el.textContent && el.textContent.includes('cookies') && 
                    (el.style.position === 'fixed' || el.style.position === 'absolute' || 
                     getComputedStyle(el).position === 'fixed' || getComputedStyle(el).position === 'absolute')) {
                    el.style.display = 'none';
                }
            }
        }""")
        
        time.sleep(1)
        
        # Capturer une série d'images en défilant progressivement
        for i in range(num_frames):
            # Calculer la position de défilement progressive
            scroll_position = (i * scroll_height) // (num_frames - 1)
            
            # Défiler jusqu'à la position
            page.evaluate(f"window.scrollTo(0, {scroll_position})")
            
            # Attendre un court instant pour le rendu
            time.sleep(0.1)
            
            # Take screenshot
            frame_path = os.path.join(frames_dir, f"frame_{i:03d}.png")
            page.screenshot(path=frame_path, full_page=True)
            logger.info(f"Screenshot {i+1}/{num_frames} at position {scroll_position}px")
        
        # Close browser
        browser.close()
    
    # Assemble images into video with ffmpeg
    logger.info("Assembling images into video with ffmpeg...")
    
    # Check if ffmpeg is installed
    try:
        # Command to create a video at 6 FPS (12 seconds for 72 frames)
        cmd = [
            "ffmpeg", "-y",  # Overwrite output file if it exists
            "-framerate", "6",  # 6 frames per second
            "-i", f"{frames_dir}/frame_%03d.png",  # Format des noms de fichiers d'entrée
            "-c:v", "libx264",  # Codec vidéo H.264
            "-profile:v", "high",  # Profil vidéo de haute qualité
            "-crf", "20",  # Facteur de qualité (0-51, où 0 est sans perte)
            "-pix_fmt", "yuv420p",  # Format de pixel compatible avec la plupart des lecteurs
            output_video  # Fichier de sortie
        ]
        
        process = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logger.info(f"Video created successfully: {output_video}")
        
        # Display video statistics
        video_info = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", output_video],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        
        duration = float(video_info.stdout.decode().strip())
        logger.info(f"Video duration: {duration:.2f} seconds")
        
        return output_video
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Error creating video: {e.stderr.decode()}")
        return None
    except FileNotFoundError:
        logger.error("ffmpeg is not installed. Please install it to create videos.")
        logger.error("On macOS: brew install ffmpeg")
        logger.error("On Linux: sudo apt-get install ffmpeg")
        return None

if __name__ == "__main__":
    video_path = create_scroll_video()
    if video_path:
        logger.info(f"Video generated successfully: {video_path}")
    else:
        logger.error("Failed to create video")
