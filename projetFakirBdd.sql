-- ============================================
-- LOL ASSISTANT - DATABASE SCHEMA
-- PostgreSQL Migration Script
-- Generated from Looping MLD export
-- ============================================

-- Clean up if tables already exist (in reverse dependency order)
DROP TABLE IF EXISTS item_component CASCADE;
DROP TABLE IF EXISTS tierlist CASCADE;
DROP TABLE IF EXISTS synergy CASCADE;
DROP TABLE IF EXISTS matchup CASCADE;
DROP TABLE IF EXISTS champion_recommended_rune CASCADE;
DROP TABLE IF EXISTS champion_recommended_summonerspell CASCADE;
DROP TABLE IF EXISTS champion_recommended_item CASCADE;
DROP TABLE IF EXISTS head_to CASCADE;
DROP TABLE IF EXISTS spell CASCADE;
DROP TABLE IF EXISTS champion CASCADE;
DROP TABLE IF EXISTS patch CASCADE;
DROP TABLE IF EXISTS lane CASCADE;
DROP TABLE IF EXISTS summoner_spell CASCADE;
DROP TABLE IF EXISTS rune CASCADE;
DROP TABLE IF EXISTS item CASCADE;

-- ============================================
-- TABLES PRINCIPALES (entités)
-- ============================================

-- CHAMPION
CREATE TABLE champion (
    id_champion     SERIAL PRIMARY KEY,
    name            VARCHAR(50)  NOT NULL UNIQUE,
    title           VARCHAR(100),
    main_role       VARCHAR(30)  NOT NULL,
    damage_type     VARCHAR(20)  NOT NULL CHECK (damage_type IN ('AD', 'AP', 'Hybrid')),
    secondary_role  VARCHAR(30),
    attack_range    VARCHAR(10)  NOT NULL CHECK (attack_range IN ('Melee', 'Ranged')),
    release_date    DATE,
    difficulty      INTEGER      CHECK (difficulty BETWEEN 1 AND 10),
    description     TEXT,
    -- Resource
    resource_type   VARCHAR(20)  NOT NULL DEFAULT 'mana' CHECK (resource_type IN ('mana', 'energy', 'none', 'health', 'fury', 'rage', 'flow', 'ferocity', 'heat', 'shield', 'bloodwell', 'grit', 'courage')),
    mana_base       FLOAT        NOT NULL DEFAULT 0,
    mana_per_lvl    FLOAT        NOT NULL DEFAULT 0,
    mana_regen_base     FLOAT    NOT NULL DEFAULT 0,
    mana_regen_per_lvl  FLOAT    NOT NULL DEFAULT 0,
    -- HP
    hp_base         FLOAT        NOT NULL,
    hp_per_lvl      FLOAT        NOT NULL,
    hp_regen_base       FLOAT    NOT NULL,
    hp_regen_per_lvl    FLOAT    NOT NULL,
    -- Armor & Magic Resist
    armor_base      FLOAT        NOT NULL,
    armor_per_lvl   FLOAT        NOT NULL,
    rm_base         FLOAT        NOT NULL,
    rm_per_lvl      FLOAT        NOT NULL,
    -- Attack Damage
    ad_base         FLOAT        NOT NULL,
    ad_per_lvl      FLOAT        NOT NULL,
    -- Attack Speed
    attackspeed_base    FLOAT    NOT NULL,
    attackspeed_ratio   FLOAT    NOT NULL,
    attackspeed_per_lvl FLOAT    NOT NULL,
    -- Movement Speed
    movespeed       FLOAT        NOT NULL
);

-- SPELL (abilities)
CREATE TABLE spell (
    id_spell        SERIAL PRIMARY KEY,
    input_key       VARCHAR(10)  NOT NULL CHECK (input_key IN ('Passive', 'Q', 'W', 'E', 'R')),
    name            VARCHAR(80)  NOT NULL,
    description     TEXT,
    mana_cost       VARCHAR(50),   -- ex: "60/65/70/75/80" (varie par rang)
    energy_cost     VARCHAR(50),   -- pour les champions energy
    cooldown_base   VARCHAR(50),   -- ex: "12/11/10/9/8" (varie par rang)
    damage_type     VARCHAR(20)   CHECK (damage_type IN ('AD', 'AP', 'True', 'Hybrid', 'None')),
    is_cc           BOOLEAN       NOT NULL DEFAULT FALSE,
    type_cc         VARCHAR(30),   -- stun, slow, knock_up, root, silence, etc.
    -- FK
    id_champion     INTEGER       NOT NULL REFERENCES champion(id_champion) ON DELETE CASCADE
);

