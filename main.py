import os
import discord
from discord.ext import commands
import sqlite3
import logging
from logging.handlers import RotatingFileHandler
import datetime
from functools import partial
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

# ===== CONFIGURATION =====

# Load environment variables from .env file
load_dotenv()
BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN")

# SQLite connection
def create_db_connection():
    os.makedirs('./data', exist_ok=True)
    conn = sqlite3.connect('./data/tournament.db')
    conn.row_factory = sqlite3.Row
    
    # Initialize database
    with open('init-db.sql', 'r') as f:
        sql_script = f.read()
        cursor = conn.cursor()
        cursor.executescript(sql_script)
        conn.commit()
        cursor.close()
    
    return conn

db = create_db_connection()

class TournamentBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True
        
        super().__init__(
            command_prefix="!", 
            intents=intents,
            help_command=None
        )
        
        # Create thread pool for database operations
        self.executor = ThreadPoolExecutor(max_workers=3)
        self.db = create_db_connection()

    async def execute_db(self, sql: str, params: tuple = ()):
        """Thread-safe database execution"""
        def _execute():
            conn = create_db_connection()
            cursor = conn.cursor()
            cursor.execute(sql, params)
            conn.commit()
            result = cursor.fetchall() if cursor.description else None
            cursor.close()
            conn.close()
            return result
            
        return await self.loop.run_in_executor(None, _execute)

    async def fetch_one(self, sql: str, params: tuple = ()):
        """Thread-safe fetch one row"""
        def _fetch_one():
            conn = create_db_connection()
            cursor = conn.cursor()
            cursor.execute(sql, params)
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            return result
            
        return await self.loop.run_in_executor(None, _fetch_one)

    async def fetch_all(self, sql: str, params: tuple = ()):
        """Thread-safe fetch all rows"""
        def _fetch_all():
            conn = create_db_connection()
            cursor = conn.cursor()
            cursor.execute(sql, params)
            result = cursor.fetchall()
            cursor.close()
            conn.close()
            return result
            
        return await self.loop.run_in_executor(None, _fetch_all)

    async def setup_hook(self):
        # Load all cogs
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py") and not filename.startswith("__"):
                await self.load_extension(f"cogs.{filename[:-3]}")
                print(f"Loaded {filename}")

    async def on_ready(self):
        print(f"✅ Logged in as {self.user}")
        print(f"Bot is in {len(self.guilds)} guilds")

# Configure logging
def setup_logging():
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # File handler
    file_handler = RotatingFileHandler(
        filename=f'logs/discord_{datetime.datetime.now().strftime("%Y%m%d")}.log',
        maxBytes=5242880,  # 5MB
        backupCount=5
    )
    file_handler.setFormatter(formatter)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # Discord logger
    discord_logger = logging.getLogger('discord')
    discord_logger.setLevel(logging.INFO)

# Setup logging before bot initialization
setup_logging()

bot = TournamentBot()
bot.run(BOT_TOKEN)