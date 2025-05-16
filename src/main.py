# TODO: Replace result instead of map_name get the first that status is not finished

import json
import os
import logging
from logging.handlers import RotatingFileHandler
import datetime
from dotenv import load_dotenv
import random

import discord
from discord.ext import commands
import re

import requests
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

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')

@bot.command()
@discord.ext.commands.has_role("admin")
async def help(ctx):
    """Show help information based on user role"""
    
    help_msg = ("🔧 **Initial Setup**\n"
                "• Send `!start` to create all necessary roles, categories and channels\n")
    await ctx.send(help_msg)

    help_msg = (
        "🎮 **CS2 Tournament Bot Help**\n\n"
        "⚠️ Please use the #admin channel for all admin commands!\n\n"
        
        "**Initial Setup:**\n"
        "• `!start` - Initialize server setup (roles, categories, channels)\n\n"

        "**Game Settings:**\n"
        "• `!set_game_type <round_name> <game_type>` - Set game type for a round\n"
        "• `!get_settings` - Get all settings for the server\n"
        
        "**Team Management:**\n"
        "• `!create_team <team_name>` - Create a new team\n"
        "• `!add_player <team_name> <nickname> <steamid> <role>` - Add player to team\n"
        "  Roles can be: captain/coach/player\n"
        "• `!delete_team <team_name>` - Delete team\n"
        "• `!delete_player <nickname>` - Delete player\n\n"
        
        "**Tournament Flow:**\n"
        "• `!all_teams_created` - Lock teams and start tournament\n"
        "• `!finish_round` - Complete current round and start next\n"
        "• `!tournamentsummary` - Show tournament progress\n\n"
        
        "**Game Management:**\n"
        "• `!veto <map_name>` - Veto a map (execute in game channel)\n"
        "• `!pick <map_name>` - Pick a map (execute in game channel)\n"
        "• `!result <map_name> <team_number>` - Set map winner (1 or 2)\n"
        "• `!summary` - Show game status\n\n"

        "**Game Channel Management:**\n"
        "• `!set_game_server_setting <key> <value>` - Set game server settings\n"
        "• `!set_game_ip <game_id> <ip>` - Set server IP\n"
        "• `!set_game_port <game_id> <port>` - Set server port\n"
        "• `!set_game_password <game_id> <password>` - Set server password\n"
        "• `!set_hltv_ip <game_id> <ip>` - Set HLTV IP\n"
        "• `!set_hltv_port <game_id> <port>` - Set HLTV port\n"
        "• `!set_hltv_password <game_id> <password>` - Set HLTV password\n"
        "• `!set_rcon_password <game_id> <password>` - Set RCON password\n\n"

        "**Admin Testing:**\n"
        "• `!mock_teams` - Create mock teams until 16 teams\n"
        "• `!autoveto` - Auto execute vetos for all games\n" 
        "• `!autoresults` - Auto set results for all games\n"
        "• `!autovetoautoresults` - Auto veto and set results\n"
        "• `!delete_games <game_type>` - Delete all games from a round\n"
        "• `!im_all_teams_captain` - Make my user captain of all teams\n"
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
                await _add_player(ctx, team_name=team_name, nickname=nickname, role_name=role, steamid=steamid)           
    except Exception as e:
        logging.error(f"Error during mock_teams command: {e}")
        await ctx.send(f"❌ Error during mock_teams command: {e}")

@bot.command()
async def veto(ctx, map_name: str):
    """
    Veto a map from the game admin channel. This only could be executed by the captain
    of the team that can veto at the moment
    Format: !veto <map_name>
        - names: Single word (e.g., "dust2")
    """
    try:
        channel_id = ctx.channel.id
        game = bot.game_service.get_game_by_admin_game_channel_id(admin_game_channel_id=channel_id)
        if game is None:
            await ctx.send("This must be sent from a admin game channel.")
            return
        game_to_wins = await _get_game_to_wins(ctx, game=game)
        await _execute_veto(ctx, game_to_wins=game_to_wins, game=game, map_name=map_name) 
    except Exception as e:
        logging.error(f"Error during veto command: {e}")
        await ctx.send(f"❌ Error during veto command: {e}")

@bot.command()
async def pick(ctx, map_name: str):
    """
    Pick a map from the game admin channel. This only could be executed by the captain
    of the team that can pick at the moment
    Format: !pick <map_name>
        - names: Single word (e.g., "dust2")
    """
    try:
        channel_id = ctx.channel.id
        game = bot.game_service.get_game_by_admin_game_channel_id(admin_game_channel_id=channel_id)
        if game is None:
            await ctx.send("This must be sent from a admin game channel.")
            return
        game_to_wins = await _get_game_to_wins(ctx, game=game)
        await _execute_pick(ctx, game_to_wins=game_to_wins, game=game, map_name=map_name)
    except Exception as e:
        logging.error(f"Error during pick command: {e}")
        await ctx.send(f"❌ Error during pick command: {e}")

@bot.command()
@discord.ext.commands.has_role("admin")
async def summary(ctx):
    """
    Creates summary of the game of the game admin channel. This is only intended to be used if
    any problem happened when updating game summary.
    Format: !summary
    """
    try:
        channel_id = ctx.channel.id
        game = bot.game_service.get_game_by_admin_game_channel_id(admin_game_channel_id=channel_id)
        if game is None:
            await ctx.send("This must be sent from a admin game channel.")
            return
        await _game_summary(ctx, game)
    except Exception as e:
        logging.error(f"Error during summary command: {e}")
        await ctx.send(f"❌ Error during summary command: {e}")
    
@bot.command()
@discord.ext.commands.has_role("admin")
async def result(ctx, map_name: str, team_number: int):
    """
    Set the result of a map for a game from an admin game channel. This only can be executed by an admin.
    Once the game is finished, the results cannot be changed.
    Team one refers on the first team to appear in the channel name.
    Team two refers on the second team to appear in the cannel name.
    Format: !result <map_name> <team_number>
        - names: Single word (e.g., "dust2")
        - team_number: Int (1 or 2)
    If team_number is 1, the Team One wins.
    If team_number is 2, the Team Two wins.
    """
    try:
        channel_id = ctx.channel.id
        game = bot.game_service.get_game_by_admin_game_channel_id(admin_game_channel_id=channel_id)
        if game is None:
            await ctx.send("This must be sent from a admin game channel.")
            return
        await _set_result(ctx, game=game, team_number=team_number, map_name=map_name)
        await _game_summary(ctx, game=game)
        await _tournament_summary(ctx)
    except Exception as e:
        logging.error(f"Error during result command: {e}")
        await ctx.send(f"❌ Error during result command: {e}")
    
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
async def autoveto(ctx):
    """
    Create automatic veto depending of the game type.
    NOTE: CAREFUL!! Use this only for testing
    Format: !autoveto
    """
    try:
        guild = ctx.guild
        if not ctx.channel.name == "admin":
            await ctx.send("Must be executed from admin channel")
            return
        else:
            games = bot.game_service.get_all_games_not_finished(guild_id=guild.id)
            for game in games:
                game_to_wins = await _get_game_to_wins(ctx, game=game)
                if game_to_wins == "bo1":
                    await _execute_veto(ctx, game=game, map_name="anubis", game_to_wins=game_to_wins)
                    await _execute_veto(ctx, game=game, map_name="train", game_to_wins=game_to_wins)
                    await _execute_veto(ctx, game=game, map_name="inferno", game_to_wins=game_to_wins)
                    await _execute_veto(ctx, game=game, map_name="mirage", game_to_wins=game_to_wins)
                    await _execute_veto(ctx, game=game, map_name="nuke", game_to_wins=game_to_wins)
                    await _execute_veto(ctx, game=game, map_name="ancient", game_to_wins=game_to_wins)
                elif game_to_wins == "bo3":
                    await _execute_veto(ctx, game=game, map_name="anubis", game_to_wins=game_to_wins)
                    await _execute_veto(ctx, game=game, map_name="train", game_to_wins=game_to_wins)
                    await _execute_pick(ctx, game=game, map_name="inferno", game_to_wins=game_to_wins)
                    await _execute_pick(ctx, game=game, map_name="mirage", game_to_wins=game_to_wins)
                    await _execute_veto(ctx, game=game, map_name="nuke", game_to_wins=game_to_wins)
                    await _execute_veto(ctx, game=game, map_name="ancient", game_to_wins=game_to_wins)
                elif game_to_wins == "bo5":
                    await _execute_veto(ctx, game=game, map_name="anubis", game_to_wins=game_to_wins)
                    await _execute_veto(ctx, game=game, map_name="train", game_to_wins=game_to_wins)
                    await _execute_pick(ctx, game=game, map_name="inferno", game_to_wins=game_to_wins)
                    await _execute_pick(ctx, game=game, map_name="mirage", game_to_wins=game_to_wins)
                    await _execute_pick(ctx, game=game, map_name="nuke", game_to_wins=game_to_wins)
                    await _execute_pick(ctx, game=game, map_name="ancient", game_to_wins=game_to_wins)
    except Exception as e:
        logging.error(f"Error during autoveto command: {e}")
        await ctx.send(f"❌ Error during autoveto command: {e}")    
@bot.command()
@discord.ext.commands.has_role("admin")
async def autoresults(ctx):
    """
    Create automatic results depending of the game type.
    NOTE: CAREFUL!! Use this only for testing
    Format: !autoresults
    """
    try:
        guild = ctx.guild
        if not ctx.channel.name == "admin":
            await ctx.send("Must be executed from admin channel")
            return
        else:
            games = bot.game_service.get_all_games_not_finished(guild_id=guild.id)
        for game in games:
            game_to_wins = (await _get_game_to_wins(ctx, game=game))
            if game_to_wins == "bo1":
                await _set_result(ctx, game=game, team_number=1, map_name="dust2")
            elif game_to_wins == "bo3":
                await _set_result(ctx, game=game, team_number=1, map_name="inferno")
                await _set_result(ctx, game=game, team_number=1, map_name="mirage")
            elif game_to_wins == "bo5":
                await _set_result(ctx, game=game, team_number=1, map_name="inferno")
                await _set_result(ctx, game=game, team_number=1, map_name="mirage")
                await _set_result(ctx, game=game, team_number=1, map_name="nuke")
    except Exception as e:
        logging.error(f"Error during autoresults command: {e}")
        await ctx.send(f"❌ Error during autoresults command: {e}")    
@bot.command()
@discord.ext.commands.has_role("admin")
async def autovetoautoresults(ctx):
    """
    Create automatic vetos and results depending of the game type.
    NOTE: CAREFUL!! Use this only for testing
    Format: !autovetoautoresults
    """
    try:
        if not ctx.channel.name == "admin":
            await ctx.send("Must be executed from admin channel")
            return
        else:
            await ctx.send("Auto vetoing...")
            await autoveto(ctx)
            await ctx.send("Auto results...")
            await autoresults(ctx) 
    except Exception as e:
        logging.error(f"Error during autovetoautoresults command: {e}")
        await ctx.send(f"❌ Error during autovetoautoresults command: {e}")    

@bot.command()
@discord.ext.commands.has_role("admin")
async def tournamentsummary(ctx):
    """
    Creates summary of the whole tournament. This is only intended to be used if
    any problem happened when updating tournament summary.
    Format: !tournamentsummary
    """
    try:
        await _tournament_summary(ctx)
    except Exception as e:
        logging.error(f"Error during tournamentsummary command: {e}")
        await ctx.send(f"❌ Error during tournamentsummary command: {e}")    

@bot.command()
@discord.ext.commands.has_role("admin")
async def get_settings(ctx):
    """
    Get all settings for the server.
    Format: !get_settings
    """
    try:
        if not ctx.channel.name == "admin":
            await ctx.send("Must be executed from admin channel")
            return
        else:
            guild = ctx.guild
            settings = bot.setting_service.get_all_settings(guild_id=guild.id)
            if not settings:
                await ctx.send("No settings found.")
                return
            settings_msg = "Settings:\n"
            for setting in settings:
                settings_msg += f"{setting.key}: {setting.value}\n"
            await ctx.send(settings_msg)
    except Exception as e:
        logging.error(f"Error during get_settings command: {e}")
        await ctx.send(f"❌ Error during get_settings command: {e}")

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
            if game_type not in ["swiss_1", "swiss_2_high", "swiss_2_low", "swiss_3_high", "swiss_3_low", "quarterfinal_rounds", "semifinal_rounds", "final_rounds", "third_place_rounds"]:
                await ctx.send("❌ Invalid game type name! Must be one of: swiss_1, swiss_2_high, swiss_2_low, swiss_3_high, swiss_3_low, quarterfinal_rounds, semifinal_rounds, final_rounds, third_place_rounds")
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
async def start_map(ctx):
    """
    Start the current map for the current game. 
    Format: !start_map
    """
    guild = ctx.guild
    channel_id = ctx.channel.id
    game = bot.game_service.get_game_by_admin_game_channel_id(admin_game_channel_id=channel_id)
    if game is None:
        await ctx.send("This must be sent from a admin game channel.")
        return
    
    game_map = bot.game_map_service.get_first_not_finished_game_map(guild_id=guild.id, game_id=game.id)
    if game_map is None:
        await ctx.send("No maps found for this game or all maps have been finished.")
        return
    
    await _create_dathost_match(ctx, game=game, game_map=game_map)
            
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
    default_map_pool = "inferno,anubis,nuke,ancient,mirage,train,dust2"

    bot.MAP_POOL = os.environ.get("MAP_POOL", default_map_pool).split(',')
    bot.MAP_POOL_DATHOST = [f"de_{map_name}" for map_name in bot.MAP_POOL]
    bot.SWISS_DECIDER=os.environ.get("SWISS_DECIDER", "bo3")
    bot.SWISS_NOT_DECIDER=os.environ.get("SWISS_NOT_DECIDER", "bo1")
    bot.QUATERFINAL_ROUND=os.environ.get("QUATERFINAL_ROUND", "bo3")
    bot.SEMIFINAL_ROUND=os.environ.get("SEMIFINAL_ROUND", "bo3")
    bot.FINAL_ROUND=os.environ.get("FINAL_ROUND", "bo5")
    bot.THIRD_PLACE_ROUND=os.environ.get("THIRD_PLACE_ROUND", "bo3")
    bot.TOURNAMENT_NAME=os.environ.get("TOURNAMENT_NAME", None)
    bot.WEBHOOK_BASE_URL=os.environ.get("WEBHOOK_BASE_URL", None)
    bot.DATHOST_USERNAME=os.environ.get("DATHOST_USERNAME", None)
    bot.DATHOST_PASSWORD=os.environ.get("DATHOST_PASSWORD", None)
    bot.DATHOST_WEBHOOK_AUTHORIZATION_HEADER=os.environ.get("DATHOST_WEBHOOK_AUTHORIZATION_HEADER", "1A2B3C4D5E6F7G8H9I0J")
    bot.DATHOST_GAME_SERVER_ID=os.environ.get("DATHOST_GAME_SERVER_ID", None)
    bot.DATHOST_SERVER_HOST=os.environ.get("DATHOST_SERVER_HOST", None)
    bot.DATHOST_SERVER_PORT=os.environ.get("DATHOST_SERVER_PORT", None)
    bot.DATHOST_SERVER_PASSWORD=os.environ.get("DATHOST_SERVER_PASSWORD", None)
    bot.DATHOST_RCON_PASSWORD=os.environ.get("DATHOST_RCON_PASSWORD", None)



def _is_valid_team_name(name: str) -> bool:
    """Allows alphanumeric + spaces, no symbols"""
    return all(c.isalnum() or c.isspace() for c in name)

async def _create_team(ctx, name:str) -> Team:
    """
    Creates a new team based on the name.
    """
    guild = ctx.guild
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
        await _create_game(ctx, game, category=discord_game_category)
    await _tournament_summary(ctx)

async def _tournament_summary(ctx):
    """
    Creates tournament summary
    """
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
        ("swiss_5", "Swiss round 5 (2 Wins, 2 Losses)"),
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
            summary = bot.summary_service.get_summary_by_round_name(guild_id=guild.id, round_name=game_round)
            if summary is None:
                msg = await discord_summary_channel.send(embed=embed)
                summary = Summary(guild_id= guild.id, round_name=game_round, message_id=msg.id)
                bot.summary_service.create_summary(summary=summary)
            else:
                msg = await discord_summary_channel.fetch_message(summary.message_id)
                await msg.edit(embed=embed)

async def _get_game_to_wins(ctx, game: Game) -> str:
    """
    Have to return if the game is bo1, bo3 or bo5
    """
    game_type = game.game_type
    if game_type == "swiss_1" or game_type == "swiss_2_high" or game_type == "swiss_2_low" or game_type == "swiss_3_low" or game_type == "swiss_3_mid":
        return bot.SWISS_NOT_DECIDER
    elif game_type == "swiss_3_high" or game_type == "swiss_4_high" or game_type == "swiss_4_low" or game_type == "swiss_5":
        return bot.SWISS_DECIDER
    else:
        return bot.__getattribute__(f"{game_type}_ROUND", "bo3")

async def _execute_veto(ctx, game: Game, game_to_wins:str, map_name:str):
    """
    Executes a veto on a game
    """
    guild = ctx.guild

    admin_channel = bot.get_channel(game.admin_game_channel_id)

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
    remaining_maps = [map_ for map_ in bot.MAP_POOL if map_ not in map_names]

    if map_name not in remaining_maps:
        await admin_channel.send(f"This map was already vetoed or picked or is not in the map pool. Please select one of {remaining_maps}.")
        return

    if (all_order > 6):
        await admin_channel.send("All vetoes have been executed in this game.")
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
        await admin_channel.send(message)
        return  
    
    veto = Veto(order_veto=all_order + 1, game_id=game.id, team_id=current_team.id, map_name=map_name, guild_id=guild.id)
    if game_to_wins == "bo1":
        await admin_channel.send(f"{current_team.name} vetoed {map_name}")
        if all_order + 1 < 6: # Still vetoing
            await admin_channel.send(f"{next_team.name} time to veto.\nUse the command `!veto <map_name>` for vetoing a map.")
    elif game_to_wins == "bo3":
        if all_order == 2 or all_order == 3: # pick turn
            await admin_channel.send(f"Is pick time!")
            return
        await admin_channel.send(f"{team_one.name} vetoed {map_name}")
        if all_order + 1 == 2 or all_order + 1 == 3: # time to pick
            await admin_channel.send(f"{next_team.name} time to pick.\nUse the command `!pick <map_name>` for picking a map.")
        elif all_order + 1 < 6:
            await admin_channel.send(f"{next_team.name} time to veto.\nUse the command `!veto <map_name>` for vetoing a map.")
    elif game_to_wins == "bo5":
        if all_order + 1 > 2:
            await admin_channel.send(f"Is pick time!")
            return
        await admin_channel.send(f"{team_one.name} vetoed {map_name}")
        if all_order + 1 == 1:
            await admin_channel.send(f"{next_team.name} time to veto.\nUse the command `!veto <map_name>` for vetoing a map.")
        elif all_order + 1 < 6:
            await admin_channel.send(f"{next_team.name} time to pick.\nUse the command `!pick <map_name>` for picking a map.")
    bot.veto_service.create_veto(veto)

    if all_order + 1 == 6: # Remaining map is the decider
        map_names.append(map_name)
        remaining_maps = [map_ for map_ in bot.MAP_POOL if map_ not in map_names]
        pick = Pick(order_pick=all_order + 2, game_id=game.id, team_id=-1, map_name=remaining_maps[0], guild_id=guild.id)
        bot.pick_service.create_pick(pick)
        await admin_channel.send(f"Decider will be {remaining_maps[0]}.")
        await _create_game_maps(ctx, game=game)
    public_channel = bot.get_channel(game.game_channel_id)
    embed = await _game_embed(ctx, game)
    if public_channel:
        try:
            msg = await public_channel.fetch_message(game.public_game_message_id)
            await msg.edit(embed=embed)
        except Exception as e:
            await admin_channel.send(f"⚠️ Veto added but failed to update display: {e}")

async def _create_dathost_match(ctx, game: Game, game_map:GameMap):
    """
    Creates the dathost match
    """

    # Get all values of dathost
    team_one = bot.team_service.get_team_by_id(team_id=game.team_one_id)
    team_two = bot.team_service.get_team_by_id(team_id=game.team_two_id)
    match_endpoint = f"{game.id}/{game_map.map_name}"
    players_team_1 = bot.player_service.get_players_by_team_id(team_id=team_one.id)
    players_team_2 = bot.player_service.get_players_by_team_id(team_id=team_two.id)
    hostname = f"{game.game_type}: {team_one.name} vs {team_two.name} #{game.id}"
    
    # Create a dathost map
    username = bot.DATHOST_USERNAME
    if username is None:
        await ctx.send("❌ Dathost username not set in environment variables.")
        return None
    password = bot.DATHOST_PASSWORD
    if password is None:
        await ctx.send("❌ Dathost password not set in environment variables.")
        return None
    server_id = bot.DATHOST_GAME_SERVER_ID
    if server_id is None:
        await ctx.send("❌ Dathost server id not set in environment variables.")
        return None
    server_host = bot.DATHOST_SERVER_HOST
    if server_host is None:
        await ctx.send("❌ Dathost server host not set in environment variables.")
        return None
    server_port= bot.DATHOST_SERVER_PORT
    if server_port is None:
        await ctx.send("❌ Dathost server port not set in environment variables.")
        return None
    webhook_url = bot.WEBHOOK_BASE_URL
    rcon_password = bot.DATHOST_RCON_PASSWORD
    if rcon_password is not None:
        try:
            response = await rcon(
                'hostname', hostname,
                host=server_host, port=server_port, passwd=rcon_password
            )
            print(f"RCON response: {response}")
        except Exception as e:
            await ctx.send(f"❌ Error setting hostname: {e}")
        
    body = {}
    body['game_server_id'] = server_id
    body['team1'] = {}
    body['team1']['name'] = team_one.name
    body['team1']['flag'] = ""
    body['team2'] = {}
    body['team2']['name'] = team_two.name
    body['team2']['flag'] = ""
    body['players'] = []
    for p in players_team_1:
        player = {}
        player['steam_id_64'] = str(p.steamid)
        player['nickname_override'] = p.nickname
        player['team'] = "team1"
        body['players'].append(player)
    for p in players_team_2:
        player = {}
        player['steam_id_64'] = str(p.steamid)
        player['nickname_override'] = p.nickname
        player['team'] = "team2"
        body['players'].append(player)
    body['settings'] = {}
    body['settings']['map'] = game_map.map_name
    body['settings']['team_size'] = 7
    body['settings']['wait_for_gotv'] = True
    body['settings']['enable_plugin'] = True
    body['settings']['enable_tech_pause'] = True
    if webhook_url is not None:
        body['webhooks'] = {}
        body['webhooks']['event_url'] = f"{webhook_url}/match/{match_endpoint}"
        body['webhooks']['enabled_events'] = []
        body['webhooks']['enabled_events'].append("*")
        body['webhooks']['authorization_header'] = bot.DATHOST_WEBHOOK_AUTHORIZATION_HEADER
    headers = {
        "accept": "application/json",
        "content-type": "application/json"
    }
    await ctx.send(body)
    try:
        response = requests.post(
            "https://dathost.net/api/0.1/cs2-matches",
            headers=headers,
            json=body,
            auth=(username, password)
        )
    except requests.exceptions.RequestException as e:
        await ctx.send(f"❌ Error creating match: {e}")
        return None   
    print(f"Dathost response: {response.status_code} - {response.text}")
    if response.status_code == 200:
        await ctx.send(f"Match started in dathost. Connect to ||{server_host}:{server_port} with password {password}||")
    else:
        await ctx.send(f"❌ Error creating match: {response.text}")

async def _execute_pick(ctx, game: Game, game_to_wins:str, map_name:str):
    """
    Executes a pick on a game
    """
    guild = ctx.guild

    admin_channel = bot.get_channel(game.admin_game_channel_id)

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
    remaining_maps = [map_ for map_ in bot.MAP_POOL if map_ not in map_names]

    if map_name not in remaining_maps:
        await admin_channel.send(f"This map was already vetoed or picked or is not in the map pool. Please select one of {remaining_maps}.")
        return

    if (all_order > 6):
        await admin_channel.send("All picks have been executed in this game.")
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
        await admin_channel.send(message)
        return  

    pick = Pick(order_pick=all_order + 1, game_id=game.id, team_id=current_team.id, map_name=map_name, guild_id=guild.id)
    if game_to_wins == "bo1":
        await admin_channel.send(f"No picks on bo1 have to be assigned.")
        return
    elif game_to_wins == "bo3":
        if all_order != 2 and all_order != 3: # pick turn
            await admin_channel.send(f"Is veto time!")
            return
        await admin_channel.send(f"{team_one.name} picked {map_name}")
        if all_order + 1 == 2 or all_order + 1 == 3: # time to pick
            await admin_channel.send(f"{next_team.name} time to pick.\nUse the command `!pick <map_name>` for picking a map.")
        elif all_order + 1 < 6:
            await admin_channel.send(f"{next_team.name} time to veto.\nUse the command `!veto <map_name>` for vetoing a map.")
    elif game_to_wins == "bo5":
        if all_order + 1 < 2:
            await admin_channel.send(f"Is veto time!")
            return
        await admin_channel.send(f"{team_one.name} vetoed {map_name}")
        if all_order + 1 == 1:
            await admin_channel.send(f"{next_team.name} time to veto.\nUse the command `!veto <map_name>` for vetoing a map.")
        elif all_order + 1 < 6:
            await admin_channel.send(f"{next_team.name} time to pick.\nUse the command `!pick <map_name>` for picking a map.")
    bot.pick_service.create_pick(pick)

    if all_order + 1 == 6: # Remaining map is the decider
        map_names.append(map_name)
        remaining_maps = [map_ for map_ in bot.MAP_POOL if map_ not in map_names]
        pick = Pick(order_pick=all_order + 2, game_id=game.id, team_id=-1, map_name=remaining_maps[0], guild_id=guild.id)
        bot.pick_service.create_pick(pick)
        await admin_channel.send(f"Decider will be {remaining_maps[0]}.")
        await _create_game_maps(ctx, game=game)
        
    public_channel = bot.get_channel(game.game_channel_id)
    embed = await _game_embed(ctx, game)
    if public_channel:
        try:
            msg = await public_channel.fetch_message(game.public_game_message_id)
            await msg.edit(embed=embed)
        except Exception as e:
            await ctx.send(f"⚠️ Pick added but failed to update display: {e}")
   
async def _game_embed(ctx, game: Game) -> discord.Embed:
    """
    Creates the summary embed for a game
    """
    guild = ctx.guild

    game_to_wins = await _get_game_to_wins(ctx, game)
    
    team_one = bot.team_service.get_team_by_id(game.team_one_id)
    team_two = bot.team_service.get_team_by_id(game.team_two_id)
    vetoes = bot.veto_service.get_all_vetoes_by_game(guild_id=guild.id, game_id=game.id)
    picks = bot.pick_service.get_all_picks_by_game(guild_id=guild.id, game_id=game.id)
    game_maps = bot.game_map_service.get_all_game_maps_by_game(guild_id=guild.id, game_id=game.id)

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
    """
    Creates all game maps for a game depending on its picks
    """
    guild = ctx.guild
    picks = bot.pick_service.get_all_picks_by_game_ordered(guild_id=guild.id, game_id=game.id)
    i = 1
    game_maps = []
    for pick in picks:
        game_map = GameMap(game_number=i, map_name=pick.map_name, game_id=game.id, team_id_winner=-1, guild_id=guild.id)
        await ctx.send(f"Creating game map {game_map.map_name} for game {game.id}")
        game_map.id = bot.game_map_service.create_game_map(game_map)
        game_maps.append(game_map)
        i = i + 1
    return game_maps

async def _game_summary(ctx, game: Game):
    """
    Creates a game summary
    """
    public_channel = bot.get_channel(game.game_channel_id)
    embed = await _game_embed(ctx, game)
    if public_channel:
        try:
            msg = await public_channel.fetch_message(game.public_game_message_id)
            await msg.edit(embed=embed)
        except Exception as e:
            await ctx.send(f"⚠️ Error on sending msg: {e}")

async def _set_result(ctx, game: Game, team_number: int, map_name: str):
    """
    Sets the winner on a game map
    """
    admin_channel = bot.get_channel(game.admin_game_channel_id)

    if game.team_winner > 0:
        await admin_channel.send("The winner have been already setted.")
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
        await admin_channel.send(f"Winner must be set as 1 if winner is {team_one.name} or 2 if winner is {team_two.name}.")
        return
    
    game_map = bot.game_map_service.get_game_map_by_game_and_map_name(guild_id=guild.id, game_id=game.id, map_name=map_name)
    if game_map == None:
        await admin_channel.send(f"The map {map_name} is not one of the game.")
        return
    game_map.team_id_winner = team_winner.id
    bot.game_map_service.update_game_map(game_map)
    await admin_channel.send(f"{team_winner.name} won map number {game_map.game_number} played in {map_name}.")

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
        # TODO: Delete server from dathost
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
        await _tournament_summary(ctx)

def main():
    try:
        logging.info("Starting bot initialization...")
        
        load_dotenv()
        logging.info(f"TOKEN: {os.environ['DISCORD_BOT_TOKEN']}")
        setup_database()
        setup_vars()
        
        bot.run(os.environ["DISCORD_BOT_TOKEN"])
    except KeyError:
        logging.critical("Missing DISCORD_BOT_TOKEN in environment variables")
    except Exception as e:
        logging.critical(f"Fatal error: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    main()