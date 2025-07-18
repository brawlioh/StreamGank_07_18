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
            'Films 1-2' as description_text
        FROM 
            group_data
        
        UNION ALL
        
        -- Deuxième screenshot
        SELECT 
            2::BIGINT as img_order,
            cloudinary_url_films_3_4 as url,
            'Films 3-4' as description_text
        FROM 
            group_data
        
        UNION ALL
        
        -- Troisième screenshot
        SELECT 
            3::BIGINT as img_order,
            cloudinary_url_films_5_6 as url,
            'Films 5-6' as description_text
        FROM 
            group_data
    )
    SELECT 
        img_order as image_order,
        url as cloudinary_url,
        description_text as description
    FROM 
        urls
    WHERE 
        url IS NOT NULL
    ORDER BY 
        img_order;
END;
$$ LANGUAGE plpgsql;
