import discord
from discord.ext import commands
import logging

# Configure logger
logger = logging.getLogger('discord.setup')
logger.setLevel(logging.INFO)

class Setup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db

    async def _embed_summary(self, ctx) -> discord.Embed:
        """Creates an embed for game pick/veto"""

        guild = ctx.guild
        embed = discord.Embed(title="Championship summary", color=discord.Color.blue())
        embed.description = f"Championship summary.\n"
        message = ""
        try:
            teams = await self.bot.fetch_all(
                    "SELECT * FROM team WHERE guild_id = ? ORDER BY swiss_wins DESC, swiss_losses ASC",
                    (guild.id,)
                )
            if teams:
                i = 1
                for team in teams:

                    team_name = team["name"]
                    team_swiss_wins = team["swiss_wins"]
                    team_swiss_losses = team["swiss_losses"]
                        
                    message += f"{i} - {team_name}: {team_swiss_wins}W - {team_swiss_losses}L\n"
                    i = i + 1
                embed.add_field(name="Swiss record", value=message, inline=False)
            else:
                embed.add_field(name="Swiss record", value="No teams yet", inline=False)
        except Exception as e:
            logger.error(f"Error processing result: {e}")
            embed.add_field(name="Swiss record", value="No teams yet", inline=False)

        # Quaterfinal
        try:
            logger.info("games")
            games = await self.bot.fetch_all(
                "SELECT * FROM game WHERE guild_id = ? AND game_type = ?",
                (guild.id, "quarterfinal")
            )
            logger.info(games)
            if games:
                message = ""
                for game in games:
                    team_one = await self.bot.fetch_one(
                        "SELECT * FROM team WHERE guild_id = ? AND id = ?",
                        (guild.id, game["team_one_id"])
                    )        
                    team_two = await self.bot.fetch_one(
                        "SELECT * FROM team WHERE guild_id = ? AND id = ?",
                        (guild.id, game["team_two_id"])
                    )                
                    if team_one and team_two:
                        winner_number = game["winner_number"]
                        team_one_name = team_one['name']
                        team_two_name = team_two['name']

                        if winner_number == 1:
                            team_one_name = "👑 " + team_one_name
                        elif winner_number == 2:
                            team_one_name = "👑 " + team_two_name

                        message += f"{team_one_name} vs {team_two_name}\n"
                embed.add_field(name="Quaterfinal", value=message, inline=False)
            else:
                embed.add_field(name="Quaterfinal", value="No teams yet", inline=False)
        except Exception as e:
            logger.error(f"Error processing result: {e}")
            embed.add_field(name="Quaterfinal", value="No teams yet", inline=False)

        # Semifinal
        try:
            games = await self.bot.fetch_all(
                "SELECT * FROM game WHERE guild_id = ? AND game_type = ?",
                (guild.id, "semifinal")
            )
            if games:
                message = ""
                for game in games:
                    team_one = await self.bot.fetch_one(
                        "SELECT * FROM team WHERE guild_id = ? AND id = ?",
                        (guild.id, game["team_one_id"])
                    )        
                    team_two = await self.bot.fetch_one(
                        "SELECT * FROM team WHERE guild_id = ? AND id = ?",
                        (guild.id, game["team_two_id"])
                    )                
                    if team_one and team_two:
                        winner_number = game["winner_number"]
                        team_one_name = team_one['name']
                        team_two_name = team_two['name']

                        if winner_number == 1:
                            team_one_name = "👑 " + team_one_name
                        elif winner_number == 2:
                            team_one_name = "👑 " + team_two_name

                        message += f"{team_one_name} vs {team_two_name}\n"
                embed.add_field(name="Semifinal", value=message, inline=False)
            else:
                embed.add_field(name="Semifinal", value="No teams yet", inline=False)
        except Exception as e:
            logger.error(f"Error processing result: {e}")
            embed.add_field(name="Semifinal", value="No teams yet", inline=False)

        # Third place
        try:
            games = await self.bot.fetch_all(
                "SELECT * FROM game WHERE guild_id = ? AND game_type = ?",
                (guild.id, "third_place")
            )
            if games:
                message = ""
                for game in games:
                    team_one = await self.bot.fetch_one(
                        "SELECT * FROM team WHERE guild_id = ? AND id = ?",
                        (guild.id, game["team_one_id"])
                    )        
                    team_two = await self.bot.fetch_one(
                        "SELECT * FROM team WHERE guild_id = ? AND id = ?",
                        (guild.id, game["team_two_id"])
                    )                
                    if team_one and team_two:
                        winner_number = game["winner_number"]
                        team_one_name = team_one['name']
                        team_two_name = team_two['name']

                        if winner_number == 1:
                            team_one_name = "👑 " + team_one_name
                        elif winner_number == 2:
                            team_one_name = "👑 " + team_two_name

                        message += f"{team_one_name} vs {team_two_name}\n"
                embed.add_field(name="Third place", value=message, inline=False)
            else:
                embed.add_field(name="Third place", value="No teams yet", inline=False)
        except Exception as e:
            logger.error(f"Error processing result: {e}")
            embed.add_field(name="Third place", value="No teams yet", inline=False)

        # Final
        try:
            games = await self.bot.fetch_all(
                "SELECT * FROM game WHERE guild_id = ? AND game_type = ?",
                (guild.id, "final")
            )
            if games:
                message = ""
                for game in games:
                    team_one = await self.bot.fetch_one(
                        "SELECT * FROM team WHERE guild_id = ? AND id = ?",
                        (guild.id, game["team_one_id"])
                    )        
                    team_two = await self.bot.fetch_one(
                        "SELECT * FROM team WHERE guild_id = ? AND id = ?",
                        (guild.id, game["team_two_id"])
                    )                
                    if team_one and team_two:
                        winner_number = game["winner_number"]
                        team_one_name = team_one['name']
                        team_two_name = team_two['name']

                        if winner_number == 1:
                            team_one_name = "👑 " + team_one_name
                        elif winner_number == 2:
                            team_one_name = "👑 " + team_two_name

                        message += f"{team_one_name} vs {team_two_name}\n"
                embed.add_field(name="Final", value=message, inline=False)
            else:
                embed.add_field(name="Final", value="No teams yet", inline=False)
        except Exception as e:
            logger.error(f"Error processing result: {e}")
            embed.add_field(name="Final", value="No teams yet", inline=False)
        
        return embed

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

    async def _create_category(self, guild, name: str):
        """Create a category and store it in the database"""
        try:
            category = await guild.create_category(name)
            await self.bot.execute_db(
                "INSERT INTO category (guild_id, category_id, category_name) VALUES (?, ?, ?)",
                (guild.id, category.id, name)
            )
            logger.info(f"Created category {name} in {guild.name}")
            return category
        except Exception as e:
            logger.error(f"Error creating category: {e}")
            return None

    async def _create_first_settings(self, guild): 
        """Create the settings by default"""
        logger.info("Creating settings")
        try:
            await self.bot.execute_db(
                "INSERT INTO setting (guild_id, key, value) VALUES (?, ?, ?)",
                (guild.id, "swiss_1_rounds", "bo3")
            )
            await self.bot.execute_db(
                "INSERT INTO setting (guild_id, key, value) VALUES (?, ?, ?)",
                (guild.id, "swiss_2_rounds", "bo3")
            )
            await self.bot.execute_db(
                "INSERT INTO setting (guild_id, key, value) VALUES (?, ?, ?)",
                (guild.id, "swiss_3_rounds", "bo3")
            )
            await self.bot.execute_db(
                "INSERT INTO setting (guild_id, key, value) VALUES (?, ?, ?)",
                (guild.id, "swiss_4_rounds", "bo3")
            )
            await self.bot.execute_db(
                "INSERT INTO setting (guild_id, key, value) VALUES (?, ?, ?)",
                (guild.id, "swiss_5_rounds", "bo3")
            )
            await self.bot.execute_db(
                "INSERT INTO setting (guild_id, key, value) VALUES (?, ?, ?)",
                (guild.id, "quarterfinal_rounds", "bo3")
            )
            await self.bot.execute_db(
                "INSERT INTO setting (guild_id, key, value) VALUES (?, ?, ?)",
                (guild.id, "semifinal_rounds", "bo3")
            )
            await self.bot.execute_db(
                "INSERT INTO setting (guild_id, key, value) VALUES (?, ?, ?)",
                (guild.id, "third_place_rounds", "bo3")
            )
            await self.bot.execute_db(
                "INSERT INTO setting (guild_id, key, value) VALUES (?, ?, ?)",
                (guild.id, "final_rounds", "bo3")
            )
            await self.bot.execute_db(
                "INSERT INTO setting (guild_id, key, value) VALUES (?, ?, ?)",
                (guild.id, "start_executed", "true")
            )
        
        except Exception as e:
            logger.error(f"Error creating settings: {e}")
            return None

    @commands.command()
    @commands.has_role("Admin")
    async def setup(self, ctx, key: str, value: str):
        """Set up a key-value pair in the database"""
        if key == "swiss_rounds":
            if value != "bo1" and value != "bo3" and value != "bo5":
                await ctx.send("❌ Invalid value for swiss_rounds. Use bo1, bo3, or bo5.")
                return
        elif key == "quaterfinal_rounds":
            if value != "bo1" and value != "bo3" and value != "bo5":
                await ctx.send("❌ Invalid value for quaterfinal_rounds. Use bo1, bo3, or bo5.")
                return
        elif key == "semifinal_rounds":
            if value != "bo1" and value != "bo3" and value != "bo5":
                await ctx.send("❌ Invalid value for knockout_rounds. Use bo1, bo3, or bo5.")
                return
        elif key == "final_rounds":
            if value != "bo1" and value != "bo3" and value != "bo5":
                await ctx.send("❌ Invalid value for final_rounds. Use bo1, bo3, or bo5.")
                return
        elif key == "third_place_rounds":
            if value != "bo1" and value != "bo3" and value != "bo5":
                await ctx.send("❌ Invalid value for third_place_rounds. Use bo1, bo3, or bo5.")
                return
        elif key == "hosted_by_dathost":
            if value != "true" or value != "false":
                await ctx.send("❌ Invalid value for hosted_by_dathost. Use true or false.")
                return
        try:
            await self.bot.execute_db("INSERT INTO setting (key, value) VALUES (?, ?)", (key, value))
            await ctx.send(f"✅ Setup completed: {key} = {value}")
            await ctx.send("Now only BO3 is accepted")
            logger.info(f"Setup completed: {key} = {value}")
        except Exception as e:
            logger.error(f"Error during setup: {e}")
            await ctx.send(f"❌ Error during setup: {e}")

    @commands.command()
    async def start(self, ctx):
        """Initialize the server setup"""
        guild = ctx.guild
        setting_started = None
        try:
            setting_started = await self.bot.fetch_one(
                "SELECT * FROM setting WHERE key = ? AND guild_id = ?",
                ("start_executed", guild.id)
            )
            if setting_started is not None:
                await ctx.send(f"Already started")
                return
            logger.info(f"Not started, continue")
        except Exception as e:
            logger.info(f"Not started, continue")
        try:
            # Create Admin role if it doesn't exist
            admin_role = discord.utils.get(guild.roles, name="Admin")
            if not admin_role:
                admin_role = await guild.create_role(name="Admin", mentionable=True)
                await self.bot.execute_db(
                    "INSERT INTO server_role (guild_id, role_name) VALUES (?, ?)",
                    (guild.id, "Admin")
                )
                logger.info("Created Admin role")
                
                if guild.owner:
                    await guild.owner.add_roles(admin_role)
                    logger.info(f"Gave Admin role to guild owner: {guild.owner.name}")
            # Create categories and channels
            await self._create_categories(guild, admin_role)
            await self._create_channels(guild, ctx)
            logger.info("_create_first_settings")
            await self._create_first_settings(guild)
            await ctx.send("✅ Setup completed!")
            
        except Exception as e:
            logger.error(f"Error in start command: {e}")
            await ctx.send(f"❌ Error: {str(e)}")

    async def _create_categories(self, guild, admin_role):
        """Create all necessary categories"""
        try:
            categories = {
                "Admin": {"position": 0, "public": False},
                "Info": {"position": 1, "public": True},
                "Swiss stage round 1": {"position": 2, "public": True},
                "Swiss stage round 2": {"position": 3, "public": True},
                "Swiss stage round 3": {"position": 4, "public": True},
                "Swiss stage round 4": {"position": 5, "public": True},
                "Swiss stage round 5": {"position": 6, "public": True},
                "Quarterfinals": {"position": 7, "public": True},
                "Semifinals": {"position": 8, "public": True},
                "Third Place": {"position": 9, "public": True},
                "Final": {"position": 10, "public": True}
            }

            for name, config in categories.items():
                category = discord.utils.get(guild.categories, name=name)
                if not category:
                    overwrites = {
                        guild.default_role: discord.PermissionOverwrite(
                            read_messages=config["public"]
                        ),
                        admin_role: discord.PermissionOverwrite(
                            read_messages=True, 
                            send_messages=True
                        ),
                        guild.me: discord.PermissionOverwrite(
                            read_messages=True, 
                            send_messages=True
                        )
                    }
                    
                    category = await guild.create_category(
                        name, 
                        position=config["position"], 
                        overwrites=overwrites
                    )

                    # Using thread-safe execute_db
                    await self.bot.execute_db(
                        """INSERT INTO category (guild_id, category_id, category_name) 
                        VALUES (?, ?, ?)""",
                        (guild.id, category.id, name)
                    )
                    logger.info(f"Created category {name} in {guild.name}")

        except Exception as e:
            logger.error(f"Error creating categories: {e}")
            raise
    
    async def _create_channels(self, guild, ctx):
        info_category = discord.utils.get(guild.categories, name="Info")
        teams_channel = discord.utils.get(guild.text_channels, name="teams", category=info_category)
        if not teams_channel:
            channel = await guild.create_text_channel("teams", category=info_category, position=0)
            logger.info(f"Creating setting for {channel.id}")
            await self.bot.execute_db(
                "INSERT INTO setting (guild_id, key, value) VALUES (?, ?, ?)",
                (guild.id, "teams_channel_id", channel.id)
            )
            logger.info(f"Created #teams channel in {guild.name}")
        
        admin_category = discord.utils.get(guild.categories, name="Admin")
        admin_channel = discord.utils.get(guild.text_channels, name="admin", category=admin_category)
        if not admin_channel:
            channel = await guild.create_text_channel("admin", category=admin_category, position=0)
            await self.bot.execute_db(
                "INSERT INTO setting (guild_id, key, value) VALUES (?, ?, ?)",
                (guild.id, "admin_channel_id", channel.id)
            )
            logger.info(f"Created #admin channel in {guild.name}")
        
        summary_channel = discord.utils.get(guild.text_channels, name="Summary", category=info_category)
        if not summary_channel:
            channel = await guild.create_text_channel("Summary", category=info_category, position=1)
            await self.bot.execute_db(
                "INSERT INTO setting (guild_id, key, value) VALUES (?, ?, ?)",
                (guild.id, "summary_channel_id", channel.id)
            )
            logger.info(f"Created #admin channel in {guild.name}")
            embed = await self._embed_summary(ctx)
            msg = await channel.send(embed=embed)
            await self.bot.execute_db(
                "INSERT INTO setting (guild_id, key, value) VALUES (?, ?, ?)",
                (guild.id, "summary_msg_id", msg.id)
            )
        return

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        logger.error(f"Error executing {ctx.command}: {str(error)}")
        await ctx.send(f"❌ An error occurred: {str(error)}")

async def setup(bot):
    await bot.add_cog(Setup(bot))