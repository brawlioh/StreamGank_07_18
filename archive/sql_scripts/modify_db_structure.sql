-- Étape 1: Créer une nouvelle colonne temporaire de type TEXT
ALTER TABLE enriched_streams ADD COLUMN temp_id TEXT;

-- Étape 2: Copier les valeurs existantes (conversion de UUID à TEXT)
UPDATE enriched_streams SET temp_id = id::TEXT;

-- Étape 3: Supprimer la contrainte de clé primaire sur id
ALTER TABLE enriched_streams DROP CONSTRAINT enriched_streams_pkey;

-- Étape 4: Supprimer l'ancienne colonne id
ALTER TABLE enriched_streams DROP COLUMN id;

-- Étape 5: Renommer la colonne temporaire en id
ALTER TABLE enriched_streams RENAME COLUMN temp_id TO id;

-- Étape 6: Ajouter la contrainte de clé primaire sur la nouvelle colonne id
ALTER TABLE enriched_streams ADD PRIMARY KEY (id);

-- Étape 7: S'assurer que la colonne id n'est pas nullable
ALTER TABLE enriched_streams ALTER COLUMN id SET NOT NULL;

-- Commentaire: Cette modification permet d'utiliser des identifiants descriptifs au format texte
-- comme "FR_TOP5_NETFLIX_HORROR_20250419_1" à la place des UUIDs standards.
