-- Ajout des colonnes pour stocker les URLs Cloudinary directement dans la table
ALTER TABLE enriched_streams 
ADD COLUMN cloudinary_url_films_1_2 TEXT,
ADD COLUMN cloudinary_url_films_3_4 TEXT,
ADD COLUMN cloudinary_url_films_5_6 TEXT;

-- Migration des données existantes
-- Pour chaque groupe, nous allons extraire les URLs des JSONs et les stocker dans les nouvelles colonnes
WITH group_ids AS (
    SELECT DISTINCT
        REGEXP_REPLACE(id, '_[0-9]+$', '') as group_id
    FROM
        enriched_streams
)
UPDATE enriched_streams es
SET 
    cloudinary_url_films_1_2 = (
        SELECT json_extract_path_text(es2.enrichment::json, 'screenshot_url')
        FROM enriched_streams es2
        WHERE es2.id = REGEXP_REPLACE(es.id, '_[0-9]+$', '') || '_1'
        LIMIT 1
    ),
    cloudinary_url_films_3_4 = (
        SELECT json_extract_path_text(es2.enrichment::json, 'screenshot_url')
        FROM enriched_streams es2
        WHERE es2.id = REGEXP_REPLACE(es.id, '_[0-9]+$', '') || '_2'
        LIMIT 1
    ),
    cloudinary_url_films_5_6 = (
        SELECT json_extract_path_text(es2.enrichment::json, 'screenshot_url')
        FROM enriched_streams es2
        WHERE es2.id = REGEXP_REPLACE(es.id, '_[0-9]+$', '') || '_3'
        LIMIT 1
    );

-- Création d'index pour améliorer les performances des requêtes
CREATE INDEX IF NOT EXISTS idx_cloudinary_url_films_1_2 ON enriched_streams (cloudinary_url_films_1_2);
CREATE INDEX IF NOT EXISTS idx_cloudinary_url_films_3_4 ON enriched_streams (cloudinary_url_films_3_4);
CREATE INDEX IF NOT EXISTS idx_cloudinary_url_films_5_6 ON enriched_streams (cloudinary_url_films_5_6);

-- Mise à jour de la requête simplifiée pour récupérer les URLs Cloudinary
DROP FUNCTION IF EXISTS get_cloudinary_urls(text);

CREATE OR REPLACE FUNCTION get_cloudinary_urls(group_id_prefix TEXT)
RETURNS TABLE (
    image_order BIGINT,
    cloudinary_url TEXT,
    description TEXT
) AS $$
BEGIN
    -- Récupérer les URLs depuis les colonnes dédiées
    RETURN QUERY
    WITH group_data AS (
        SELECT 
            cloudinary_url_films_1_2,
            cloudinary_url_films_3_4,
            cloudinary_url_films_5_6
        FROM 
            enriched_streams
        WHERE 
            id LIKE group_id_prefix || '_%'
        LIMIT 1
    ),
    urls AS (
        -- Premier screenshot
        SELECT 
            1::BIGINT as img_order,
            cloudinary_url_films_1_2 as url,
            'Films 1-2' as desc
        FROM 
            group_data
        
        UNION ALL
        
        -- Deuxième screenshot
        SELECT 
            2::BIGINT as img_order,
            cloudinary_url_films_3_4 as url,
            'Films 3-4' as desc
        FROM 
            group_data
        
        UNION ALL
        
        -- Troisième screenshot
        SELECT 
            3::BIGINT as img_order,
            cloudinary_url_films_5_6 as url,
            'Films 5-6' as desc
        FROM 
            group_data
    )
    SELECT 
        img_order as image_order,
        url as cloudinary_url,
        desc as description
    FROM 
        urls
    WHERE 
        url IS NOT NULL
    ORDER BY 
        img_order;
END;
$$ LANGUAGE plpgsql;
