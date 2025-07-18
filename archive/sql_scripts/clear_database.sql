-- Supprimer les entrées avec l'identifiant de groupe spécifique
DELETE FROM enriched_streams 
WHERE id LIKE 'FR_TOP5_NETFLIX_HORROR_20250419_%';

-- Si vous souhaitez vider complètement toutes les tables
-- DELETE FROM enriched_streams;
-- DELETE FROM streams;
