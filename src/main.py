import os
import logging
from logging.handlers import RotatingFileHandler
import datetime
from dotenv import load_dotenv
import random

import discord
from discord.ext import commands
import re

from services import DatabaseManager
from models.team import Team
from models.setting import Setting
from models.server_role import ServerRole
from models.category import Category
from models.channel import Channel
from models.player import Player
from models.game import Game
from models.veto import Veto
from models.pick import Pick
from models.game_map import GameMap
from models.summary import Summary

from services.team_service import TeamService
from services.setting_service import SettingService
from services.server_role_service import ServerRoleService
from services.category_service import CategoryService
from services.channel_service import ChannelService
from services.player_service import PlayerService
from services.game_service import GameService
from services.veto_service import VetoService
from services.pick_service import PickService
from services.game_map_service import GameMapService
from services.summary_service import SummaryService

description = '''
Bot for creating a Counter Strike Tournament with 16 teams,
swiss-round and knock-out stage.
'''

# Bot configuration
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(
    command_prefix=os.environ.get("BOT_PREFIX", "!"),
    description=description,
    intents=intents,
    help_command=None
)

default_map_pool = "inferno,anubis,nuke,ancient,mirage,train,dust2"

map_pool = os.environ.get("MAP_POOL", default_map_pool).split(',')

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')

@bot.command()
@discord.ext.commands.has_role("admin")
async def help(ctx):
    """Show help information based on user role"""
    guild = ctx.guild
    admin_role = discord.utils.get(guild.roles, name="admin")
    
    if not admin_role:
        help_msg = ("🔧 **Initial Setup**\n"
                "• Send `!start` to create all necessary roles, categories and channels\n")
        await ctx.send(help_msg)
        return

    # Check if user has admin role
    if admin_role not in ctx.author.roles:
        await ctx.send("❌ You need the Admin role to view administrator commands")
        return

    help_msg = (
        "🎮 **CS2 Tournament Bot Help**\n\n"
        "⚠️ Please use the #admin channel for all commands!\n\n"
        "**Team Management:**\n"
        "• `!create_team <teamname>` - Create a new team\n"
        "• `!add_player <teamname> <nickname> <steamid> <role>` - Add player to team\n"
        "  Roles can be: captain/coach/player\n"
        "• `!delete_team <teamname>` - Delete team and its players\n"
        "• `!remove_player <teamname> <nickname>` - Remove player from team\n\n"
        
        "**Tournament Flow:**\n"
        "• `!mock_teams` - Create 16 test teams (for testing only)\n"
        "• `!all_teams_created` - Lock teams and start tournament\n"
        "  ⚠️ After this command, teams cannot be modified!\n\n"
        
        "**Round Management:**\n"
        "• `!result <team_number>` - Set the result of the current map of a game.\n" 
        "  ⚠️ This command should be executed in the public game channel.\n"
        "  ⚠️ Winner should be 1 or 2 (team number)\n"
        "• `!veto <map_name>` - Veto a map in the current game.\n"
        "  ⚠️ This command should be executed in the public game channel.\n"
        "  ⚠️ Only the captain of the team can veto a map.\n"
        "• `!pick <map_name>` - Pick a map in the current game.\n"
        "  ⚠️ Only the captain of the team can pick a map.\n\n"
    )
    
    try:
        await ctx.send(help_msg)
        logging.info(f"Help message sent to {ctx.author.name}")
    except discord.errors.HTTPException as e:
        logging.error(f"Failed to send help message: {e}")
        await ctx.send("❌ Error sending help message. Please check logs.")

@bot.command()
async def start(ctx):
    """
    Initialize the server setup.
    It creates all categories, channels and settings.
    """
    guild = ctx.guild
    try:
        # No matter if already started, but roles should not be created twice.
        start_executed_setting = bot.setting_service.get_setting_by_name(
            setting_key="start_executed", guild_id=guild.id)
        
        if start_executed_setting is not None:
            admin_role = discord.utils.get(guild.roles, name="admin")
            if admin_role is not None:
                await ctx.send("You must be an admin!")
                return
            if not ctx.channel.name == "admin":
                await ctx.send("Must be executed from admin channel")
                return
        
        # If the admin server role don't exists, create it
        admin_role = await _create_server_role(ctx, "admin")

        # Create categories and channels
        private_overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            admin_role: discord.PermissionOverwrite(
                            read_messages=True, 
                            send_messages=True
                        ),
        }
        public_overwrites = {
            guild.default_role: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=False
            ),
            admin_role: discord.PermissionOverwrite(
                read_messages=True, 
                send_messages=True
            ),
        }

        # Category object to create
        categories = {
            "Admin": {"position": 0, "overwrites": private_overwrites},
            "Info": {"position": 1, "overwrites": public_overwrites},
            "Swiss stage round 1": {"position": 2, "overwrites": public_overwrites},
            "Swiss stage round 2": {"position": 3, "overwrites": public_overwrites},
            "Swiss stage round 3": {"position": 4, "overwrites": public_overwrites},
            "Swiss stage round 4": {"position": 5, "overwrites": public_overwrites},
            "Swiss stage round 5": {"position": 6, "overwrites": public_overwrites},
            "Quarterfinals": {"position": 7, "overwrites": public_overwrites},
            "Semifinals": {"position": 8, "overwrites": public_overwrites},
            "Third Place": {"position": 9, "overwrites": public_overwrites},
            "Final": {"position": 10, "overwrites": public_overwrites}
        }
        
        # For each category create it
        discord_categories = {}
        for name, config in categories.items():
            category = await _create_server_category(ctx, category_name=name, category_position=config["position"], overwrites=config["overwrites"])
            discord_categories[name] = {
                "category": category
            }
        await ctx.send(f"Categories {discord_categories}")
        
        # Create object of channels

        channels = {
            "admin": {"category": discord_categories["Admin"]["category"], "overwrites": private_overwrites},
            "teams": {"category": discord_categories["Info"]["category"], "overwrites": public_overwrites},
            "summary": {"category": discord_categories["Info"]["category"], "overwrites": public_overwrites},
        }
        # For each channel create it
        for name, config in channels.items():            
            await _create_text_channel(ctx, channel_name=name, overwrites=config["overwrites"], category=config["category"])
        settings = {
            "swiss_not_to_three_wins": {"value": "bo1"},
            "swiss_to_three_wins": {"value": "bo3"},
            "quarterfinal_rounds": {"value": "bo3"},
            "semifinal_rounds": {"value": "bo3"},
            "final_rounds": {"value": "bo5"},
            "third_place_rounds": {"value": "bo3"},
            "start_executed": {"value": "true"}
        }

        for key, config in settings.items():
            await _create_server_setting(ctx, key, config["value"])

    except Exception as e:
        await ctx.send(f"Error during setup: {str(e)}")
        logging.error(f"Setup error: {e}", exc_info=True)

@bot.command()
@discord.ext.commands.has_role("admin")
async def create_team(ctx, *name: str):
    """Create a new team"""
    guild = ctx.guild
    admin_role = discord.utils.get(guild.roles, name="admin")
    name = " ".join(name)
    if admin_role is None:
        await ctx.send("Only admins can execute this")
        return
    if not ctx.channel.name == "admin":
        await ctx.send("Must be executed from admin channel")
        return
    try:
        await _create_team(ctx, name)
    except Exception as e:
        logging.error(f"Error creating team: {e}")
        await ctx.send(f"❌ Error creating team: {e}")

