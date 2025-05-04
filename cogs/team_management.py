import random
import discord
from discord.ext import commands
import os
import logging

# Configure logger
logger = logging.getLogger('discord.setup')
logger.setLevel(logging.INFO)

class TeamManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot 

    async def _get_category_id(self, category_name: str) -> int:
        """Fetches the category ID for a given category name"""
        try:
            category = await self.bot.fetch_one(
                "SELECT category_id FROM category WHERE category_name = ? AND guild_id = ?",
                (category_name, self.bot.guilds[0].id)
            )
            return category["category_id"] if category else None
        except Exception as e:
            logger.error(f"Error getting category ID: {e}")
            return None
    
    async def _get_teams_channel(self, guild) -> any:
        """Fetches the teams channel id"""
        try:
                teams_channel_setting = await self.bot.fetch_one(
                    "SELECT * FROM setting WHERE key = ? AND guild_id = ?",
                    ("teams_channel_id", guild.id)
                )
                if teams_channel_setting is None:
                    return None

        except Exception as e:
            return None

        teams_channel_id = int(teams_channel_setting["value"])
        teams_channel = self.bot.get_channel(teams_channel_id)
        return teams_channel

    async def _create_team(self, ctx, guild, team_name:str) -> bool:
        teams_channel = await self._get_teams_channel(guild)
        if teams_channel is None:
            await ctx.send("❌ Teams channel not found.")
            return false
        # Create team embed and message
        embed = await self._create_team_embed(team_name, [])
        msg = await teams_channel.send(embed=embed)
        
        # Create team in database
        await self.bot.execute_db(
            "INSERT INTO team (name, discord_message_id, guild_id) VALUES (?, ?, ?)",
            (team_name, msg.id, guild.id)
        )
        
        # Create roles
        for role_type in ["captain", "player", "coach"]:
            role_name = f"{team_name}_{role_type}"
            role = await guild.create_role(name=role_name, mentionable=True)
            await self.bot.execute_db(
                "INSERT INTO server_role (guild_id, role_name) VALUES (?, ?)",
                (guild.id, role_name)
            )
        
        embed = await self._create_team_embed(team_name, [])
        msg = await teams_channel.fetch_message(msg.id)
        await msg.edit(embed=embed)

    async def _create_team_embed(self, team_name: str, members: list) -> discord.Embed:
        """Creates an embed for team display with current members and status"""
        embed = discord.Embed(title=f"Team {team_name}", color=discord.Color.blue())

        if not members or len(members) == 0:
            embed.description = "_No players yet_"
            return embed

        # Sort members by role
        captain = next((m for m in members if m["role_name"] == "captain"), None)
        players = [m for m in members if m["role_name"] == "player"]
        coaches = [m for m in members if m["role_name"] == "coach"]

        # Add fields for each role
        if captain:
            embed.add_field(name="👑 Captain", value=f"・{captain['nickname']}", inline=False)
        if players:
            embed.add_field(name="🧍 Players", value="\n".join(f"・{p['nickname']}" for p in players), inline=False)
        if coaches:
            embed.add_field(name="🧠 Coaches", value="\n".join(f"・{c['nickname']}" for c in coaches), inline=False)

        # Calculate team status
        count_captains = sum(m["role_name"] == "captain" for m in members)
        count_coaches = sum(m["role_name"] == "coach" for m in members)
        count_players = sum(m["role_name"] == "player" for m in members)

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

    @commands.command()
    @commands.has_role("Admin")
    async def create_team(self, ctx, team_name: str):
        """Create a new team"""
        guild = ctx.guild
        
        try:
            await self._create_team(ctx, guild, team_name)
            logger.info(f"Team {team_name} created in guild {guild.name}")

        except Exception as e:
            logger.error(f"Error creating team: {e}")
            await ctx.send(f"❌ Error creating team: {e}")
            
    @commands.command()
    @commands.has_role("Admin")
    async def delete_team(self, ctx, name: str):
        """Delete a team and all its players"""
        guild = ctx.guild

        try:
            # Check if in admin channel
            channel_name = ctx.channel.name
            if channel_name != "admin":
                await ctx.send("❌ This command can only be used in the **admin** channel.")
                return

            team = await self.bot.fetch_one(
                "SELECT id, discord_message_id FROM team WHERE name = ? AND guild_id = ?", 
                (name, guild.id)
            )

            if not team:
                await ctx.send(f"❌ No team named **{name}** found.")
                return

            # Delete message
            teams_channel = discord.utils.get(ctx.guild.text_channels, name="teams")
            try:
                msg = await teams_channel.fetch_message(team["discord_message_id"])
                await msg.delete()
            except Exception as e:
                logger.error(f"Failed to delete message: {e}")

            # Delete players and team
            await self.bot.execute_db(
                "DELETE FROM player WHERE team_id = ? AND guild_id = ?", 
                (team["id"], guild.id)
            )
            await self.bot.execute_db(
                "DELETE FROM team WHERE id = ? AND guild_id = ?", 
                (team["id"], guild.id)
            )

            # Delete roles
            roles = guild.roles
            for role_type in ["captain", "player", "coach"]:
                role = discord.utils.get(roles, name=f"{name}_{role_type}")
                if role:
                    await role.delete(reason=f"Team {name} removed")
                    await self.bot.execute_db(
                        "DELETE FROM server_role WHERE role_name = ? AND guild_id = ?",
                        (f"{name}_{role_type}", guild.id)
                    )

            await ctx.send(f"✅ Team **{name}** and all related data deleted.")

        except Exception as e:
            logger.error(f"Error deleting team: {e}")
            await ctx.send(f"❌ Error deleting team: {e}")

    @commands.command()
    @commands.has_role("Admin")
    async def add_player(self, ctx, team_name: str, nickname: str, steamid: str, role: str):
        """Add a player to a team"""
        guild = ctx.guild

        try:
            # Check if in admin channel
            channel_name = ctx.channel.name
            if channel_name != "admin":
                await ctx.send("❌ This command can only be used in the **admin** channel.")
                return

            # Get team
            team = await self.bot.fetch_one(
                "SELECT id FROM team WHERE name = ? AND guild_id = ?", 
                (team_name, guild.id)
            )
            if not team:
                await ctx.send(f"❌ No team named **{team_name}**.")
                return

            # Check if player already exists
            existing_player = await self.bot.fetch_one(
                "SELECT * FROM player WHERE (nickname = ? OR steamid = ?) AND guild_id = ?",
                (nickname, steamid, guild.id)
            )
            if existing_player:
                if existing_player["nickname"] == nickname:
                    await ctx.send(f"❌ A player with nickname **{nickname}** already exists.")
                else:
                    await ctx.send(f"❌ A player with Steam ID **{steamid}** already exists.")
                return

            # Get current team members
            members = await self.bot.fetch_all(
                "SELECT * FROM player WHERE team_id = ? AND guild_id = ?",
                (team["id"], guild.id)
            )

            # Check role limits
            count_captains = sum(1 for m in members if m["role_name"] == "captain")
            count_coaches = sum(1 for m in members if m["role_name"] == "coach")
            count_players = sum(1 for m in members if m["role_name"] == "player")

            if role == "captain":
                if count_captains >= 1:
                    await ctx.send("❌ There's already a captain.")
                    return
            elif role == "coach":
                if count_coaches >= 2:
                    await ctx.send("❌ Maximum of 2 coaches.")
                    return
            else:  # player
                if count_players >= 5:
                    await ctx.send("❌ Maximum of 5 players (including captain).")
                    return
                if count_players >= 4 and count_captains == 0:
                    await ctx.send("❌ You can't have 5 players without a captain.")
                    return

            # Add player
            await self.bot.execute_db(
                """INSERT INTO player (team_id, nickname, steamid, role_name, guild_id)
                VALUES (?, ?, ?, ?, ?)""",
                (team["id"], nickname, steamid, role, guild.id)
            )

            # Get team details for message update
            team_details = await self.bot.fetch_one(
                "SELECT name, discord_message_id FROM team WHERE id = ? AND guild_id = ?",
                (team["id"], guild.id)
            )
            if not team_details:
                logger.error("Could not find team details after adding player")
                return

            # Get updated member list
            updated_members = await self.bot.fetch_all(
                "SELECT nickname, role_name FROM player WHERE team_id = ? AND guild_id = ?",
                (team["id"], guild.id)
            )

            # Update embed
            embed = await self._create_team_embed(team_details["name"], updated_members)
            
            # Update message
            # Check if is started and get teams channel id
            teams_channel = await self._get_teams_channel(guild)
            if teams_channel is None:
                await ctx.send("❌ Teams channel not found.")
            if teams_channel:
                try:
                    msg = await teams_channel.fetch_message(team_details["discord_message_id"])
                    await msg.edit(embed=embed)
                    await ctx.send(f"✅ Added **{nickname}** to team **{team_name}** as {role}")
                except Exception as e:
                    logger.error(f"Failed to update message: {e}")
                    await ctx.send(f"⚠️ Player added but failed to update display: {e}")
            
        except Exception as e:
            logger.error(f"Error adding player: {e}")
            await ctx.send(f"❌ Error adding player: {e}")

    @commands.command()
    @commands.has_role("Admin")
    async def remove_player(self, ctx, team_name: str, nickname: str):
        """Remove a player from a team"""
        guild = ctx.guild

        try:
            # Check if in admin channel
            channel_name = ctx.channel.name
            if channel_name != "admin":
                await ctx.send("❌ This command can only be used in the **admin** channel.")
                return
            
            # Check if is started and get teams channel id
            teams_channel = await self._get_teams_channel(guild)
            if teams_channel is None:
                await ctx.send("❌ Teams channel not found.")

            # Get team
            team = await self.bot.fetch_one(
                "SELECT id, discord_message_id FROM team WHERE name = ? AND guild_id = ?", 
                (team_name, guild.id)
            )
            if not team:
                await ctx.send(f"❌ No team named **{team_name}**.")
                return

            # Remove player
            await self.bot.execute_db(
                "DELETE FROM player WHERE team_id = ? AND nickname = ? AND guild_id = ?",
                (team["id"], nickname, guild.id)
            )

            # Get remaining members
            remaining_members = await self.bot.fetch_all(
                "SELECT nickname, role_name FROM player WHERE team_id = ? AND guild_id = ?",
                (team["id"], guild.id)
            )

            # Update embed
            embed = await self._create_team_embed(team_name, remaining_members)

            # Update message
            if teams_channel:
                try:
                    msg = await teams_channel.fetch_message(team["discord_message_id"])
                    await msg.edit(embed=embed)
                    await ctx.send(f"✅ Removed **{nickname}** from team **{team_name}**")
                except Exception as e:
                    logger.error(f"Failed to update message: {e}")
                    await ctx.send(f"⚠️ Player removed but failed to update display: {e}")

        except Exception as e:
            logger.error(f"Error removing player: {e}")
            await ctx.send(f"❌ Error removing player: {e}")

    @commands.command()
    @commands.has_role("Admin")
    async def mock_teams(self, ctx):
        """Create mock teams for testing"""
        guild = ctx.guild
        
        try:
            # Check if in admin channel
            channel_name = ctx.channel.name
            logger.info(f"Channel name: {channel_name}")
            if channel_name != "admin":
                await ctx.send("❌ This command can only be used in the **admin** channel.")
                return

            # Check if is started and get teams channel id
            teams_channel = await self._get_teams_channel(guild)
            if teams_channel is None:
                await ctx.send("❌ Teams channel not found.")

            teams = await self.bot.fetch_all(
                    "SELECT * FROM team WHERE guild_id = ?",
                    (guild.id,)
                )

            for i in range(1, (17 - len(teams))):
                team_name = f"TeamX_{i}"
                
                await self._create_team(ctx, guild, team_name)

                # Get team ID
                team = await self.bot.fetch_one(
                    "SELECT id FROM team WHERE name = ? AND guild_id = ?",
                    (team_name, guild.id)
                )
                
                # Create players
                players = [
                    (f"{team_name}_captain", "captain"),
                    (f"{team_name}_player1", "player"),
                    (f"{team_name}_player2", "player"),
                    (f"{team_name}_player3", "player"),
                    (f"{team_name}_player4", "player"),
                    (f"{team_name}_coach", "coach")
                ]

                for nickname, role in players:
                    steamid = str(random.randint(100000, 999999))
                    await self.add_player(ctx, team_name, nickname, steamid, role)

            await ctx.send("✅ Successfully created 16 mock teams!")
            
        except Exception as e:
            logger.error(f"Error creating mock teams: {e}")
            await ctx.send(f"❌ Error creating mock teams: {e}")
            

async def setup(bot):
    await bot.add_cog(TeamManagement(bot))