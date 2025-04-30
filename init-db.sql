CREATE TABLE IF NOT EXISTS team (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    discord_message_id INTEGER,
    guild_id INTEGER,
    swiss_wins INTEGER DEFAULT 0,
    swiss_losses INTEGER DEFAULT 0,
    is_quaterfinalist INTEGER DEFAULT 0,
    is_semifinalist INTEGER DEFAULT 0,
    is_finalist INTEGER DEFAULT 0,
    is_third_place INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS player (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER,
    team_id INTEGER,
    nickname TEXT NOT NULL UNIQUE,
    steamid TEXT NOT NULL UNIQUE,
    role_name TEXT CHECK(role_name IN ('captain', 'player', 'coach')) DEFAULT 'player',
    FOREIGN KEY (team_id) REFERENCES team(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS server_role (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER,
    role_name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS game (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER,
    team_one_id INTEGER,
    team_two_id INTEGER,
    winner_number INTEGER,
    game_type TEXT CHECK(game_type IN ('swiss_1', 'swiss_2', 'swiss_3', 'swiss_4', 'swiss_5',
     'quarterfinal', 'semifinal', 'final', 'third_place')) NOT NULL,
    game_channel_id INTEGER NOT NULL,
    admin_game_channel_id INTEGER NOT NULL,
    voice_channel_team1_id INTEGER NOT NULL,
    voice_channel_team2_id INTEGER NOT NULL,
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
    FOREIGN KEY (game_id) REFERENCES game(id) ON DELETE CASCADE,
    FOREIGN KEY (team_id_winner) REFERENCES team(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS category (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    category_name TEXT NOT NULL UNIQUE,
    category_id INTEGER NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS setting (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    key TEXT NOT NULL UNIQUE,
    value TEXT NOT NULL
);