import bisect
import random

import discord
from discord.ext import commands

from main import MeowBot

from . import _settings as settings

import sys
sys.path.append("...")
import reuse
from locales import Locale

class HowGay(commands.Cog):
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
        1532712415832047637: 100
    }


    def __init__(self, bot: MeowBot):
        self.bot: MeowBot = bot

    def format_howgay_reply(self, gay: int) -> str:
        gay = self.GAY_OVERRIDES.get(gay, gay)
        if isinstance(gay, str): return gay
        idx = bisect.bisect_right(list(self.GAY_REPLIES.keys()), gay) - 1
        if idx == 0: return "what?"
        return self.GAY_REPLIES[list(self.GAY_REPLIES.keys())[idx]]

    @reuse.hybrid("howgay")
    @reuse.cmd_describe("howgay", ["someone"])
    @reuse.guild_and_app
    async def howgay(self, ctx: commands.Context, someone: str):
        user = await self.bot.extract_user(ctx, someone)
        name = None
        color = None
        override_id = None
        found_member = None
        to_be = "is"

        if isinstance(user, reuse.USER):
            name = user.display_name
            color = settings.DEFAULT_COLOR
            if ctx.guild:
                try:
                    member = await ctx.guild.fetch_member(int(user.id))
                    color =  member.color
                except: pass
            override_id = user.id
            found_member = user
        elif isinstance(user, str) and user in settings.EVERYONE:
                name = "everyone"
                to_be = "are"
                if ctx.guild:
                    name += f" in {ctx.guild.name}"
                    override_id = ctx.guild.id
        if not name: return await ctx.send(Locale.get("error.no_members_arg"), ephemeral=True)

        color = color if color and color != discord.Colour.default() else settings.DEFAULT_COLOR
        random_gay = random.randint(self.GAY_MIN, self.GAY_MAX)
        gay = self.USER_GAY_OVERRIDES.get(override_id, random_gay) if override_id else random_gay
        desc = self.format_howgay_reply(gay)

        embed = discord.Embed()
        embed.set_author(
            name=Locale.get("howgay.result", name=name, to_be=to_be, gay=gay),
            icon_url=found_member.display_avatar if found_member else None,
        )
        embed.color = color
        embed.set_footer(text=desc)

        await ctx.reply(embed=embed)

    @howgay.error
    async def howgay_error(self, ctx, error):
        await ctx.reply(error)

async def setup(bot: MeowBot):
    await bot.add_cog(HowGay(bot))