@bot.command()
@discord.ext.commands.has_role("admin")
async def add_player(ctx, *values: str):
    """
    Adds a player with nickname, SteamID (numbers only), and role to a team.
    Format: !add_player <team_name> <nickname> <steamid> <role_name>
    - team_name: Multi-word (e.g., "Natus Vincere")
    - nickname: Single word (e.g., "s1mple")
    - steamid: Numbers only (e.g., "123456789")
    - role_name: captain/player/coach
    """
    # Check for minimum required arguments
    if len(values) < 4:
        await ctx.send("❌ Format: !add_player <team_name> <nickname> <steamid> <role>")
        return
    guild = ctx.guild
    admin_role = discord.utils.get(guild.roles, name="admin")

    if admin_role is None:
        await ctx.send("Only admins can execute this")
        return
    
    if not ctx.channel.name == "admin":
        await ctx.send("Must be executed from admin channel")
        return

    *team_name_parts, nickname, steamid, role_name = values
    team_name = " ".join(team_name_parts)  # Combine team name parts with spaces
    role_name = role_name.lower()  # Normalize role to lowercase

    try:
        await _add_player(ctx, team_name=team_name, nickname=nickname, role_name=role_name, steamid=steamid)
    except Exception as e:
        logging.error(f"Error creating team: {e}")
        await ctx.send(f"❌ Error creating team: {e}")

@bot.command()
@discord.ext.commands.has_role("admin")
async def delete_player(ctx, nickname: str):
    """
    Deletes a player with nickname.
    Format: !add_player <nickname>
    - nickname: Single word (e.g., "s1mple")
    """
    
    guild = ctx.guild
    admin_role = discord.utils.get(guild.roles, name="admin")

    if admin_role is None:
        await ctx.send("Only admins can execute this")
        return

    if not ctx.channel.name == "admin":
        await ctx.send("Must be executed from admin channel")
        return
        
    try:
        await _delete_player(ctx, nickname=nickname)
    except Exception as e:
        logging.error(f"Error creating team: {e}")
        await ctx.send(f"❌ Error creating team: {e}")

@bot.command()
@discord.ext.commands.has_role("admin")
async def delete_team(ctx, *name: str):
    """Delete team"""
    guild = ctx.guild
    admin_role = discord.utils.get(guild.roles, name="admin")
    name = " ".join(name)
    if admin_role is None:
        await ctx.send("Only admins can execute this")
        return
    
    if not ctx.channel.name == "admin":
        await ctx.send("Must be executed from admin channel")
        return
        
    try:
        await _delete_team(ctx, name)
    except Exception as e:
        logging.error(f"Error creating team: {e}")
        await ctx.send(f"❌ Error creating team: {e}")
        
@bot.command()
@discord.ext.commands.has_role("admin")
async def create_teams(ctx, *names: str):
    """Create a new team"""
    guild = ctx.guild
    admin_role = discord.utils.get(guild.roles, name="admin")
    names = " ".join(names)
    names_splitted = [name.strip() for name in names.split(",")]
    if admin_role is None:
        await ctx.send("Only admins can execute this")
        return
    
    if not ctx.channel.name == "admin":
        await ctx.send("Must be executed from admin channel")
        return
    
    try:
        for name in names_splitted:
            await _create_team(ctx, name=name)
    except Exception as e:
        logging.error(f"Error creating teams: {e}")
        await ctx.send(f"❌ Error creating team: {e}")  

@bot.command()
@discord.ext.commands.has_role("admin")
async def all_teams_created(ctx):
    """Starts the tournament"""
    guild = ctx.guild
    admin_role = discord.utils.get(guild.roles, name="admin")
    if admin_role is None:
        await ctx.send("Only admins can execute this")
        return
    
    if not ctx.channel.name == "admin":
        await ctx.send("Must be executed from admin channel")
        return
    
    try:
        await _set_new_round(ctx)
    except Exception as e:
        logging.error(f"All teams created error: {e}")
        await ctx.send(f"❌ All teams created error: {e}")  

@bot.command()
@discord.ext.commands.has_role("admin")
async def mock_teams(ctx):
    """Create mock teams"""
    guild = ctx.guild
    admin_role = discord.utils.get(guild.roles, name="admin")
    if admin_role is None:
        await ctx.send("Only admins can execute this")
        return
    
    if not ctx.channel.name == "admin":
        await ctx.send("Must be executed from admin channel")
        return
        
    try:
        teams = bot.team_service.get_all_teams(guild_id=guild.id)
        for i in range(1, (17 - len(teams))):
            team_name = f"TeamX{i}"
            await _create_team(ctx, name=team_name)
            players = [
                (f"{team_name}captain", "captain"),
                (f"{team_name}player1", "player"),
                (f"{team_name}player2", "player"),
                (f"{team_name}player3", "player"),
                (f"{team_name}player4", "player"),
                (f"{team_name}coach", "coach")
            ]
        teams = bot.team_service.get_all_teams(guild_id=guild.id)
        for team in teams:
            team_name = team.name
            await ctx.send(f"Creating {team_name} players:")
            players = [
                (f"{team_name}captain", "captain"),
                (f"{team_name}player1", "player"),
                (f"{team_name}player2", "player"),
                (f"{team_name}player3", "player"),
                (f"{team_name}player4", "player"),
                (f"{team_name}coach", "coach")
            ]
            for nickname, role in players:
                steamid = str(random.randint(100000, 999999))
                await ctx.send("add_player")
                await _add_player(ctx, team_name=team_name, nickname=nickname, role_name=role, steamid=steamid)           
    except Exception as e:
        logging.error(f"Error creating mock teams: {e}")
        await ctx.send(f"❌ Error creating mock team: {e}")  

@bot.command()
async def veto(ctx, map_name: str):
    guild = ctx.guild
    channel_id = ctx.channel.id
    game = bot.game_service.get_game_by_admin_game_channel_id(admin_game_channel_id=channel_id)
    if game is None:
        await ctx.send("This must be sent from a admin game channel.")
        return
    game_to_wins = await _get_game_to_wins(ctx, game=game)
    await _execute_veto(ctx, game_to_wins=game_to_wins.value, game=game, map_name=map_name)

@bot.command()
async def pick(ctx, map_name: str):
    guild = ctx.guild
    channel_id = ctx.channel.id
    game = bot.game_service.get_game_by_admin_game_channel_id(admin_game_channel_id=channel_id)
    if game is None:
        await ctx.send("This must be sent from a admin game channel.")
        return
    game_to_wins = await _get_game_to_wins(ctx, game=game)
    await _execute_pick(ctx, game_to_wins=game_to_wins.value, game=game, map_name=map_name)

@bot.command()
@discord.ext.commands.has_role("admin")
async def summary(ctx):
    channel_id = ctx.channel.id
    game = bot.game_service.get_game_by_admin_game_channel_id(admin_game_channel_id=channel_id)
    if game is None:
        await ctx.send("This must be sent from a admin game channel.")
        return
    await _game_summary(ctx, game)
    
@bot.command()
@discord.ext.commands.has_role("admin")
async def result(ctx, map_name: str, team_number: int):
    channel_id = ctx.channel.id
    game = bot.game_service.get_game_by_admin_game_channel_id(admin_game_channel_id=channel_id)
    if game is None:
        await ctx.send("This must be sent from a admin game channel.")
        return
    await _set_result(ctx, game=game, team_number=team_number, map_name=map_name)
    await _game_summary(ctx, game=game)
    await _games_summary(ctx)
    
@bot.command()
@discord.ext.commands.has_role("admin")
async def finish_round(ctx):
    if not ctx.channel.name == "admin":
        await ctx.send("Must be executed from admin channel")
        return
    else:
        await _set_new_round(ctx)

