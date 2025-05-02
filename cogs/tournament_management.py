import random
import discord
from discord.ext import commands
import os
import logging

# Configure logger
logger = logging.getLogger('discord.setup')
logger.setLevel(logging.INFO)

class TournamentManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _get_teams_on_round(self, ctx, round: str) -> list:
        """Get teams on the given round"""
        guild = ctx.guild
        
        valid_rounds = ['is_quaterfinalist', 'is_semifinalist', 'is_finalist', 'is_third_place']
        if round not in valid_rounds:
            logger.error(f"Invalid round parameter: {round}")
            return []
        
        try:
            sql = f"SELECT * FROM team WHERE {round} = 1 AND guild_id = ?"
            teams = await self.bot.fetch_all(sql, (guild.id,))
            logger.info(f"Found {len(teams)} teams for round {round}")
            return teams
        except Exception as e:
            logger.error(f"Error getting teams for round {round}: {e}")
            return []
        
    async def _get_teams_with_wins(self, ctx, wins: int, losses: int) -> list:
        """Get teams with specific wins and losses"""
        try:
            teams = await self.bot.fetch_all(
                """
                SELECT * FROM team 
                WHERE swiss_wins = ? 
                AND swiss_losses = ? 
                AND guild_id = ?
                """,
                (wins, losses, self.bot.guilds[0].id)
            )
            logger.info(f"Found {len(teams)} teams with {wins} wins and {losses} losses")
            return teams
        except Exception as e:
            logger.error(f"Error getting teams with wins/losses: {e}")
            return []
    
    async def _get_summary_channel(self, guild) -> any:
        """Fetches the summary channel id"""
        try:
                summary_channel_setting = await self.bot.fetch_one(
                    "SELECT * FROM setting WHERE key = ? AND guild_id = ?",
                    ("summary_channel_id", guild.id)
                )
                if summary_channel_setting is None:
                    return None

        except Exception as e:
            return None

        summary_channel_id = int(summary_channel_setting["value"])
        summary_channel = self.bot.get_channel(summary_channel_id)
        logger.info(f"channel: {summary_channel}")
        return summary_channel
    
    async def _get_info_message_id(self, guild) -> str:
        """Fetches the info message id"""
        try:
                summary_msg_setting = await self.bot.fetch_one(
                    "SELECT * FROM setting WHERE key = ? AND guild_id = ?",
                    ("summary_msg_id", guild.id)
                )
                if summary_msg_setting is None:
                    return None

        except Exception as e:
            return None

        info_message_id = int(summary_msg_setting["value"])
        return info_message_id

    async def _random_games(self, teams: list) -> list:
        """Randomize the games for the given teams"""
        if not teams:
            logger.warning("No teams provided for random games")
            return []
            
        if len(teams) % 2 != 0:
            logger.error("Uneven number of teams")
            raise ValueError("Number of teams must be even")
        
        # Shuffle the teams
        random.shuffle(teams)
        
        # Create pairs of teams
        games = []
        for i in range(0, len(teams), 2):
            if i + 1 < len(teams):  # Safety check
                games.append((teams[i], teams[i + 1]))
                
        return games
    
    async def _create_pickveto_embed(self, ctx, game) -> discord.Embed:
        """Creates an embed for game pick/veto"""
        guild = ctx.guild

        message = ""
        rounds = ""
        logger.info(f"_create_pickveto_embed: game_id --> {game['id']}")
        if game is not None:
            logger.info("Game is not None")
            vetoes = None
            try:
                vetoes = await self.bot.fetch_all(
                        "SELECT * FROM veto WHERE game_id = ? AND guild_id = ?",
                        (game["id"], guild.id)
                    )
                logger.info(f"vetoes : {vetoes}")
            except Exception as e:
                vetoes = None

            # Get game picks
            picks = None
            try:
                picks = await self.bot.fetch_all(
                        "SELECT * FROM pick WHERE game_id = ? AND guild_id = ?",
                        (game["id"], guild.id)
                    )
                logger.info(f"picks : {picks}")
            except Exception as e:
                picks = None
            
            team_one_id = game["team_one_id"]
            team_two_id = game["team_two_id"]

            team_one = await self.bot.fetch_one(
                    "SELECT * FROM team WHERE id = ? AND guild_id = ?",
                    (team_one_id, guild.id)
                )
            
            team_two = await self.bot.fetch_one(
                    "SELECT * FROM team WHERE id = ? AND guild_id = ?",
                    (team_two_id, guild.id)
                )

            team_one_name = team_one["name"]
            team_two_name = team_two["name"]
            logger.info(f"team_one_name : {team_one_name}")
            logger.info(f"team_two_name : {team_two_name}")

            # Add fields for veto
            if len(vetoes) > 0:
                message = f"・**{team_one_name}** vetoed {vetoes[0]['map_name']}"
            if len(vetoes) > 1:
                message += f"\n・**{team_two_name}** vetoed {vetoes[1]['map_name']}"
            if len(picks) > 0:
                message += f"\n・**{team_one_name}** picked {picks[0]['map_name']}"
            if len(picks) > 1:
                message += f"\n・**{team_two_name}** picked {picks[1]['map_name']}"
            if len(vetoes) > 2:
                message += f"\n・**{team_one_name}** vetoed {vetoes[2]['map_name']}"
            if len(vetoes) > 3:
                message += f"\n・**{team_two_name}** vetoed {vetoes[3]['map_name']}"
            if len(picks) > 2:
                message += f"\n・**Decider map** is {picks[2]['map_name']}"
            logger.info(f"message : {message}")

            game_maps = await self.bot.fetch_all(
                    "SELECT * FROM game_map WHERE game_id = ? AND guild_id = ?",
                    (game["id"], guild.id)
                )
            logger.info(f"game_maps : {game_maps}")

            if game_maps is not None:
                i = 0
                for game_map in game_maps:
                    team_id_winner = game_map["team_id_winner"]
                    if team_id_winner == team_one_id:
                        winner_name = team_one_name
                    else:
                        winner_name = team_two_name
                    rounds += f"・**{winner_name}** won {picks[i]['map_name']}.\n"
                    i = i + 1
            else:
                rounds = "No round played yet."

        logger.info(f"rounds: {rounds}")
        
        embed = discord.Embed(title=f"{team_one_name} vs {team_two_name} picks, bans and maps", color=discord.Color.blue())
        embed.description = f"Game between {team_one_name} vs {team_two_name}.\n"
        embed.add_field(name="Picks & Bans", value=message, inline=False)
        embed.add_field(name="Rounds", value=rounds, inline=False)
        
        return embed

    async def _setup_game_channels(self, ctx, guild, category, team_one, team_two):
        """Setup channels for a game with proper permissions"""
        try:
            # Get roles
            roles = {
                "admin": discord.utils.get(guild.roles, name="Admin"),
                "team_one_captain": discord.utils.get(guild.roles, name=f"{team_one['name']}_captain"),
                "team_one_coach": discord.utils.get(guild.roles, name=f"{team_one['name']}_coach"),
                "team_one_player": discord.utils.get(guild.roles, name=f"{team_one['name']}_player"),
                "team_two_captain": discord.utils.get(guild.roles, name=f"{team_two['name']}_captain"),
                "team_two_coach": discord.utils.get(guild.roles, name=f"{team_two['name']}_coach"),
                "team_two_player": discord.utils.get(guild.roles, name=f"{team_two['name']}_player")
            }

            # Validate roles exist
            if not all(roles.values()):
                missing = [k for k, v in roles.items() if not v]
                logger.error(f"Missing roles: {missing}")
                await ctx.send(f"❌ Missing required roles: {', '.join(missing)}")
                return None

            channel_name = f"admin-{team_one['name']}-vs-{team_two['name']}"
            
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
            
            admin_channel = await category.create_text_channel(channel_name, overwrites=admin_overwrites)
            await admin_channel.send(f"This channel will be used for communicating between org and teams on this game, remember that only admins and users with role {team_one['name']}_captain and {team_two['name']}_captain can write in this channel.")
            await admin_channel.send(f"Time of picks and bans, {team_one['name']} captain please send your veto with the command `!veto <mapname>`")

            # Create public channel
            public_overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                roles["admin"]: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
            
            channel_name = f"{team_one['name']}-vs-{team_two['name']}"

            public_channel = await category.create_text_channel(channel_name, overwrites=public_overwrites)
            embed = discord.Embed(title=f"{team_one['name']} vs {team_two['name']} picks, bans and maps", color=discord.Color.blue())
            embed.description = f"Game between {team_one['name']} vs {team_two['name']}.\n"
            msg = await public_channel.send(embed=embed)

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
            
            voice1 = await category.create_voice_channel(team_one['name'], overwrites=voice1_overwrites)
            voice2 = await category.create_voice_channel(team_two['name'], overwrites=voice2_overwrites)

            return {
                "admin": admin_channel,
                "public": public_channel,
                "public_game_message": msg,
                "voice1": voice1,
                "voice2": voice2
            }
            
        except Exception as e:
            logger.error(f"Error setting up channels: {e}")
            await ctx.send(f"❌ Error setting up channels: {e}")
            return None

    async def _create_game(self, ctx, game, category_name: str, game_type: str):
        """Create a new game between two teams"""
        team_one = game[0]
        team_two = game[1]
        guild = ctx.guild

        try:
            # Create channels and get roles
            game_category = discord.utils.get(guild.categories, name=category_name)
            if not game_category:
                logger.error(f"Category {category_name} not found")
                return

            # Check if game already exists
            existing_game = await self.bot.fetch_one(
                """SELECT * FROM game WHERE 
                ((team_one_id = ? AND team_two_id = ?) OR 
                    (team_one_id = ? AND team_two_id = ?)) AND
                game_type = ? AND guild_id = ?""",
                (team_one["id"], team_two["id"], team_two["id"], team_one["id"], game_type, guild.id)
            )
            
            if existing_game:
                await ctx.send(f"❌ Game already exists between {team_one['name']} and {team_two['name']}!")
                return

            # Create channels and get permissions setup
            channels = await self._setup_game_channels(ctx, guild, game_category, team_one, team_two)
            if not channels:
                return
            
            # Insert game into database
            await self.bot.execute_db(
                """INSERT INTO game (
                    team_one_id, team_two_id, winner_number, game_type,
                    admin_game_channel_id, game_channel_id,
                    voice_channel_team_one_id, voice_channel_team_two_id, guild_id, 
                    public_game_message_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    team_one["id"], team_two["id"], -1, game_type,
                    channels["admin"].id, channels["public"].id,
                    channels["voice1"].id, channels["voice2"].id,
                    guild.id, channels["public_game_message"].id
                )
            )

            logger.info("Get created game")
            created_game = await self.bot.fetch_one(
                "SELECT * FROM game WHERE admin_game_channel_id = ? AND guild_id = ?",
                (channels["admin"].id, guild.id)
            )
            logger.info(f"Created game: {created_game}")

            embed = await self._create_pickveto_embed(ctx, created_game)
            logger.info(f"EMBED: {embed}")
            await channels["public_game_message"].edit(embed=embed)
            
            logger.info(f"Created game: {team_one['name']} vs {team_two['name']}")
            
        except Exception as e:
            logger.error(f"Error creating game: {e}")
            await ctx.send(f"❌ Error creating game: {e}")

    async def _create_swiss_games(self, ctx, round: int) -> list:
        """Create the swiss round games"""
        games = []
        
        try:
            if round == 1:
                teams = await self._get_teams_with_wins(ctx, wins=0, losses=0)
                games = await self._random_games(teams)
            elif round == 2:
                teams_1_0 = await self._get_teams_with_wins(ctx, wins=1, losses=0)
                games = await self._random_games(teams_1_0)
                teams_0_1 = await self._get_teams_with_wins(ctx, wins=0, losses=1)
                games.extend(await self._random_games(teams_0_1)) 
            elif round == 3:
                teams_2_0 = await self._get_teams_with_wins(ctx, wins=2, losses=0)
                games = await self._random_games(teams_2_0)
                teams_1_1 = await self._get_teams_with_wins(ctx, wins=1, losses=1)
                games.extend(await self._random_games(teams_1_1))
                teams_0_2 = await self._get_teams_with_wins(ctx, wins=0, losses=2)
                games.extend(await self._random_games(teams_0_2))
            elif round == 4:
                teams_2_1 = await self._get_teams_with_wins(ctx, wins=2, losses=1)
                games = await self._random_games(teams_2_1)
                teams_1_2 = await self._get_teams_with_wins(ctx, wins=1, losses=2)
                games.extend(await self._random_games(teams_1_2))
            elif round == 5:
                teams_2_2 = await self._get_teams_with_wins(ctx, wins=2, losses=2)
                games = await self._random_games(teams_2_2)

            logger.info(f"Created {len(games)} games for round {round}")
            
            # Verify games is not empty and is iterable
            if not games:
                logger.warning(f"No games created for round {round}")
                return []
                
            return games
        except Exception as e:
            logger.error(f"Error creating swiss games for round {round}: {e}")
            await ctx.send(f"❌ Error creating games: {e}")
            return []

    async def _create_playoff_games(self, ctx, round: str) -> list:
        """Create the playoff games for the given round"""
        # Check if the round is valid
        if round not in ['quarterfinal', 'semifinal', 'final', 'third_place']:
            logger.error("Round must be quarterfinal, semifinal, final or third_place")
            return
        # Create the games for the round using a switch statement for rounds from 1 to 5.
        if round == 'quarterfinal':
            teams = await self._get_teams_on_round(ctx, round='is_quaterfinalist')
            logger.info(f"Teams for quarterfinal: {teams}")
            if len(teams) != 8:
                logger.error("Number of teams for quarterfinal must be 8")
                return
            games = await self._random_games(teams)
        elif round == 'semifinal':
            teams = await self._get_teams_on_round(ctx, round='is_semifinalist')
            games = await self._random_games(teams)
        elif round == 'final':
            teams = await self._get_teams_on_round(ctx, round='is_finalist')
            games = await self._random_games(teams)
        elif round == 'third_place':
            teams = await self._get_teams_on_round(ctx, round='is_third_place')
            games = await self._random_games(teams)

        return games

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
                             
    async def _is_current_round_finished(self, ctx):
        """Check if the current round is finished and create next round if needed"""
        guild = ctx.guild
        
        try:
            # Check number of finished games vs total games
            count_finished = await self.bot.fetch_one(
                "SELECT COUNT(*) as count FROM game WHERE winner_number != -1 AND guild_id = ?", 
                (guild.id,)
            )
            count_all = await self.bot.fetch_one(
                "SELECT COUNT(*) as count FROM game WHERE guild_id = ?", 
                (guild.id,)
            )

            finished = count_finished["count"]
            total = count_all["count"]

            if finished == total:
                logger.info(f"Round finished! Games finished: {finished}")
                games = []
                next_game_type = ""
                category_name = ""

                # Determine next round based on number of finished games
                if finished == 8:  # round 1 finished
                    next_game_type = "swiss_2"
                    category_name = "Swiss stage round 2"
                    games = await self._create_swiss_games(ctx, round=2)
                elif finished == 16:  # round 2 finished
                    next_game_type = "swiss_3"
                    category_name = "Swiss stage round 3"
                    games = await self._create_swiss_games(ctx, round=3)
                elif finished == 24:  # round 3 finished
                    next_game_type = "swiss_4"
                    category_name = "Swiss stage round 4"
                    games = await self._create_swiss_games(ctx, round=4)
                elif finished == 30:  # round 4 finished
                    next_game_type = "swiss_5"
                    category_name = "Swiss stage round 5"
                    games = await self._create_swiss_games(ctx, round=5)
                elif finished == 33:  # swiss stage finished
                    next_game_type = "quarterfinal"
                    category_name = "Quarterfinals"
                    games = await self._create_playoff_games(ctx, round='quarterfinal')
                elif finished == 37:  # quarterfinals finished
                    next_game_type = "semifinal"
                    category_name = "Semifinals"
                    games = await self._create_playoff_games(ctx, round='semifinal')
                elif finished == 39:  # semifinals finished
                    # Create both final and third place games
                    next_game_type = "final"
                    category_name = "Finals"
                    games = await self._create_playoff_games(ctx, round='final')
                    
                    third_place_games = await self._create_playoff_games(ctx, round='third_place')
                    if third_place_games:
                        for game in third_place_games:
                            await self._create_game(ctx, game, category_name="Third Place", game_type="third_place")
                        final_place_games = await self._create_playoff_games(ctx, round='final')
                        for game in final_place_games:
                            await self._create_game(ctx, game, category_name="Final", game_type="final")

                # Create games for next round if any
                if games and next_game_type:
                    for game in games:
                        logger.info(f"Creating game for {game[0]['name']} vs {game[1]['name']}")
                        await self._create_game(ctx, game, category_name=category_name, game_type=next_game_type)
                    await ctx.send(f"✅ Round finished! Created games for {next_game_type}")
                elif finished == 41:  # tournament finished
                    await ctx.send("🏆 Tournament finished!")

        except Exception as e:
            logger.error(f"Error checking round status: {e}")
            await ctx.send(f"❌ Error checking round status: {e}")
        await self.summary(ctx)


    @commands.command()
    @commands.has_role("Admin")
    async def all_teams_created(self, ctx):
        guild = ctx.guild
        
        channel_name = ctx.channel.name
        logger.info(f"Channel name: {channel_name}")
        if channel_name != "admin":
            await ctx.send("❌ This command can only be used in the **admin** channel.")
            return
            
        # Check number of teams
        team_count = await self.bot.fetch_one("SELECT COUNT(*) as count FROM team WHERE guild_id = ?", (guild.id,))
        count = team_count["count"]
        if count != 16:
            await ctx.send("❌ 16 teams are needed!")
            return

        games = await self._create_swiss_games(ctx, round=1)
        
        category_name = "Swiss stage round 1"
        next_game_type = "swiss_1"
        # Create the games
        for game in games:
            logger.info(f"Creating game for {game[0]['name']} vs {game[1]['name']}")
            embed = await self._create_game(ctx, game, category_name=category_name, game_type=next_game_type)
            
        await ctx.send(f"✅ Created games for {next_game_type}!")

        await self.summary(ctx)

        return       
    
    @commands.command()
    @commands.has_role("Admin")
    async def summary(self, ctx):
        guild = ctx.guild
        
        embed_info = await self._embed_summary(ctx)
        summary_channel = await self._get_summary_channel(guild)
        info_message_id = await self._get_info_message_id(guild)
        msg = await summary_channel.fetch_message(info_message_id)
        await msg.edit(embed=embed_info)

        return       
 
    @commands.command()
    @commands.has_role("Admin")
    async def autoresult(self, ctx):
        await self.result(ctx, 1)
        await self.result(ctx, 1)

    # Do  it by map
    @commands.command()
    @commands.has_role("Admin")
    async def result(self, ctx, winner:int):                         
        """Set the result of the map"""

        try:
            guild = ctx.guild
            channel_id = ctx.channel.id
            # Check game with guild_id == ctx.guild.id and admin_game_channel_id == channel_id
            game = await self.bot.fetch_one(
                "SELECT * FROM game WHERE admin_game_channel_id = ? AND guild_id = ?", 
                (channel_id, guild.id)
            )
            # if game no exists, log error and return
            if not game:
                await ctx.send("❌ This command can only be used in an **admin game** channel.")
                return
            game_id = game["id"]

            picks = await self.bot.fetch_all(
                        "SELECT * FROM pick WHERE game_id = ? AND guild_id = ?",
                        (game["id"], guild.id)
                    )
            if len(picks) != 3:
                await ctx.send("There are not 3 picks already.")
                return

            # Check if the winner is valid
            if winner not in [1, 2]:
                await ctx.send("❌ Invalid winner!")
                return

            if game["winner_number"] == 1 or game["winner_number"] == 2:
                await ctx.send("❌ Game already finished!")
                return

            # Set team results into teams table
            game_type = game["game_type"]
            team_one_id = game["team_one_id"]
            team_two_id = game["team_two_id"]

            # get teams from the database
            team_one = await self.bot.fetch_one(
                "SELECT * FROM team WHERE id = ? AND guild_id = ?", 
                (team_one_id, guild.id)
            )
            team_two = await self.bot.fetch_one(
                "SELECT * FROM team WHERE id = ? AND guild_id = ?", 
                (team_two_id, guild.id)
            )

            winner_team = team_one if winner == 1 else team_two
            looser_team = team_two if winner == 1 else team_one

            # if game_type contains "swiss" then update the swiss_wins and swiss_losses columns
            if "swiss" in game_type:
                await self.bot.execute_db(
                    "INSERT INTO game_map (guild_id, game_id, team_id_winner) VALUES (?,?,?)",
                    (guild.id, game["id"], winner_team["id"])
                )

                game_maps = await self.bot.fetch_all(
                    "SELECT * FROM game_map WHERE guild_id = ? AND game_id = ? AND team_id_winner = ?",
                    (guild.id, game["id"], winner_team["id"])
                )
                number = "none"
                quaterfinalist = False
                finished = False
                if len(game_maps) == 1:
                    number = "first"
                    finished = False
                elif len(game_maps) == 2:
                    number = "second"
                    finished = True
                elif len(game_maps) == 3:
                    number = "decider"
                    finished = True
                
                message = f"{winner_team['name']} won {number} map."
                if finished:
                    quaterfinalist = winner_team["swiss_wins"] + 1 == 3
                    await self.bot.execute_db(
                        "UPDATE team SET swiss_wins = swiss_wins + 1, is_quaterfinalist = ? WHERE id = ?",
                        (1 if quaterfinalist else 0, winner_team["id"])
                    )   
                    await self.bot.execute_db(
                        "UPDATE team SET swiss_losses = swiss_losses + 1 WHERE id = ? AND guild_id = ?",
                        (looser_team["id"], guild.id)
                    )
                    await self.bot.execute_db(
                        "UPDATE game SET winner_number = ? WHERE id = ?", 
                        (winner, game_id)
                    )
                    message += f"\n{winner_team['name']} won the game."
                
            elif game_type == "quarterfinal":
                await self.bot.execute_db(
                    "INSERT INTO game_map (guild_id, game_id, team_id_winner) VALUES (?,?,?)",
                    (guild.id, game["id"], winner_team["id"])
                )

                game_maps = await self.bot.fetch_all(
                    "SELECT * FROM game_map WHERE guild_id = ? AND game_id = ? AND team_id_winner = ?",
                    (guild.id, game["id"], winner_team["id"])
                )
                number = "none"
                finished = False
                if len(game_maps) == 1:
                    number = "first"
                elif len(game_maps) == 2:
                    number = "second"
                    finished = True
                elif len(game_maps) == 3:
                    number = "decider"      
                message = f"{winner_team['name']} won {number} map."
                if finished:
                    # Update the game in the database
                    await self.bot.execute_db(
                        "UPDATE game SET winner_number = ? WHERE id = ?", 
                        (winner, game_id)
                    )
                    await self.bot.execute_db(
                        "UPDATE team SET is_semifinalist = ? WHERE id = ? AND guild_id = ?",
                        (1, winner_team["id"], guild.id)
                    )          
                    message += f"\n{winner_team['name']} won the game."
            elif game_type == "semifinal":
                await self.bot.execute_db(
                    "INSERT INTO game_map (guild_id, game_id, team_id_winner) VALUES (?,?,?)",
                    (guild.id, game["id"], winner_team["id"])
                )

                game_maps = await self.bot.fetch_all(
                    "SELECT * FROM game_map WHERE guild_id = ? AND game_id = ? AND team_id_winner = ?",
                    (guild.id, game["id"], winner_team["id"])
                )
                number = "none"
                finished = False
                if len(game_maps) == 1:
                    number = "first"
                elif len(game_maps) == 2:
                    number = "second"
                    finished = True
                elif len(game_maps) == 3:
                    number = "decider"    
                    finished = True  
                message = f"{winner_team['name']} won {number} map."
                if finished:
                    await self.bot.execute_db(
                        "UPDATE team SET is_finalist = 1 WHERE id = ? AND guild_id = ?",
                        (winner_team["id"], guild.id)
                    )
                    await self.bot.execute_db(
                        "UPDATE team SET is_third_place = 1 WHERE id = ? AND guild_id = ?",
                        (looser_team["id"], guild.id)
                    )
                    # Update the game in the database
                    await self.bot.execute_db(
                        "UPDATE game SET winner_number = ? WHERE id = ?", 
                        (winner, game_id)
                    )
                    message += f"\n{winner_team['name']} won the game."
            elif game_type == "final":
                await self.bot.execute_db(
                    "INSERT INTO game_map (guild_id, game_id, team_id_winner) VALUES (?,?,?)",
                    (guild.id, game["id"], winner_team["id"])
                )

                game_maps = await self.bot.fetch_all(
                    "SELECT * FROM game_map WHERE guild_id = ? AND game_id = ? AND team_id_winner = ?",
                    (guild.id, game["id"], winner_team["id"])
                )
                number = "none"
                finished = False
                if len(game_maps) == 1:
                    number = "first"
                elif len(game_maps) == 2:
                    number = "second"
                    finished = True
                elif len(game_maps) == 3:
                    number = "decider"     
                    finished = True 
                message = f"{winner_team['name']} won {number} map."
                if finished:
                    # Update the game in the database
                    await self.bot.execute_db(
                        "UPDATE game SET winner_number = ? WHERE id = ?", 
                        (winner, game_id)
                    )        
                    message += f"\n{winner_team['name']} won the game and is the winner of the tournament."
            elif game_type == "third_place":
                await self.bot.execute_db(
                    "INSERT INTO game_map (guild_id, game_id, team_id_winner) VALUES (?,?,?)",
                    (guild.id, game["id"], winner_team["id"])
                )

                game_maps = await self.bot.fetch_all(
                    "SELECT * FROM game_map WHERE guild_id = ? AND game_id = ? AND team_id_winner = ?",
                    (guild.id, game["id"], winner_team["id"])
                )
                number = "none"
                finished = False
                if len(game_maps) == 1:
                    number = "first"
                elif len(game_maps) == 2:
                    number = "second"
                    finished = True
                elif len(game_maps) == 3:
                    number = "decider"     
                    finished = True    
                message = f"{winner_team['name']} won {number} map."
                if finished:
                    # Update the game in the database
                    await self.bot.execute_db(
                        "UPDATE game SET winner_number = ? WHERE id = ?", 
                        (winner, game_id)
                    )        
                    message += f"\n{winner_team['name']} won the game and is the gets the third place of the tournament."
            await ctx.send(f"✅ Map finished! Winner: {winner_team['name']}")
            if finished:
            # Delete the voice channels
                voice_channel_team_one_name = team_one["name"]
                voice_channel_team_one = discord.utils.get(guild.voice_channels, name=voice_channel_team_one_name)
                if voice_channel_team_one:
                    await voice_channel_team_one.delete()
                voice_channel_team_two_name = team_two["name"]
                voice_channel_team_two = discord.utils.get(guild.voice_channels, name=voice_channel_team_two_name)
                if voice_channel_team_two:
                    await voice_channel_team_two.delete()

                await ctx.send(f"✅ Game finished! Winner: {winner_team['name']}")
            
            public_channel = self.bot.get_channel(game["game_channel_id"])
            if public_channel:
                try:
                    await public_channel.send(message)
                except Exception as e:
                    logger.error(f"Failed to update message: {e}")
                    await ctx.send(f"⚠️ Pick added but failed to update display: {e}")

        except Exception as e:
            logger.error(f"Error processing result: {e}")
            await ctx.send(f"❌ Error: {e}")

        public_game_message_id = game["public_game_message_id"]
        game_channel_id = game["game_channel_id"]
        game_channel = self.bot.get_channel(game_channel_id)
        msg = await game_channel.fetch_message(public_game_message_id)

        embed = await self._create_pickveto_embed(ctx, game)
        await msg.edit(embed=embed)
        await self.summary(ctx)
        await self._is_current_round_finished(ctx)

async def setup(bot):
    await bot.add_cog(TournamentManagement(bot))