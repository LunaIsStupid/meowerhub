import discord
from discord.ext import commands

from main import MeowBot

import sys
sys.path.append("...")
from utils import reuse
from utils.locales import Locale

class AFK(commands.Cog):
    MAX_MESSAGE_LENGTH = 200

    def __init__(self, bot: MeowBot):
        self.bot: MeowBot = bot
        # cache so i dont hit the disk as hard i think
        self.cache: dict[tuple[int, int], str] = {}  # guild_id: user_id: message


    async def update_caches(self):
        self.cache = {}
        rows = await self.bot.db.afk.get_many()
        for row in rows:
            self.update_cache_entry(row["guild_id"], row["user_id"], row["message"])  # populate cache

    def update_cache_entry(self, guild_id: int, member_id: int, message: str):
        self.cache[guild_id, member_id] = message

    def delete_cache_entry(self, guild_id: int, member_id: int) -> str:
        return self.cache.pop((guild_id, member_id), "")

    async def set_afk(self, guild_id: int, member_id: int, message: str) -> str:
        message = message[:self.MAX_MESSAGE_LENGTH]
        await self.bot.db.afk.upsert(guild_id, member_id, message)
        self.update_cache_entry(guild_id, member_id, message)
        return message

    async def reset_afk(self, guild_id: int, member_id: int) -> str:
        await self.bot.db.afk.rem(guild_id, member_id)
        message = self.delete_cache_entry(guild_id, member_id)
        return message


    @reuse.hybrid_cmd("afk")
    @reuse.cmd_describe("afk", ["message"])
    @reuse.guild_only
    async def afk(self, ctx: commands.Context, *, message: str = ""):
        message = await self.set_afk(ctx.guild.id, ctx.author.id, message)
        await ctx.reply(Locale.get("afk.result"+(".meow" if message.startswith("meow") else ""), message = message), ephemeral=True)

    @reuse.hybrid_cmd("forceafk")
    @reuse.cmd_describe("forceafk", ["message", "member"])
    @reuse.guild_only
    @reuse.check_permissions(administrator = True)
    async def forceafk(self, ctx: commands.Context, member: discord.Member, *, message: str):
        message = await self.set_afk(ctx.guild.id, member.id, message)
        await ctx.reply(Locale.get("forceafk.result"+(".meow" if message.startswith("meow") else ""), member = member.mention, message = message), allowed_mentions=reuse.NO_MENTION, ephemeral=True)

    @reuse.hybrid_cmd("resetafk")
    @reuse.cmd_describe("resetafk", ["member"])
    @reuse.guild_only
    @reuse.check_permissions(administrator = True)
    async def resetafk(self, ctx: commands.Context, member: discord.Member):
        message = await self.reset_afk(ctx.guild.id, member.id)
        await ctx.reply(Locale.get("resetafk.result"+(".meow" if message.startswith("meow") else ""), member = member.mention), allowed_mentions=reuse.NO_MENTION, ephemeral=True)


    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if (
            not message.guild
            or message.author.bot
            or message.content.startswith(str(self.bot.command_prefix))
        ): return  # not in guild, or is a bot, or is a command


        if (message.guild.id, message.author.id) in self.cache and not message.content.startswith(">>"):
            text = await self.reset_afk(message.guild.id, message.author.id)
            return await message.reply(Locale.get("afk.reset"+(".meow" if text.startswith("meow") else ""), message = text))
            # Avoid duplicate messages if the author mentions themself

        for member in message.mentions:
            if not (message.guild, member.id) in self.cache:
                text = self.cache[message.guild.id, member.id]
                return await message.reply(Locale.get("afk.reminder"+(".meow" if text.startswith("meow") else ""), member = member.mention, message = text), allowed_mentions=reuse.NO_MENTION)
                # to prevent spam exit here


async def setup(bot: MeowBot):
    cog = AFK(bot)
    await cog.update_caches()
    await bot.add_cog(cog)