@bot.command()
@discord.ext.commands.has_role("admin")
async def autoveto(ctx):
    guild = ctx.guild
    if not ctx.channel.name == "admin":
        await ctx.send("Must be executed from admin channel")
        return
    else:
        games = bot.game_service.get_all_games_not_finished(guild_id=guild.id)
        await ctx.send(f"games_len = {len(games)}")
        for game in games:
            game_to_wins = (await _get_game_to_wins(ctx, game=game)).value
            await ctx.send(f"autoveto0-{game_to_wins}")
            if game_to_wins == "bo1":
                await ctx.send(f"autoveto1-{game_to_wins}")
                await _execute_veto(ctx, game=game, map_name="anubis", game_to_wins=game_to_wins)
                await _execute_veto(ctx, game=game, map_name="train", game_to_wins=game_to_wins)
                await _execute_veto(ctx, game=game, map_name="inferno", game_to_wins=game_to_wins)
                await _execute_veto(ctx, game=game, map_name="mirage", game_to_wins=game_to_wins)
                await _execute_veto(ctx, game=game, map_name="nuke", game_to_wins=game_to_wins)
                await _execute_veto(ctx, game=game, map_name="ancient", game_to_wins=game_to_wins)
            elif game_to_wins == "bo3":
                await ctx.send(f"autoveto2-{game_to_wins}")
                await _execute_veto(ctx, game=game, map_name="anubis", game_to_wins=game_to_wins)
                await _execute_veto(ctx, game=game, map_name="train", game_to_wins=game_to_wins)
                await _execute_pick(ctx, game=game, map_name="inferno", game_to_wins=game_to_wins)
                await _execute_pick(ctx, game=game, map_name="mirage", game_to_wins=game_to_wins)
                await _execute_veto(ctx, game=game, map_name="nuke", game_to_wins=game_to_wins)
                await _execute_veto(ctx, game=game, map_name="ancient", game_to_wins=game_to_wins)
            elif game_to_wins == "bo5":
                await ctx.send(f"autoveto3-{game_to_wins}")
                await _execute_veto(ctx, game=game, map_name="anubis", game_to_wins=game_to_wins)
                await _execute_veto(ctx, game=game, map_name="train", game_to_wins=game_to_wins)
                await _execute_pick(ctx, game=game, map_name="inferno", game_to_wins=game_to_wins)
                await _execute_pick(ctx, game=game, map_name="mirage", game_to_wins=game_to_wins)
                await _execute_pick(ctx, game=game, map_name="nuke", game_to_wins=game_to_wins)
                await _execute_pick(ctx, game=game, map_name="ancient", game_to_wins=game_to_wins)
            
@bot.command()
@discord.ext.commands.has_role("admin")
async def autoresults(ctx):
    guild = ctx.guild
    if not ctx.channel.name == "admin":
        await ctx.send("Must be executed from admin channel")
        return
    else:
        games = bot.game_service.get_all_games_not_finished(guild_id=guild.id)
        for game in games:
            game_to_wins = (await _get_game_to_wins(ctx, game=game)).value
            if game_to_wins == "bo1":
                await _set_result(ctx, game=game, team_number=1, map_name="dust2")
            elif game_to_wins == "bo3":
                await _set_result(ctx, game=game, team_number=1, map_name="inferno")
                await _set_result(ctx, game=game, team_number=1, map_name="mirage")
            elif game_to_wins == "bo5":
                await _set_result(ctx, game=game, team_number=1, map_name="inferno")
                await _set_result(ctx, game=game, team_number=1, map_name="mirage")
                await _set_result(ctx, game=game, team_number=1, map_name="nuke")

@bot.command()
@discord.ext.commands.has_role("admin")
async def tournamentsummary(ctx):
    await _games_summary(ctx)

