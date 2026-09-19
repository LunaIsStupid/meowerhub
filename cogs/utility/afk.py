import discord
from discord.ext import commands

from main import MeowBot

import sys
sys.path.append("...")
from utils import reuse
from utils.locales import Locale

class AFK(commands.Cog):
    def __init__(self, bot: MeowBot):
        self.bot: MeowBot = bot
        # cache so i dont hit the disk as hard i think
        self.afk_users: dict[int, dict[int, str]] = {}  # guild_id: user_id: message

    async def cog_load(self):
        rows = await self.bot.db.afk.get_many()
        for row in rows:
            if row["guild_id"] not in self.afk_users: self.afk_users[row["guild_id"]] = {}
            self.afk_users[row["guild_id"]][row["user_id"]] = row["message"]  # populate cache

    @reuse.hybrid_cmd("afk")
    @reuse.cmd_describe("afk", ["message"])
    @reuse.guild_only
    async def afk(self, ctx: commands.Context, *, message: str):
        await self.bot.db.afk.upsert(ctx.guild.id, ctx.author.id, message)

        if ctx.guild.id not in self.afk_users: self.afk_users[ctx.guild.id] = {}
        self.afk_users[ctx.guild.id][ctx.author.id] = message

        if message.startswith("meow"): await ctx.reply(f"Mrow mew miau: `{message}`", ephemeral=True)
        else: await ctx.reply(f"AFK set: `{message}`", ephemeral=True)
        # TODO: locales

    @reuse.hybrid_cmd("forceafk")
    @reuse.cmd_describe("forceafk", ["message", "member"])
    @reuse.guild_only
    @reuse.check_permissions(administrator = True)
    async def forceafk(self, ctx: commands.Context, member: discord.Member, *, message: str):
        await self.bot.db.afk.upsert(ctx.guild.id, member.id, message)

        if ctx.guild.id not in self.afk_users: self.afk_users[ctx.guild.id] = {}
        self.afk_users[ctx.guild.id][ctx.author.id] = message

        if message.startswith("meow"): await ctx.reply(f"Mrow mew miau mow {member.mention}: `{message}`", allowed_mentions=reuse.NO_MENTION, ephemeral=True)
        else: await ctx.reply(f"AFK set for {member.mention}: `{message}`", allowed_mentions=reuse.NO_MENTION, ephemeral=True)
        # TODO: locales


    @reuse.hybrid_cmd("resetafk")
    @reuse.cmd_describe("resetafk", ["message", "member"])
    @reuse.guild_only
    @reuse.check_permissions(administrator = True)
    async def resetafk(self, ctx: commands.Context, member: discord.Member, *, message: str):
        await self.bot.db.afk.rem(ctx.guild.id, member.id)

        del self.afk_users[ctx.guild.id][ctx.author.id]

        await ctx.reply(f"AFK reset for {member.mention}", allowed_mentions=reuse.NO_MENTION, ephemeral=True)
        # TODO: locales


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
            await self.bot.db.afk.rem(guild_id, user_id)
            await message.reply("You are no longer afk!")
            return  # Avoid duplicate messages if the author mentions themself

        for mention in message.mentions:
            if mention.id in guild_afk:
                afk_msg = guild_afk[mention.id]
                await message.reply(f"{mention.display_name} is afk: `{afk_msg}`")
                return  # to prevent spam exit here


async def setup(bot: MeowBot):
    await bot.add_cog(AFK(bot))
