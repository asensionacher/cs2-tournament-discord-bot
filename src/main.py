import json
from PIL import Image, ImageDraw, ImageFont
import os
import logging
from logging.handlers import RotatingFileHandler
import datetime
from dotenv import load_dotenv
import random
from fastapi import FastAPI, Request
import discord
from discord.ext import commands
from discord.ui import View, Button
import re

import asyncio
from threading import Thread

import requests
import subprocess
from rcon.source import rcon

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
import uvicorn
import uuid

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

# API for MatchZy events
app = FastAPI()

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')

@bot.command()
@discord.ext.commands.has_role("admin")
async def help(ctx):
    """
    Show help information based on user role
    Format: !help
    """

    # Commands information
    help_msg = (
        "🔧 **Initial Setup**\n"
        "• Send `!start` to create all necessary roles, categories and channels\n\n"
        "🎮 **CS2 Tournament Bot Help**\n\n"
        "⚠️ Please use the #admin channel for all admin commands!\n\n"
        "• `!start` - Initialize server setup (roles, categories, channels)\n\n"
        "• `!get_settings` - Get all settings for the server\n\n"
        "• `!create_team <team_name>` - Create a new team\n"
        "• `!add_player <team_name> <nickname> <steamid> <role>` - Add player to team\n"
        "  Roles can be: captain/coach/player\n"
        "• `!delete_team <team_name>` - Delete team\n"
        "• `!delete_player <nickname>` - Delete player\n\n"
        "• `!all_teams_created` - Lock teams and start tournament\n"
        "• `!finish_round` - Complete current round and start next\n\n"
        "• `!start_live_game` - Sends all the information to the CS2/matchzy server.\n\n"
        "**Admin Testing:** - ONLY USE FOR TESTING.\n"
        "• `!mock_teams` - Create mock teams until 16 teams\n"
        "• `!autovetoautoresults` - Auto veto and set results\n"
        "• `!delete_games <game_type>` - Delete all games from a round\n"
        "• `!im_all_teams_captain` - Make my user captain of all teams\n"
    )
    await ctx.send(help_msg)

    # Get admin channel id if exists
    admin_channel = bot.channel_service.get_channel_by_name(channel_name="admin", guild_id=ctx.guild.id)
    admin_channel_text = "#admin"
    if admin_channel is not None:
        admin_channel_text = f"<#{admin_channel.channel_id}>"
    
    # How to use the bot help
    help_msg = (
        "**ℹ️How to use the bot:**\n"
        "1. Execute the bot with a `.env` file with all environment variables set. If not, the bot will not report automatically the results and vetoes.\n"
        "2. Execute `!start` for all the categories and channels being created. Optionally remove initial channels in the server.\n"
        f"3. Go to the {admin_channel_text} channel and create teams and players.\n"
        "4. Whith all teams created, execute `!all_teams_created`. Be sure that before executing this, all settings have been setted up.\n"
        "5. Swiss stage round 1 games have been created. Go to the first admin channel game you want to start.\n"
        "   • If you have setted the all the environment variables and you want the server to be autosetted, execute `!start_live_game`\n"
        "   • If not, you have to send events manually to the bot for veto, picking and results (NOT RECOMMENDED).\n"
        f"6. Once all games have been finished, execute `!finish_round` in the {admin_channel_text} channel."
    )
    await ctx.send(help_msg)

@bot.command()
async def start(ctx):
    """
    Initialize the server setup.
    It creates all categories, channels and settings.
    Format: !start
    """
    guild = ctx.guild
    try:
        # No matter if already started, but roles should not be created twice.
        start_executed_setting = bot.setting_service.get_setting_by_name(
            setting_key="start_executed", guild_id=guild.id)
        if start_executed_setting is not None:
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
            "start_executed": {"value": "true"},
            "all_teams_created": {"value": "false"},
        }

        for key, config in settings.items():
            await _create_server_setting(ctx, key, config["value"])

    except Exception as e:
        await ctx.send(f"Error during start command: {str(e)}")
        logging.error(f"Error during start command: {e}", exc_info=True)

@bot.command()
@discord.ext.commands.has_role("admin")
async def executercon(ctx, *command: str):
    """
    Executes rcon command into server
    Format: !executercon <command>
    - command: Multiple words (e.g., "changemap de_dust2)
    """
    # Check if values are setted
    if not ctx.channel.name == "admin":
        await ctx.send("Must be executed from admin channel")
        return
    if (bot.SERVER_PORT is None or bot.SERVER_IP is None or bot.RCON_PASSWORD is None):
        await ctx.send(
            """ 
            Environment variables SERVER_IP, SERVER_PORT, RCON_PASSWORD have to be setted for executing rcon commands.
            """
        )
        return
    response = await _execute_rcon(command)
    await ctx.send(response)

@bot.command()
@discord.ext.commands.has_role("admin")
async def create_team(ctx, *name: str):
    """
    Create a new team
    Format: !create_team <team_name>
    - team_name: Single word (e.g., "Iberian_Soul)
    If it is a word separated by spaces, a '_' will be replaced
    """
    # Join multiple words and replace spaces with underscore only if multiple words
    name = " ".join(name)
    if " " in name:
        name = name.replace(" ", "_")
    if not ctx.channel.name == "admin":
        await ctx.send("Must be executed from admin channel")
        return
    try:
        await _create_team(ctx, name)
    except Exception as e:
        logging.error(f"Error during create_team command: {e}")
        await ctx.send(f"❌ Error during create_team command: {e}")

@bot.command()
@discord.ext.commands.has_role("admin")
async def add_player(ctx, team_name: str, nickname: str, steamid: str, role_name:str):
    """
    Adds a player with nickname, SteamID (numbers only), and role to a team.
    Format: !add_player <team_name> <nickname> <steamid> <role_name>
    - team_name: Single-word (e.g., "Natus Vincere")
    - nickname: Single word (e.g., "s1mple")
    - steamid: Numbers only (e.g., "123456789")
    - role_name: captain/player/coach
    """
    
    if not ctx.channel.name == "admin":
        await ctx.send("Must be executed from admin channel")
        return

    try:
        await _add_player(ctx, team_name=team_name, nickname=nickname, role_name=role_name, steamid=steamid)
    except Exception as e:
        logging.error(f"Error during add_player command: {e}")
        await ctx.send(f"❌ Error during add_player command: {e}")

@bot.command()
@discord.ext.commands.has_role("admin")
async def delete_player(ctx, nickname: str):
    """
    Deletes a player with nickname.
    Format: !delete_player <nickname>
    - nickname: Single word (e.g., "s1mple")
    """

    if not ctx.channel.name == "admin":
        await ctx.send("Must be executed from admin channel")
        return
    try:
        await _delete_player(ctx, nickname=nickname)
    except Exception as e:
        logging.error(f"Error during delete_player command: {e}")
        await ctx.send(f"❌ Error during delete_player command: {e}")

@bot.command()
@discord.ext.commands.has_role("admin")
async def delete_team(ctx, *name: str):
    """
    Delete a single team
    Format: !delete_team <team_name>
    - team_name Single word (e.g., "Iberian_Soul")
    """
    # Join multiple words and replace spaces with underscore only if multiple words
    name = " ".join(name)
    if " " in name:
        name = name.replace(" ", "_")

    
    if not ctx.channel.name == "admin":
        await ctx.send("Must be executed from admin channel")
        return
        
    try:
        await _delete_team(ctx, name)
    except Exception as e:
        logging.error(f"Error during delete_team command: {e}")
        await ctx.send(f"❌ Error during delete_team command: {e}")