def setup_logging():
    """Configure logging with file rotation"""
    os.makedirs('logs', exist_ok=True)
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    file_handler = RotatingFileHandler(
        filename=f'logs/discord_{datetime.datetime.now().strftime("%Y%m%d")}.log',
        maxBytes=5*1024*1024,  # 5MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Configure loggers
    logging.basicConfig(
        level=logging.INFO,
        handlers=[file_handler, console_handler]
    )
    
    # Silence noisy loggers
    logging.getLogger('discord.http').setLevel(logging.info)

def setup_database():
    """Initialize database and attach to bot instance"""
    bot.db = DatabaseManager()
    bot.setting_service = SettingService(bot.db.get_connection())
    bot.service_role_service = ServerRoleService(bot.db.get_connection())
    bot.team_service = TeamService(bot.db.get_connection())
    bot.server_role_service = ServerRoleService(bot.db.get_connection())
    bot.category_service = CategoryService(bot.db.get_connection())
    bot.channel_service = ChannelService(bot.db.get_connection())
    bot.player_service = PlayerService(bot.db.get_connection())
    bot.game_service = GameService(bot.db.get_connection())
    bot.team_service = TeamService(bot.db.get_connection())
    bot.veto_service = VetoService(bot.db.get_connection())
    bot.pick_service = PickService(bot.db.get_connection())
    bot.game_map_service = GameMapService(bot.db.get_connection())
    bot.summary_service = SummaryService(bot.db.get_connection())
    logging.info("Database and services initialized")

def _is_valid_team_name(name: str) -> bool:
    """Allows alphanumeric + spaces, no symbols"""
    return all(c.isalnum() or c.isspace() for c in name)

async def _create_team(ctx, name:str) -> Team:
    guild = ctx.guild
    try:
        if not _is_valid_team_name(name=name):
            await ctx.send("Team names can only contain alphanumerics and spaces.")
            return
        discord_info_category = discord.utils.get(guild.categories, name="Info")
        discord_teams_channel = discord.utils.get(guild.text_channels, name="teams", category=discord_info_category)
        if discord_teams_channel is None:
            await ctx.send("There is no teams channel, please use !start")
            return

        team = bot.team_service.get_team_by_name(name=name, guild_id = guild.id)
        if team is not None:
            await ctx.send(f"Team {name} already exists.")
            return
        embed = await _create_team_embed(team_name=name, members=[])
        msg = await discord_teams_channel.send(embed=embed)

        team = Team(name=name, guild_id=guild.id, discord_message_id=msg.id)
        await ctx.send(f"Creating team {team}...")
        logging.info(team.name)
        team.id = bot.team_service.create_team(team=team)

        logging.info(f"Team {name} created in guild {guild.name}")
        await ctx.send(f"Created team {name}")

        # Create roles
        for role_type in ["captain", "player", "coach"]:
            server_role_name = f"{name}_{role_type}"
            await _create_server_role(ctx, server_role_name=server_role_name)
        return team

    except Exception as e:
        logging.error(f"Error creating team: {e}")
        await ctx.send(f"❌ Error creating team: {e}")
        return None

async def _add_player(ctx, team_name:str, nickname:str, role_name:str, steamid:str) -> Player:
    guild = ctx.guild
    # Validate player name (single word)
    if " " in nickname:
        await ctx.send("❌ Player name must be a single word!")
        return None
    
    # Validate role
    valid_roles = {"captain", "player", "coach"}
    if role_name not in valid_roles:
        await ctx.send(f"❌ Invalid role! Must be one of: {', '.join(valid_roles)}")
        return None
    try:
        discord_info_category = discord.utils.get(guild.categories, name="Info")
        discord_teams_channel = discord.utils.get(guild.text_channels, name="teams", category=discord_info_category)
        if discord_teams_channel is None:
            await ctx.send("There is no teams channel, please use !start")
            return
        team = bot.team_service.get_team_by_name(name=team_name, guild_id=guild.id)
        await ctx.send(f"Team: {team.name}")
        if team is None:
            return
        player = bot.player_service.get_player_by_nickname(nickname=nickname, guild_id=guild.id)
        if player is not None:
            await ctx.send(f"Player {nickname} already exists with this name.")
            return None
        player = bot.player_service.get_player_by_steamid(steamid=steamid, guild_id=guild.id)
        if player is not None:
            await ctx.send(f"Player with steamid {steamid} already exists.")
            return None
        if not steamid.isdigit():
            await ctx.send("❌ SteamID must contain only numbers (steamID64)!")
            return None
        players = bot.player_service.get_players_by_team_id(team_id=team.id)

        if role_name == "captain":
            await ctx.send(players)
            count_captains = sum(1 for p in players if p.role_name == role_name)
            await ctx.send(f"count_captains={count_captains }")
            if count_captains >= 1:
                await ctx.send("❌ Only one captain can be assigned.")
                return None
        elif role_name == "coach":
            count_coaches = sum(1 for p in players if p.role_name == role_name)
            if count_coaches >= 2:
                await ctx.send("❌ Only two coaches can be assigned.")
                return None
        elif role_name == "player":
            count_players = sum(1 for p in players if p.role_name == role_name)
            if count_players >= 4:
                await ctx.send("❌ Only four non-captain players can be assigned.")
                return None
        else:
            await ctx.send("❌ Role must be \"captain\", \"coach\" or \"player\".")
            return None
    

        player = Player(
            guild_id=guild.id, 
            team_id=team.id, 
            nickname=nickname, 
            steamid=steamid,
            role_name=role_name)
        player.id = bot.player_service.create_player(player)
        await ctx.send(f"Player {nickname} with steamid {steamid} added as a {role_name} to team {team_name}")

        players = bot.player_service.get_players_by_team_id(team_id=team.id)
        embed = await _create_team_embed(team_name=team_name, members=players)
        discord_team_message = await discord_teams_channel.fetch_message(team.discord_message_id)
        await discord_team_message.edit(embed=embed)
        return player    
    except Exception as e:
        logging.error(f"Error adding player: {e}")
        await ctx.send(f"❌ Error adding player: {e}")
        return None

async def _delete_player(ctx, nickname:str):
    guild = ctx.guild
    # Validate player name (single word)
    if " " in nickname:
        await ctx.send("❌ Player name must be a single word!")
        return None

    discord_info_category = discord.utils.get(guild.categories, name="Info")
    discord_teams_channel = discord.utils.get(guild.text_channels, name="teams", category=discord_info_category)
    if discord_teams_channel is None:
        await ctx.send("There is no teams channel, please use !start")
        return
    player = bot.player_service.get_player_by_nickname(nickname=nickname, guild_id=guild.id)
    if player is None:
        await ctx.send(f"There is no player with nickname {nickname}")
        return
    
    team = bot.team_service.get_team_by_id(team_id=player.team_id)
    if team is None:
        ctx.send(f"Player's team don't exists. Is weird.")
        return
    player.id = bot.player_service.delete_player_by_id(id=player.id)
    await ctx.send(f"Player {nickname} deleted successfully.")

    players = bot.player_service.get_players_by_team_id(team_id=team.id)
    embed = await _create_team_embed(team_name=team.name, members=players)
    discord_team_message = await discord_teams_channel.fetch_message(team.discord_message_id)
    await discord_team_message.edit(embed=embed)
    return    

async def _delete_team(ctx, name:str):
    guild = ctx.guild
    try:
        if not _is_valid_team_name(name=name):
            await ctx.send("Team names can only contain alphanumerics and spaces.")
            return

        discord_info_category = discord.utils.get(guild.categories, name="Info")
        discord_teams_channel = discord.utils.get(guild.text_channels, name="teams", category=discord_info_category)
        if discord_teams_channel is None:
            await ctx.send("There is no teams channel, please use !start")
            return

        team = bot.team_service.get_team_by_name(name=name, guild_id = guild.id)
        if team is None:
            await ctx.send(f"Team {name} doesn't exist.")
            return

        discord_team_message = await discord_teams_channel.fetch_message(team.discord_message_id)
        await discord_team_message.delete()

        logging.info(team.name)
        team.id = bot.team_service.delete_team_by_id(id=team.id)

        logging.info(f"Team {name} deleted in guild {guild.name}")
        await ctx.send(f"Deleted team {name}")

    except Exception as e:
        logging.error(f"Error creating team: {e}")
        await ctx.send(f"❌ Error creating team: {e}")
        
async def _create_team_embed(team_name: str, members: list) -> discord.Embed:
    """Creates an embed for team display with current members and status"""
    embed = discord.Embed(title=f"Team {team_name}", color=discord.Color.blue())

    if len(members) == 0:
        embed.description = "_No players yet_"
        return embed

    # Sort members by role
    captain = next((m for m in members if m.role_name == "captain"), None)
    players = [m for m in members if m.role_name == "player"]
    coaches = [m for m in members if m.role_name == "coach"]

    # Add fields for each role
    if captain:
        embed.add_field(name="👑 Captain", value=f"・{captain.nickname}", inline=False)
    if players:
        embed.add_field(name="🧍 Players", value="\n".join(f"・{p.nickname}" for p in players), inline=False)
    if coaches:
        embed.add_field(name="🧠 Coaches", value="\n".join(f"・{c.nickname}" for c in coaches), inline=False)

    # Calculate team status
    count_captains = sum(m.role_name== "captain" for m in members)
    count_coaches = sum(m.role_name== "coach" for m in members)
    count_players = sum(m.role_name== "player" for m in members)

    # Set description based on team status
    description = []
    if count_captains == 0:
        description.append("_Missing one 👑captain._")
    if count_coaches < 2:
        description.append("_Optionally two 🧠coaches can be added._")
    if count_players < 5:
        description.append("_Five players (including captain) are needed._")
    
    embed.description = "\n".join(description) if description else "_The team is complete._"
    
    return embed

async def _create_server_category(ctx, category_name:str, category_position:int, overwrites) -> discord.CategoryChannel:
    """
    Creates a server category taking in account also them to be stored in the DB
    """
    # Get category from discord
    guild = ctx.guild
    discord_category = discord.utils.get(guild.categories, name=category_name)
    if discord_category is None: # If the category don't exist, create it on Discord and DB        
        discord_category = await guild.create_category(
            name=category_name, 
            position=category_position, 
            overwrites=overwrites
        )
        await ctx.send(f"Category {category_name} created")
    else:
        await ctx.send(f"Category {category_name} already created")
    return discord_category

async def _create_server_role(ctx, server_role_name: str) -> discord.Role:
    """
    Creates a server role taking in account also them to be stored in the DB
    """
    guild = ctx.guild
    # Check if role exists by name in discord
    discord_server_role = discord.utils.get(guild.roles, name=server_role_name)
    if discord_server_role is None:  # The role don't exist on discord, create on Discord and upsert on DB
        # Create server role on discord
        discord_server_role = await guild.create_role(name=server_role_name, mentionable=True)
        await ctx.send(f"Server role {server_role_name} created")
    else:
        await ctx.send(f"Server role {server_role_name} already created")
    return discord_server_role

async def _create_text_channel(ctx, channel_name: str, category: discord.CategoryChannel, overwrites:dict):
    """
    Creates a text channel if not exist
    """
    guild = ctx.guild
    discord_text_channel = discord.utils.get(guild.text_channels, name=channel_name, category=category)
    if discord_text_channel is None:
        discord_text_channel = await category.create_text_channel(channel_name, overwrites=overwrites)
        await ctx.send(f"Channel {channel_name} created")
    else:
        await ctx.send(f"Channel {channel_name} already created")
    return discord_text_channel

async def _create_server_setting(ctx, key:str, value:str) -> Setting:
    """
    Create a server setting if it don't exists
    """
    guild = ctx.guild
    setting = bot.setting_service.get_setting_by_name(guild_id=guild.id, setting_key=key)

    if setting is not None:
        return setting
    else:
        setting = Setting(guild_id=guild.id, key=key, value=value)
        setting.id = bot.setting_service.create_setting(setting=setting)
    return setting

async def _set_new_round(ctx):
    """
    Checks if a new round have to be and creates the needed resources if true
    """
    guild = ctx.guild
    all_games_finished = bot.game_service.get_all_games_finished(guild_id=guild.id)
    all_games = bot.game_service.get_all_games(guild_id=guild.id)
    number_of_games_finished = len(all_games_finished)
    number_of_games = len(all_games)
    
    game_type = ""
    if number_of_games_finished == 0 and number_of_games == 0: # First round of swiss (swiss_1)
        game_types = ["swiss_1"]
    elif number_of_games_finished == 8 and number_of_games == 8: # Second round of swiss (swiss_2)
        game_types = ["swiss_2"]
    elif number_of_games_finished == 16 and number_of_games == 16: # Third round of swiss (swiss_3)
        game_types = ["swiss_3"]
    elif number_of_games_finished == 24 and number_of_games == 24: # Fourth round of swiss (swiss_4)
        game_types = ["swiss_4"]
    elif number_of_games_finished == 30 and number_of_games == 30: # Firth round of swiss (swiss_5)
        game_types = ["swiss_5"]
    elif number_of_games_finished == 33 and number_of_games == 33: # First knockout round (quarterfinal)
        game_types = ["quarterfinal"]
    elif number_of_games_finished == 37 and number_of_games == 37: # Second knockout round (semifinal)
        game_types = ["semifinal"]
    elif number_of_games_finished == 39 and number_of_games == 39: # Third knockout round (third_place and final)
        game_types = ["third_place", "final"]
    else:
        return
    await ctx.send(f"Game types -> {game_types}")
    for game_type in game_types:
        await _create_games(ctx, game_type) 

async def _random_games(ctx, teams: list[Team], game_type: str) -> list[Game]:
    """Randomize the games for the given teams"""  
    guild = ctx.guild  
    # Shuffle the teams
    random.shuffle(teams)
    
    # Create pairs of teams
    games = []
    for i in range(0, len(teams), 2):
        if i + 1 < len(teams):  # Safety check
            game = Game(
                game_type=game_type, 
                guild_id=guild.id,
                team_one_id = teams[i].id,
                team_two_id=teams[i+1].id
            )
            games.append(game)
            
    return games

async def _create_game(ctx, game: Game, category: discord.CategoryChannel):
    """
    Create a game with its type and so on
    """
    guild = ctx.guild
    team_one = bot.team_service.get_team_by_id(game.team_one_id)
    team_two = bot.team_service.get_team_by_id(game.team_two_id)
    roles = {
        "admin": discord.utils.get(guild.roles, name="admin"),
        "team_one_captain": discord.utils.get(guild.roles, name=f"{team_one.name}_captain"),
        "team_one_coach": discord.utils.get(guild.roles, name=f"{team_one.name}_coach"),
        "team_one_player": discord.utils.get(guild.roles, name=f"{team_one.name}_player"),
        "team_two_captain": discord.utils.get(guild.roles, name=f"{team_two.name}_captain"),
        "team_two_coach": discord.utils.get(guild.roles, name=f"{team_two.name}_coach"),
        "team_two_player": discord.utils.get(guild.roles, name=f"{team_two.name}_player")
    }

    if not all(roles.values()):
        missing = [k for k, v in roles.items() if not v]
        await ctx.send(f"❌ Missing required roles: {', '.join(missing)}")
        return None
    
    # Create admin channel
    admin_overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        roles["admin"]: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        roles["team_one_captain"]: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        roles["team_one_coach"]: discord.PermissionOverwrite(read_messages=True, send_messages=False),
        roles["team_one_player"]: discord.PermissionOverwrite(read_messages=True, send_messages=False),
        roles["team_two_captain"]: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        roles["team_two_coach"]: discord.PermissionOverwrite(read_messages=True, send_messages=False),
        roles["team_two_player"]: discord.PermissionOverwrite(read_messages=True, send_messages=False)
    }

    admin_channel_name = f"ADMINS {team_one.name} vs {team_two.name}"
    await ctx.send(category)
    admin_channel = await _create_text_channel(ctx, channel_name=admin_channel_name, overwrites=admin_overwrites, category=category)
    await admin_channel.send(f"This channel will be used for communicating between org and teams on this game, remember that only admins and users with role {team_one.name}_captain and {team_two.name}_captain can write in this channel.")
    await admin_channel.send(f"Time of picks and bans, {team_one.name} captain please send your veto with the command `!veto <mapname>`")

    # Create public channel
    public_overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        roles["admin"]: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }

    game_channel_name = f"{team_one.name} vs {team_two.name}"
    public_channel = await _create_text_channel(ctx, channel_name=game_channel_name, overwrites=public_overwrites, category=category)

    # Create voice channels
    voice1_overwrites = {
        guild.default_role: discord.PermissionOverwrite(connect=False),
        guild.me: discord.PermissionOverwrite(connect=True, speak=True),
        roles["admin"]: discord.PermissionOverwrite(connect=True, speak=True),
        roles["team_one_captain"]: discord.PermissionOverwrite(connect=True, speak=True),
        roles["team_one_coach"]: discord.PermissionOverwrite(connect=True, speak=True),
        roles["team_one_player"]: discord.PermissionOverwrite(connect=True, speak=True)
    }
    
    voice2_overwrites = {
        guild.default_role: discord.PermissionOverwrite(connect=False),
        guild.me: discord.PermissionOverwrite(connect=True, speak=True),
        roles["admin"]: discord.PermissionOverwrite(connect=True, speak=True),
        roles["team_two_captain"]: discord.PermissionOverwrite(connect=True, speak=True),
        roles["team_two_coach"]: discord.PermissionOverwrite(connect=True, speak=True),
        roles["team_two_player"]: discord.PermissionOverwrite(connect=True, speak=True)
    }
    
    voice1 = await category.create_voice_channel(team_one.name, overwrites=voice1_overwrites)
    voice2 = await category.create_voice_channel(team_two.name, overwrites=voice2_overwrites)
    embed = await _game_embed(ctx, game)
    msg = await public_channel.send(embed=embed)

    game.admin_game_channel_id = admin_channel.id
    game.game_channel_id = public_channel.id
    game.public_game_message_id = msg.id
    game.voice_channel_team_one_id = voice1.id
    game.voice_channel_team_two_id = voice2.id

    bot.game_service.create_game(game)