-- ITEM
CREATE TABLE item (
    id_item         SERIAL PRIMARY KEY,
    name            VARCHAR(80)  NOT NULL UNIQUE,
    description     TEXT,
    total_price     INTEGER      NOT NULL DEFAULT 0,
    category        VARCHAR(30)  NOT NULL CHECK (category IN ('Mythic', 'Legendary', 'Epic', 'Basic', 'Boots', 'Consumable', 'Starter', 'Trinket')),
    price_recipe    INTEGER      NOT NULL DEFAULT 0,
    provided_stats  TEXT,          -- JSON string des stats fournies
    unique_passive  TEXT,
    unique_active   TEXT,
    is_available    BOOLEAN       NOT NULL DEFAULT TRUE
);

-- RUNE
CREATE TABLE rune (
    id_rune         SERIAL PRIMARY KEY,
    name            VARCHAR(50)  NOT NULL UNIQUE,
    description     TEXT,
    rune_tree       VARCHAR(30)  NOT NULL CHECK (rune_tree IN ('Precision', 'Domination', 'Sorcery', 'Resolve', 'Inspiration')),
    rune_rank       VARCHAR(20)  NOT NULL CHECK (rune_rank IN ('Keystone', 'Slot1', 'Slot2', 'Slot3'))
);

-- SUMMONER SPELL
CREATE TABLE summoner_spell (
    id_summoner_spell   SERIAL PRIMARY KEY,
    name                VARCHAR(30)  NOT NULL UNIQUE,
    description         TEXT,
    cooldown            INTEGER      NOT NULL,
    effect              TEXT
);

-- LANE
CREATE TABLE lane (
    id_lane         SERIAL PRIMARY KEY,
    name            VARCHAR(20)  NOT NULL UNIQUE CHECK (name IN ('Top', 'Jungle', 'Mid', 'ADC', 'Support'))
);

-- PATCH
CREATE TABLE patch (
    id_patch        SERIAL PRIMARY KEY,
    patch_number    VARCHAR(10)  NOT NULL UNIQUE,  -- ex: "15.1.1"
    release_date    DATE         NOT NULL,
    end_date        DATE,
    patch_note      TEXT
);

-- ============================================
-- TABLES D'ASSOCIATION
-- ============================================

-- HEAD_TO (champion <-> lane, par patch)
CREATE TABLE head_to (
    id_champion     INTEGER NOT NULL REFERENCES champion(id_champion) ON DELETE CASCADE,
    id_lane         INTEGER NOT NULL REFERENCES lane(id_lane) ON DELETE CASCADE,
    id_patch        INTEGER NOT NULL REFERENCES patch(id_patch) ON DELETE CASCADE,
    is_meta         BOOLEAN NOT NULL DEFAULT FALSE,
    pickrate        FLOAT   CHECK (pickrate >= 0 AND pickrate <= 100),
    winrate         FLOAT   CHECK (winrate >= 0 AND winrate <= 100),
    PRIMARY KEY (id_champion, id_lane, id_patch)
);

-- CHAMPION RECOMMENDED ITEM (par patch)
CREATE TABLE champion_recommended_item (
    id_champion     INTEGER     NOT NULL REFERENCES champion(id_champion) ON DELETE CASCADE,
    id_item         INTEGER     NOT NULL REFERENCES item(id_item) ON DELETE CASCADE,
    id_patch        INTEGER     NOT NULL REFERENCES patch(id_patch) ON DELETE CASCADE,
    buy_order       INTEGER     NOT NULL CHECK (buy_order > 0),
    build_type      VARCHAR(30) NOT NULL DEFAULT 'standard',
    build_winrate   FLOAT       CHECK (build_winrate >= 0 AND build_winrate <= 100),
    PRIMARY KEY (id_champion, id_item, id_patch)
);

-- CHAMPION RECOMMENDED SUMMONER SPELL
CREATE TABLE champion_recommended_summonerspell (
    id_champion         INTEGER NOT NULL REFERENCES champion(id_champion) ON DELETE CASCADE,
    id_summoner_spell   INTEGER NOT NULL REFERENCES summoner_spell(id_summoner_spell) ON DELETE CASCADE,
    PRIMARY KEY (id_champion, id_summoner_spell)
);

-- CHAMPION RECOMMENDED RUNE (par patch)
CREATE TABLE champion_recommended_rune (
    id_champion     INTEGER     NOT NULL REFERENCES champion(id_champion) ON DELETE CASCADE,
    id_rune         INTEGER     NOT NULL REFERENCES rune(id_rune) ON DELETE CASCADE,
    id_patch        INTEGER     NOT NULL REFERENCES patch(id_patch) ON DELETE CASCADE,
    is_primary      BOOLEAN     NOT NULL DEFAULT TRUE,
    type_page       VARCHAR(20) NOT NULL DEFAULT 'standard',
    PRIMARY KEY (id_champion, id_rune, id_patch)
);

