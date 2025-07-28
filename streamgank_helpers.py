#!/usr/bin/env python3
"""
StreamGank Helper Functions

This module contains helper functions for StreamGank URL construction and country-specific mappings.
Also includes dynamic movie trailer processing for creating 10-second highlight clips.
Also includes AI content generation with dynamic language support.
"""

import os
import re
import time
import tempfile
import logging
import subprocess
import requests
import textwrap
import math
from typing import Dict, List, Optional, Tuple
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageColor, ImageFilter
import yt_dlp
import cloudinary
import cloudinary.uploader
from pathlib import Path
import openai

# Set up logging
logger = logging.getLogger(__name__)

# =============================================================================
# AI CONTENT GENERATION - DYNAMIC LANGUAGE SYSTEM
# =============================================================================

def get_translations():
    """Get all translations for dynamic language support (descriptions + scripts)"""
    return {
        'en': {
            # Movie Description Generation
            'desc_expert_role': "You are a cinema expert who writes {focus} descriptions for social media.",
            'desc_task_instruction': "You ALWAYS write exactly 2 complete sentences that precisely describe the given movie/series content.",
            'desc_task_critical': "CRITICAL TASK: Write EXACTLY 2 precise sentences for \"{title}\".",
            'desc_search_context': "SEARCH CONTEXT:",
            'desc_user_search': "User search: {search}",
            'desc_found_content': "This {content_type} found{platform}{country}",
            'desc_precise_info': "PRECISE {content_type_upper} INFORMATION:",
            'desc_exact_title': "Exact title: {title}",
            'desc_imdb_score': "IMDb Score: {score}",
            'desc_year': "Year: {year}",
            'desc_actual_genres': "Actual genres: {genres}",
            'desc_mandatory_instructions': "MANDATORY INSTRUCTIONS:",
            'desc_first_sentence': "1. FIRST SENTENCE: Description of real {content_type} content (20-35 words)",
            'desc_use_genres': "   - Use actual genres: {genres}",
            'desc_mention_platform': "   - Mention{platform}{genre}",
            'desc_authentic_content': "   - Describe authentic content, not generic",
            'desc_second_sentence': "2. SECOND SENTENCE: Score + year + contextual recommendation (15-25 words)",
            'desc_exact_score': "   - Exact score: {score}",
            'desc_exact_year': "   - Exact year: {year}",
            'desc_personalized_rec': "   - Personalized recommendation for your search",
            'desc_response_instruction': "RESPONSE (2 precise sentences based on real content):",
            'content_movie': "movie",
            'content_series': "series",
            'focus_detailed': "detailed and structured",
            'focus_simple': "simple and direct", 
            'focus_creative': "creative but focused",
            
            # Script Generation
            'script_system_role': "You are a {genre} expert who creates engaging scripts for TikTok/YouTube videos. You follow timing and word count constraints PRECISELY.",
            'script_intro_prompt': "Create a CINEMATIC, high-energy intro that immediately hooks viewers and builds excitement for this {content_type} collection! This should be a COMPREHENSIVE introduction that takes sufficient time to properly engage the audience. Start with a powerful opening statement that creates urgency and curiosity, then build momentum by setting the scene and context for what viewers are about to experience. Reference and tease the SPECIFIC SELECTED MOVIES from the StreamGank results - mention their titles, years, or compelling details to show viewers exactly what incredible {content_type}s they're about to discover. Explain WHY this collection is special, WHAT makes these specific {content_type}s worth watching, and HOW viewers will benefit from staying tuned. Use TikTok/YouTube Shorts presenter energy - think dynamic, punchy, and irresistible. Create anticipation by teasing the quality and variety of the specific content coming up from these StreamGank selections. Make viewers feel they're about to discover something incredible and that they absolutely cannot scroll away from these handpicked {content_type}s! Then smoothly transition to presenting the first {content_type} with enthusiasm and confidence. The intro should feel substantial and complete, not rushed.",
            'script_movie_prompt': "Present this {content_type} recommendation. Be concise and compelling.",
            'script_constraints': "CONSTRAINTS: Duration: {duration} | Max words: {word_count} | Max sentences: {sentence_limit}",
            'script_content_info': "Content: {title} ({year}) - IMDb: {imdb}",
            'script_instruction': "Respond ONLY with the final script text.",
            
        },
        'fr': {
            # Movie Description Generation
            'desc_expert_role': "Tu es un expert en cinéma qui écrit des descriptions {focus} pour les réseaux sociaux.",
            'desc_task_instruction': "Tu écris TOUJOURS exactement 2 phrases complètes qui décrivent précisément le contenu du film/série donné.",
            'desc_task_critical': "TÂCHE CRITIQUE: Écrire EXACTEMENT 2 phrases précises pour \"{title}\".",
            'desc_search_context': "CONTEXTE DE RECHERCHE:",
            'desc_user_search': "Recherche utilisateur: {search}",
            'desc_found_content': "Ce {content_type} trouvé{platform}{country}",
            'desc_precise_info': "INFORMATIONS PRÉCISES DU {content_type_upper}:",
            'desc_exact_title': "Titre exact: {title}",
            'desc_imdb_score': "Score IMDb: {score}",
            'desc_year': "Année: {year}",
            'desc_actual_genres': "Genres réels: {genres}",
            'desc_mandatory_instructions': "INSTRUCTIONS OBLIGATOIRES:",
            'desc_first_sentence': "1. PREMIÈRE PHRASE: Description du contenu réel du {content_type} (20-35 mots)",
            'desc_use_genres': "   - Utilisez les genres réels: {genres}",
            'desc_mention_platform': "   - Mentionnez{platform}{genre}",
            'desc_authentic_content': "   - Décrivez le contenu authentique, pas générique",
            'desc_second_sentence': "2. DEUXIÈME PHRASE: Score + année + recommandation contextuelle (15-25 mots)",
            'desc_exact_score': "   - Score exact: {score}",
            'desc_exact_year': "   - Année exacte: {year}",
            'desc_personalized_rec': "   - Recommandation personnalisée pour votre recherche",
            'desc_response_instruction': "RÉPONSE (2 phrases précises basées sur le vrai contenu):",
            'content_film': "film",
            'content_serie': "série",
            'focus_detailed': "détaillées et structurées",
            'focus_simple': "simples et directes",
            'focus_creative': "créatives mais focalisées",
            
            # Script Generation
            'script_system_role': "Tu es un expert en {genre} qui crée des scripts engageants pour des vidéos TikTok/YouTube. Tu respectes PRÉCISÉMENT les contraintes de timing et de nombre de mots.",
            'script_intro_prompt': "Crée une introduction CINÉMATIQUE et haute énergie qui accroche immédiatement les spectateurs et génère de l'excitation pour cette collection de {content_type} ! Cette introduction doit être COMPLÈTE et prendre le temps nécessaire pour engager correctement l'audience. Commence par une déclaration percutante qui crée de l'urgence et de la curiosité, puis développe l'élan en plantant le décor et le contexte de ce que les spectateurs s'apprêtent à vivre. Référence et teases les FILMS/SÉRIES SPÉCIFIQUES SÉLECTIONNÉS des résultats StreamGank - mentionne leurs titres, années, ou détails captivants pour montrer aux spectateurs exactement quels {content_type}s incroyables ils sont sur le point de découvrir. Explique POURQUOI cette collection est spéciale, CE QUI rend ces {content_type}s spécifiques dignes d'être regardés, et COMMENT les spectateurs vont bénéficier de rester jusqu'au bout. Utilise l'énergie d'un présentateur TikTok/YouTube Shorts - pense dynamique, percutant et irrésistible. Crée de l'anticipation en teasant la qualité et la variété du contenu spécifique à venir de ces sélections StreamGank. Fais en sorte que les spectateurs sentent qu'ils sont sur le point de découvrir quelque chose d'incroyable et qu'ils ne peuvent absolument pas faire défiler ces {content_type}s triés sur le volet ! Puis passe fluidement à la présentation du premier {content_type} avec enthousiasme et confiance. L'introduction doit paraître substantielle et complète, pas précipitée.",
            'script_movie_prompt': "Présente cette recommandation de {content_type}. Sois concis et convaincant.",
            'script_constraints': "CONTRAINTES: Durée: {duration} | Max mots: {word_count} | Max phrases: {sentence_limit}",
            'script_content_info': "Contenu: {title} ({year}) - IMDb: {imdb}",
            'script_instruction': "Réponds UNIQUEMENT avec le texte du script final.",
            
        },
        'es': {
            # Script Generation (Spanish)
            'script_system_role': "Eres un experto en {genre} que crea guiones atractivos para videos de TikTok/YouTube. Sigues PRECISAMENTE las restricciones de tiempo y conteo de palabras.",
            'script_intro_prompt': "¡Crea una introducción CINEMATOGRÁFICA de alta energía que enganche inmediatamente a los espectadores y genere emoción por esta colección de {content_type}! Esta debe ser una introducción COMPLETA que tome el tiempo suficiente para involucrar apropiadamente a la audiencia. Comienza con una declaración poderosa que cree urgencia y curiosidad, luego construye impulso estableciendo la escena y el contexto de lo que los espectadores están a punto de experimentar. Referencia y adelanta las PELÍCULAS/SERIES ESPECÍFICAS SELECCIONADAS de los resultados de StreamGank - menciona sus títulos, años, o detalles convincentes para mostrar a los espectadores exactamente qué {content_type}s increíbles están a punto de descubrir. Explica POR QUÉ esta colección es especial, QUÉ hace que estas {content_type}s específicas valgan la pena ver, y CÓMO se beneficiarán los espectadores de quedarse hasta el final. Usa la energía de un presentador de TikTok/YouTube Shorts - piensa dinámico, impactante e irresistible. Crea expectativa adelantando la calidad y variedad del contenido específico que viene de estas selecciones de StreamGank. ¡Haz que los espectadores sientan que están a punto de descubrir algo increíble y que absolutamente no pueden hacer scroll de estas {content_type}s cuidadosamente seleccionadas! Luego haz una transición fluida para presentar la primera {content_type} con entusiasmo y confianza. La introducción debe sentirse sustancial y completa, no apresurada.",
            'script_movie_prompt': "Presenta esta recomendación de {content_type}. Sé conciso y convincente.",
            'script_constraints': "RESTRICCIONES: Duración: {duration} | Máx palabras: {word_count} | Máx oraciones: {sentence_limit}",
            'script_content_info': "Contenido: {title} ({year}) - IMDb: {imdb}",
            'script_instruction': "Responde SOLO con el texto del guión final.",
        },
        'de': {
            # Script Generation (German)
            'script_system_role': "Du bist ein {genre}-Experte, der ansprechende Skripte für TikTok/YouTube-Videos erstellt. Du hältst dich PRÄZISE an Zeit- und Wortzahl-Beschränkungen.",
            'script_intro_prompt': "Erstelle eine CINEMATISCHE, energiegeladene Einführung, die sofort die Zuschauer fesselt und Begeisterung für diese {content_type}-Sammlung aufbaut! Dies sollte eine UMFASSENDE Einführung sein, die sich ausreichend Zeit nimmt, um das Publikum richtig einzubinden. Beginne mit einer kraftvollen Aussage, die Dringlichkeit und Neugier erzeugt, dann baue Schwung auf, indem du die Szene und den Kontext für das setzt, was die Zuschauer gleich erleben werden. Referenziere und tease die SPEZIFISCHEN AUSGEWÄHLTEN FILME/SERIEN aus den StreamGank-Ergebnissen - erwähne ihre Titel, Jahre oder überzeugende Details, um den Zuschauern genau zu zeigen, welche unglaublichen {content_type}s sie gleich entdecken werden. Erkläre WARUM diese Sammlung besonders ist, WAS diese spezifischen {content_type}s sehenswert macht, und WIE die Zuschauer davon profitieren werden, dranzubleiben. Nutze die Energie eines TikTok/YouTube Shorts Moderators - denke dynamisch, packend und unwiderstehlich. Schaffe Vorfreude, indem du die Qualität und Vielfalt des spezifischen kommenden Inhalts aus diesen StreamGank-Auswahlen anteaserst. Lass die Zuschauer spüren, dass sie etwas Unglaubliches entdecken werden und dass sie absolut nicht von diesen handverlesenen {content_type}s wegscrollen können! Dann gehe flüssig zur Präsentation des ersten {content_type} mit Begeisterung und Selbstvertrauen über. Die Einführung sollte sich substanziell und vollständig anfühlen, nicht gehetzt.",
            'script_movie_prompt': "Präsentiere diese {content_type}-Empfehlung. Sei prägnant und überzeugend.",
            'script_constraints': "BESCHRÄNKUNGEN: Dauer: {duration} | Max Wörter: {word_count} | Max Sätze: {sentence_limit}",
            'script_content_info': "Inhalt: {title} ({year}) - IMDb: {imdb}",
            'script_instruction': "Antworte NUR mit dem finalen Skripttext.",
        },
        'it': {
            # Script Generation (Italian)
            'script_system_role': "Sei un esperto di {genre} che crea script coinvolgenti per video TikTok/YouTube. Segui PRECISAMENTE i vincoli di tempo e conteggio parole.",
            'script_intro_prompt': "Crea un'introduzione CINEMATOGRAFICA ad alta energia che catturi immediatamente gli spettatori e generi eccitazione per questa collezione di {content_type}! Questa deve essere un'introduzione COMPLETA che prenda il tempo sufficiente per coinvolgere adeguatamente il pubblico. Inizia con una dichiarazione potente che crei urgenza e curiosità, poi costruisci slancio stabilendo la scena e il contesto per quello che gli spettatori stanno per sperimentare. Riferisci e anticipa i FILM/SERIE SPECIFICI SELEZIONATI dai risultati di StreamGank - menziona i loro titoli, anni, o dettagli convincenti per mostrare agli spettatori esattamente quali {content_type} incredibili stanno per scoprire. Spiega PERCHÉ questa collezione è speciale, COSA rende questi {content_type} specifici degni di essere visti, e COME gli spettatori beneficeranno dal rimanere sintonizzati. Usa l'energia di un presentatore TikTok/YouTube Shorts - pensa dinamico, incisivo e irresistibile. Crea aspettativa anticipando la qualità e varietà del contenuto specifico in arrivo da queste selezioni StreamGank. Fai sentire agli spettatori che stanno per scoprire qualcosa di incredibile e che assolutamente non possono scrollare via da questi {content_type} selezionati con cura! Poi passa fluidamente alla presentazione del primo {content_type} con entusiasmo e fiducia. L'introduzione deve sembrare sostanziale e completa, non affrettata.",
            'script_movie_prompt': "Presenta questa raccomandazione di {content_type}. Sii conciso e convincente.",
            'script_constraints': "VINCOLI: Durata: {duration} | Max parole: {word_count} | Max frasi: {sentence_limit}",
            'script_content_info': "Contenuto: {title} ({year}) - IMDb: {imdb}",
            'script_instruction': "Rispondi SOLO con il testo dello script finale.",
        },
        'pt': {
            # Script Generation (Portuguese)
            'script_system_role': "Você é um especialista em {genre} que cria roteiros envolventes para vídeos do TikTok/YouTube. Você segue PRECISAMENTE as restrições de tempo e contagem de palavras.",
            'script_intro_prompt': "Crie uma introdução CINEMATOGRÁFICA de alta energia que capture imediatamente os espectadores e gere empolgação por esta coleção de {content_type}! Esta deve ser uma introdução ABRANGENTE que tome tempo suficiente para envolver adequadamente a audiência. Comece com uma declaração poderosa que crie urgência e curiosidade, depois construa momentum estabelecendo o cenário e contexto para o que os espectadores estão prestes a experienciar. Referencie e antecipe os FILMES/SÉRIES ESPECÍFICOS SELECIONADOS dos resultados do StreamGank - mencione seus títulos, anos, ou detalhes convincentes para mostrar aos espectadores exatamente quais {content_type}s incríveis eles estão prestes a descobrir. Explique POR QUE esta coleção é especial, O QUE torna estes {content_type}s específicos dignos de serem assistidos, e COMO os espectadores se beneficiarão de ficar até o fim. Use a energia de um apresentador do TikTok/YouTube Shorts - pense dinâmico, impactante e irresistível. Crie expectativa antecipando a qualidade e variedade do conteúdo específico que vem por aí dessas seleções do StreamGank. Faça os espectadores sentirem que estão prestes a descobrir algo incrível e que absolutamente não podem rolar a tela destes {content_type}s cuidadosamente selecionados! Depois faça uma transição suave para apresentar o primeiro {content_type} com entusiasmo e confiança. A introdução deve parecer substancial e completa, não apressada.",
            'script_movie_prompt': "Apresente esta recomendação de {content_type}. Seja conciso e convincente.",
            'script_constraints': "RESTRIÇÕES: Duração: {duration} | Máx palavras: {word_count} | Máx frases: {sentence_limit}",
            'script_content_info': "Conteúdo: {title} ({year}) - IMDb: {imdb}",
            'script_instruction': "Responda APENAS com o texto do roteiro final.",
        }
    }