async def _create_games(ctx, game_type: str):
    """
    Get games and create them
    """
    games = []
    guild = ctx.guild
    if game_type == "swiss_1":
        teams = bot.team_service.get_all_teams(guild.id)
        games += await _random_games(ctx, teams=teams, game_type=game_type)
        game_category_name = "Swiss stage round 1"
    if game_type == "swiss_2":
        teams = bot.team_service.get_teams_by_record(guild_id=guild.id, wins=1,losses=0)
        games += await _random_games(ctx, teams=teams, game_type=f"{game_type}_high")
        teams = bot.team_service.get_teams_by_record(guild_id=guild.id, wins=0,losses=1)
        games += await _random_games(ctx, teams=teams, game_type=f"{game_type}_low")
        game_category_name = "Swiss stage round 2"
    if game_type == "swiss_3":
        teams = bot.team_service.get_teams_by_record(guild_id=guild.id, wins=2,losses=0)
        games += await _random_games(ctx, teams=teams, game_type=f"{game_type}_high")
        teams = bot.team_service.get_teams_by_record(guild_id=guild.id, wins=1,losses=1)
        games += await _random_games(ctx, teams=teams, game_type=f"{game_type}_mid")
        teams = bot.team_service.get_teams_by_record(guild_id=guild.id, wins=0,losses=2)
        games += await _random_games(ctx, teams=teams, game_type=f"{game_type}_low")
        game_category_name = "Swiss stage round 3"
    if game_type == "swiss_4":
        teams = bot.team_service.get_teams_by_record(guild_id=guild.id, wins=2,losses=1)
        games += await _random_games(ctx, teams=teams, game_type=f"{game_type}_high")
        teams = bot.team_service.get_teams_by_record(guild_id=guild.id, wins=1,losses=2)
        games += await _random_games(ctx, teams=teams, game_type=f"{game_type}_low")
        game_category_name = "Swiss stage round 4"
    if game_type == "swiss_5":
        teams = bot.team_service.get_teams_by_record(guild_id=guild.id, wins=2,losses=2)
        games += await _random_games(ctx, teams=teams, game_type=game_type)
        game_category_name = "Swiss stage round 5"        
    if game_type == "quarterfinal":
        teams = bot.team_service.get_teams_quarterfinalist(guild_id=guild.id)
        games += await _random_games(ctx, teams=teams, game_type=game_type)
        game_category_name = "Quarterfinals"       
    if game_type == "semifinal":
        teams = bot.team_service.get_teams_semifinalist(guild_id=guild.id)
        games += await _random_games(ctx, teams=teams, game_type=game_type)
        game_category_name = "Semifinals"
    if game_type == "final":
        teams = bot.team_service.get_teams_finalist(guild_id=guild.id)
        games += await _random_games(ctx, teams=teams, game_type=game_type)
        game_category_name = "Final"
    if game_type == "third_place":
        teams = bot.team_service.get_teams_third_place(guild_id=guild.id)
        games += await _random_games(ctx, teams=teams, game_type=game_type)
        game_category_name = "Third Place"
    
    discord_game_category = discord.utils.get(guild.categories, name=game_category_name)
    for game in games:
        await ctx.send(f"Creating game {game}")
        await _create_game(ctx, game, category=discord_game_category)
    await _games_summary(ctx)