@bot.command()
@discord.ext.commands.has_role("admin")
async def all_teams_created(ctx):
    """
    Starts the tournament once all teams are created
    Format: !all_teams_created
    """
    guild = ctx.guild
    all_teams_created_setting = bot.setting_service.get_setting_by_name(
        setting_key="all_teams_created", guild_id=guild.id)
    if all_teams_created_setting is not None:
        if all_teams_created_setting.value == "true":
            await ctx.send("Tournament already started!")
            return
    if not ctx.channel.name == "admin":
        await ctx.send("Must be executed from admin channel")
        return
    
    try:
        await _create_server_setting(ctx, key="all_teams_created", value="true")
        await ctx.send("All teams created, tournament started! Remember, you cannot change server settings now.")
        await _set_new_round(ctx)
    except Exception as e:
        logging.error(f"Error during all_teams_created command: {e}")
        await ctx.send(f"❌ Error during all_teams_created command: {e}")

@bot.command()
@discord.ext.commands.has_role("admin")
async def mock_teams(ctx):
    """
    Create mock teams until complete the all the 16 teams
    NOTE: CAREFUL!! Use this only for testing
    Format: !mock_teams
    """
    guild = ctx.guild
    
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
            logging.info(f"Creating {team_name} players:")
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
                await _add_player(ctx, team_name=team_name, nickname=nickname, role_name=role, steamid=steamid)           
    except Exception as e:
        logging.error(f"Error during mock_teams command: {e}")
        await ctx.send(f"❌ Error during mock_teams command: {e}")

@bot.command()
@discord.ext.commands.has_role("admin")
async def finish_round(ctx):
    """
    Checks if all matches from current round are finished and if true creates the new random games for the next round.
    Format: !finish_round
    """
    if not ctx.channel.name == "admin":
        await ctx.send("Must be executed from admin channel")
        return
    else:
        await _set_new_round(ctx)

@bot.command()
@discord.ext.commands.has_role("admin")
async def delete_games(ctx, game_type:str):
    """
    Delete all games from a round and its channels.
    Format: !delete_games <game_type>
        - game_type: Single word (e.g., "quarterfinals")
    """
    try:
        if not ctx.channel.name == "admin":
            await ctx.send("Must be executed from admin channel")
            return
        else:
            if game_type not in ["swiss_1", "swiss_2_high", "swiss_2_low", "swiss_3_high", "swiss_3_low", "swiss_3_mid", "quarterfinal", "semifinal", "final", "third_place"]:
                await ctx.send("❌ Invalid game type name! Must be one of: swiss_1, swiss_2_high, swiss_2_low, swiss_3_high, swiss_3_low, swiss_3_mid, quarterfinal, semifinal, final, third_place")
                return
            # Delete all games and channels from the specified round
            games = bot.game_service.get_games_by_type(game_type=game_type, guild_id=ctx.guild.id)
            if not games:
                await ctx.send(f"No games found for {game_type}.")
                return  
            for game in games:
                public_channel = bot.get_channel(game.game_channel_id)
                await public_channel.delete()
                admin_channel = bot.get_channel(game.admin_game_channel_id)
                await admin_channel.delete()
                voice_channel_team_one = bot.get_channel(game.voice_channel_team_one_id)
                await voice_channel_team_one.delete()
                voice_channel_team_two = bot.get_channel(game.voice_channel_team_two_id)
                await voice_channel_team_two.delete()
                # Delete game from database
                bot.game_service.delete_game_by_id(id=game.id)
            await ctx.send(f"All games from {game_type} deleted successfully.")
    except Exception as e:
        logging.error(f"Error during delete_games command: {e}")
        await ctx.send(f"❌ Error during delete_games command: {e}")

@bot.command()
@discord.ext.commands.has_role("admin")
async def im_all_teams_captain(ctx):
    """
    Make my user captain of all teams.
    Format: !im_all_teams_captain
    NOTE: CAREFUL!! Use this only for testing
    """
    try:
        if not ctx.channel.name == "admin":
            await ctx.send("Must be executed from admin channel")
            return
        else:
            guild = ctx.guild
            user = ctx.author
            teams = bot.team_service.get_all_teams(guild_id=guild.id)
            for team in teams:
                role_name = f"{team.name}_captain"
                role = discord.utils.get(guild.roles, name=role_name)
                if role is None:
                    await ctx.send(f"❌ Role {role_name} not found.")
                    return
                # Add user to the captain role
                await user.add_roles(role)
            await ctx.send(f"User {user.name} set as captain for all teams.")
    except Exception as e:
        logging.error(f"Error during im_all_teams_captain command: {e}")
        await ctx.send(f"❌ Error during im_all_teams_captain command: {e}")

@bot.command()
@discord.ext.commands.has_role("admin")
async def start_live_game(ctx):
    """
    Start the game. 
    Format: !start_map
    """
    guild = ctx.guild
    channel_id = ctx.channel.id
    # Get game based on admin game where channel has been created
    game = bot.game_service.get_game_by_admin_game_channel_id(admin_game_channel_id=channel_id)
    admin_game_channel = bot.get_channel(channel_id)
    if game is None:
        await ctx.send("This must be sent from a admin game channel.")
        return
    
    # Environment variables WEBHOOK_BASE_URL, SERVER_IP, SERVER_PORT, RCON_PASSWORD have to be setted
    if (bot.WEBHOOK_BASE_URL is None or bot.SERVER_IP is None or bot.RCON_PASSWORD is None or bot.SERVER_PORT is None):
        await ctx.send(""" 
            Environment variables WEBHOOK_BASE_URL, SERVER_IP, SERVER_PORT, RCON_PASSWORD have to be setted for live games.
            Please set the enviroment variables or start manually the game.
            """)
        return

    json = await _get_matchzy_values(game=game)

    try:
        # Save JSON to local file
        os.makedirs('/usr/src/app/match_configs', exist_ok=True)
        filename = f"/usr/src/app/match_configs/{game.id}.json"
        with open(filename, 'w') as f:
            f.write(json)
        
        file = discord.File(filename, filename=f"match_configs_game_{game.id}.json")
        await admin_game_channel.send("Match config:", file=file)
        rcons = {
            "matchzy_remote_log_url": {'matchzy_loadmatch_url', f"\"{bot.WEBHOOK_BASE_URL}/match_configs/{game.id}.json\""},
            "matchzy_remote_log_url": {'matchzy_remote_log_url', f"\"{bot.WEBHOOK_BASE_URL}/match_logs/{game.id}\""},
            "matchzy_demo_upload_url": {'matchzy_demo_upload_url', f"\"{bot.WEBHOOK_BASE_URL}/match_demos/{game.id}\""},
            "matchzy_minimum_ready_required": {'matchzy_minimum_ready_required', '1'},
            "matchzy_chat_prefix": {'matchzy_chat_prefix', "[{Green}" + bot.TOURNAMENT_NAME + "{Default}]"},
            "matchzy_admin_chat_prefix": {'matchzy_admin_chat_prefix', "[{Red}Admin{Default}]"},
            "matchzy_hostname_format": {'matchzy_hostname_format', "\"\""},
            "matchzy_knife_enabled_default": {'matchzy_knife_enabled_default', "true"},
            "matchzy_kick_when_no_match_loaded": {'matchzy_kick_when_no_match_loaded', "true"},
            "matchzy_enable_damage_report": {'matchzy_enable_damage_report', 'false'}
        }
        for key, command in rcons.items():
            logging.info(f"Executing rcon command `{command}`")
            response = await _execute_rcon(command)
            if response is not None and response != "":
                logging.info(response)
                
    except Exception as e:
        logging.error(f"Error saving match config: {e}")
        await ctx.send(f"❌ Error saving match config. Start manually the game on the server: {e}")