def get_language_code(country):
    """Get language code from country - supports 5+ languages"""
    language_map = {
        'FR': 'fr',    # French
        'ES': 'es',    # Spanish  
        'DE': 'de',    # German
        'IT': 'it',    # Italian
        'PT': 'pt',    # Portuguese
        'US': 'en',    # English
        'GB': 'en',    # English (UK)
        'CA': 'en',    # English (Canada)
    }
    return language_map.get(country, 'en')  # Default to English

def build_context_elements(country, platform, genre, lang):
    """Build context elements dynamically"""
    t = get_translations()[lang]
    
    # Country context
    if lang == 'fr':
        country_ctx = " en France" if country == 'FR' else (f" en {country}" if country else "")
        platform_ctx = f" sur {platform}" if platform else ""
    else:
        country_ctx = " in France" if country == 'FR' else (f" in {country}" if country and country != 'US' else "")
        platform_ctx = f" on {platform}" if platform else ""
    
    genre_ctx = f" {genre.lower()}" if genre else ""
    
    return {
        'country': country_ctx,
        'platform': platform_ctx,
        'genre': genre_ctx
    }

def create_dynamic_prompt(movie, search_summary, context_elements, content_type, lang):
    """Create fully dynamic prompt using translations"""
    t = get_translations()[lang]
    
    title = movie.get('title', 'Unknown')
    genres = ', '.join(movie.get('genres', ['Divers'] if lang == 'fr' else ['Various']))
    content_name = content_type or (t['content_film'] if lang == 'fr' else t['content_movie'])
    content_upper = content_name.upper()
    
    return f"""{t['desc_task_critical'].format(title=title)}

{t['desc_search_context']}
- {t['desc_user_search'].format(search=search_summary)}
- {t['desc_found_content'].format(content_type=content_name, platform=context_elements['platform'], country=context_elements['country'])}

{t['desc_precise_info'].format(content_type_upper=content_upper)}
- {t['desc_exact_title'].format(title=title)}
- {t['desc_imdb_score'].format(score=movie['imdb'])}
- {t['desc_year'].format(year=movie['year'])}
- {t['desc_actual_genres'].format(genres=genres)}

{t['desc_mandatory_instructions']}
{t['desc_first_sentence'].format(content_type=content_name)}
{t['desc_use_genres'].format(genres=genres)}
{t['desc_mention_platform'].format(platform=context_elements['platform'], genre=context_elements['genre'])}
{t['desc_authentic_content']}

{t['desc_second_sentence']}
{t['desc_exact_score'].format(score=movie['imdb'])}
{t['desc_exact_year'].format(year=movie['year'])}
{t['desc_personalized_rec']}

{t['desc_response_instruction']}"""