async def _games_summary(ctx):
    guild = ctx.guild
    game_rounds = [
        ("swiss_1", "Swiss round 1 (0 Wins, 0 Losses)"),
        ("swiss_2_high", "Swiss round 2 high (1 Win, 0 Losses)"),
        ("swiss_2_low", "Swiss round 2 low (0 Wins, 1 Loss)"),
        ("swiss_3_high", "Swiss round 3 high (2 Wins, 0 Losses)"),
        ("swiss_3_mid", "Swiss round 3 mid (1 Win, 1 Loss)"),
        ("swiss_3_low", "Swiss round 3 low (0 Wins, 2 Losses)"),
        ("swiss_4_high", "Swiss round 4 high (2 Wins, 1 Losses)"),
        ("swiss_4_low", "Swiss round 4 low (1 Win, 2 Losses)"),
        ("swiss_5", "Swiss round 2 high (2 Wins, 2 Losses)"),
        ("quarterfinal", "Quarter-final"),
        ("semifinal", "Semi-final"),
        ("third_place", "Third place"),
        ("final", "Final")
    ] 
    discord_info_category = discord.utils.get(guild.categories, name="Info")
    discord_summary_channel = discord.utils.get(guild.text_channels, name="summary", category=discord_info_category)
    for game_round, title in game_rounds:
        embed = discord.Embed(title=title, color=discord.Color.blue())
        games = bot.game_service.get_games_by_type(game_type=game_round, guild_id=guild.id)
        if len(games) > 0:
            text = ""
            for game in games:
                team_one = bot.team_service.get_team_by_id(team_id=game.team_one_id)
                team_two = bot.team_service.get_team_by_id(team_id=game.team_two_id)
                team_one_name = team_one.name
                team_two_name = team_two.name
                game_maps = bot.game_map_service.get_all_game_maps_by_game(guild_id=guild.id, game_id=game.id)
                team_one_wins = 0
                team_two_wins = 0
                for game_map in game_maps:
                    if game_map.team_id_winner == team_one.id:
                        team_one_wins = team_one_wins + 1
                    elif game_map.team_id_winner == team_two.id:
                        team_two_wins = team_two_wins + 1
                games_to_wins = await _get_game_to_wins(ctx, game)
                game_winner = None
                if games_to_wins.value == "bo1":
                    if team_one_wins >= 1:
                        team_one_name = f"✅{team_one_name}"
                        team_two_name = f"{team_two_name}❌"
                    elif team_two_wins >= 1:
                        team_one_name = f"❌{team_one_name}"
                        team_two_name = f"{team_two_name}✅"
                elif games_to_wins.value == "bo3":
                    if team_one_wins >= 2:
                        team_one_name = f"✅{team_one_name}"
                        team_two_name = f"{team_two_name}❌"
                    elif team_two_wins >= 2:
                        team_one_name = f"❌{team_one_name}"
                        team_two_name = f"{team_two_name}✅"
                elif games_to_wins.value == "bo5":
                    if team_one_wins >= 3:
                        team_one_name = f"✅{team_one_name}"
                        team_two_name = f"{team_two_name}❌"
                    elif team_two_wins >= 3:
                        team_one_name = f"❌{team_one_name}"
                        team_two_name = f"{team_two_name}✅"

                text += f"・{team_one_name} {team_one_wins}:{team_two_wins} {team_two_name}\n"
            
            embed.add_field(name="Games", value=text, inline=False)
            summary = bot.summary_service.get_summary_by_round_name(guild_id=guild.id, round_name=game_round)
            if summary is None:
                msg = await discord_summary_channel.send(embed=embed)
                summary = Summary(guild_id= guild.id, round_name=game_round, message_id=msg.id)
                bot.summary_service.create_summary(summary=summary)
            else:
                msg = await discord_summary_channel.fetch_message(summary.message_id)
                await ctx.send(msg.id)
                await msg.edit(embed=embed)

async def _check_all_teams(ctx) -> bool:
    """
    Checks if all teams have been created and have enough players
    """
    guild = ctx.guild
    all_teams = bot.team_service.get_all_teams(guild_id=guild.id)
    if len(all_teams) != 16:
        return False
    for team in all_teams:
        members = bot.player_service.get_players_by_team_id(ctx, team.id)
        captain = next((m for m in members if m.role_name == "captain"), None)
        players = [m for m in members if m.role_name == "player"]
        coaches = [m for m in members if m.role_name == "coach"]

        if len(captain) != 1 or len(players) != 4 or len(coaches) < 1 or len(coaches) > 2:
            return False
    return True

