import random
import discord
from discord.ext import commands
import os
import logging

# Configure logger
logger = logging.getLogger('discord.setup')
logger.setLevel(logging.INFO)

class GameManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db

    async def _get_game(self, channel_id: int, guild: int):
        try:
            # Get game id
            game = await self.bot.fetch_one(
                "SELECT * FROM game WHERE admin_game_channel_id = ? AND guild_id = ?",
                (channel_id, guild)
            )
            return game
        except Exception as e:
            logger.error(f"Error getting game: {e}")
            return None     
        
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

    @commands.command()
    async def pick(self, ctx, map_name: str):
        guild = ctx.guild
        channel_id = ctx.channel.id
        message = ""
        
        # Get game id
        game = await self._get_game(channel_id, guild.id)
        if game is None:
            message = "No game found for this channel."
            await ctx.send(message)
            return

        # Get game vetoes
        vetoes = None
        try:
            vetoes = await self.bot.fetch_all(
                    "SELECT * FROM veto WHERE game_id = ? AND guild_id = ?",
                    (game["id"], guild.id)
                )
        except Exception as e:
            vetoes = None
        number_of_vetoes = len(vetoes) if vetoes is not None else 0

        # Get game picks
        picks = None
        try:
            picks = await self.bot.fetch_all(
                    "SELECT * FROM pick WHERE game_id = ? AND guild_id = ?",
                    (game["id"], guild.id)
                )
        except Exception as e:
            picks = None
        number_of_picks = len(picks) if picks is not None else 0

        team_picking_id = -1
        if (number_of_picks % 2 == 0):
            team_picking_id = game["team_one_id"]
            team_not_picking_id = game["team_two_id"]
        else:
            team_picking_id = game["team_two_id"]
            team_not_picking_id = game["team_one_id"]

        # Get team that is picking turn
        team_picking = await self.bot.fetch_one(
                "SELECT * FROM team WHERE id = ? AND guild_id = ?",
                (team_picking_id, guild.id)
            )
        team_not_picking = await self.bot.fetch_one(
                "SELECT * FROM team WHERE id = ? AND guild_id = ?",
                (team_not_picking_id, guild.id)
            )
        team_picking_name = team_picking["name"]
        team_not_picking_name = team_not_picking["name"]

        # Check if sender is team captain
        roles = ctx.author.roles
        role_name = f"{team_picking_name}_captain"
        if role_name not in [role.name for role in roles]:
            message = f"You are not the captain of {team_picking_name}."
            await ctx.send(message)
            return    

        # Map pool
        valid_maps = ["ancient", "inferno", "anubis", "nuke", "mirage", "dust2", "train"]
        if map_name not in valid_maps:
            message = "Invalid map name. Possible values are \"ancient\", \"inferno\", \"anubis\", \"nuke\", \"mirage\", \"dust2\", \"train\". Don't use quotes."
            await ctx.send(message)
            return
        
        # Get all vetoed map names
        selected_maps = []
        if vetoes is not None:
            for veto in vetoes:
                selected_maps.append(veto["map_name"])
        if picks is not None:
            for pick in picks:
                selected_maps.append(pick["map_name"])

        if map_name in selected_maps:
            message = "Map already vetoed or selected."
            await ctx.send(message)
            return
        is_veto_time = (number_of_vetoes == 0 or number_of_vetoes == 1 or (number_of_vetoes == 2 and number_of_picks == 2))
        is_pick_time = (number_of_vetoes == 2 and (number_of_picks == 0 or number_of_picks == 1))
        veto_finished = (number_of_vetoes == 4 and number_of_picks > 2)
        if is_pick_time:
            await self.bot.execute_db(
                    "INSERT INTO pick (order_pick, game_id, team_id, map_name, guild_id) VALUES (?, ?, ?, ?, ?)",
                    ((number_of_picks + 1), game["id"], team_picking_id, map_name, guild.id)
                )
            if number_of_picks == 0 or number_of_picks == 2:
                message = f"""
                    {team_picking_name} picked {map_name}.\n
                    Turn of {team_picking_name} of picking map. Write `!pick <map_name>` to pick a map.\n
                """
            elif number_of_picks == 1:
                message = f"""
                    {team_picking_name} picked {map_name}.\n
                    Turn of {team_not_picking_name} of vetoing map. Write  `!veto <map_name>` to veto a map.\n
                """
        elif is_veto_time:
            message = f"""
                Is not pick turn. Please check list and veto a map.
            """
        elif veto_finished:
            message = f"""
                Veto finished and maps have been decided.
            """    
        await ctx.send(message)
           
        try:
            new_vetoes = await self.bot.fetch_all(
                    "SELECT * FROM veto WHERE game_id = ? AND guild_id = ?",
                    (game["id"], guild.id)
                )
        except Exception as e:
            new_vetoes = None

        # Get game picks
        new_picks = None
        try:
            new_picks = await self.bot.fetch_all(
                    "SELECT * FROM pick WHERE game_id = ? AND guild_id = ?",
                    (game["id"], guild.id)
                )
        except Exception as e:
            new_picks = None
        number_of_picks = len(new_picks) if new_picks is not None else 0

        # Update message
        embed = await self._create_pickveto_embed(ctx, game)
            
        public_channel = self.bot.get_channel(game["game_channel_id"])
        if public_channel:
            try:
                msg = await public_channel.fetch_message(game["public_game_message_id"])
                await msg.edit(embed=embed)
            except Exception as e:
                logger.error(f"Failed to update message: {e}")
                await ctx.send(f"⚠️ Pick added but failed to update display: {e}")

    @commands.command()
    async def veto(self, ctx, map_name: str):
        guild = ctx.guild
        channel_id = ctx.channel.id
        message = ""
        
        # Get game id
        game = await self._get_game(channel_id, guild.id)
        if game is None:
            message = "No game found for this channel."
            await ctx.send(message)
            return

        # Get game vetoes
        vetoes = None
        try:
            vetoes = await self.bot.fetch_all(
                    "SELECT * FROM veto WHERE game_id = ? AND guild_id = ?",
                    (game["id"], guild.id)
                )
        except Exception as e:
            vetoes = None
        number_of_vetoes = len(vetoes) if vetoes is not None else 0

        # Get game picks
        picks = None
        try:
            picks = await self.bot.fetch_all(
                    "SELECT * FROM pick WHERE game_id = ? AND guild_id = ?",
                    (game["id"], guild.id)
                )
        except Exception as e:
            picks = None
        number_of_picks = len(picks) if picks is not None else 0

        team_vetoing_id = -1
        if (number_of_vetoes % 2 == 0):
            team_vetoing_id = game["team_one_id"]
            team_not_vetoing_id = game["team_two_id"]
        else:
            team_vetoing_id = game["team_two_id"]
            team_not_vetoing_id = game["team_one_id"]

        # Get team that is vetoing turn
        team_vetoing = await self.bot.fetch_one(
                "SELECT * FROM team WHERE id = ? AND guild_id = ?",
                (team_vetoing_id, guild.id)
            )
        team_not_vetoing = await self.bot.fetch_one(
                "SELECT * FROM team WHERE id = ? AND guild_id = ?",
                (team_not_vetoing_id, guild.id)
            )
        team_vetoing_name = team_vetoing["name"]
        team_not_vetoing_name = team_not_vetoing["name"]

        # Check if sender is team captain
        roles = ctx.author.roles
        role_name = f"{team_vetoing_name}_captain"
        if role_name not in [role.name for role in roles]:
            message = f"You are not the captain of {team_vetoing_name}."
            await ctx.send(message)
            return    

        # Map pool
        valid_maps = ["ancient", "inferno", "anubis", "nuke", "mirage", "dust2", "train"]
        if map_name not in valid_maps:
            message = "Invalid map name. Possible values are \"ancient\", \"inferno\", \"anubis\", \"nuke\", \"mirage\", \"dust2\", \"train\". Don't use quotes."
            await ctx.send(message)
            return
        
        # Get all vetoed map names
        selected_maps = []
        if vetoes is not None:
            for veto in vetoes:
                selected_maps.append(veto["map_name"])
        if picks is not None:
            for pick in picks:
                selected_maps.append(pick["map_name"])

        if map_name in selected_maps:
            message = "Map already vetoed or selected."
            await ctx.send(message)
            return

        is_veto_time = (number_of_vetoes == 0 or number_of_vetoes == 1 or (number_of_vetoes == 2 and number_of_picks == 2))
        is_pick_time = (number_of_vetoes == 2 and (number_of_picks == 0 or number_of_picks == 1))
        veto_finished = (number_of_vetoes == 4 and number_of_picks > 2)
        is_decider_time = (number_of_vetoes == 3 and number_of_picks == 2)
        if is_veto_time:
            await self.bot.execute_db(
                    "INSERT INTO veto (order_veto, game_id, team_id, map_name, guild_id) VALUES (?, ?, ?, ?, ?)",
                    ((number_of_vetoes + 1), game["id"], team_vetoing_id, map_name, guild.id)
                )
            if number_of_vetoes == 1 or number_of_vetoes == 3:
                message = f"""
                    {team_vetoing_name} vetoed {map_name}.\n
                    Turn of {team_vetoing_name} of picking map. Write `!pick <map_name>` to pick a map.\n
                """
            else:
                message = f"""
                    {team_vetoing_name} vetoed {map_name}.\n
                    Turn of {team_not_vetoing_name} of vetoing map. Write `!veto <map_name>` to veto a map.\n
                """
        elif is_pick_time:
            message = f"""
                Is not veto turn. Please check list and pick a map.
            """
        elif veto_finished:
            message = f"""
                Veto finished and maps have been decided.
            """
        elif is_decider_time:
            await self.bot.execute_db(
                    "INSERT INTO veto (order_veto, game_id, team_id, map_name, guild_id) VALUES (?, ?, ?, ?, ?)",
                    ((number_of_vetoes + 1), game["id"], team_vetoing_id, map_name, guild.id)
                )
            selected_maps.append(map_name)
            # Get map from valid maps missing in selected maps
            missing_maps = list(set(valid_maps) - set(selected_maps))
            if len(missing_maps) != 1:
                message = "Error: missing map not found."
                await ctx.send(message)
                return
            decider_map = missing_maps[0]
            await self.bot.execute_db(
                "INSERT INTO pick (order_pick, game_id, team_id, map_name, guild_id) VALUES (?, ?, ?, ?, ?)",
                ((number_of_picks + 1), game["id"], team_vetoing_id, decider_map, guild.id)
            )
            message = f"""
                {team_vetoing_name} vetoed {map_name}.\n
                Decider map will be {decider_map}.\n
            """
        await ctx.send(message)

        # Get game vetoes
        new_vetoes = None
        try:
            new_vetoes = await self.bot.fetch_all(
                    "SELECT * FROM veto WHERE game_id = ? AND guild_id = ?",
                    (game["id"], guild.id)
                )
        except Exception as e:
            new_vetoes = None
        number_of_vetoes = len(new_vetoes) if new_vetoes is not None else 0

        # Get game picks
        new_picks = None
        try:
            new_picks = await self.bot.fetch_all(
                    "SELECT * FROM pick WHERE game_id = ? AND guild_id = ?",
                    (game["id"], guild.id)
                )
        except Exception as e:
            new_picks = None

        # Update message
        embed = await self._create_pickveto_embed(ctx, game)
            
        public_channel = self.bot.get_channel(game["game_channel_id"])
        if public_channel:
            try:
                msg = await public_channel.fetch_message(game["public_game_message_id"])
                logger.info(msg)
                await msg.edit(embed=embed)
            except Exception as e:
                logger.error(f"Failed to update message: {e}")
                await ctx.send(f"⚠️ Veto added but failed to update display: {e}")

async def setup(bot):
    await bot.add_cog(GameManagement(bot))