def generate_movie_description_simple(movie, search_summary, context_elements, content_type, lang, strategy):
    """Generate description - simplified version"""
    t = get_translations()[lang]
    
    # Get focus text dynamically
    focus_map = {
        'detailed_structured': t['focus_detailed'],
        'simple_direct': t['focus_simple'],
        'creative_flexible': t['focus_creative']
    }
    focus = focus_map.get(strategy['name'], t['focus_simple'])
    
    # Create messages
    system_msg = f"{t['desc_expert_role'].format(focus=focus)} {t['desc_task_instruction']}"
    user_prompt = create_dynamic_prompt(movie, search_summary, context_elements, content_type, lang)
    
    # Call OpenAI
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_prompt}
        ],
        temperature=strategy['temperature'],
        max_tokens=strategy['max_tokens'],
        presence_penalty=0.1,
        frequency_penalty=0.1
    )
    
    return response.choices[0].message.content.strip()

def validate_and_fix_description(text):
    """Simple validation and fix"""
    sentences = [s.strip() for s in text.split('.') if s.strip()]
    
    if len(sentences) >= 2 and len(text) > 50:
        return {
            'valid': True,
            'text': f"{sentences[0]}. {sentences[1]}.",
            'count': len(sentences)
        }
    else:
        return {
            'valid': False,
            'text': text,
            'count': len(sentences)
        }

def enrich_movie_data(movie_data, country=None, genre=None, platform=None, content_type=None):
    """
    Simplified movie data enrichment with dynamic language support
    """
    logger.info(f"🤖 Enriching {len(movie_data)} movies with AI descriptions")
    
    # Get language and build context once
    lang = get_language_code(country)
    search_summary = ", ".join([f"{k}: {v}" for k, v in {
        'country': country, 'genre': genre, 'platform': platform, 'type': content_type
    }.items() if v and (k != 'country' or v != 'US')])
    
    context_elements = build_context_elements(country, platform, genre, lang)
    
    # Simple strategy list
    strategies = [
        {"name": "detailed_structured", "temperature": 0.3, "max_tokens": 300},
        {"name": "simple_direct", "temperature": 0.1, "max_tokens": 250},
        {"name": "creative_flexible", "temperature": 0.5, "max_tokens": 350}
    ]
    
    # Process each movie
    for movie in movie_data:
        title = movie.get('title', 'Unknown')
        logger.info(f"🎯 Processing: {title}")
        
        description = None
        
        # Try strategies until success
        for i, strategy in enumerate(strategies):
            try:
                logger.info(f"   Strategy {i+1}/3: {strategy['name']}")
                
                # Generate description
                generated = generate_movie_description_simple(
                    movie, search_summary, context_elements, content_type, lang, strategy
                )
                
                # Validate
                result = validate_and_fix_description(generated)
                
                if result['valid']:
                    description = result['text']
                    logger.info(f"   ✅ SUCCESS: {result['count']} sentences")
                    break
                else:
                    logger.warning(f"   ⚠️ Invalid: {result['count']} sentences")
                    if i == len(strategies) - 1:
                        logger.error(f"❌ All strategies failed for {title}")
                        raise Exception(f"Failed to generate description for {title}")
                    
            except Exception as e:
                logger.warning(f"   ⚠️ Error: {str(e)}")
                if i == len(strategies) - 1:
                    logger.error(f"❌ Critical failure for {title}")
                    raise Exception(f"Critical: Failed for {title}")
        
        # Store result
        if not description:
            raise Exception(f"No description generated for {title}")
            
        movie["enriched_description"] = description
        logger.info(f"✅ DONE: {title}")
        logger.info(f"   Text: {description}")
        
        time.sleep(0.8)  # Rate limiting
    
    logger.info("✅ All movies enriched")
    return movie_data

# =============================================================================
# SCRIPT GENERATION - DYNAMIC LANGUAGE SYSTEM
# =============================================================================

def create_script_prompt(movie, rule, content_type, genre, platform, lang, all_movies=None):
    """Create dynamic script prompt using translations"""
    t = get_translations()[lang]
    
    title = movie.get('title', 'Unknown')
    year = movie.get('year', 'Unknown')
    imdb = movie.get('imdb', '7+')
    
    # Special handling for intro + movie1 combination
    if rule.get('is_intro', False):
        # Use the enhanced cinematic intro prompt and include info about all movies
        prompt_type = t['script_intro_prompt']
        
        # Create a summary of all selected movies WITHOUT revealing titles
        movies_summary = ""
        if all_movies and len(all_movies) >= 3:
            # Calculate average IMDb score and get quality indicators
            imdb_scores = []
            years = []
            for movie_data in all_movies[:3]:
                try:
                    score = float(movie_data.get('imdb', '7.0'))
                    imdb_scores.append(score)
                except (ValueError, TypeError):
                    imdb_scores.append(7.0)
                
                try:
                    year = int(movie_data.get('year', '2020'))
                    years.append(year)
                except (ValueError, TypeError):
                    years.append(2020)
            
            avg_score = sum(imdb_scores) / len(imdb_scores)
            min_year = min(years)
            max_year = max(years)
            
            # Create engaging summary without revealing titles
            movies_intro = {
                'en': f"StreamGank Selection: 3 incredible {content_type or 'movies'} (IMDb avg: {avg_score:.1f}) spanning {min_year}-{max_year}",
                'fr': f"Sélection StreamGank: 3 {content_type or 'films'} incroyables (IMDb moy: {avg_score:.1f}) de {min_year} à {max_year}",
                'es': f"Selección StreamGank: 3 {content_type or 'películas'} increíbles (IMDb prom: {avg_score:.1f}) desde {min_year}-{max_year}",
                'de': f"StreamGank-Auswahl: 3 unglaubliche {content_type or 'Filme'} (IMDb Ø: {avg_score:.1f}) von {min_year}-{max_year}",
                'it': f"Selezione StreamGank: 3 {content_type or 'film'} incredibili (IMDb media: {avg_score:.1f}) dal {min_year}-{max_year}",
                'pt': f"Seleção StreamGank: 3 {content_type or 'filmes'} incríveis (IMDb média: {avg_score:.1f}) de {min_year}-{max_year}"
            }
            movies_summary = movies_intro.get(lang, movies_intro['en'])
        
        # Add the movies summary to the content info WITHOUT specific titles
        enhanced_content_info = f"""
{movies_summary}

First {content_type or ('film' if lang == 'fr' else 'movie')} to present: {title} ({year}) - IMDb: {imdb}
Platform: {platform or 'streaming platform'} | Genre: {genre or 'entertainment'}"""
        
        return f"""{prompt_type.format(content_type=content_type or ('film' if lang == 'fr' else 'movie'))}

{t['script_constraints'].format(
    duration=rule['duration'],
    word_count=rule['word_count'],
    sentence_limit=rule['sentence_limit']
)}

{enhanced_content_info}

{t['script_instruction']}"""
    else:
        # Use default prompt based on rule name
        if rule['name'] == 'movie1':
            prompt_type = t['script_intro_prompt']
        else:
            prompt_type = t['script_movie_prompt']
     
    return f"""{prompt_type.format(content_type=content_type or ('film' if lang == 'fr' else 'movie'))}

{t['script_constraints'].format(
    duration=rule['duration'],
    word_count=rule['word_count'],
    sentence_limit=rule['sentence_limit']
)}

{t['script_content_info'].format(title=title, year=year, imdb=imdb)}

{t['script_instruction']}"""

def generate_single_script(movie, rule, content_type, genre, platform, lang, all_movies=None):
    """Generate a single script section"""
    t = get_translations()[lang]
    
    try:
        # Create system message
        system_msg = t['script_system_role'].format(genre=genre or ('divertissement' if lang == 'fr' else 'entertainment'))
        
        # Create user prompt - pass all_movies for intro generation
        user_prompt = create_script_prompt(movie, rule, content_type, genre, platform, lang, all_movies)
        
        logger.info(f"🤖 Generating script for {rule['name']}")
        
        # Generate script using OpenAI
        client = openai.OpenAI()
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=300
        )
        
        script = response.choices[0].message.content.strip()
        
        logger.info(f"✅ Script generated for {rule['name']}: {len(script.split())} words")
        return script
        
    except Exception as e:
        logger.error(f"❌ Script generation failed for {rule['name']}: {str(e)}")
        logger.error(f"❌ STRICT MODE - No fallback allowed for script generation")
        # Return None to indicate failure - let caller handle the error
        return None