@bot.command()
@discord.ext.commands.has_role("admin")
async def autovetoautoresults(ctx):
    """
    autovetoautoresults 
    Format: !autovetoautoresults
    NOTE: CAREFUL!! Use this only for testing
    """
    try:
        guild = ctx.guild
        response = []
        for r in await _auto_veto(guild_id=guild.id):
            response.append(r)
        for r in await _auto_result(guild_id=guild.id):
            response.append(r) 

        # Create directory if doesn't exist
        os.makedirs('response', exist_ok=True)
        
        # Write response to file
        filename = f"response/response_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.sh"
        with open(filename, 'w') as f:
            for line in response:
                f.write(f"{line}\n")

        # Send file to channel
        file = discord.File(filename)
        await ctx.send("Response file:", file=file)

    except Exception as e:
        logging.error(f"Error during response_to_file command: {e}")
        await ctx.send(f"❌ Error generating response file: {e}")
        

async def _get_matchzy_values(game: Game) -> str:
    """
    Get json for configurate the Matchzy game
    More info at https://shobhit-pathak.github.io/MatchZy/match_setup/
    """

    match_id = str(game.id)
    team_one = bot.team_service.get_team_by_id(game.team_one_id) 
    team_two = bot.team_service.get_team_by_id(game.team_two_id) 

    players_team_one = bot.player_service.get_players_by_team_id(team_one.id)
    players_team_two = bot.player_service.get_players_by_team_id(team_two.id)

    game_to_wins = await _get_game_to_wins(game=game)
    num_maps = int(game_to_wins.replace('bo',''))

    data = {}
    data['matchid'] = match_id

    team1 = {}
    team1['name'] = team_one.name
    players = {}
    for player in players_team_one:
        players[player.steamid] = player.nickname
    team1['players'] = players
    data['team1'] = team1

    team2 = {}
    team2['name'] = team_two.name
    players = {}
    for player in players_team_two:
        players[player.steamid] = player.nickname
    team2['players'] = players
    data['team2'] = team2

    data['num_maps'] = num_maps

    data['maplist'] = bot.MAP_POOL

    map_sides = ["knife", "team1_ct", "team2_ct"]
    data['map_sides'] = map_sides

    data['clinch_series'] = True
    data['skip_veto'] = False

    data['players_per_team'] = 5

    # Return the json with indent for sending it as file
    return json.dumps(data, indent=4)    
    
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

def setup_vars():
    """
    Initialize values from environment values.
    """
    default_map_pool = "inferno,anubis,nuke,ancient,mirage,train,dust2"

    bot.MAP_POOL = os.environ.get("MAP_POOL", default_map_pool).split(',')
    bot.SWISS_DECIDER=os.environ.get("SWISS_DECIDER", "bo3")
    bot.SWISS_NOT_DECIDER=os.environ.get("SWISS_NOT_DECIDER", "bo1")
    bot.QUARTERFINAL_ROUND=os.environ.get("QUARTERFINAL_ROUND", "bo3")
    bot.SEMIFINAL_ROUND=os.environ.get("SEMIFINAL_ROUND", "bo3")
    bot.FINAL_ROUND=os.environ.get("FINAL_ROUND", "bo5")
    bot.THIRD_PLACE_ROUND=os.environ.get("THIRD_PLACE_ROUND", "bo3")
    bot.TOURNAMENT_NAME=os.environ.get("TOURNAMENT_NAME", "MY_TOURNAMENT")
    bot.WEBHOOK_BASE_URL=os.environ.get("WEBHOOK_BASE_URL", None)
    bot.SERVER_IP=os.environ.get("SERVER_IP", None)
    bot.SERVER_PORT=os.environ.get("SERVER_PORT", None)
    bot.RCON_PASSWORD=os.environ.get("RCON_PASSWORD", None)

async def _create_team(ctx, name:str) -> Team:
    """
    Creates a new team based on the name.
    """
    guild = ctx.guild
    discord_info_category = discord.utils.get(guild.categories, name="Info")
    discord_teams_channel_id = (bot.channel_service.get_channel_by_name(channel_name="teams", guild_id=guild.id)).channel_id
    discord_teams_channel = bot.get_channel(discord_teams_channel_id)
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
    team.id = bot.team_service.create_team(team=team)

    logging.info(f"Team {name} created in guild {guild.name}")
    await ctx.send(f"Created team {name}")

    # Create roles
    for role_type in ["captain", "player", "coach"]:
        server_role_name = f"{name}_{role_type}"
        await _create_server_role(ctx, server_role_name=server_role_name)
    return team

async def _add_player(ctx, team_name:str, nickname:str, role_name:str, steamid:str) -> Player:
    """
    Adds a player to a team.
    """
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
    discord_info_category = discord.utils.get(guild.categories, name="Info")
    discord_teams_channel = discord.utils.get(guild.text_channels, name="teams", category=discord_info_category)
    if discord_teams_channel is None:
        await ctx.send("There is no teams channel, please use !start")
        return
    team = bot.team_service.get_team_by_name(name=team_name, guild_id=guild.id)
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
        count_captains = sum(1 for p in players if p.role_name == role_name)
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

async def _delete_player(ctx, nickname:str):
    """
    Delets a player from a team.
    """
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
    player.id = bot.player_service.delete_player_by_id(id=player.id)
    await ctx.send(f"Player {nickname} deleted successfully.")

    players = bot.player_service.get_players_by_team_id(team_id=team.id)
    embed = await _create_team_embed(team_name=team.name, members=players)
    discord_team_message = await discord_teams_channel.fetch_message(team.discord_message_id)
    await discord_team_message.edit(embed=embed)
    return    

async def _delete_team(ctx, name:str):
    """
    Deletes a team and its players.
    """
    guild = ctx.guild
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

    captain_role = discord.utils.get(guild.roles, name=f"{name}_captain")
    player_role = discord.utils.get(guild.roles, name=f"{name}_player")
    coach_role = discord.utils.get(guild.roles, name=f"{name}_coach")

    await captain_role.delete()
    await player_role.delete()
    await coach_role.delete()

    players = bot.player_service.get_players_by_team_id(team_id=team.id)
    for player in players:
        bot.player_service.delete_player_by_id(id=player.id)

    logging.info(team.name)
    team.id = bot.team_service.delete_team_by_id(id=team.id)

    logging.info(f"Team {name} deleted in guild {guild.name}")
    await ctx.send(f"Deleted team {name}")
        
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
        channel = Channel(guild_id=guild.id, channel_name=channel_name, channel_id=discord_text_channel.id)
        bot.channel_service.create_channel(channel=channel)
    else:
        await ctx.send(f"Channel {channel_name} already created")
    return discord_text_channel

