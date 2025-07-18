-- Fonction pour récupérer directement les URLs Cloudinary sans tableau
-- Utilisation: SELECT * FROM get_cloudinary_urls_direct('FR_TOP5_NETFLIX_HORROR_20250419');
DROP FUNCTION IF EXISTS get_cloudinary_urls_direct(text);

CREATE OR REPLACE FUNCTION get_cloudinary_urls_direct(group_id_prefix TEXT)
RETURNS TABLE (
    cloudinary_url_1 TEXT,
    cloudinary_url_2 TEXT,
    cloudinary_url_3 TEXT,
    description_1 TEXT,
    description_2 TEXT,
    description_3 TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        es.cloudinary_url_films_1_2 as cloudinary_url_1,
        es.cloudinary_url_films_3_4 as cloudinary_url_2,
        es.cloudinary_url_films_5_6 as cloudinary_url_3,
        'Films 1-2' as description_1,
        'Films 3-4' as description_2,
        'Films 5-6' as description_3
    FROM 
        enriched_streams es
    WHERE 
        es.id LIKE group_id_prefix || '_%'
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;