def generate_video_scripts(enriched_movies, country=None, genre=None, platform=None, content_type=None):
    """
    Generate scripts for video segments using dynamic language support
    """
    logger.info(f"📝 Generating scripts for {len(enriched_movies)} movies")
    
    # Get language
    lang = get_language_code(country)
    
    # Script timing rules for reels (60-90 seconds total)
    script_rules = [
        {
            "name": "movie1", 
            "duration": "25-30 seconds",
            "word_count": "50-70",
            "sentence_limit": "2-3",
            "movie_index": 0,
            "is_intro": True  # Special flag for intro + movie1 combination
        },
        {
            "name": "movie2",
            "duration": "15-20 seconds", 
            "word_count": "30-45",
            "sentence_limit": "1-2",
            "movie_index": 1
        },
        {
            "name": "movie3",
            "duration": "15-20 seconds", 
            "word_count": "30-45",
            "sentence_limit": "1-2",
            "movie_index": 2
        }
    ]
    
    # Generate scripts - STRICT MODE (NO FALLBACKS)
    generated_scripts = {}
    
    for rule in script_rules:
        movie = enriched_movies[rule["movie_index"]]
        
        # Pass all movies data when generating intro script
        if rule.get('is_intro', False):
            script = generate_single_script(movie, rule, content_type, genre, platform, lang, enriched_movies)
        else:
            script = generate_single_script(movie, rule, content_type, genre, platform, lang)
        
        # STRICT VALIDATION - Fail if any script generation fails
        if script is None:
            logger.error(f"❌ Script generation failed for {rule['name']} - STRICT MODE")
            logger.error(f"❌ Cannot continue without all scripts - returning None")
            return None
            
        generated_scripts[rule["name"]] = script
    
    # Create scripts dictionary (all scripts validated and generated successfully)
    scripts = {
        "movie1": {
            "text": generated_scripts["movie1"],  # Direct access - we know it exists
            "path": "videos/script_movie1.txt"
        },
        "movie2": {
            "text": generated_scripts["movie2"],  # Direct access - we know it exists
            "path": "videos/script_movie2.txt"
        },
        "movie3": {
            "text": generated_scripts["movie3"],  # Direct access - we know it exists
            "path": "videos/script_movie3.txt"
        }
    }
    
    # Save individual scripts
    for key, script_data in scripts.items():
        try:
            with open(script_data["path"], "w", encoding='utf-8') as f:
                f.write(script_data["text"])
        except Exception as e:
            logger.error(f"Failed to save script {key}: {str(e)}")
    
    # Create combined script
    combined_script = "\n\n".join([scripts[key]["text"] for key in ["movie1", "movie2", "movie3"]])
    combined_path = "videos/combined_script.txt"
    
    try:
        with open(combined_path, "w", encoding='utf-8') as f:
            f.write(combined_script)
    except Exception as e:
        logger.error(f"Failed to save combined script: {str(e)}")
    
    logger.info("✅ Script generation completed")
    return combined_script, combined_path, scripts

# =============================================================================
# EXISTING STREAMGANK HELPER FUNCTIONS
# =============================================================================

def extract_youtube_video_id(url: str) -> Optional[str]:
    """
    Extract YouTube video ID from various YouTube URL formats
    
    Args:
        url (str): YouTube URL in various formats
        
    Returns:
        str: YouTube video ID or None if not found
    """
    # Various YouTube URL patterns
    patterns = [
        r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)',
        r'(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]+)',
        r'(?:https?://)?(?:www\.)?youtu\.be/([a-zA-Z0-9_-]+)',
        r'(?:https?://)?(?:www\.)?youtube\.com/v/([a-zA-Z0-9_-]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    logger.warning(f"Could not extract YouTube video ID from URL: {url}")
    return None

def download_youtube_trailer(trailer_url: str, output_dir: str = "temp_trailers") -> Optional[str]:
    """
    Download YouTube trailer video using yt-dlp
    
    Args:
        trailer_url (str): YouTube trailer URL
        output_dir (str): Directory to save downloaded video
        
    Returns:
        str: Path to downloaded video file or None if failed
    """
    try:
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Extract video ID for consistent naming
        video_id = extract_youtube_video_id(trailer_url)
        if not video_id:
            logger.error(f"Invalid YouTube URL: {trailer_url}")
            return None
        
        # Configure yt-dlp options for best quality video
        ydl_opts = {
            'format': 'best[height<=720][ext=mp4]/best[ext=mp4]/best',  # Prefer 720p MP4
            'outtmpl': os.path.join(output_dir, f'{video_id}_trailer.%(ext)s'),
            'quiet': True,  # Reduce verbose output
            'no_warnings': True,
        }
        
        logger.info(f"🎬 Downloading YouTube trailer: {trailer_url}")
        logger.info(f"   Video ID: {video_id}")
        logger.info(f"   Output directory: {output_dir}")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Download the video
            ydl.download([trailer_url])
            
            # Find the downloaded file
            for file in os.listdir(output_dir):
                if video_id in file and file.endswith(('.mp4', '.webm', '.mkv')):
                    downloaded_path = os.path.join(output_dir, file)
                    logger.info(f"✅ Successfully downloaded: {downloaded_path}")
                    return downloaded_path
        
        logger.error(f"❌ Could not find downloaded file for video ID: {video_id}")
        return None
        
    except Exception as e:
        logger.error(f"❌ Error downloading YouTube trailer {trailer_url}: {str(e)}")
        return None

def extract_second_highlight(video_path: str, start_time: int = 30, output_dir: str = "temp_clips") -> Optional[str]:
    """
    Extract a highlight clip from a video and convert to CINEMATIC PORTRAIT format (9:16)
    
    This function converts landscape YouTube trailers to portrait format using advanced techniques:
    1. Creates a soft Gaussian-blurred background from the original video
    2. Centers the original frame on top of the blurred background
    3. Enhances contrast, clarity, and saturation for TikTok/Instagram Reels aesthetics
    4. Maintains HD quality (1080x1920) without black bars
    
    Args:
        video_path (str): Path to the source video file (typically landscape YouTube trailer)
        start_time (int): Start time in seconds (default: 30s to skip intros)
        output_dir (str): Directory to save the cinematic portrait highlight clip
        
    Returns:
        str: Path to the extracted CINEMATIC PORTRAIT highlight clip or None if failed
    """
    try:
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate output filename
        video_name = Path(video_path).stem
        output_path = os.path.join(output_dir, f"{video_name}_10s_highlight.mp4")
        
        logger.info(f"🎞️ Extracting CINEMATIC PORTRAIT highlight from: {video_path}")
        logger.info(f"   Start time: {start_time}s")
        logger.info(f"   Technique: Gaussian blur background + centered frame")
        logger.info(f"   Enhancement: Contrast, clarity, and saturation boost")
        logger.info(f"   Output: {output_path}")
        
        # Use FFmpeg with Gaussian blur background for cinematic portrait conversion
        # Creates a soft blurred background instead of black bars for TikTok/Instagram Reels
        ffmpeg_cmd = [
            'ffmpeg',
            '-i', video_path,           # Input file
            '-ss', str(start_time),     # Start time
            '-t', '15',                 # Duration
            '-c:v', 'libx264',         # Video codec
            '-c:a', 'aac',             # Audio codec
            '-crf', '15',              # Ultra-high quality for social media
            '-preset', 'slow',         # Better compression efficiency
            '-profile:v', 'high',      # H.264 high profile for better quality
            '-level:v', '4.0',         # H.264 level 4.0 for high resolution
            '-movflags', '+faststart', # Optimize for web streaming
            '-pix_fmt', 'yuv420p',     # Ensure compatibility
            # Complex filter for Gaussian blur background + centered original
            '-filter_complex', 
            '[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,gblur=sigma=20[blurred];'
            '[0:v]scale=1080:1920:force_original_aspect_ratio=decrease[scaled];'
            '[blurred][scaled]overlay=(W-w)/2:(H-h)/2,unsharp=5:5:1.0:5:5:0.3,eq=contrast=1.1:brightness=0.05:saturation=1.2',
            '-r', '30',                # 30 FPS for smooth playback
            '-maxrate', '4000k',       # Higher bitrate for premium quality
            '-bufsize', '8000k',       # Larger buffer size
            '-y',                       # Overwrite output file
            output_path
        ]
        
        # Run FFmpeg command
        result = subprocess.run(
            ffmpeg_cmd, 
            capture_output=True, 
            text=True,
            timeout=60  # 60 second timeout
        )
        
        if result.returncode == 0:
            logger.info(f"✅ Successfully created CINEMATIC PORTRAIT highlight: {output_path}")
            logger.info(f"   🎬 Format: 1080x1920 with Gaussian blur background")
            logger.info(f"   🎨 Enhanced for TikTok/Instagram Reels aesthetics")
            return output_path
        else:
            logger.error(f"❌ FFmpeg error: {result.stderr}")
            return None
            
    except subprocess.TimeoutExpired:
        logger.error(f"❌ FFmpeg timeout while processing: {video_path}")
        return None
    except Exception as e:
        logger.error(f"❌ Error extracting highlight from {video_path}: {str(e)}")
        return None