async def _create_server_setting(ctx, key:str, value:str) -> Setting:
    """
    Create a server setting if it don't exists
    """
    guild = ctx.guild
    all_teams_created_setting = bot.setting_service.get_setting_by_name(guild_id=guild.id, setting_key="all_teams_created")
    if all_teams_created_setting is not None:
        if all_teams_created_setting.value == "true":
            await ctx.send("❌ You cannot change server settings once the tournament has started.")
            return None
        
    setting = bot.setting_service.get_setting_by_name(guild_id=guild.id, setting_key=key)

    if setting is not None:
        setting.value = value
        bot.setting_service.update_setting(setting=setting)
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
    admin_channel = await _create_text_channel(ctx, channel_name=admin_channel_name, overwrites=admin_overwrites, category=category)
    await admin_channel.send(f"This channel will be used for communicating between org and teams on this game, remember that only admins and users with role {team_one.name}_captain and {team_two.name}_captain can write in this channel.")

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
    channel = Channel(guild_id=guild.id, channel_name=team_one.name, channel_id=voice1.id)
    bot.channel_service.create_channel(channel=channel)

    voice2 = await category.create_voice_channel(team_two.name, overwrites=voice2_overwrites)
    channel = Channel(guild_id=guild.id, channel_name=team_two.name, channel_id=voice2.id)
    bot.channel_service.create_channel(channel=channel)

    embed = await _game_embed(game)
    msg = await public_channel.send(embed=embed)

    game.admin_game_channel_id = admin_channel.id
    game.game_channel_id = public_channel.id
    game.public_game_message_id = msg.id
    game.voice_channel_team_one_id = voice1.id
    game.voice_channel_team_two_id = voice2.id
    game.admin_pick_veto_button_message_id = -1
    game.result_button_message_id = -1

    game.id = bot.game_service.create_game(game)

    embed = discord.Embed(title=f"{team_one.name} vs {team_two.name} picks, bans and maps", color=discord.Color.blue())
    game_to_wins = await _get_game_to_wins(game=game)
    embed.description = f"Game between {team_one.name} vs {team_two.name} of type {game_to_wins}.\n"
    
    embed.add_field(name="Waiting", value=f"Waiting the admin to execute `!start_live_game`", inline=False)
    msg = await admin_channel.send(embed=embed)
    bot.game_service.update_game(game)

async def _create_games(ctx, game_type: str):
    """
    Get games and create them
    """
    games = []
    guild = ctx.guild
    if game_type == "swiss_1":
        teams = bot.team_service.get_all_teams(guild_id=guild.id)
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
        await _create_game(ctx, game, category=discord_game_category)
    await _tournament_summary(guild_id=guild.id)

async def _tournament_summary(guild_id: int):
    """
    Creates tournament summary
    """
    game_rounds = [
        ("swiss_1", "Swiss round 1 (0 Wins, 0 Losses)"),
        ("swiss_2_high", "Swiss round 2 high (1 Win, 0 Losses)"),
        ("swiss_2_low", "Swiss round 2 low (0 Wins, 1 Loss)"),
        ("swiss_3_high", "Swiss round 3 high (2 Wins, 0 Losses)"),
        ("swiss_3_mid", "Swiss round 3 mid (1 Win, 1 Loss)"),
        ("swiss_3_low", "Swiss round 3 low (0 Wins, 2 Losses)"),
        ("swiss_4_high", "Swiss round 4 high (2 Wins, 1 Losses)"),
        ("swiss_4_low", "Swiss round 4 low (1 Win, 2 Losses)"),
        ("swiss_5", "Swiss round 5 (2 Wins, 2 Losses)"),
        ("quarterfinal", "Quarter-final"),
        ("semifinal", "Semi-final"),
        ("third_place", "Third place"),
        ("final", "Final")
    ] 
    discord_summary_channel_id = (bot.channel_service.get_channel_by_name(channel_name="summary", guild_id=guild_id)).channel_id
    discord_summary_channel = bot.get_channel(discord_summary_channel_id)

    for game_round, title in game_rounds:
        embed = discord.Embed(title=title, color=discord.Color.blue())
        games = bot.game_service.get_games_by_type(game_type=game_round, guild_id=guild_id)
        if len(games) > 0:
            text = ""
            for game in games:
                team_one = bot.team_service.get_team_by_id(team_id=game.team_one_id)
                team_two = bot.team_service.get_team_by_id(team_id=game.team_two_id)
                team_one_name = team_one.name
                team_two_name = team_two.name
                game_maps = bot.game_map_service.get_all_game_maps_by_game(guild_id=guild_id, game_id=game.id)
                team_one_wins = 0
                team_two_wins = 0
                for game_map in game_maps:
                    if game_map.team_id_winner == team_one.id:
                        team_one_wins = team_one_wins + 1
                    elif game_map.team_id_winner == team_two.id:
                        team_two_wins = team_two_wins + 1
                games_to_wins = await _get_game_to_wins(game)
                game_winner = None
                if games_to_wins == "bo1":
                    if team_one_wins >= 1:
                        team_one_name = f"✅{team_one_name}"
                        team_two_name = f"{team_two_name}❌"
                    elif team_two_wins >= 1:
                        team_one_name = f"❌{team_one_name}"
                        team_two_name = f"{team_two_name}✅"
                elif games_to_wins == "bo3":
                    if team_one_wins >= 2:
                        team_one_name = f"✅{team_one_name}"
                        team_two_name = f"{team_two_name}❌"
                    elif team_two_wins >= 2:
                        team_one_name = f"❌{team_one_name}"
                        team_two_name = f"{team_two_name}✅"
                elif games_to_wins == "bo5":
                    if team_one_wins >= 3:
                        team_one_name = f"✅{team_one_name}"
                        team_two_name = f"{team_two_name}❌"
                    elif team_two_wins >= 3:
                        team_one_name = f"❌{team_one_name}"
                        team_two_name = f"{team_two_name}✅"

                text += f"・{team_one_name} {team_one_wins}:{team_two_wins} {team_two_name}\n"
            
            embed.add_field(name="Games", value=text, inline=False)
            summary = bot.summary_service.get_summary_by_round_name(guild_id=guild_id, round_name=game_round)
            if summary is None:
                msg = await discord_summary_channel.send(embed=embed)
                summary = Summary(guild_id=guild_id, round_name=game_round, message_id=msg.id)
                bot.summary_service.create_summary(summary=summary)
            else:
                msg = await discord_summary_channel.fetch_message(summary.message_id)
                await msg.edit(embed=embed)

async def _get_game_to_wins(game: Game) -> str:
    """
    Have to return if the game is bo1, bo3 or bo5
    """
    game_type = game.game_type
    if game_type == "swiss_1" or game_type == "swiss_2_high" or game_type == "swiss_2_low" or game_type == "swiss_3_low" or game_type == "swiss_3_mid":
        return bot.SWISS_NOT_DECIDER
    if game_type == "swiss_3_high" or game_type == "swiss_4_high" or game_type == "swiss_4_low" or game_type == "swiss_5":
        return bot.SWISS_DECIDER
    if game_type == "quarterfinal":
        return bot.QUARTERFINAL_ROUND
    if game_type == "semifinal":
        return bot.SEMIFINAL_ROUND
    if game_type == "third_place":
        return bot.THIRD_PLACE_ROUND
    if game_type == "final":
        return bot.FINAL_ROUND

