import os
import logging
from logging.handlers import RotatingFileHandler
import datetime
from dotenv import load_dotenv

import discord
from discord.ext import commands

from services.database import DatabaseManager
from models.team import Team
from models.setting import Setting
from models.server_role import ServerRole
from models.category import Category
from models.channel import Channel

from services.team_service import TeamService
from services.setting_service import SettingService
from services.server_role_service import ServerRoleService
from services.category_service import CategoryService
from services.channel_service import ChannelService

description = '''
Bot for creating a Counter Strike Tournament with 16 teams,
swiss-round and knock-out stage.
'''

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')

@commands.command()
    async def help(self, ctx):
        """Show help information based on user role"""
        guild = ctx.guild
        admin_role = discord.utils.get(guild.roles, name="Admin")
        
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
            logger.info(f"Help message sent to {ctx.author.name}")
        except discord.errors.HTTPException as e:
            logger.error(f"Failed to send help message: {e}")
            await ctx.send("❌ Error sending help message. Please check logs.")


@bot.command()
async def start(ctx):
    """
    Initialize the server setup.
    It creates all categories, channels and settings.
    """

    try:
        # No matter if already started, but roles should not be created twice.
        
        # If the admin server role don't exists, create it
        admin_role = await self._create_server_role(ctx, "admin")

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
            "Quarterfinals": {"position": 7, "poverwritesublic": public_overwrites},
            "Semifinals": {"position": 8, "overwrites": public_overwrites},
            "Third Place": {"position": 9, "overwrites": public_overwrites},
            "Final": {"position": 10, "overwrites": public_overwrites}
        }
        
        # For each category create it
        discord_categories = {}
        for name, config in categories.items():
            category = 
                await self._create_server_category(ctx, category_name=name, category_position=config[position], category_overwrites=config[overwrites])

            discord_categories[name] = {
                "category": category
            }
        
        # Create object of channels

        channels = {
            "admin": {"category": discord_categories["Admin"].category, "overwrites": private_overwrites, "position": 0},
            "teams": {"category": discord_categories["Info"].category, "overwrites": public_overwrites, "position": 0},
            "summary": {"category": discord_categories["Info"].category, "overwrites": public_overwrites, "position": 1},
        }
        # For each channel create it
        for name, config in channels.items():
            category = 
                await self._create_server_channel(ctx, channel_name=name, category_position=config[position], overwrites=config[overwrites])
        
        
    except Exception as e:
        await ctx.send(f"Error during setup: {str(e)}")
        logging.error(f"Setup error: {e}", exc_info=True)

@bot.command(description='For when you wanna settle the score some other way')
async def choose(ctx, *choices: str):
    """Chooses between multiple choices."""
    await ctx.send(random.choice(choices))

@bot.command()
async def joined(ctx, member: discord.Member):
    """Says when a member joined."""
    await ctx.send(f'{member.name} joined {discord.utils.format_dt(member.joined_at)}')

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
    logging.getLogger('discord.http').setLevel(logging.WARNING)

async def setup_database():
    """Initialize database and attach to bot instance"""
    bot.db = DatabaseManager()
    bot.team_service = TeamService(bot.db.get_connection())
    bot.setting_service = SettingService(bot.db.get_connection())
    bot.service_role_service = ServerRoleService(bot.db.get_connection())
    logging.info("Database and services initialized")

async def _create_server_category(ctx, category_name:str, category_position:int, overwrites) -> discord.Category:
    """
    Creates a server category taking in account also them to be stored in the DB
    """
    # Get category from discord
    discord_category = discord.utils.get(guild.categories, name=category_name)
    if discord_category is None: # If the category don't exist, create it on Discord and DB        
        discord_category = await guild.create_category(
            category_name, 
            position=category_position, 
            overwrites=overwrites
        )
        # Check if the category already existed in DB. If true, means that was manually removed and needs to update
        category = bot.category_service.get_category_by_name(category_name=category_name, guild_id=ctx.guild.id)
        if category is not None: # The category was removed manually from Discord, recreate
            category.category_id = discord_category.id
            bot.category_service.update_category(category)
        else: # Default stage, this don't exists in Discord neither on DB
            category = Category(guild_id=ctx.guild.id, category_name=category_name, category_id=discord_category.id)
            bot.category_service.create_category(category)
    return discord_category

async def _create_server_channel(ctx, channel_name:str, channel_position:int, category:discord.Category, overwrites:dict) -> discord.TextChannel:
    """
    Creates a text channel taking in account also them to be stored in the DB
    """
    # Get text channels from discord
    discord_channel = discord.utils.get(ctx.guild.channels, name=channel_name, category=category)

    if discord_channel is None: # If this text channel don't exist
        discord_channel = await guild.create_channel(
            channel_name, 
            category=category, 
            position=channel_position, 
            overwrites=overwrites)
        channel = bot.channel_service.get_channel_by_name(channel_name=channel_name, guild_id=ctx.guild.id)
        if channel is not None: # The channel was removed manually from Discord, recreate
            channel.channel_id = discord_channel.id
            bot.channel_service.update_channel(channel)
        else: Default stage, this don't exists in Discord neither on DB
            channel = Channel(guild_id=ctx.guild.id, channel_name=channel_name, channel_id=discord_channel.id)
            bot.channel_service.create_channel(channel)
    return discord_channel    

async def _create_server_role(ctx, server_role_name: str) -> discord.Role:
    """
    Creates a server role taking in account also them to be stored in the DB
    """
    # Check if role exists by name in discord
    discord_server_role = discord.utils.get(guild.roles, name=server_role_name)
    if discord_server_role is None:  # The role don't exist on discord, create on Discord and upsert on DB
        # Create server role on discord
        discord_server_role = ctx.guild.create_role(name=server_role_name, mentionable=True)

        # Get server role by name in DB
        server_role = get_server_role_by_name(server_role_name=server_role_name, guild_id=ctx.guild.id)
        if server_role is not None: # The role exists in the DB, it means that somebody removed the role from the server manually
            # Update the server role
            server_role.id = discord_server_role.id
            bot.service_role_service.update_server_role(discord_server_role)
        else: # The role don't exists in DB, so create a new one
            # Create the server role
            server_role = ServerRole(guild_id=ctx.guild.id, role_name=server_role_name, role_id= discord_server_role.id)
    return discord_server_role

def main():
    try:
        logging.info("Starting bot initialization...")
        
        load_dotenv()
        setup_database()
        
        bot.run(os.environ["DISCORD_BOT_TOKEN"])
    except KeyError:
        logging.critical("Missing DISCORD_BOT_TOKEN in environment variables")
    except Exception as e:
        logging.critical(f"Fatal error: {e}", exc_info=True)
        raise

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

if __name__ == "__main__":
    main()