def upload_clip_to_cloudinary(clip_path: str, movie_title: str, movie_id: str = None, transform_mode: str = "youtube_shorts") -> Optional[str]:
    """
    Upload a video clip to Cloudinary with optimized settings
    
    Args:
        clip_path (str): Path to the video clip file
        movie_title (str): Movie title for naming
        movie_id (str): Movie ID for unique identification
        transform_mode (str): Transformation mode - "fit", "pad", "scale", or "auto"
        
    Returns:
        str: Cloudinary URL of uploaded clip or None if failed
    """
    try:
        # Create a clean filename from movie title
        clean_title = re.sub(r'[^a-zA-Z0-9_-]', '_', movie_title.lower())
        clean_title = re.sub(r'_+', '_', clean_title).strip('_')
        
        # Create unique public ID
        public_id = f"movie_clips/{clean_title}_{movie_id}_10s" if movie_id else f"movie_clips/{clean_title}_10s"
        
        logger.info(f"☁️ Uploading clip to Cloudinary: {clip_path}")
        logger.info(f"   Movie: {movie_title}")
        logger.info(f"   Public ID: {public_id}")
        logger.info(f"   Transform mode: {transform_mode}")
        
        # YouTube Shorts optimized transformation modes (9:16 portrait - 1080x1920)
        transform_modes = {
            "fit": [
                {"width": 1080, "height": 1920, "crop": "fit", "background": "black"},  # YouTube Shorts standard resolution
                {"quality": "auto:best"},
                {"format": "mp4"},
                {"video_codec": "h264"},
                {"bit_rate": "2000k"}  # High bitrate for crisp quality
            ],
            "smart_fit": [
                {"width": 1080, "height": 1920, "crop": "fill", "gravity": "center"},  # Smart crop with center focus
                {"quality": "auto:best"},
                {"format": "mp4"},
                {"video_codec": "h264"},
                {"bit_rate": "2500k"},  # Even higher bitrate
                {"flags": "progressive"}  # Progressive scan for smooth playbook
            ],
            "pad": [
                {"width": 1080, "height": 1920, "crop": "pad", "background": "auto"},   # Smart padding with auto background
                {"quality": "auto:best"},
                {"format": "mp4"},
                {"bit_rate": "2000k"}
            ],
            "scale": [
                {"width": 1080, "height": 1920, "crop": "scale"},                      # Scale to fit (may distort)
                {"quality": "auto:best"},
                {"format": "mp4"},
                {"bit_rate": "1800k"}
            ],
            "youtube_shorts": [
                {"width": 1080, "height": 1920, "crop": "fill", "gravity": "center"},  # YouTube Shorts optimized
                {"quality": "auto:best"},
                {"format": "mp4"},
                {"video_codec": "h264"},
                {"bit_rate": "3000k"},  # Premium bitrate for YouTube Shorts quality
                {"flags": "progressive"},
                {"audio_codec": "aac"},
                {"audio_frequency": 48000}  # High quality audio
            ]
        }
        
        # Get the transformation based on mode
        transformation = transform_modes.get(transform_mode, transform_modes["youtube_shorts"])
        
        # Upload to Cloudinary with video optimization (using selected transformation)
        upload_result = cloudinary.uploader.upload(
            clip_path,
            resource_type="video",
            public_id=public_id,
            folder="movie_clips",
            overwrite=True,
            quality="auto",              # Automatic quality optimization
            format="mp4",               # Ensure MP4 format
            video_codec="h264",         # Use H.264 codec for compatibility
            audio_codec="aac",          # Use AAC audio codec
            transformation=transformation
        )
        
        cloudinary_url = upload_result.get('secure_url')
        logger.info(f"✅ Successfully uploaded to Cloudinary: {cloudinary_url}")
        
        return cloudinary_url
        
    except Exception as e:
        logger.error(f"❌ Error uploading {clip_path} to Cloudinary: {str(e)}")
        return None

def process_movie_trailers_to_clips(movie_data: List[Dict], max_movies: int = 3, transform_mode: str = "fit") -> Dict[str, str]:
    """
    Process movie trailers to create 10-second highlight clips and upload to Cloudinary
    
    Args:
        movie_data (List[Dict]): List of movie data dictionaries with trailer_url
        max_movies (int): Maximum number of movies to process
        transform_mode (str): Transformation mode - "fit", "pad", "scale", or "auto"
        
    Returns:
        Dict[str, str]: Dictionary mapping movie titles to Cloudinary clip URLs
    """
    clip_urls = {}
    temp_dirs = ["temp_trailers", "temp_clips"]
    
    try:
        # Create temporary directories
        for temp_dir in temp_dirs:
            os.makedirs(temp_dir, exist_ok=True)
        
        logger.info(f"🎬 PROCESSING MOVIE TRAILERS TO CLIPS")
        logger.info(f"📋 Processing {min(len(movie_data), max_movies)} movies")
        
        # Process each movie (up to max_movies)
        for i, movie in enumerate(movie_data[:max_movies]):
            movie_title = movie.get('title', f'Movie_{i+1}')
            movie_id = str(movie.get('id', i+1))
            trailer_url = movie.get('trailer_url', '')
            
            logger.info(f"🎯 Processing Movie {i+1}: {movie_title}")
            logger.info(f"   Movie ID: {movie_id}")
            logger.info(f"   Trailer URL: {trailer_url}")
            
            if not trailer_url:
                logger.warning(f"⚠️ No trailer URL for {movie_title}, skipping...")
                continue
            
            # Step 1: Download YouTube trailer
            downloaded_trailer = download_youtube_trailer(trailer_url)
            if not downloaded_trailer:
                logger.error(f"❌ Failed to download trailer for {movie_title}")
                continue
            
            # Step 2: Extract highlight
            highlight_clip = extract_second_highlight(downloaded_trailer)
            if not highlight_clip:
                logger.error(f"❌ Failed to extract highlight for {movie_title}")
                continue
            
            # Step 3: Upload to Cloudinary
            cloudinary_url = upload_clip_to_cloudinary(highlight_clip, movie_title, movie_id, transform_mode)
            if cloudinary_url:
                clip_urls[movie_title] = cloudinary_url
                logger.info(f"✅ Successfully processed {movie_title}: {cloudinary_url}")
            else:
                logger.error(f"❌ Failed to upload clip for {movie_title}")
        
        logger.info(f"🏁 PROCESSING COMPLETE: {len(clip_urls)}/{min(len(movie_data), max_movies)} clips processed")
        
        return clip_urls
        
    except Exception as e:
        logger.error(f"❌ Error in process_movie_trailers_to_clips: {str(e)}")
        return clip_urls
        
    finally:
        # Clean up temporary files
        try:
            import shutil
            for temp_dir in temp_dirs:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                    logger.info(f"🧹 Cleaned up temporary directory: {temp_dir}")
        except Exception as e:
            logger.warning(f"⚠️ Could not clean up temporary files: {str(e)}")

# === EXISTING STREAMGANK HELPER FUNCTIONS ===

def get_genre_mapping_by_country(country_code):
    """
    Get genre mapping dictionary based on country code for StreamGank URL parameters
    
    Args:
        country_code (str): Country code (e.g., 'FR', 'US', 'DE', etc.)
        
    Returns:
        dict: Mapping from database genre names to StreamGank URL genre parameters
        
    Example:
        >>> mapping_fr = get_genre_mapping_by_country('FR')
        >>> mapping_fr.get('Horror')   # Returns 'Horreur' (French translation)
        >>> mapping_fr.get('Drama')    # Returns 'Drame' (French translation)
        >>> mapping_us = get_genre_mapping_by_country('US')
        >>> mapping_us.get('Horror')   # Returns 'Horror' (English, no translation)
        >>> mapping_us.get('Drama')    # Returns 'Drama' (English, no translation)
    """
    
    # Base English genre mapping (for US and other English-speaking countries)
    english_genres = {
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
    };
    
    # French genre mapping for StreamGank France
    french_genres = {
        "Action & Adventure": "Action & Aventure",
        "Animation": "Animation",
        "Comedy": "Comédie",
        "Crime": "Crime",
        "Documentary": "Documentaire",
        "Drama": "Drame",
        "Fantasy": "Fantastique",
        "History": "Histoire",
        "Horror": "Horreur",
        "Kids & Family": "Enfants & Famille",
        "Made in Europe": "Made in Europe",
        "Music & Musical": "Musique & Musical",
        "Mystery & Thriller": "Mystère & Thriller",
        "Reality TV": "Télé-réalité",
        "Romance": "Romance",
        "Science-Fiction": "Science-Fiction",
        "Sport": "Sport",
        "War & Military": "Guerre & Militaire",
        "Western": "Western"
    };
    
    # Country-specific genre mappings
    country_mappings = {
        'FR': french_genres,
        'US': english_genres,
        # Add more countries as needed
        # 'DE': german_genres,  # Could add German mapping later
        # 'ES': spanish_genres,  # Could add Spanish mapping later
        # 'IT': italian_genres,  # Could add Italian mapping later
    }
    
    # Return country-specific mapping or default to English
    return country_mappings.get(country_code, english_genres)


def get_platform_mapping():
    """
    Get platform for StreamGank URL parameters
    """
    
    # Base platform mapping (consistent across most countries)
    base_platforms = {
        'Prime': 'amazon',
        'Apple TV+': 'apple',
        'Disney+': 'disney',
        'Max': 'max',
        'Netflix': 'Netflix',
        'Free': 'free',
    }
    
    return base_platforms

def get_content_type_mapping():
    """
    Get content type mapping dictionary for StreamGank URL parameters
    Note: Content types are consistent across all supported countries (FR, US)
    
    Returns:
        dict: Mapping from database content types to StreamGank URL type parameters
        
    Example:
        >>> mapping = get_content_type_mapping()
        >>> mapping.get('Série')    # Returns 'Serie'
        >>> mapping.get('Émission') # Returns 'Serie' (French TV show term)
    """
    
    # Universal content type mapping (supports both French and English terms)
    return {
        'Film': 'Film',
        'Movie': 'Film',
        'Série': 'Serie',
        'Series': 'Serie',
        'TV Show': 'Serie',
        'TV Series': 'Serie',
        'Émission': 'Serie'  # French TV show term
    }

def get_content_type_mapping_by_country(country_code):
    """
    Legacy function - content types are now universal across countries
    
    Args:
        country_code (str): Country code (ignored, kept for backward compatibility)
        
    Returns:
        dict: Universal content type mapping
    """
    # Content types are now consistent across all countries
    return get_content_type_mapping()