async def _get_game_to_wins(ctx, game: Game) -> str:
    """
    Have to return if the game is bo1, bo3 or bo5
    """
    guild = ctx.guild
    game_type = game.game_type
    key = ""
    if game_type == "swiss_1" or game_type == "swiss_2_high" or game_type == "swiss_2_low" or game_type == "swiss_3_low" or game_type == "swiss_3_mid":
        key = "swiss_not_to_three_wins"
    elif game_type == "swiss_3_high" or game_type == "swiss_4_high" or game_type == "swiss_4_low" or game_type == "swiss_5":
        key = "swiss_to_three_wins"
    else:
        key = f"{game_type}_rounds"
    await ctx.send(f"game_type = {game_type}, key = {key}")
    return bot.setting_service.get_setting_by_name(guild_id=guild.id, setting_key=key)

async def _execute_veto(ctx, game: Game, game_to_wins:str, map_name:str):
    guild = ctx.guild
    vetoes = bot.veto_service.get_all_vetoes_by_game(guild_id=guild.id, game_id=game.id)
    picks = bot.pick_service.get_all_picks_by_game(guild_id=guild.id, game_id=game.id)

    team_one = bot.team_service.get_team_by_id(team_id=game.team_one_id)
    team_two = bot.team_service.get_team_by_id(team_id=game.team_two_id)
    order_veto = len(vetoes)
    order_pick = len(picks)
    all_order = order_veto + order_pick

    # Get remaining maps
    map_names = [veto.map_name for veto in vetoes]
    map_names += [pick.map_name for pick in picks]
    remaining_maps = [map_ for map_ in map_pool if map_ not in map_names]

    if map_name not in remaining_maps:
        await ctx.send(f"This map was already vetoed or picked or is not in the map pool. Please select one of {remaining_maps}.")
        return

    if (all_order > 6):
        await ctx.send("All vetoes have been executed in this game.")
        return
    if (all_order % 2 == 0): # Have to be done by team 1
        current_team = team_one
        next_team = team_two
    else:
        current_team = team_two
        next_team = team_one
    
    role_name = f"{current_team.name}_captain"
    roles = ctx.author.roles
    if role_name not in [role.name for role in roles]:
        message = f"You are not the captain of {current_team.name}."
        await ctx.send(message)
        return  
    
    veto = Veto(order_veto=all_order + 1, game_id=game.id, team_id=current_team.id, map_name=map_name, guild_id=guild.id)
    if game_to_wins == "bo1":
        await ctx.send(f"{current_team.name} vetoed {map_name}")
        if all_order + 1 < 6: # Still vetoing
            await ctx.send(f"{next_team.name} time to veto.")
    elif game_to_wins == "bo3":
        if all_order == 2 or all_order == 3: # pick turn
            await ctx.send(f"Is pick time!")
            return
        await ctx.send(f"{team_one.name} vetoed {map_name}")
        if all_order + 1 == 2 or all_order + 1 == 3: # time to pick
            await ctx.send(f"{next_team.name} time to pick.")
        elif all_order + 1 < 6:
            await ctx.send(f"{next_team.name} time to veto.")
    elif game_to_wins == "bo5":
        if all_order + 1 > 2:
            await ctx.send(f"Is pick time!")
            return
        await ctx.send(f"{team_one.name} vetoed {map_name}")
        if all_order + 1 == 1:
            await ctx.send(f"{next_team.name} time to veto.")
        elif all_order + 1 < 6:
            await ctx.send(f"{next_team.name} time to pick.")
    bot.veto_service.create_veto(veto)

    if all_order + 1 == 6: # Remaining map is the decider
        map_names.append(map_name)
        remaining_maps = [map_ for map_ in map_pool if map_ not in map_names]
        pick = Pick(order_pick=all_order + 2, game_id=game.id, team_id=-1, map_name=remaining_maps[0], guild_id=guild.id)
        bot.pick_service.create_pick(pick)
        await ctx.send(f"Decider will be {remaining_maps[0]}.")
        await _create_game_maps(ctx, game=game)
        
    public_channel = bot.get_channel(game.game_channel_id)
    embed = await _game_embed(ctx, game)
    if public_channel:
        try:
            msg = await public_channel.fetch_message(game.public_game_message_id)
            await msg.edit(embed=embed)
        except Exception as e:
            logger.error(f"Failed to update message: {e}")
            await ctx.send(f"⚠️ Pick added but failed to update display: {e}")

async def _execute_pick(ctx, game: Game, game_to_wins:str, map_name:str):
    guild = ctx.guild
    vetoes = bot.veto_service.get_all_vetoes_by_game(guild_id=guild.id, game_id=game.id)
    picks = bot.pick_service.get_all_picks_by_game(guild_id=guild.id, game_id=game.id)

    team_one = bot.team_service.get_team_by_id(team_id=game.team_one_id)
    team_two = bot.team_service.get_team_by_id(team_id=game.team_two_id)
    order_veto = len(vetoes)
    order_pick = len(picks)
    all_order = order_veto + order_pick

    # Get remaining maps
    map_names = [veto.map_name for veto in vetoes]
    map_names += [pick.map_name for pick in picks]
    remaining_maps = [map_ for map_ in map_pool if map_ not in map_names]

    if map_name not in remaining_maps:
        await ctx.send(f"This map was already vetoed or picked or is not in the map pool. Please select one of {remaining_maps}.")
        return

    if (all_order > 6):
        await ctx.send("All picks have been executed in this game.")
        return
    if (all_order % 2 == 0): # Have to be done by team 1
        current_team = team_one
        next_team = team_two
    else:
        current_team = team_two
        next_team = team_one

    role_name = f"{current_team.name}_captain"
    roles = ctx.author.roles
    if role_name not in [role.name for role in roles]:
        message = f"You are not the captain of {current_team.name}."
        await ctx.send(message)
        return  

    pick = Pick(order_pick=all_order + 1, game_id=game.id, team_id=current_team.id, map_name=map_name, guild_id=guild.id)
    if game_to_wins == "bo1":
        await ctx.send(f"No picks on bo1 have to be assigned.")
        return
    elif game_to_wins == "bo3":
        if all_order != 2 and all_order != 3: # pick turn
            await ctx.send(f"Is veto time!")
            return
        await ctx.send(f"{team_one.name} picked {map_name}")
        if all_order + 1 == 2 or all_order + 1 == 3: # time to pick
            await ctx.send(f"{next_team.name} time to pick.")
        elif all_order + 1 < 6:
            await ctx.send(f"{next_team.name} time to veto.")
    elif game_to_wins == "bo5":
        if all_order + 1 < 2:
            await ctx.send(f"Is veto time!")
            return
        await ctx.send(f"{team_one.name} vetoed {map_name}")
        if all_order + 1 == 1:
            await ctx.send(f"{next_team.name} time to veto.")
        elif all_order + 1 < 6:
            await ctx.send(f"{next_team.name} time to pick.")
    bot.pick_service.create_pick(pick)

    if all_order + 1 == 6: # Remaining map is the decider
        map_names.append(map_name)
        remaining_maps = [map_ for map_ in map_pool if map_ not in map_names]
        pick = Pick(order_pick=all_order + 2, game_id=game.id, team_id=-1, map_name=remaining_maps[0], guild_id=guild.id)
        bot.pick_service.create_pick(pick)
        await ctx.send(f"Decider will be {remaining_maps[0]}.")
        await _create_game_maps(ctx, game=game)
        
    public_channel = bot.get_channel(game.game_channel_id)
    embed = await _game_embed(ctx, game)
    if public_channel:
        try:
            msg = await public_channel.fetch_message(game.public_game_message_id)
            await msg.edit(embed=embed)
        except Exception as e:
            logger.error(f"Failed to update message: {e}")
            await ctx.send(f"⚠️ Pick added but failed to update display: {e}")
   