async def _game_embed(game: Game) -> discord.Embed:
    """
    Creates the summary embed for a game
    """

    game_to_wins = await _get_game_to_wins(game)
    
    team_one = bot.team_service.get_team_by_id(game.team_one_id)
    team_two = bot.team_service.get_team_by_id(game.team_two_id)
    vetoes = bot.veto_service.get_all_vetoes_by_game(guild_id=game.guild_id, game_id=game.id)
    picks = bot.pick_service.get_all_picks_by_game(guild_id=game.guild_id, game_id=game.id)
    game_maps = bot.game_map_service.get_all_game_maps_by_game(guild_id=game.guild_id, game_id=game.id)

    embed = discord.Embed(title=f"{team_one.name} vs {team_two.name} picks, bans and maps", color=discord.Color.blue())
    embed.description = f"Game between {team_one.name} vs {team_two.name} of type {game_to_wins}.\n"
    
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
    bot.game_map_service.get_all_game_maps_by_game(guild_id=game.guild_id, game_id=game.id)
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

async def _game_summary(game: Game):
    """
    Creates a game summary
    """
    public_channel = bot.get_channel(game.game_channel_id)
    embed = await _game_embed(game)
    if public_channel:
        try:
            msg = await public_channel.fetch_message(game.public_game_message_id)
            await msg.edit(embed=embed)
        except Exception as e:
            print(f"⚠️ Error on sending msg: {e}")

async def _set_result(game: Game, team_number: int, map_name: str):
    """
    Sets the winner on a game map
    """
    admin_channel = bot.get_channel(game.admin_game_channel_id)

    if game.team_winner > 0:
        await admin_channel.send("The winner have been already setted.")
        return
    team_one = bot.team_service.get_team_by_id(game.team_one_id)
    team_two = bot.team_service.get_team_by_id(game.team_two_id)
    guild_id = game.guild_id
    if team_number == 1:
        team_winner = team_one
        team_looser = team_two
    elif team_number == 2:
        team_looser = team_one
        team_winner = team_two
    else:
        await admin_channel.send(f"Winner must be set as 1 if winner is {team_one.name} or 2 if winner is {team_two.name}.")
        return
    
    game_map = bot.game_map_service.get_game_map_by_game_and_map_name(guild_id=guild_id, game_id=game.id, map_name=map_name)
    if game_map == None:
        await admin_channel.send(f"The map {map_name} is not one of the game.")
        return
    game_map.team_id_winner = team_winner.id
    bot.game_map_service.update_game_map(game_map)
    await admin_channel.send(f"{team_winner.name} won map number {game_map.game_number} played in {map_name}.")

    game_maps = bot.game_map_service.get_all_game_maps_by_game(guild_id=guild_id, game_id=game.id)
    team_one_wins = 0
    team_two_wins = 0
    for game_map in game_maps:
        if game_map.team_id_winner == team_one.id:
            team_one_wins = team_one_wins + 1
        elif game_map.team_id_winner == team_two.id:
            team_two_wins = team_two_wins + 1

    games_to_wins = await _get_game_to_wins(game)
    game_winner = None
    if games_to_wins == "bo1":
        if team_one_wins >= 1:
            game_winner = team_one
        elif team_two_wins >= 1:
            game_winner = team_two
    elif games_to_wins == "bo3":
        if team_one_wins >= 2:
            game_winner = team_one
        elif team_two_wins >= 2:
            game_winner = team_two
    elif games_to_wins == "bo5":
        if team_one_wins >= 3:
            game_winner = team_one
        elif team_two_wins >= 3:
            game_winner = team_two
    
    if game_winner is not None:
        await admin_channel.send(f"The winner of the game is {game_winner.name}.")
        game.team_winner = game_winner.id
        bot.game_service.update_game(game=game)
        await _game_summary(game)
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
        voice_channel_team_one = bot.get_channel(game.voice_channel_team_one_id)
        if voice_channel_team_one:
            await voice_channel_team_one.delete()
            
        voice_channel_team_two = bot.get_channel(game.voice_channel_team_two_id)
        if voice_channel_team_two:
            await voice_channel_team_two.delete()
        await _tournament_summary(guild_id=guild_id)
    
    await _game_summary(game=game)

async def _execute_rcon(*command: str) -> str : 
    """
    Sends rcon command to host
    """
    try:    
        command = ' '.join(command[0])
        response = await rcon(
            command,
            host=bot.SERVER_IP, port=int(bot.SERVER_PORT), passwd=bot.RCON_PASSWORD
        )
        return response
    except Exception as e:
        logging.error(f"Error on execute_rcon: {e}")
        return f"❌ Error on execute_rcon. Start manually the game on the server: {e}"

async def _auto_veto(guild_id: int) -> list:
    """
    Sends auto veto for testing
    """
    # Get all not finished games
    response = []
    games = bot.game_service.get_all_games_not_finished(guild_id=guild_id)
    for game in games:
        games_to_wins = await _get_game_to_wins(game)
        if games_to_wins == "bo1":
            response.append(await _send_veto(matchid=game.id, team="team1", map_name="inferno"))
            response.append(await _send_veto(matchid=game.id, team="team2", map_name="anubis"))
            response.append(await _send_veto(matchid=game.id, team="team1", map_name="train"))
            response.append(await _send_veto(matchid=game.id, team="team2", map_name="dust2"))
            response.append(await _send_veto(matchid=game.id, team="team1", map_name="mirage"))
            response.append(await _send_veto(matchid=game.id, team="team2", map_name="ancient"))
            response.append(await _send_pick(matchid=game.id, team="decider", map_name="nuke", map_number=1))
        elif games_to_wins == "bo3":
            response.append(await _send_veto(matchid=game.id, team="team1", map_name="inferno"))
            response.append(await _send_veto(matchid=game.id, team="team2", map_name="anubis"))
            response.append(await _send_pick(matchid=game.id, team="team1", map_name="train", map_number=1))
            response.append(await _send_pick(matchid=game.id, team="team2", map_name="dust2", map_number=2))
            response.append(await _send_veto(matchid=game.id, team="team1", map_name="mirage"))
            response.append(await _send_veto(matchid=game.id, team="team2", map_name="ancient"))
            response.append(await _send_pick(matchid=game.id, team="decider", map_name="nuke", map_number=3))
        elif games_to_wins == "bo5":
            response.append(await _send_veto(matchid=game.id, team="team1", map_name="inferno"))
            response.append(await _send_veto(matchid=game.id, team="team2", map_name="anubis"))
            response.append(await _send_pick(matchid=game.id, team="team1", map_name="train", map_number=1))
            response.append(await _send_pick(matchid=game.id, team="team2", map_name="dust2", map_number=2))
            response.append(await _send_pick(matchid=game.id, team="team1", map_name="mirage", map_number=3))
            response.append(await _send_pick(matchid=game.id, team="team2", map_name="ancient", map_number=4))
            response.append(await _send_pick(matchid=game.id, team="decider", map_name="nuke", map_number=5))
    return response
    