def validate_platform(platform):
    """
    Validate if platform is supported
    
    Args:
        platform (str): Platform to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    mapping = get_platform_mapping()
    return platform in mapping

def validate_content_type(content_type):
    """
    Validate if content type is supported
    
    Args:
        content_type (str): Content type to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    mapping = get_content_type_mapping()
    return content_type in mapping


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
        >>> url = build_streamgank_url('FR', 'Horror', 'Netflix', 'Série')
        >>> print(url)
        https://streamgank.com/?country=FR&genres=Horreur&platforms=Netflix&type=Serie
        >>> url = build_streamgank_url('US', 'Drama', 'Netflix', 'Film')
        >>> print(url)
        https://streamgank.com/?country=US&genres=Drama&platforms=Netflix&type=Film
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
        platform_mapping = get_platform_mapping()
        streamgank_platform = platform_mapping.get(platform, platform.lower())
        url_params.append(f"platforms={streamgank_platform}")
    
    if content_type:
        # Use universal content type mapping (same across all countries)
        type_mapping = get_content_type_mapping()
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
        ['FR', 'US']
    """
    
    return ['FR', 'US']


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
    Note: Only genres are country-specific now. Platforms and content types are universal.
    
    Args:
        country_code (str): Country code (used only for genre mapping)
        
    Returns:
        dict: Dictionary containing all mappings
        
    Example:
        >>> mappings = get_all_mappings_for_country('FR')
        >>> print(mappings.keys())
        dict_keys(['genres', 'platforms', 'content_types'])
    """
    
    return {
        'genres': get_genre_mapping_by_country(country_code),  # Still country-specific (FR vs US translations)
        'platforms': get_platform_mapping(),  # Universal across countries
        'content_types': get_content_type_mapping()  # Universal across countries
    } 

def get_platform_mapping_by_country(country_code):
    """
    Get platform mapping dictionary based on country code for StreamGank URL parameters
    
    Args:
        country_code (str): Country code (e.g., 'FR', 'US', etc.)
        
    Returns:
        dict: Platform mapping (same across all countries currently)
    """
    # Platform mapping is consistent across countries
    return get_platform_mapping()

def _get_thematic_colors(platform: str, genres: List[str], title: str) -> Dict[str, tuple]:
    """Get thematic colors based on platform, genres, and title"""
    # Platform-based base colors
    platform_themes = {
        'Netflix': {'primary': (229, 9, 20), 'secondary': (139, 0, 0)},
        'Max': {'primary': (0, 229, 255), 'secondary': (0, 100, 139)}, 
        'Prime Video': {'primary': (0, 168, 225), 'secondary': (0, 80, 120)},
        'Disney+': {'primary': (17, 60, 207), 'secondary': (10, 30, 100)},
        'Hulu': {'primary': (28, 231, 131), 'secondary': (10, 120, 60)},
        'Apple TV+': {'primary': (27, 27, 27), 'secondary': (60, 60, 60)}
    }
    
    # Genre-based mood colors
    genre_moods = {
        'Horror': {'primary': (139, 0, 0), 'secondary': (60, 0, 0)},
        'Horreur': {'primary': (139, 0, 0), 'secondary': (60, 0, 0)},
        'Thriller': {'primary': (75, 0, 130), 'secondary': (30, 0, 60)},
        'Drama': {'primary': (25, 25, 112), 'secondary': (10, 10, 50)},
        'Action': {'primary': (255, 69, 0), 'secondary': (180, 30, 0)},
        'Comedy': {'primary': (255, 165, 0), 'secondary': (200, 100, 0)},
        'Fantasy': {'primary': (148, 0, 211), 'secondary': (80, 0, 120)},
        'Fantastique': {'primary': (148, 0, 211), 'secondary': (80, 0, 120)}
    }
    
    # Title-specific themes
    title_themes = {
        'Wednesday': {'primary': (139, 0, 139), 'secondary': (70, 0, 70)},
        'Stranger Things': {'primary': (220, 20, 60), 'secondary': (120, 10, 30)},
        'The Last of Us': {'primary': (85, 107, 47), 'secondary': (40, 50, 20)}
    }
    
    # Priority: Title > Genre > Platform
    if title in title_themes:
        return title_themes[title]
    elif any(genre in genre_moods for genre in genres):
        matching_genre = next(genre for genre in genres if genre in genre_moods)
        return genre_moods[matching_genre]
    elif platform in platform_themes:
        return platform_themes[platform]
    else:
        return {'primary': (60, 60, 100), 'secondary': (30, 30, 50)}

def _add_thematic_gradient(canvas: Image.Image, colors: Dict[str, tuple]):
    """Add thematic gradient overlay to canvas"""
    width, height = canvas.size
    overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    primary = colors['primary']
    secondary = colors['secondary']
    
    # Create vertical gradient
    for y in range(height):
        # Gradient from top (secondary) to bottom (primary)
        ratio = y / height
        r = int(secondary[0] + (primary[0] - secondary[0]) * ratio)
        g = int(secondary[1] + (primary[1] - secondary[1]) * ratio)
        b = int(secondary[2] + (primary[2] - secondary[2]) * ratio)
        alpha = int(40 + 30 * ratio)  # Increasing opacity towards bottom
        
        draw.line([(0, y), (width, y)], fill=(r, g, b, alpha))
    
    canvas.paste(overlay, (0, 0), overlay)

