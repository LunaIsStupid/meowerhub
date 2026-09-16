import bisect
import random

import discord
from discord.ext import commands
from petpetgif import petpet

from main import MeowBot

from . import _settings as settings


class The(commands.Cog):
    GAY_REPLIES = {
        -1: "wow so you hate the gays, banned.",
        0: "eh, you can do better",
        70: "holy fucken gay!",
        101: "what are you a gay god?",
    }
    GAY_MIN = -1
    GAY_MAX = 101
    GAY_OVERRIDES = {
        # 69: "nice"
    }
    USER_GAY_OVERRIDES = {
        # id: integer, because thats funny
        # also supports guild ids
        # 416062410022191104: 101
    }


    def __init__(self, bot: MeowBot):
        self.bot: MeowBot = bot

    def format_howgay_reply(self, gay: int) -> str:
        gay = self.GAY_OVERRIDES.get(gay, gay)
        if isinstance(gay, str): return gay
        idx = bisect.bisect_right(list(self.GAY_REPLIES.keys()), gay) - 1
        if idx == 0: return "what?"
        return self.GAY_REPLIES[list(self.GAY_REPLIES.keys())[idx]]

    @commands.command()
    async def howgay(self, ctx: commands.Context, member: discord.Member | str):
        name = None
        color = None
        override_id = None
        found_member = None
        to_be = "is"

        if isinstance(member, discord.Member):
            name = member.name
            color = member.color
            override_id = member.id
            found_member = member
        elif isinstance(member, str):
            if member.isdigit():
                found_member = None
                if ctx.guild: found_member = await ctx.guild.fetch_member(int(member))
                if not ctx.guild or not found_member: found_member = await self.bot.fetch_user(int(member))
                if not found_member: return await ctx.send("I cant find that member.")
                name = found_member.name
                color = found_member.color
                override_id = found_member.id
            elif member in settings.EVERYONE_PETPET: # TODO: move to shared settings
                name = "everyone"
                to_be = "are"
                if ctx.guild:
                    name += f" in {ctx.guild.name}"
                    override_id = ctx.guild.id
        if not name: return await ctx.send("Please mention a member or their id.")

        color = color if color and color != discord.Colour.default() else settings.DEFAULT_COLOR # TODO: move to shared settings
        random_gay = random.randint(self.GAY_MIN, self.GAY_MAX)
        gay = self.USER_GAY_OVERRIDES.get(override_id, random_gay) if override_id else random_gay
        desc = self.format_howgay_reply(gay)

        embed = discord.Embed()
        embed.set_author(
            name=f"🏳️‍🌈 {name} {to_be} {gay}% gay!",
            icon_url=found_member.display_avatar if found_member else None,
        )
        embed.color = color
        embed.set_footer(text=desc)

        await ctx.reply(embed=embed)

    @howgay.error
    async def howgay_error(self, ctx, error):
        await ctx.reply(error)

async def setup(bot: MeowBot):
    await bot.add_cog(The(bot))