async def _auto_result(guild_id: int) -> list:
    """
    Sends auto result for testing
    """
    # Get all not finished games
    response = []
    games = bot.game_service.get_all_games_not_finished(guild_id=guild_id)
    for game in games:
        games_to_wins = await _get_game_to_wins(game)
        if games_to_wins == "bo1":
            response.append(await _send_result(matchid=game.id, map_number=0, winner_team="team2"))
        elif games_to_wins == "bo3":
            response.append(await _send_result(matchid=game.id, map_number=0, winner_team="team1"))
            response.append(await _send_result(matchid=game.id, map_number=1, winner_team="team2"))
            response.append(await _send_result(matchid=game.id, map_number=2, winner_team="team1"))
        elif games_to_wins == "bo5":
            response.append(await _send_result(matchid=game.id, map_number=0, winner_team="team1"))
            response.append(await _send_result(matchid=game.id, map_number=1, winner_team="team2"))
            response.append(await _send_result(matchid=game.id, map_number=2, winner_team="team1"))
            response.append(await _send_result(matchid=game.id, map_number=3, winner_team="team1"))
    return response

async def _send_veto(matchid: int, team: str, map_name: str) -> str:
    """
    Sends veto for testing
    """
    data = {}
    data['event'] = "map_vetoed"
    data['matchid'] = matchid
    data['team'] = team
    data['map_name'] = map_name

    url = f"{bot.WEBHOOK_BASE_URL}/match_logs/{matchid}"
    data = json.dumps(data)

    cmd = f"curl -X POST {url} -H \"Content-Type: application/json\" -d '{data}'"
    return cmd

async def _send_pick(matchid: int, team: str, map_name: str, map_number: int) -> str:
    """
    Sends pick for testing
    """
    data = {}
    data['event'] = "map_picked"
    data['matchid'] = matchid
    data['team'] = team
    data['map_name'] = map_name
    data['map_number'] = map_number
    
    url = f"{bot.WEBHOOK_BASE_URL}/match_logs/{matchid}"
    data = json.dumps(data)

    cmd = f"curl -X POST {url} -H \"Content-Type: application/json\" -d '{data}'"
    return cmd

async def _send_result(matchid: int, map_number: int, winner_team: str) -> str:
    """
    Sends result for testing
    """
    json_base = '{"event":"map_result","matchid":14272,"map_number":0,"team1":{"id":"2843","name":"Iberian Soul","series_score":0,"score":14,"score_ct":10,"score_t":14,"players":[{"steamid":"76561198279375306","name":"s1mple1","stats":{"kills":34,"deaths":8,"assists":5,"flash_assists":3,"team_kills":0,"suicides":0,"damage":2948,"utility_damage":173,"enemies_flashed":6,"friendlies_flashed":2,"knife_kills":1,"headshot_kills":19,"rounds_played":27,"bomb_defuses":4,"bomb_plants":3,"1k":3,"2k":2,"3k":3,"4k":0,"5k":1,"1v1":1,"1v2":3,"1v3":2,"1v4":0,"1v5":1,"first_kills_t":6,"first_kills_ct":5,"first_deaths_t":1,"first_deaths_ct":1,"trade_kills":3,"kast":23,"score":45,"mvp":4}},{"steamid":"76561198279375306","name":"s1mple2","stats":{"kills":12,"deaths":8,"assists":5,"flash_assists":3,"team_kills":0,"suicides":0,"damage":1348,"utility_damage":173,"enemies_flashed":6,"friendlies_flashed":2,"knife_kills":1,"headshot_kills":19,"rounds_played":27,"bomb_defuses":4,"bomb_plants":3,"1k":3,"2k":2,"3k":3,"4k":0,"5k":1,"1v1":1,"1v2":3,"1v3":2,"1v4":0,"1v5":1,"first_kills_t":6,"first_kills_ct":5,"first_deaths_t":1,"first_deaths_ct":1,"trade_kills":3,"kast":33,"score":45,"mvp":4}},{"steamid":"76561198279375306","name":"s1mple3","stats":{"kills":12,"deaths":8,"assists":5,"flash_assists":3,"team_kills":0,"suicides":0,"damage":1348,"utility_damage":173,"enemies_flashed":6,"friendlies_flashed":2,"knife_kills":1,"headshot_kills":19,"rounds_played":27,"bomb_defuses":4,"bomb_plants":3,"1k":3,"2k":2,"3k":3,"4k":0,"5k":1,"1v1":1,"1v2":3,"1v3":2,"1v4":0,"1v5":1,"first_kills_t":6,"first_kills_ct":5,"first_deaths_t":1,"first_deaths_ct":1,"trade_kills":3,"kast":33,"score":45,"mvp":4}},{"steamid":"76561198279375306","name":"s1mple4","stats":{"kills":12,"deaths":8,"assists":5,"flash_assists":3,"team_kills":0,"suicides":0,"damage":1348,"utility_damage":173,"enemies_flashed":6,"friendlies_flashed":2,"knife_kills":1,"headshot_kills":19,"rounds_played":27,"bomb_defuses":4,"bomb_plants":3,"1k":3,"2k":2,"3k":3,"4k":0,"5k":1,"1v1":1,"1v2":3,"1v3":2,"1v4":0,"1v5":1,"first_kills_t":6,"first_kills_ct":5,"first_deaths_t":1,"first_deaths_ct":1,"trade_kills":3,"kast":33,"score":45,"mvp":4}},{"steamid":"76561198279375306","name":"s1mple5","stats":{"kills":12,"deaths":8,"assists":5,"flash_assists":3,"team_kills":0,"suicides":0,"damage":1348,"utility_damage":173,"enemies_flashed":6,"friendlies_flashed":2,"knife_kills":1,"headshot_kills":19,"rounds_played":27,"bomb_defuses":4,"bomb_plants":3,"1k":3,"2k":2,"3k":3,"4k":0,"5k":1,"1v1":1,"1v2":3,"1v3":2,"1v4":0,"1v5":1,"first_kills_t":6,"first_kills_ct":5,"first_deaths_t":1,"first_deaths_ct":1,"trade_kills":3,"kast":33,"score":45,"mvp":4}}],"side":"ct","starting_side":"ct"},"team2":{"id":"2843","name":"Natus Vincere","series_score":0,"score":14,"score_ct":10,"score_t":14,"players":[{"steamid":"76561198279375306","name":"s1mple1","stats":{"kills":34,"deaths":8,"assists":5,"flash_assists":3,"team_kills":0,"suicides":0,"damage":2948,"utility_damage":173,"enemies_flashed":6,"friendlies_flashed":2,"knife_kills":1,"headshot_kills":19,"rounds_played":27,"bomb_defuses":4,"bomb_plants":3,"1k":3,"2k":2,"3k":3,"4k":0,"5k":1,"1v1":1,"1v2":3,"1v3":2,"1v4":0,"1v5":1,"first_kills_t":6,"first_kills_ct":5,"first_deaths_t":1,"first_deaths_ct":1,"trade_kills":3,"kast":23,"score":45,"mvp":4}},{"steamid":"76561198279375306","name":"s1mple2","stats":{"kills":12,"deaths":8,"assists":5,"flash_assists":3,"team_kills":0,"suicides":0,"damage":1348,"utility_damage":173,"enemies_flashed":6,"friendlies_flashed":2,"knife_kills":1,"headshot_kills":19,"rounds_played":27,"bomb_defuses":4,"bomb_plants":3,"1k":3,"2k":2,"3k":3,"4k":0,"5k":1,"1v1":1,"1v2":3,"1v3":2,"1v4":0,"1v5":1,"first_kills_t":6,"first_kills_ct":5,"first_deaths_t":1,"first_deaths_ct":1,"trade_kills":3,"kast":33,"score":45,"mvp":4}},{"steamid":"76561198279375306","name":"s1mple3","stats":{"kills":12,"deaths":8,"assists":5,"flash_assists":3,"team_kills":0,"suicides":0,"damage":1348,"utility_damage":173,"enemies_flashed":6,"friendlies_flashed":2,"knife_kills":1,"headshot_kills":19,"rounds_played":27,"bomb_defuses":4,"bomb_plants":3,"1k":3,"2k":2,"3k":3,"4k":0,"5k":1,"1v1":1,"1v2":3,"1v3":2,"1v4":0,"1v5":1,"first_kills_t":6,"first_kills_ct":5,"first_deaths_t":1,"first_deaths_ct":1,"trade_kills":3,"kast":33,"score":45,"mvp":4}},{"steamid":"76561198279375306","name":"s1mple4","stats":{"kills":12,"deaths":8,"assists":5,"flash_assists":3,"team_kills":0,"suicides":0,"damage":1348,"utility_damage":173,"enemies_flashed":6,"friendlies_flashed":2,"knife_kills":1,"headshot_kills":19,"rounds_played":27,"bomb_defuses":4,"bomb_plants":3,"1k":3,"2k":2,"3k":3,"4k":0,"5k":1,"1v1":1,"1v2":3,"1v3":2,"1v4":0,"1v5":1,"first_kills_t":6,"first_kills_ct":5,"first_deaths_t":1,"first_deaths_ct":1,"trade_kills":3,"kast":33,"score":45,"mvp":4}},{"steamid":"76561198279375306","name":"s1mple5","stats":{"kills":12,"deaths":8,"assists":5,"flash_assists":3,"team_kills":0,"suicides":0,"damage":1348,"utility_damage":173,"enemies_flashed":6,"friendlies_flashed":2,"knife_kills":1,"headshot_kills":19,"rounds_played":27,"bomb_defuses":4,"bomb_plants":3,"1k":3,"2k":2,"3k":3,"4k":0,"5k":1,"1v1":1,"1v2":3,"1v3":2,"1v4":0,"1v5":1,"first_kills_t":6,"first_kills_ct":5,"first_deaths_t":1,"first_deaths_ct":1,"trade_kills":3,"kast":33,"score":45,"mvp":4}}],"side":"ct","starting_side":"ct"},"winner":{"side":"ct","team":"team1"}}'
    data = json.loads(json_base)
    data['matchid'] = matchid
    data['map_number'] = map_number
    data['winner']['team'] = winner_team
    json = json.dumps(data)
    url = f"{bot.WEBHOOK_BASE_URL}/match_logs/{matchid}"

    cmd = f"curl -X POST {url} -H \"Content-Type: application/json\" -d '{json}'"
    return cmd