async def _game_embed(ctx, game: Game) -> discord.Embed:
    guild = ctx.guild

    game_to_wins = await _get_game_to_wins(ctx, game)
    
    team_one = bot.team_service.get_team_by_id(game.team_one_id)
    team_two = bot.team_service.get_team_by_id(game.team_two_id)
    vetoes = bot.veto_service.get_all_vetoes_by_game(guild_id=guild.id, game_id=game.id)
    picks = bot.pick_service.get_all_picks_by_game(guild_id=guild.id, game_id=game.id)
    game_maps = bot.game_map_service.get_all_game_maps_by_game(guild_id=guild.id, game_id=game.id)

    embed = discord.Embed(title=f"{team_one.name} vs {team_two.name} picks, bans and maps", color=discord.Color.blue())
    embed.description = f"Game between {team_one.name} vs {team_two.name} of type {game_to_wins.value}.\n"
    
    # Get picks and bans order
    # Normalize both to a unified list with a common 'order'
    combined = [
        {"type": "veto", "order": veto.order_veto, "team_id": veto.team_id, "object": veto}
        for veto in vetoes
    ] + [
        {"type": "pick", "order": pick.order_pick, "team_id": pick.team_id, "object": pick}
        for pick in picks
    ]

    # Sort by order
    combined_sorted = sorted(combined, key=lambda x: x["order"])
    text = ""
    for entry in combined_sorted:
        if entry['team_id'] == team_one.id:
            text += f"{entry['order']}.- {team_one.name} {entry['type'].capitalize()} {entry['object'].map_name}.\n"
        elif entry['team_id'] == team_two.id:
            text += f"{entry['order']}.- {team_two.name} {entry['type'].capitalize()} {entry['object'].map_name}.\n"
        else:
            text += f"{entry['order']}.- Decider map will be {entry['object'].map_name}."
    if len(combined_sorted) == 0:
        text = "No picks and bans already."
    embed.add_field(name="Picks and bans", value=text, inline=False)
    
    # Set game maps
    text = ""
    bot.game_map_service.get_all_game_maps_by_game(guild_id=guild.id, game_id=game.id)
    for game_map in game_maps:
        if game_map.team_id_winner == team_one.id:
            text += f"{game_map.game_number}.- {team_one.name} won {game_map.map_name}.\n"
        elif game_map.team_id_winner == team_two.id:
            text += f"{game_map.game_number}.- {team_two.name} won {game_map.map_name}.\n"
        else:
            text += f"{game_map.game_number}.- {game_map.map_name} have not been played.\n"
    if len(game_maps) == 0:
        text = "No game maps picked already."
    embed.add_field(name="Game maps", value=text, inline=False)

    return embed

async def _create_game_maps(ctx, game: Game) -> list[GameMap]:
    guild = ctx.guild
    picks = bot.pick_service.get_all_picks_by_game_ordered(guild_id=guild.id, game_id=game.id)
    i = 1
    game_maps = []
    for pick in picks:
        game_map = GameMap(game_number=i, map_name=pick.map_name, game_id=game.id, team_id_winner=-1, guild_id=guild.id)
        game_map.id = bot.game_map_service.create_game_map(game_map)
        game_maps.append(game_map)
        i = i + 1
    return game_maps

async def _game_summary(ctx, game: Game):
    public_channel = bot.get_channel(game.game_channel_id)
    embed = await _game_embed(ctx, game)
    if public_channel:
        try:
            msg = await public_channel.fetch_message(game.public_game_message_id)
            await msg.edit(embed=embed)
        except Exception as e:
            logger.error(f"Failed to update message: {e}")
            await ctx.send(f"⚠️ Pick added but failed to update display: {e}")

async def _set_result(ctx, game: Game, team_number: int, map_name: str):
    if game.team_winner > 0:
        await ctx.send("The winner have been already setted.")
        return
    team_one = bot.team_service.get_team_by_id(game.team_one_id)
    team_two = bot.team_service.get_team_by_id(game.team_two_id)
    guild = ctx.guild
    if team_number == 1:
        team_winner = team_one
        team_looser = team_two
    elif team_number == 2:
        team_looser = team_one
        team_winner = team_two
    else:
        await ctx.send(f"Winner must be set as 1 if winner is {team_one.name} or 2 if winner is {team_two.name}.")
        return
    
    game_map = bot.game_map_service.get_game_map_by_game_and_map_name(guild_id=guild.id, game_id=game.id, map_name=map_name)
    if game_map == None:
        await ctx.send(f"The map {map_name} is not one of the game.")
        return
    game_map.team_id_winner = team_winner.id
    bot.game_map_service.update_game_map(game_map)
    await ctx.send(f"{team_winner.name} won map number {game_map.game_number} played in {map_name}.")

    game_maps = bot.game_map_service.get_all_game_maps_by_game(guild_id=guild.id, game_id=game.id)
    team_one_wins = 0
    team_two_wins = 0
    for game_map in game_maps:
        if game_map.team_id_winner == team_one.id:
            team_one_wins = team_one_wins + 1
        elif game_map.team_id_winner == team_two.id:
            team_two_wins = team_two_wins + 1
    
    await ctx.send(f"team_one_wins={team_one_wins} - team_two_wins = {team_two_wins}")

    games_to_wins = await _get_game_to_wins(ctx, game)
    await ctx.send(f"games_to_wins={games_to_wins.value}")
    game_winner = None
    if games_to_wins.value == "bo1":
        if team_one_wins >= 1:
            game_winner = team_one
        elif team_two_wins >= 1:
            game_winner = team_two
    elif games_to_wins.value == "bo3":
        await ctx.send("is bo3")
        if team_one_wins >= 2:
            game_winner = team_one
        elif team_two_wins >= 2:
            game_winner = team_two
    elif games_to_wins.value == "bo5":
        if team_one_wins >= 3:
            game_winner = team_one
        elif team_two_wins >= 3:
            game_winner = team_two
    
    if game_winner is not None:
        await ctx.send(f"The winner of the game is {game_winner.name}.")
        game.team_winner = game_winner.id
        bot.game_service.update_game(game=game)
        await _game_summary(ctx, game)
        if "swiss_" in game.game_type:
            team_winner.swiss_wins = team_winner.swiss_wins + 1
            team_looser.swiss_losses = team_looser.swiss_losses + 1
            if team_winner.swiss_wins >= 3:
                team_winner.is_quarterfinalist = True
        if game.game_type == "quarterfinal":
            team_winner.is_semifinalist = True
        if game.game_type == "semifinal":
            team_winner.is_finalist = True
            team_looser.is_third_place = True

        bot.team_service.update_team(team_winner)
        bot.team_service.update_team(team_looser)
        
        voice_channel_team_one_name = team_one.name
        voice_channel_team_one = discord.utils.get(guild.voice_channels, name=voice_channel_team_one_name)
        if voice_channel_team_one:
            await voice_channel_team_one.delete()
        voice_channel_team_two_name = team_two.name
        voice_channel_team_two = discord.utils.get(guild.voice_channels, name=voice_channel_team_two_name)
        if voice_channel_team_two:
            await voice_channel_team_two.delete()

def main():
    try:
        logging.info("Starting bot initialization...")
        
        load_dotenv()
        logging.info(f"TOKEN: {os.environ['DISCORD_BOT_TOKEN']}")
        setup_database()
        
        bot.run(os.environ["DISCORD_BOT_TOKEN"])
    except KeyError:
        logging.critical("Missing DISCORD_BOT_TOKEN in environment variables")
    except Exception as e:
        logging.critical(f"Fatal error: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    main()