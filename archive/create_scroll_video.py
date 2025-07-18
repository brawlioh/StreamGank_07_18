#!/usr/bin/env python3
"""
Script pour créer une vidéo de défilement (scroll) de StreamGank en mode responsive (mobile).
Le script capture une série d'images pendant le défilement et les assemble en vidéo.
"""

import os
import time
import logging
import subprocess
from playwright.sync_api import sync_playwright

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_scroll_video(
    url="https://streamgank.com/?country=PT&genres=Terror&type=Film",
    num_frames=48,  # 48 images pour 8 secondes à 6 FPS
    output_video="streamgank_scroll_readable.mp4",  # Nouveau nom pour la vidéo plus lisible
    scroll_height=2500,  # Réduit de moitié pour un défilement plus lent
    device_name="iPhone 12 Pro Max"
):
    """
    Crée une vidéo de défilement de StreamGank en mode responsive (mobile).
    """
    # Créer les dossiers pour les captures et la vidéo
    frames_dir = "scroll_frames"
    os.makedirs(frames_dir, exist_ok=True)
    
    logger.info(f"Début de la capture d'écran pour {url} en mode {device_name}")
    
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
        
        # Accéder à la page StreamGank
        logger.info(f"Accès à la page : {url}")
        page.goto(url)
        
        # Attendre que la page soit chargée
        page.wait_for_selector("text=RESULTS", timeout=30000)
        logger.info("Page chargée avec succès")
        
        # Gérer la bannière de cookies si présente
        try:
            cookie_banner = page.wait_for_selector("text=We use cookies", timeout=5000)
            if cookie_banner:
                logger.info("Bannière de cookies détectée")
                essential_button = page.wait_for_selector("button:has-text('Essential Only')", timeout=3000)
                if essential_button:
                    logger.info("Clic sur le bouton 'Essential Only'")
                    essential_button.click()
                    time.sleep(2)
        except Exception as e:
            logger.info(f"Pas de bannière de cookies ou erreur: {str(e)}")
        
        # Supprimer tout élément de cookie restant
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
            
            # Prendre la capture d'écran
            frame_path = os.path.join(frames_dir, f"frame_{i:03d}.png")
            page.screenshot(path=frame_path, full_page=False)
            logger.info(f"Capture d'écran {i+1}/{num_frames} à la position {scroll_position}px")
        
        # Fermer le navigateur
        browser.close()
    
    # Assembler les images en vidéo avec ffmpeg
    logger.info("Assemblage des images en vidéo avec ffmpeg...")
    
    # Vérifier si ffmpeg est installé
    try:
        # Commande ffmpeg pour créer une vidéo à 6 FPS (8 secondes pour 48 frames)
        cmd = [
            "ffmpeg", "-y",  # Écraser le fichier de sortie si existant
            "-framerate", "6",  # 6 images par seconde
            "-i", f"{frames_dir}/frame_%03d.png",  # Format des noms de fichiers d'entrée
            "-c:v", "libx264",  # Codec vidéo H.264
            "-profile:v", "high",  # Profil vidéo de haute qualité
            "-crf", "20",  # Facteur de qualité (0-51, où 0 est sans perte)
            "-pix_fmt", "yuv420p",  # Format de pixel compatible avec la plupart des lecteurs
            output_video  # Fichier de sortie
        ]
        
        process = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logger.info(f"Vidéo créée avec succès : {output_video}")
        
        # Afficher les statistiques de la vidéo
        video_info = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", output_video],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        
        duration = float(video_info.stdout.decode().strip())
        logger.info(f"Durée de la vidéo : {duration:.2f} secondes")
        
        return output_video
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Erreur lors de la création de la vidéo : {e.stderr.decode()}")
        return None
    except FileNotFoundError:
        logger.error("ffmpeg n'est pas installé. Veuillez l'installer pour créer des vidéos.")
        logger.error("Sur macOS: brew install ffmpeg")
        logger.error("Sur Linux: sudo apt-get install ffmpeg")
        return None

if __name__ == "__main__":
    video_path = create_scroll_video()
    if video_path:
        logger.info(f"Vidéo générée avec succès: {video_path}")
    else:
        logger.error("Échec de la création de la vidéo")