async def _get_teams_stats_from_json(datas: list) -> any: 
    """
    Gets team stats from a list of jsons
    """
    teams_data = {}
    for data in datas:
        for team_key in ['team1', 'team2']:
            team = data[team_key]
            if not team:
                continue
            team_name = team['name']
            if not team_name:
                continue
            if team_name not in teams_data:
                teams_data[team_name] = {}

            for player in team['players']:
                name = player['name']
                stats = player['stats']
                if not name:
                    continue
                if name not in teams_data[team_name]:
                    teams_data[team_name][name] = {
                        "kills": 0,
                        "deaths": 0,
                        "damage": 0,
                        "kast": 0,
                        "matches": 0
                    }
                teams_data[team_name][name]["kills"] += stats.get("kills", 0)
                teams_data[team_name][name]["deaths"] += stats.get("deaths", 0)
                teams_data[team_name][name]["damage"] += stats.get("damage", 0)
                teams_data[team_name][name]["kast"] += stats.get("kast", 0)
                teams_data[team_name][name]["matches"] += 1

    # Construcción del resultado
    teams = []
    for team_name, players in teams_data.items():
        team_entry = {"name": team_name, "players": []}
        for player_name, stats in players.items():
            kills = stats["kills"]
            deaths = stats["deaths"]
            damage = stats["damage"]
            kast_total = stats["kast"]
            matches = stats["matches"]

            kd = f"{kills}-{deaths}"
            diff = f"{'+' if kills - deaths >= 0 else ''}{kills - deaths}"
            adr = f"{(damage / deaths):.1f}" if deaths != 0 else "0.0"
            kast = f"{(kast_total / matches):.1f}%"

            team_entry["players"].append((player_name, kd, diff, adr, kast))

        teams.append(team_entry)

    return teams