def _add_vignette_effect(canvas: Image.Image):
    """Add cinematic vignette effect"""
    width, height = canvas.size
    vignette = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(vignette)
    
    # Create radial vignette
    center_x, center_y = width // 2, height // 2
    max_distance = ((width // 2) ** 2 + (height // 2) ** 2) ** 0.5
    
    for x in range(0, width, 10):  # Step by 10 for performance
        for y in range(0, height, 10):
            distance = ((x - center_x) ** 2 + (y - center_y) ** 2) ** 0.5
            alpha = int((distance / max_distance) * 120)  # Max 120 alpha at edges
            if alpha > 0:
                draw.rectangle([x, y, x+10, y+10], fill=(0, 0, 0, min(alpha, 120)))
    
    canvas.paste(vignette, (0, 0), vignette)

def _add_light_rays(canvas: Image.Image, center_x: int, center_y: int):
    """Add subtle light rays effect"""
    width, height = canvas.size
    rays = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(rays)
    
    # Create light rays emanating from center
    for angle in range(0, 360, 45):  # 8 rays
        rad = math.radians(angle)
        end_x = center_x + int(400 * math.cos(rad))
        end_y = center_y + int(400 * math.sin(rad))
        
        # Create gradient line (light ray)
        for i in range(20):  # Width of ray
            offset_x = int(i * math.cos(rad + math.pi/2) / 2)
            offset_y = int(i * math.sin(rad + math.pi/2) / 2)
            alpha = max(0, 30 - i)  # Fade towards edges
            
            draw.line([
                (center_x + offset_x, center_y + offset_y),
                (end_x + offset_x, end_y + offset_y)
            ], fill=(255, 255, 255, alpha), width=1)
    
    canvas.paste(rays, (0, 0), rays)

# 🔧 COMPREHENSIVE VOTE FORMATTING - Support thousands AND millions
def format_votes(votes):
    """Format votes with proper k/M suffix based on magnitude"""

    if not isinstance(votes, (int, float)):
        return str(votes)
    
    votes = int(votes)  # Ensure integer for proper formatting

    if votes < 1000:
        # Less than 1000: Show as-is (e.g., 800 → "800")
        return str(votes)
    elif votes < 10000:
        # 1000-9999: Show as X.Xk (e.g., 8240 → "8.2k")
        return f"{votes/1000:.1f}k"
    elif votes < 1000000:
        # 10000-999999: Show as XXXk (e.g., 82400 → "82k", 234567 → "235k")  
        return f"{int(votes/1000)}k"
    elif votes < 10000000:
        # 1M-9.9M: Show as X.XM (e.g., 1500000 → "1.5M", 8240000 → "8.2M")
        return f"{votes/1000000:.1f}M"
    elif votes < 100000000:
        # 10M-99.9M: Show as XX.XM (e.g., 15000000 → "15.0M", 25600000 → "25.6M")
        return f"{votes/1000000:.1f}M"
    else:
        # 100M+: Show as XXXM (e.g., 156000000 → "156M")
        return f"{int(votes/1000000)}M"
            
def create_enhanced_movie_poster(movie_data: Dict, output_dir: str = "temp_posters") -> Optional[str]:
    """
    Create an enhanced movie poster card with metadata overlay for TikTok/Instagram Reels
    
    This function creates a professional movie poster card that includes:
    1. Original poster with preserved aspect ratio (no distortion)
    2. Beautiful metadata display below the poster
    3. Platform badge, genres, IMDb score, runtime, year
    4. Optimized for 9:16 portrait format (1080x1920)
    
    Args:
        movie_data (Dict): Movie information including poster_url, title, platform, etc.
        output_dir (str): Directory to save the enhanced poster
        
    Returns:
        str: Path to the enhanced poster image or None if failed
    """
    try:
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Extract movie information
        title = movie_data.get('title', 'Unknown Movie')
        year = str(movie_data.get('year', ''))
        platform = movie_data.get('platform', '')
        genres = movie_data.get('genres', [])
        imdb_score = movie_data.get('imdb_score', 0)
        runtime = movie_data.get('runtime', '0 min')
        imdb_votes = movie_data.get('imdb_votes', 0)
        poster_url = movie_data.get('poster_url') or movie_data.get('cloudinary_poster_url', '')
        
        logger.info(f"🎨 Creating enhanced poster card for: {title}")
        logger.info(f"   Platform: {platform} | IMDb: {imdb_score}/10 | Year: {year}")
        
        if not poster_url:
            logger.warning(f"⚠️ No poster URL for {title}")
            return None
        
        # Canvas dimensions (9:16 portrait for TikTok/Instagram Reels)
        canvas_width = 1080
        canvas_height = 1920
        
        # Create canvas with cinematic background
        canvas = Image.new('RGB', (canvas_width, canvas_height), color='#0f0f23')
        draw = ImageDraw.Draw(canvas)
        
        # 🎨 GODLIKE DESIGNER MODE: Create cinematic masterpiece
        poster_downloaded = False
        try:
            response = requests.get(poster_url, timeout=30)
            response.raise_for_status()
            
            poster_image = Image.open(BytesIO(response.content))
            poster_image = poster_image.convert('RGBA')
            poster_downloaded = True
            
            logger.info(f"   🎨 Creating CINEMATIC MASTERPIECE for: {title}")
            
            # Step 1: Create blurred background that fills entire canvas
            logger.info(f"   🌫️ Creating Gaussian blur background extension")
            
            # Create blurred background that COMPLETELY fills canvas (fix bottom gap)
            # Scale to cover entire canvas height AND width
            scale_w = canvas_width / poster_image.width
            scale_h = canvas_height / poster_image.height
            scale = max(scale_w, scale_h)  # Use larger scale to ensure full coverage
            
            new_bg_width = int(poster_image.width * scale)
            new_bg_height = int(poster_image.height * scale)
            bg_poster = poster_image.resize((new_bg_width, new_bg_height), Image.Resampling.LANCZOS)
            
            # Create blurred background
            blurred_bg = bg_poster.filter(ImageFilter.GaussianBlur(radius=25))
            
            # Apply dark overlay to blurred background
            dark_overlay = Image.new('RGBA', blurred_bg.size, (0, 0, 0, 160))
            blurred_bg = Image.alpha_composite(blurred_bg.convert('RGBA'), dark_overlay)
            
            # Center the blurred background to ensure full canvas coverage
            bg_x = (canvas_width - new_bg_width) // 2
            bg_y = (canvas_height - new_bg_height) // 2
            
            # Paste ensuring complete coverage (may overflow edges, which is fine)
            canvas.paste(blurred_bg, (bg_x, bg_y), blurred_bg)
            
            # Step 2: Add thematic gradient overlay based on movie theme
            logger.info(f"   🎭 Adding thematic overlays for {platform}")
            
            # Create thematic gradient based on platform and genre
            thematic_colors = _get_thematic_colors(platform, genres, title)
            _add_thematic_gradient(canvas, thematic_colors)
            
            # Step 3: Add cinematic vignette effect
            _add_vignette_effect(canvas)
            
            # Calculate main poster dimensions (preserve aspect ratio) 
            poster_max_width = int(canvas_width * 0.75)  # 75% width for main poster
            poster_max_height = int(canvas_height * 0.50)  # 50% height for main poster
            
            # Resize main poster while maintaining aspect ratio
            poster_ratio = poster_image.width / poster_image.height
            if poster_ratio > poster_max_width / poster_max_height:
                new_width = poster_max_width
                new_height = int(new_width / poster_ratio)
            else:
                new_height = poster_max_height
                new_width = int(new_height * poster_ratio)
            
            poster_image = poster_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Step 4: Add cinematic lighting effects to main poster
            logger.info(f"   ✨ Adding cinematic lighting effects")
            
            # Create dramatic shadow
            shadow = Image.new('RGBA', (new_width + 40, new_height + 40), (0, 0, 0, 140))
            shadow = shadow.filter(ImageFilter.GaussianBlur(radius=15))
            
            # Position main poster
            poster_x = int((canvas_width - new_width) / 2)
            poster_y = 60   # Higher positioning for better composition
            
            # Paste shadow and main poster
            canvas.paste(shadow, (poster_x - 20, poster_y + 20), shadow)
            canvas.paste(poster_image, (poster_x, poster_y), poster_image)
            
            # Step 5: Add subtle light rays effect
            _add_light_rays(canvas, poster_x + new_width//2, poster_y)
            
            logger.info(f"   📐 Main poster: {new_width}x{new_height} (cinematic composition)")
            
        except Exception as e:
            logger.error(f"❌ Failed to download/process poster: {str(e)}")
            poster_downloaded = False
            # Create cinematic placeholder
            new_width, new_height = 600, 900  # Larger placeholder
            poster_x = int((canvas_width - new_width) / 2)
            poster_y = 60
            
            # Create gradient placeholder background
            for y in range(canvas_height):
                alpha = int(100 * (1 - y / canvas_height))
                color = (40, 40, 60, alpha)
                draw.line([(0, y), (canvas_width, y)], fill=color[:3])
            
            draw.rectangle([poster_x, poster_y, poster_x + new_width, poster_y + new_height], 
                          fill='#2a2a3a', outline='#4a4a5a', width=3)
            draw.text((poster_x + new_width//2, poster_y + new_height//2), "CINEMATIC\nPOSTER", 
                     fill='white', anchor='mm', font=title_font)
        
        # Load fonts with BOLD title font
        try:
            title_font = ImageFont.truetype("arialbd.ttf", 52)   # BOLD title font
            platform_font = ImageFont.truetype("arial.ttf", 36) # Platform badge  
            metadata_font = ImageFont.truetype("arial.ttf", 36) # Metadata values
            small_font = ImageFont.truetype("arial.ttf", 32)    # Labels
        except:
            try:
                title_font = ImageFont.truetype("/System/Library/Fonts/Arial Bold.ttf", 52)  # BOLD
                platform_font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 36)
                metadata_font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 36)
                small_font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 32)
            except:
                # Fallback to default with simulated bold effect
                title_font = ImageFont.load_default()
                platform_font = ImageFont.load_default()
                metadata_font = ImageFont.load_default()
                small_font = ImageFont.load_default()
        
        # 🎨 CINEMATIC METADATA SECTION - PERFECT SPACING
        metadata_start_y = poster_y + new_height + 90  # Perfect breathing room from poster
        
        logger.info(f"   🎭 Creating cinematic text backgrounds")
        
        # Step 6: Draw BOLD title text WITHOUT background
        title_lines = textwrap.wrap(title, width=22)  # Wrap long titles
        current_y = metadata_start_y
        
        # Draw BOLD title text with cinematic effects (NO BACKGROUND)
        for line in title_lines[:2]:
            bbox = draw.textbbox((0, 0), line, font=title_font)
            text_width = bbox[2] - bbox[0]
            text_x = int((canvas_width - text_width) / 2)
            
            # Multiple shadow layers for depth
            draw.text((text_x + 3, current_y + 3), line, fill='#000000', font=title_font)  # Deep shadow
            draw.text((text_x + 1, current_y + 1), line, fill='#333333', font=title_font)  # Mid shadow
            
            # BOLD title with enhanced effect (multiple draws for extra boldness)
            # Simulate bold by drawing multiple times with slight offsets
            draw.text((text_x, current_y), line, fill='#FFFFFF', font=title_font)  # Base
            draw.text((text_x + 1, current_y), line, fill='#FFFFFF', font=title_font)  # Bold effect 1
            draw.text((text_x, current_y + 1), line, fill='#FFFFFF', font=title_font)  # Bold effect 2
            draw.text((text_x + 1, current_y + 1), line, fill='#FFFFFF', font=title_font)  # Bold effect 3
            draw.text((text_x, current_y - 1), line, fill='#F8F8F8', font=title_font)  # Highlight
            
            current_y += 75  # More spacing after title
        
        # Step 7: Create cinematic platform badge
        platform_y = current_y + 30  # More spacing after title
        if platform:
            platform_colors = {
                'Netflix': '#E50914', 'Max': '#00E5FF', 'Prime Video': '#00A8E1',
                'Disney+': '#113CCF', 'Hulu': '#1CE783', 'Apple TV+': '#1B1B1B'
            }
            
            platform_color = platform_colors.get(platform, '#FF6B35')
            display_platform = platform if len(platform) <= 12 else platform[:10] + "..."
            
            # Create cinematic platform badge with multiple effects
            platform_bbox = draw.textbbox((0, 0), display_platform, font=platform_font)
            text_width = platform_bbox[2] - platform_bbox[0]
            platform_width = text_width + 50
            platform_height = 55
            platform_x = int((canvas_width - platform_width) / 2)
            
            # Outer glow (multiple layers for cinema effect)
            for i in range(6, 0, -1):
                glow_alpha = max(20, 80 - i * 10)
                glow_color = ImageColor.getrgb(platform_color) + (glow_alpha,)
                draw.rounded_rectangle([
                    platform_x - i, platform_y - i, 
                    platform_x + platform_width + i, platform_y + platform_height + i
                ], radius=20 + i, fill=glow_color[:3])
            
            # Main badge with gradient effect
            badge_bg = Image.new('RGBA', (platform_width, platform_height), (0, 0, 0, 0))
            badge_draw = ImageDraw.Draw(badge_bg)
            
            # Create vertical gradient for badge
            base_color = ImageColor.getrgb(platform_color)
            for y in range(platform_height):
                ratio = y / platform_height
                # Darker at top, lighter at bottom
                r = int(base_color[0] * (0.7 + 0.3 * ratio))
                g = int(base_color[1] * (0.7 + 0.3 * ratio))
                b = int(base_color[2] * (0.7 + 0.3 * ratio))
                badge_draw.line([(0, y), (platform_width, y)], fill=(r, g, b))
            
            # Apply subtle blur and paste
            badge_bg = badge_bg.filter(ImageFilter.GaussianBlur(radius=1))
            
            # Create badge shape
            draw.rounded_rectangle([platform_x, platform_y, platform_x + platform_width, platform_y + platform_height], 
                                 radius=18, fill=platform_color)
            
            # Platform text with multiple effects
            text_center_x = platform_x + platform_width // 2
            text_center_y = platform_y + platform_height // 2
            
            # Text shadow
            draw.text((text_center_x + 2, text_center_y + 2), display_platform, 
                     fill='#000000', font=platform_font, anchor='mm')
            # Text highlight
            draw.text((text_center_x - 1, text_center_y - 1), display_platform, 
                     fill='#FFFFFF', font=platform_font, anchor='mm')
            # Main text
            draw.text((text_center_x, text_center_y), display_platform, 
                     fill='white', font=platform_font, anchor='mm')
            
            current_y = platform_y + platform_height + 40  # More spacing after platform
        
        # Step 8: Draw genres text WITHOUT background
        if genres:
            genres_text = " • ".join(genres[:3])
            genres_bbox = draw.textbbox((0, 0), genres_text, font=metadata_font)
            genres_width = genres_bbox[2] - genres_bbox[0]
            
            # Genres text with cinematic effects (NO BACKGROUND)
            text_x = int((canvas_width - genres_width) / 2)
            # Multiple shadow layers
            draw.text((text_x + 2, current_y + 2), genres_text, fill='#000000', font=metadata_font)
            draw.text((text_x + 1, current_y + 1), genres_text, fill='#333333', font=metadata_font)
            # Main text with subtle glow
            draw.text((text_x, current_y), genres_text, fill='#F5F5F5', font=metadata_font)
            
            current_y += 60  # More spacing after genres
        
        # Step 9: Create ROUNDED and TRANSPARENT metadata panel
        metadata_y = current_y + 30  # More spacing before metadata
        
        formatted_votes = format_votes(imdb_votes)
        
        metadata_items = [
            ("Date:", str(year)),
            ("IMDb:", f"{imdb_score}/10"),
            ("Votes:", formatted_votes),  # ✅ FIXED: Proper vote formatting
            ("Time:", runtime)
        ]
        
        # Create ROUNDED metadata background panel
        panel_width = canvas_width - 120
        panel_height = len(metadata_items) * 50 + 30  # Adjusted for new spacing
        panel_x = 60
        panel_y = metadata_y - 15
        
        # Create ROUNDED metadata panel with TRANSPARENT background
        metadata_bg = Image.new('RGBA', (panel_width, panel_height), (0, 0, 0, 0))
        metadata_draw = ImageDraw.Draw(metadata_bg)
        
        # Create ROUNDED background with MUCH MORE TRANSPARENCY
        if poster_downloaded:
            # Very subtle thematic color
            primary = thematic_colors['primary'][:3]
            bg_color = primary + (40,)  # Very low alpha for transparency
        else:
            bg_color = (20, 20, 30, 40)  # Very transparent dark
        
        # Draw rounded rectangle background
        metadata_draw.rounded_rectangle([0, 0, panel_width, panel_height], radius=20, fill=bg_color)
        
        # Apply minimal blur for glass effect
        metadata_bg = metadata_bg.filter(ImageFilter.GaussianBlur(radius=1))
        canvas.paste(metadata_bg, (panel_x, panel_y), metadata_bg)
        
        # Display metadata with cinematic typography
        for i, (label, value) in enumerate(metadata_items):
            item_y = metadata_y + (i * 50)  # Slightly tighter spacing
            
            # Left side - Labels with elegant styling
            label_x = 140
            # Deep shadow
            draw.text((label_x + 2, item_y + 2), label, fill='#000000', font=small_font)
            # Mid shadow
            draw.text((label_x + 1, item_y + 1), label, fill='#404040', font=small_font)
            # Main label
            draw.text((label_x, item_y), label, fill='#C0C0C0', font=small_font)
            
            # Right side - Values with dramatic effects
            value_bbox = draw.textbbox((0, 0), value, font=metadata_font)
            value_width = value_bbox[2] - value_bbox[0]
            value_x = 940 - value_width
            
            # Value with multiple shadow layers for depth
            draw.text((value_x + 3, item_y + 3), value, fill='#000000', font=metadata_font)  # Deep shadow
            draw.text((value_x + 1, item_y + 1), value, fill='#333333', font=metadata_font)  # Mid shadow
            
            # Main value with cinematic glow effect
            draw.text((value_x, item_y), value, fill='#FFFFFF', font=metadata_font)  # Base
            draw.text((value_x, item_y - 1), value, fill='#F8F8F8', font=metadata_font)  # Highlight
        
        # Save enhanced poster
        clean_title = re.sub(r'[^a-zA-Z0-9_-]', '_', title.lower()).strip('_')
        output_path = os.path.join(output_dir, f"enhanced_poster_{clean_title}_{year}.png")
        canvas.save(output_path, 'PNG', quality=95)
        
        logger.info(f"✅ Enhanced poster card created: {output_path}")
        logger.info(f"   🎨 Style: Professional TikTok/Reels format")
        logger.info(f"   📐 Dimensions: {canvas_width}x{canvas_height} (9:16 portrait)")
        logger.info(f"   🖼️ Poster: Aspect ratio preserved, no distortion")
        
        return output_path
        
    except Exception as e:
        logger.error(f"❌ Error creating enhanced poster for {title}: {str(e)}")
        return None 

def upload_enhanced_poster_to_cloudinary(poster_path: str, movie_title: str, movie_id: str = None) -> Optional[str]:
    """
    Upload an enhanced movie poster to Cloudinary
    
    Args:
        poster_path (str): Path to the enhanced poster image
        movie_title (str): Movie title for naming
        movie_id (str): Movie ID for unique identification
        
    Returns:
        str: Cloudinary URL of uploaded poster or None if failed
    """
    try:
        # Create a clean filename from movie title
        clean_title = re.sub(r'[^a-zA-Z0-9_-]', '_', movie_title.lower())
        clean_title = re.sub(r'_+', '_', clean_title).strip('_')
        
        # Create unique public ID
        public_id = f"enhanced_posters/{clean_title}_{movie_id}" if movie_id else f"enhanced_posters/{clean_title}"
        
        logger.info(f"☁️ Uploading enhanced poster to Cloudinary: {poster_path}")
        logger.info(f"   Movie: {movie_title}")
        logger.info(f"   Public ID: {public_id}")
        
        # Upload to Cloudinary with image optimization
        upload_result = cloudinary.uploader.upload(
            poster_path,
            resource_type="image",
            public_id=public_id,
            folder="enhanced_posters",
            overwrite=True,
            quality="auto:best",
            format="png",
            transformation=[
                {"width": 1080, "height": 1920, "crop": "fit"},  # Ensure exact dimensions
                {"quality": "auto:best"}
            ]
        )
        
        cloudinary_url = upload_result.get('secure_url')
        logger.info(f"✅ Enhanced poster uploaded to Cloudinary: {cloudinary_url}")
        
        return cloudinary_url
        
    except Exception as e:
        logger.error(f"❌ Error uploading enhanced poster {poster_path} to Cloudinary: {str(e)}")
        return None

def create_enhanced_movie_posters(movie_data: List[Dict], max_movies: int = 3) -> Dict[str, str]:
    """
    Create enhanced movie poster cards for all movies with metadata overlays
    
    Args:
        movie_data (List[Dict]): List of movie data dictionaries
        max_movies (int): Maximum number of movies to process
        
    Returns:
        Dict[str, str]: Dictionary mapping movie titles to enhanced poster URLs
    """
    enhanced_poster_urls = {}
    temp_dir = "temp_posters"
    
    try:
        # Create temporary directory
        os.makedirs(temp_dir, exist_ok=True)
        
        logger.info(f"🎨 CREATING ENHANCED MOVIE POSTERS WITH METADATA")
        logger.info(f"📋 Processing {min(len(movie_data), max_movies)} movies")
        logger.info(f"🎬 Style: Professional TikTok/Instagram Reels format")
        logger.info(f"📐 Dimensions: 1080x1920 (9:16 portrait)")
        
        # Process each movie (up to max_movies)
        for i, movie in enumerate(movie_data[:max_movies]):
            movie_title = movie.get('title', f'Movie_{i+1}')
            movie_id = str(movie.get('id', i+1))
            
            logger.info(f"🎯 Processing Movie {i+1}: {movie_title}")
            logger.info(f"   Movie ID: {movie_id}")
            logger.info(f"   Platform: {movie.get('platform', 'Unknown')}")
            logger.info(f"   IMDb: {movie.get('imdb_score', 0)}/10")
            
            # Step 1: Create enhanced poster with metadata
            enhanced_poster_path = create_enhanced_movie_poster(movie, temp_dir)
            if not enhanced_poster_path:
                logger.error(f"❌ Failed to create enhanced poster for {movie_title}")
                continue
            
            # Step 2: Upload to Cloudinary
            cloudinary_url = upload_enhanced_poster_to_cloudinary(enhanced_poster_path, movie_title, movie_id)
            if cloudinary_url:
                enhanced_poster_urls[movie_title] = cloudinary_url
                logger.info(f"✅ Enhanced poster processed for {movie_title}: {cloudinary_url}")
            else:
                logger.error(f"❌ Failed to upload enhanced poster for {movie_title}")
        
        logger.info(f"🏁 ENHANCED POSTERS COMPLETE: {len(enhanced_poster_urls)}/{min(len(movie_data), max_movies)} posters created")
        
        return enhanced_poster_urls
        
    except Exception as e:
        logger.error(f"❌ Error in create_enhanced_movie_posters: {str(e)}")
        return enhanced_poster_urls
        
    finally:
        # Clean up temporary files
        try:
            import shutil
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                logger.info(f"🧹 Cleaned up temporary directory: {temp_dir}")
        except Exception as e:
            logger.warning(f"⚠️ Could not clean up temporary files: {str(e)}") 