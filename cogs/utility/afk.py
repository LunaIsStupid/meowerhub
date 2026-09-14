import discord
from discord.ext import commands

from main import MeowBot


class AFK(commands.Cog):
    def __init__(self, bot: MeowBot):
        self.bot: MeowBot = bot
        # cache so i dont hit the disk as hard i think
        self.afk_users: dict[int, dict[int, str]] = {}  # guild_id: user_id: message

    async def cog_load(self):
        query = "SELECT guild_id, user_id, message FROM afk;"
        async with self.bot.db.execute(query) as cursor:
            rows = await cursor.fetchall()
            for guild_id, user_id, message in rows:
                if guild_id not in self.afk_users:
                    self.afk_users[guild_id] = {}
                self.afk_users[guild_id][user_id] = message  # populate cache

    @commands.command()
    async def afk(self, ctx: commands.Context, *, message: str):
        if not ctx.guild:
            return  # No guild

        create_query = """
        INSERT INTO afk (guild_id, user_id, message)
        VALUES (?, ?, ?)
        ON CONFLICT(guild_id, user_id)
        DO UPDATE SET message = excluded.message, updated_at = CURRENT_TIMESTAMP;
        """

        await self.bot.db.execute(create_query, (ctx.guild.id, ctx.author.id, message))

        if ctx.guild.id not in self.afk_users:
            self.afk_users[ctx.guild.id] = {}

        self.afk_users[ctx.guild.id][ctx.author.id] = message
        if message.startswith("meow"):
            await ctx.reply(f"Mrow mew miau: `{message}`")
        else:
            await ctx.reply(f"AFK Set: `{message}`")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if (
            not message.guild
            or message.author.bot
            or message.content.startswith("!afk")
        ):
            return  # not in guild, or is a bot, or updating afk message

        guild_id = message.guild.id
        user_id = message.author.id

        guild_afk = self.afk_users.get(guild_id, {})

        if message.author.id in guild_afk and not message.content.startswith(">>"):
            delete_query = "DELETE FROM afk WHERE guild_id = ? AND user_id = ?"
            await self.bot.db.execute(delete_query, (guild_id, user_id))
            guild_afk.pop(message.author.id)
            await message.reply("You are no longer afk!")
            return  # Avoid duplicate messages if the author mentions themself

        for mention in message.mentions:
            if mention.id in guild_afk:
                afk_msg = guild_afk[mention.id]
                await message.reply(f"{mention.display_name} is afk: `{afk_msg}")
                return  # to prevent spam exit here


async def setup(bot: MeowBot):
    await bot.add_cog(AFK(bot))