async def _create_image_from_stats(datas: list) -> str:
    """
    Creates an image to be sended to the public game channel for informaiton
    """
    # Creates the base image
    width, height = 450, 450
    img = Image.new('RGB', (width, height), color=(36, 45, 60))
    draw = ImageDraw.Draw(img)

    # Colors
    white = (255, 255, 255)
    gray = (180, 180, 180)
    green = (0, 255, 0)
    red = (255, 64, 64)
    blue = (100, 149, 237)

    # Draw content
    column_titles = ["K-D", "+/-", "ADR", "KAST"]
    column_x = [150, 220, 270, 330, 390]

    # Get stats and redraw with the values
    teams = await _get_teams_stats_from_json(datas)
    y_offset = 20
    for team in teams:
        draw.text((width // 2 - draw.textlength(team["name"]) // 2, y_offset),
                team["name"], fill=blue)
        y_offset += 30

        # Column titles
        draw.text((50, y_offset), "Player", fill=gray)
        for title, x in zip(column_titles, column_x):
            draw.text((x, y_offset), title, fill=gray)
        y_offset += 25

        for player in team["players"]:
            draw.text(((50 - (len(player[0]) / 2)), y_offset), player[0], fill=white)

            for i, (stat, x) in enumerate(zip(player[1:], column_x)):
                color = white
                if i == 1:  # +/- column
                    color = green if "+" in stat else red
                draw.text((x, y_offset), stat, fill=color)
            y_offset += 28

        y_offset += 25

    # Save image
    output_path_centered = "./discord_match_stats_centered.png"
    img.save(output_path_centered)
    return output_path_centered

# API paths
@app.get('/match_configs/{file_name}')
async def match_configs_file(file_name: str):
    """
    Sends Matchzy match_config for configuring a match
    More info at https://shobhit-pathak.github.io/MatchZy/match_setup/
    matchzy_loadmatch_url <url> [header name] [header value]: 
        Loads a remote (JSON-formatted) match configuration by sending an HTTP(S) GET to the given URL. 
        You may optionally provide an HTTP header and value pair using the header name and header value arguments. 
        You should put all arguments inside quotation marks (""). ("").
    """
    # Read the corresponding JSON file
    try:
        with open(f'/usr/src/app/match_configs/{file_name}', 'r') as f:
            return json.loads(f.read())
    except FileNotFoundError:
        return {"error": "Match config file not found"}

@app.post('/match_logs/{game_id}')
async def match_logs(game_id: str, request: Request):
    """
    Receives logs from Matchzy events
    More info at:
        - https://shobhit-pathak.github.io/MatchZy/configuration/#events-and-http-logging
        - https://shobhit-pathak.github.io/MatchZy/events.html
    """
    try:
        # First do common tasks for events

        # Create directory if it doesn't exist
        os.makedirs('/usr/src/app/match_logs', exist_ok=True)

        # Generate random filename
        random_filename = f"game_{game_id}_{str(uuid.uuid4())}.json"
        filepath = f'/usr/src/app/match_logs/{random_filename}'

        game = bot.game_service.get_game_by_id(game_id=int(game_id))
        team_one = bot.team_service.get_team_by_id(game.team_one_id) 
        team_two = bot.team_service.get_team_by_id(game.team_two_id) 
        public_channel = bot.get_channel(game.game_channel_id)
        logging.error(f"public_channel.id: {public_channel.id})")
        guild_id = game.guild_id

        file = None
        # Save request body as JSON file
        data = await request.json()
        with open(filepath, "w") as f:
            json.dump(data, f, indent=4)
        if data is None:
            await public_channel.send("NONO")
            return
        
        event_value = data.get('event')

        logging.error(data)
        
        if event_value == "series_start":  # If series started, Send a message to start game
            await public_channel.send("Starting game")          
        elif event_value == "map_result": # If match finishes, set map finished and send the stats to public channel
            winner = data.get('winner').get('team')
            map_number = data.get('map_number') + 1
            game_map = bot.game_map_service.get_by_game_id_game_number_game_map(game_id=game_id, game_number=map_number)
            map_name = game_map.map_name
            team_winner = None
            team_looser = None
            team_number = -1
            if winner == "team1":
                team_winner = team_one
                team_looser = team_two
                team_number = 1
            else:
                team_winner = team_two
                team_looser = team_one
                team_number = 2
            team1_score = data.get('team1').get('score')
            team2_score = data.get('team2').get('score')
            message = f"""
                        {team_winner.name} wins the map {map_number} - {map_name}.\n The result was {team1_score}:{team2_score}.
                        """
            image_path = await _create_image_from_stats([data])
            file = discord.File(image_path, filename=os.path.basename(image_path))
            await public_channel.send(message, file=file)
            await _set_result(game=game, team_number=team_number, map_name = map_name)
        elif event_value == "map_vetoed": # Set map vetoed
            vetoer = data.get('team')
            team_vetoer_id = -1
            if vetoer == "team1":
                team_vetoer_id = team_one.id
            elif vetoer == "team2":
                team_vetoer_id = team_two.id

            vetoes = bot.veto_service.get_all_vetoes_by_game_id_only(game_id=game_id)
            picks = bot.pick_service.get_all_picks_by_game_id_only(game_id=game_id)
            
            order_veto = len(vetoes)
            order_pick = len(picks)
            all_order = order_veto + order_pick
            map_name = data.get('map_name')
            veto = Veto(order_veto=all_order + 1, game_id=game_id, team_id=team_vetoer_id, map_name=map_name, guild_id=game.guild_id)
            bot.veto_service.create_veto(veto)
            embed = await _game_embed(game)
            if public_channel:
                try:
                    msg = await public_channel.fetch_message(game.public_game_message_id)
                    await msg.edit(embed=embed)
                except Exception as e:
                    await public_channel.send(f"⚠️ Veto added but failed to update display: {e}")
        elif event_value == "map_picked": # Set map picked
            picker = data.get('team')
            team_picker_id = -1
            if picker == "team1":
                team_picker_id = team_one.id
            elif picker == "team2":
                team_picker_id = team_two.id

            vetoes = bot.veto_service.get_all_vetoes_by_game_id_only(game_id=game_id)
            picks = bot.pick_service.get_all_picks_by_game_id_only(game_id=game_id)
            
            order_veto = len(vetoes)
            order_pick = len(picks)
            all_order = order_veto + order_pick
            map_name = data.get('map_name')
            pick = Pick(order_pick=all_order + 1, game_id=game_id, team_id=team_picker_id, map_name=map_name, guild_id=game.guild_id)
            bot.pick_service.create_pick(pick)
            map_number = data.get('map_number')
            game_map = GameMap(game_number=map_number, map_name=pick.map_name, game_id=game.id, team_id_winner=-1, guild_id=game.guild_id)
            bot.game_map_service.create_game_map(game_map)             
            embed = await _game_embed(game)
            if public_channel:
                try:
                    msg = await public_channel.fetch_message(game.public_game_message_id)
                    await msg.edit(embed=embed)
                except Exception as e:
                    await public_channel.send(f"⚠️ Pick added but failed to update display: {e}")
        else: # Else event is not accepted
            logging.info(f"Event value not accepted: {event_value}")
        await _tournament_summary(guild_id=guild_id)
        return {"message": "Log saved successfully", "filename": random_filename}
    except Exception as e:
        logging.error(f"Failed to save log: {str(e)}")
        return {"error": f"Failed to save log: {str(e)}"}

@app.post('/match_demos/{game_id}')
async def match_demos(game_id: str, request: Request):
    """
    Saves the demo from Matchzy
    More info at https://shobhit-pathak.github.io/MatchZy/gotv/
    """
    try:
        game = bot.game_service.get_game_by_id(game_id=int(game_id))
        public_channel = bot.get_channel(game.game_channel_id)

        # Create directory if it doesn't exist
        os.makedirs('/usr/src/app/match_logs', exist_ok=True)

        # Get filename from header
        filename = request.headers.get('MatchZy-FileName')
        filepath = f'/usr/src/app/match_demos/{filename}'
        game_number = int(request.headers.get('MatchZy-MapNumber')) + 1
        
        with open(filepath, 'wb') as f:
            contents = await request.body()
            f.write(contents)
        map_name = (bot.game_map_service.get_by_game_id_game_number_game_map(game_id=game_id, game_number=game_number)).map_name

        file = discord.File(filepath, filename=filename)
        await public_channel.send(f"Demo - {map_name}:", file=file)

        return {"message": "Demo received successfully"}
    except Exception as e:
        return {"error": f"Error writing demo file: {str(e)}"}

async def run_api():
    """
    Starts api on port 8000
    """
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

async def main():
    """
    Starts all
    """
    try:
        logging.info("Starting bot initialization...")
        
        load_dotenv()
        logging.info(f"TOKEN: {os.environ['DISCORD_BOT_TOKEN']}")
        setup_database()
        setup_vars()
        
        # Create threads for bot and API
        api_task = asyncio.create_task(run_api())
        bot_task = asyncio.create_task(bot.start(os.environ['DISCORD_BOT_TOKEN']))
        await asyncio.gather(api_task, bot_task)
        
    except KeyError:
        logging.critical("Missing DISCORD_BOT_TOKEN in environment variables")
    except Exception as e:
        logging.critical(f"Fatal error: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    """
    Executes main asyncronous
    """
    asyncio.run(main())