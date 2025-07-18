-- Fonction de débogage pour examiner la structure du JSON
DROP FUNCTION IF EXISTS debug_enrichment_structure(text);

CREATE OR REPLACE FUNCTION debug_enrichment_structure(group_id_prefix TEXT)
RETURNS TABLE (
    id TEXT,
    raw_json TEXT,
    json_keys TEXT[]
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        es.id,
        es.enrichment::TEXT as raw_json,
        array_agg(key) as json_keys
    FROM 
        enriched_streams es,
        json_object_keys(es.enrichment::json) as key
    WHERE 
        es.id LIKE group_id_prefix || '_%'
    GROUP BY
        es.id, es.enrichment
    LIMIT 5;
END;
$$ LANGUAGE plpgsql;

-- Fonction 1: Récupérer les URLs des images Cloudinary pour un groupe spécifique
-- Utilisation: SELECT * FROM get_cloudinary_urls('FR_TOP5_NETFLIX_HORROR_20250419');
DROP FUNCTION IF EXISTS get_cloudinary_urls(text);

CREATE OR REPLACE FUNCTION get_cloudinary_urls(group_id_prefix TEXT)
RETURNS TABLE (
    image_order BIGINT,
    cloudinary_url TEXT,
    description TEXT
) AS $$
DECLARE
    json_enrichment JSON;
BEGIN
    -- Récupérer le premier enregistrement du groupe pour accéder aux données d'enrichissement
    RETURN QUERY
    WITH first_records AS (
        SELECT 
            id,
            enrichment
        FROM 
            enriched_streams
        WHERE 
            id LIKE group_id_prefix || '_%'
        ORDER BY 
            id
        LIMIT 5
    ),
    extracted_urls AS (
        SELECT 
            ROW_NUMBER() OVER () as image_order,
            -- Extraire l'URL en parsant le JSON échappé correctement
            json_extract_path_text(enrichment::json, 'screenshot_url') as cloudinary_url,
            CASE 
                WHEN ROW_NUMBER() OVER () = 1 THEN 'Films 1-2'
                WHEN ROW_NUMBER() OVER () = 2 THEN 'Films 3-4'
                WHEN ROW_NUMBER() OVER () = 3 THEN 'Films 5-6'
                ELSE 'Autre'
            END as description
        FROM 
            first_records
        LIMIT 3
    )
    SELECT DISTINCT 
        eu.image_order, 
        eu.cloudinary_url, 
        eu.description
    FROM 
        extracted_urls eu
    ORDER BY 
        eu.image_order;
END;
$$ LANGUAGE plpgsql;

-- Fonction 2: Récupérer l'ID de la vidéo HeyGen pour un groupe spécifique
-- Utilisation: SELECT * FROM get_heygen_video_id('FR_TOP5_NETFLIX_HORROR_20250419');
CREATE OR REPLACE FUNCTION get_heygen_video_id(group_id_prefix TEXT)
RETURNS TABLE (
    video_id TEXT,
    group_description TEXT,
    generation_date TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        es.heygen_video_id as video_id,
        REPLACE(
            REPLACE(
                REPLACE(
                    REPLACE(
                        group_id_prefix,
                        '_', ' '
                    ),
                    'TOP', 'Top '
                ),
                'NETFLIX', 'sur Netflix'
            ),
            'HORROR', 'Horreur'
        ) as group_description,
        es.created_at as generation_date
    FROM 
        enriched_streams es
    WHERE 
        es.id LIKE group_id_prefix || '_%'
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- Exemple d'utilisation pour récupérer les données du dernier groupe généré
-- Fonction bonus: Récupérer le dernier groupe généré
CREATE OR REPLACE FUNCTION get_latest_group_id()
RETURNS TEXT AS $$
DECLARE
    latest_group_id TEXT;
BEGIN
    SELECT SUBSTRING(id FROM 1 FOR POSITION('_' IN REVERSE(id)) - 1)
    INTO latest_group_id
    FROM enriched_streams
    ORDER BY created_at DESC
    LIMIT 1;
    
    RETURN latest_group_id;
END;
$$ LANGUAGE plpgsql;

-- Exemple d'utilisation complète:
-- 1. Récupérer le dernier groupe généré
-- SELECT * FROM get_latest_group_id();
-- 
-- 2. Récupérer les URLs des images Cloudinary pour ce groupe
-- SELECT * FROM get_cloudinary_urls((SELECT get_latest_group_id()));
--
-- 3. Récupérer l'ID de la vidéo HeyGen pour ce groupe
-- SELECT * FROM get_heygen_video_id((SELECT get_latest_group_id()));
