CREATE TABLE IF NOT EXISTS team (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    discord_message_id INTEGER,
    swiss_wins INTEGER DEFAULT 0,
    swiss_losses INTEGER DEFAULT 0,
    guild_id INTEGER,
    is_quarterfinalist BOOLEAN DEFAULT FALSE,
    is_semifinalist BOOLEAN DEFAULT FALSE,
    is_finalist BOOLEAN DEFAULT FALSE,
    is_third_place BOOLEAN DEFAULT FALSE
    );

CREATE TABLE IF NOT EXISTS player (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER,
    team_id INTEGER,
    nickname TEXT NOT NULL,
    steamid TEXT NOT NULL,
    role_name TEXT CHECK(role_name IN ('captain', 'player', 'coach')) DEFAULT 'player',
    FOREIGN KEY (team_id) REFERENCES team(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS server_role (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER,
    role_name TEXT NOT NULL,
    role_id INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS game (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER,
    team_one_id INTEGER,
    team_two_id INTEGER,
    team_winner INTEGER DEFAULT -1,
    game_type TEXT CHECK(game_type IN ('swiss_1', 'swiss_2_high', 'swiss_2_low', 'swiss_3_high','swiss_3_mid','swiss_3_low', 
        'swiss_4_high', 'swiss_4_low', 'swiss_5',
        'quarterfinal', 'semifinal', 'final', 'third_place')) NOT NULL,
    game_channel_id INTEGER NOT NULL,
    admin_game_channel_id INTEGER NOT NULL,
    voice_channel_team_one_id INTEGER NOT NULL,
    voice_channel_team_two_id INTEGER NOT NULL,
    public_game_message_id INTEGER NOT NULL,
    FOREIGN KEY (team_one_id) REFERENCES team(id) ON DELETE CASCADE,
    FOREIGN KEY (team_two_id) REFERENCES team(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS veto (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_veto INTEGER NOT NULL,
    game_id INTEGER NOT NULL,
    team_id INTEGER NOT NULL,
    map_name TEXT NOT NULL,
    guild_id INTEGER NOT NULL,
    FOREIGN KEY (game_id) REFERENCES game(id) ON DELETE CASCADE,
    FOREIGN KEY (team_id) REFERENCES team(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS pick (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_pick INTEGER NOT NULL,
    game_id INTEGER NOT NULL,
    team_id INTEGER NOT NULL,
    map_name TEXT NOT NULL,
    guild_id INTEGER NOT NULL,
    FOREIGN KEY (game_id) REFERENCES game(id) ON DELETE CASCADE,
    FOREIGN KEY (team_id) REFERENCES team(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS game_map (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER NOT NULL,
    team_id_winner INTEGER NOT NULL,
    guild_id INTEGER NOT NULL,
    game_number INTEGER NOT NULL,   
    map_name TEXT NOT NULL,
    FOREIGN KEY (game_id) REFERENCES game(id) ON DELETE CASCADE,
    FOREIGN KEY (team_id_winner) REFERENCES team(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS category (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    category_name TEXT NOT NULL,
    category_id INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS channel (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    channel_name TEXT NOT NULL,
    channel_id INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS setting (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL
);

-- CREATE TABLE IF NOT EXISTS summary (
--     id INTEGER PRIMARY KEY AUTOINCREMENT,
--     guild_id INTEGER NOT NULL,
--     round TEXT CHECK(round IN ('swiss_1', 'swiss_2_high', 'swiss_2_low', 'swiss_3_high','swiss_3_mid','swiss_3_low', 'swiss_4_high', 'swiss_4_low', 'swiss_5',
--      'quarterfinal', 'semifinal', 'final', 'third_place')) NOT NULL,
--     public_game_message_id INTEGER NOT NULL,
-- );