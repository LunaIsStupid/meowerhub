import discord
from discord.ext import commands

import re
import time
import asyncio
import datetime

from main import MeowBot

import sys
sys.path.append("...")
from utils import reuse
from utils.locales import Locale
from utils.asserted import Assert


class Treats(commands.Cog):
    ARCANE_ID = 437808476106784770
    TREATS_PER_LEVEL = {
        10: 20,
        20: 20,
        30: 20,
        40: 20,
        50: 20,
        60: 20,
        70: 20,
        80: 20,
        90: 20,
        100: 20
    }
    EAT_COOLDOWN = commands.CooldownMapping.from_cooldown(1, 60, commands.BucketType.user)
    FEED_COOLDOWN = commands.CooldownMapping.from_cooldown(1, 60, commands.BucketType.user)
    SLEEPY_TIME = 10 # seconds

    def __init__(self, bot: MeowBot):
        self.bot: MeowBot = bot

    async def sleep(self, member: discord.Member):
        settings = await self.bot.db.guilds.get(member.guild.id)
        if not settings or not settings["sleepy_role_id"]: return False
        role = member.guild.get_role(settings["sleepy_role_id"])
        if not role: return False

        await member.timeout(datetime.timedelta(seconds=self.SLEEPY_TIME))
        await member.add_roles(role)
        asyncio.create_task(self.unsleep(member, role))
        return True

    async def unsleep(self, member: discord.Member, role: discord.Role):
        await asyncio.sleep(self.SLEEPY_TIME)
        try: await member.remove_roles(role)
        except: pass

    @reuse.hybrid_group("treats", "get")
    @reuse.cmd_describe("treats", ["member"])
    @reuse.guild_only
    async def treats(self, ctx: commands.Context, member: discord.Member | None = None):
        if not member and ctx.message.reference and isinstance(ctx.message.reference.resolved, discord.Message): member = ctx.message.reference.resolved.author
        if not member: member = ctx.author

        Assert.is_not_bot(member)

        try:
            row = await self.bot.db.treats.get(ctx.guild.id, member.id) or {"balance": 0}
            await ctx.reply(Locale.get("treats.result", member = member.mention, treats = row["balance"]), ephemeral=True, allowed_mentions=reuse.NO_MENTION)
        except Exception as e:
            await ctx.reply(Locale.get("treats.fail", error = f"\n-#{e}"), ephemeral = True)


    @reuse.sub_cmd(treats, "treats.set")
    @reuse.cmd_describe("treats.set", ["amount", "member"])
    @reuse.guild_only
    @reuse.check_permissions(administrator = True)
    async def treats_set(self, ctx: commands.Context, amount: int, member: discord.Member | None = None):
        if not member and ctx.message.reference and isinstance(ctx.message.reference.resolved, discord.Message): member = ctx.message.reference.resolved.author
        if not member: member = ctx.author

        Assert.is_not_bot(member)

        try:
            await self.bot.db.treats.upsert(ctx.guild.id, member.id, amount)
            await ctx.reply(Locale.get("treats.set.result", member = member.mention, treats = amount), ephemeral=True, allowed_mentions=reuse.NO_MENTION)
        except Exception as e:
            await ctx.reply(Locale.get("treats.set.fail", error = f"\n-#{e}"), ephemeral = True)

    @reuse.sub_cmd(treats, "treats.gift")
    @reuse.cmd_describe("treats.gift", ["amount", "member"])
    @reuse.guild_only
    async def treats_gift(self, ctx: commands.Context, amount: int, member: discord.Member | None = None):
        if not member and ctx.message.reference and isinstance(ctx.message.reference.resolved, discord.Message): member = ctx.message.reference.resolved.author
        if not member: member = ctx.author

        Assert.is_not_bot(member)
        if amount < 0: return await ctx.reply(Locale.get("error.no_negatives"))

        row = await self.bot.db.treats.get(ctx.guild.id, ctx.author.id) or {"balance": 0}
        if row["balance"] < amount: return await ctx.reply(Locale.get("treats.not_enough", treats = row["balance"]))

        try:
            if amount > 0: await self.bot.db.treats.transfer(ctx.guild.id, ctx.author.id, member.id, amount)
            await ctx.reply(Locale.get("treats.gift.result"+(".zero" if amount == 0 else ""), member = member.mention, treats = amount), ephemeral=True, allowed_mentions=reuse.NO_MENTION)
        except Exception as e:
            await ctx.reply(Locale.get("treats.gift.fail", error = f"\n-#{e}"), ephemeral = True)

    @reuse.sub_cmd(treats, "treats.eat")
    @reuse.guild_only
    async def treats_eat(self, ctx: commands.Context):
        bucket = self.EAT_COOLDOWN.get_bucket(ctx.message)
        if not bucket: return
        retry_after = bucket.get_retry_after(time.time())
        if retry_after: raise commands.CommandOnCooldown(bucket, retry_after, commands.BucketType.user)

        row = await self.bot.db.treats.get(ctx.guild.id, ctx.author.id) or {"balance": 0}
        if row["balance"] < 1: return await ctx.reply(Locale.get("treats.not_enough", treats = row["balance"]))

        await self.bot.db.treats.add(ctx.guild.id, ctx.author.id, -1)

        try:
            bucket.update_rate_limit(time.time())

            if not await self.sleep(ctx.author): return await ctx.reply("You ate a treat, it was delicious, but nothing else happened")
            await ctx.reply("You ate a treat, it was delicious, you feel really sleepy")
        except Exception as e:
            print(e)
            await ctx.reply(Locale.get("overall.fail", error = f"\n-#{e}"), ephemeral = True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if (not message.guild or message.author.id != self.ARCANE_ID): return  # not in guild, or not arcane

        match = re.search(r"<@(\d+)> has reached level \*\*(\d+)\*\*", message.content)
        if not match or len(match.groups()) < 2: return

        user_id, level = match.groups()
        treat = self.TREATS_PER_LEVEL.get(int(level), 0) if level.isnumeric() else 0
        if not treat or not user_id.isnumeric(): return

        await self.bot.db.treats.add(message.guild.id, int(user_id), treat)
        await message.reply(Locale.get("treats.on_levelup", member = f"<@{user_id}>", treats = treat))
        
    @treats_gift.error
    async def cooldown_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.CommandOnCooldown): await ctx.send(f"Try again in {error.retry_after:.1f}s", ephemeral=True) # TODO: LOCALES

async def setup(bot: MeowBot):
    await bot.add_cog(Treats(bot))