-- MATCHUP (champion vs champion, par lane et patch)
CREATE TABLE matchup (
    id_champion     INTEGER     NOT NULL REFERENCES champion(id_champion) ON DELETE CASCADE,
    id_champion_1   INTEGER     NOT NULL REFERENCES champion(id_champion) ON DELETE CASCADE,
    id_lane         INTEGER     NOT NULL REFERENCES lane(id_lane) ON DELETE CASCADE,
    id_patch        INTEGER     NOT NULL REFERENCES patch(id_patch) ON DELETE CASCADE,
    winrate_champion_1  FLOAT   CHECK (winrate_champion_1 >= 0 AND winrate_champion_1 <= 100),
    advantage       VARCHAR(20) NOT NULL CHECK (advantage IN ('favorable', 'neutral', 'unfavorable')),
    tips            TEXT,
    PRIMARY KEY (id_champion, id_champion_1, id_lane, id_patch),
    CHECK (id_champion <> id_champion_1)  -- un champion ne peut pas s'affronter lui-même
);

-- SYNERGY (champion + champion)
CREATE TABLE synergy (
    id_champion     INTEGER     NOT NULL REFERENCES champion(id_champion) ON DELETE CASCADE,
    id_champion_1   INTEGER     NOT NULL REFERENCES champion(id_champion) ON DELETE CASCADE,
    synergy_score   INTEGER     NOT NULL CHECK (synergy_score BETWEEN 1 AND 10),
    reason          TEXT,
    synergy_type    VARCHAR(30) CHECK (synergy_type IN ('combo_cc', 'poke', 'engage', 'protect', 'splitpush', 'teamfight', 'pick', 'dive', 'sustain')),
    PRIMARY KEY (id_champion, id_champion_1),
    CHECK (id_champion <> id_champion_1)  -- pas de synergie avec soi-même
);

-- TIERLIST (champion + lane + patch)
CREATE TABLE tierlist (
    id_champion     INTEGER     NOT NULL REFERENCES champion(id_champion) ON DELETE CASCADE,
    id_lane         INTEGER     NOT NULL REFERENCES lane(id_lane) ON DELETE CASCADE,
    id_patch        INTEGER     NOT NULL REFERENCES patch(id_patch) ON DELETE CASCADE,
    tier            VARCHAR(2)  NOT NULL CHECK (tier IN ('S+', 'S', 'A', 'B', 'C', 'D')),
    winrate         FLOAT       CHECK (winrate >= 0 AND winrate <= 100),
    pickrate        FLOAT       CHECK (pickrate >= 0 AND pickrate <= 100),
    banrate         FLOAT       CHECK (banrate >= 0 AND banrate <= 100),
    PRIMARY KEY (id_champion, id_lane, id_patch)
);

-- ITEM COMPONENT (relation réflexive item parent <-> item composant)
CREATE TABLE item_component (
    id_item_parent      INTEGER NOT NULL REFERENCES item(id_item) ON DELETE CASCADE,
    id_item_component   INTEGER NOT NULL REFERENCES item(id_item) ON DELETE CASCADE,
    quantity            INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
    PRIMARY KEY (id_item_parent, id_item_component),
    CHECK (id_item_parent <> id_item_component)  -- un item ne peut pas être son propre composant
);

-- ============================================
-- INDEX pour les performances
-- ============================================

-- Recherches fréquentes par nom
CREATE INDEX idx_champion_name ON champion(name);
CREATE INDEX idx_item_name ON item(name);

-- Recherches par rôle/lane
CREATE INDEX idx_champion_role ON champion(main_role);
CREATE INDEX idx_head_to_lane ON head_to(id_lane);

-- Recherches de matchups
CREATE INDEX idx_matchup_champion ON matchup(id_champion);
CREATE INDEX idx_matchup_champion1 ON matchup(id_champion_1);
CREATE INDEX idx_matchup_lane ON matchup(id_lane);

-- Recherches de tierlist par patch
CREATE INDEX idx_tierlist_patch ON tierlist(id_patch);
CREATE INDEX idx_tierlist_tier ON tierlist(tier);

-- Recherches de spells par champion
CREATE INDEX idx_spell_champion ON spell(id_champion);

-- ============================================
-- INSERTION DES LANES (données fixes)
-- ============================================

INSERT INTO lane (name) VALUES 
    ('Top'),
    ('Jungle'),
    ('Mid'),
    ('ADC'),
    ('Support');

-- ============================================
-- FIN DU SCRIPT
-- ============================================