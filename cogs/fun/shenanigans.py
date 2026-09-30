import bisect
import random
import asyncio

import discord
from discord.ext import commands

from main import MeowBot

from . import _settings as settings

import sys
sys.path.append("...")
from utils import reuse
from utils.locales import Locale
from utils.asserted import Assert

class Shenanigans(commands.Cog):
    def __init__(self, bot: MeowBot):
        self.bot: MeowBot = bot

    @reuse.hybrid_cmd("killeveryone")
    @reuse.guild_only
    @reuse.check_permissions(administrator = True)
    async def killeveryone(self, ctx: commands.Context):
        items = ["Preparing to ban everyone...."] * 4 + [f"Banning {member.mention}..." for member in ctx.guild.members] + ["Successfully banned everyone!"]

        message = None
        for item in items:
            if not message: message = await ctx.send(item)
            elif message.content != item:
                try: await message.edit(content = item)
                except discord.NotFound: return
            await asyncio.sleep(1)

    @reuse.hybrid_cmd("bam")
    @reuse.guild_only
    @reuse.cmd_describe("bam", ["member"])
    @reuse.check_permissions(administrator = True)
    async def bam(self, ctx: commands.Context, member: str | None = None):
        if member: user = await self.bot.extract_user(ctx, member)
        else: user = await self.bot.extract_reply_user(ctx)
        
        Assert.a(user is not None, "error.missing_reply_or_member")
        Assert.is_not_author(ctx, user)

        await ctx.reply(Locale.get("bam.result", member = user.mention))

    @reuse.cmd("nuhuh", hidden = True, aliases = ["nou"])
    @reuse.guild_only
    async def nuhuh(self, ctx: commands.Context):
        if ctx.message.reference and ctx.message.reference.resolved and ctx.message.reference.resolved.author.id == ctx.guild.me.id and ctx.message.reference.resolved.content == Locale.get("bam.result", member = ctx.author.mention): # idk how to make it prettier
            await ctx.reply(Locale.get("nuhuh.result", member = ctx.author.mention))

    
async def setup(bot: MeowBot):
    await bot.add_cog(Shenanigans(bot))
