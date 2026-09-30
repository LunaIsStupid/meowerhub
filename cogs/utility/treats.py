import discord
from discord.ext import commands

import re
import time
import random
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
    SLEEPY_TIME = 10 # seconds
    FEED_REPLIES = [
        "test"
    ]

    def __init__(self, bot: MeowBot):
        self.bot: MeowBot = bot
        self.eat_cooldown = commands.CooldownMapping.from_cooldown(1, 60, commands.BucketType.user)
        self.feed_cooldown = commands.CooldownMapping.from_cooldown(1, 60, commands.BucketType.user)

    async def sleep(self, member: discord.Member):
        settings = await self.bot.db.guilds.get(member.guild.id)
        if not settings or not settings["sleepy_role_id"]: return False
        role = member.guild.get_role(settings["sleepy_role_id"])
        if not role: return False

        try:
            await member.timeout(datetime.timedelta(seconds=self.SLEEPY_TIME))
            await member.add_roles(role)
            asyncio.create_task(self.unsleep(member, role))
            return True
        except: return False

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
    @reuse.cmd_describe("treats.gift", ["member", "amount"])
    @reuse.guild_only
    async def treats_gift(self, ctx: commands.Context, member: str, amount: int | None = None):
        target, amount = await self.bot.extract_member_and_amount(ctx, member, amount)
        if not target or not isinstance(target, discord.Member): return await ctx.reply("Mention a member or reply to their message")
        Assert.is_not_bot(target)

        if target.id == ctx.author.id: return await ctx.reply("you silly")

        if amount == 0: return await ctx.reply("wow you want to offer them nothing")
        if amount < 0: return await ctx.reply("we are stealing apparently?")

        row = await self.bot.db.treats.get(ctx.guild.id, ctx.author.id) or {"balance": 0}
        if row["balance"] < amount: return await ctx.reply(Locale.get("treats.not_enough", treats = row["balance"]))

        try:
            if amount > 0: await self.bot.db.treats.transfer(ctx.guild.id, ctx.author.id, target.id, amount)
            await ctx.reply(Locale.get("treats.gift.result"+(".zero" if amount == 0 else ""), member = target.mention, treats = amount), ephemeral=True, allowed_mentions=reuse.NO_MENTION)
        except Exception as e:
            await ctx.reply(Locale.get("treats.gift.fail", error = f"\n-#{e}"), ephemeral = True)

    @reuse.sub_cmd(treats, "treats.eat")
    @reuse.guild_only
    async def treats_eat(self, ctx: commands.Context, amount: int | None = 1):
        bucket = self.eat_cooldown.get_bucket(ctx.message)
        if not bucket: return
        retry_after = bucket.get_retry_after(time.time())
        if retry_after: raise commands.CommandOnCooldown(bucket, retry_after, commands.BucketType.user)

        if amount > 1: return await ctx.reply("you wanna explode?")
        if amount == 0: return await ctx.reply("you want to eat air apparently?")
        if amount < 0: return await ctx.reply("no infinite treats glitches sowwy")

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

    @reuse.sub_cmd(treats, "treats.feed")
    @reuse.guild_only
    async def treats_feed(self, ctx: commands.Context, member: str, amount: int | None = 1):
        bucket = self.feed_cooldown.get_bucket(ctx.message)
        if not bucket: return
        retry_after = bucket.get_retry_after(time.time())
        if retry_after: raise commands.CommandOnCooldown(bucket, retry_after, commands.BucketType.user)

        target, amount = await self.bot.extract_member_and_amount(ctx, member, amount)
        if not target or not isinstance(amount, int) or not isinstance(target, discord.Member): return await ctx.reply("Mention a member or reply to their message")

        if target.id == ctx.author.id: return await ctx.reply("you silly")

        if amount > 1: return await ctx.reply("more than one? you want them to explode")
        if amount == 0: return await ctx.reply("wow you want to offer them nothing")
        if amount < 0: return await ctx.reply("you so generous")

        if target.id != ctx.guild.me.id: Assert.is_not_bot(target)

        row = await self.bot.db.treats.get(ctx.guild.id, ctx.author.id) or {"balance": 0}
        if row["balance"] < 1: return await ctx.reply(Locale.get("treats.not_enough", treats = row["balance"]))

        await self.bot.db.treats.add(ctx.guild.id, ctx.author.id, -1)

        try:
            bucket.update_rate_limit(time.time())

            if target.id == ctx.guild.me.id: return await ctx.reply(random.choice(self.FEED_REPLIES))
            view = AcceptTreatView(ctx.author, target, self.bot, self)
            await ctx.reply(f"{ctx.author.mention} offered {target.mention} a treat", view=view)
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


# https://fallendeity.github.io/discord.py-masterclass/views/#basic-view
class AcceptTreatView(discord.ui.View):
    message: discord.Message | None = None

    def __init__(self, author: discord.Member, receiver: discord.Member, bot: MeowBot, treats_cog: Treats, timeout: float = 60*3):
        super().__init__(timeout=timeout)
        self.author = author
        self.receiver = receiver
        self.bot = bot
        self.treats_cog = treats_cog

    async def interaction_check(self, interaction: discord.Interaction[discord.Client]) -> bool:
        if interaction.user.id not in (self.receiver.id, self.author.id):
            await interaction.response.send_message("This is not for you, silly.", ephemeral = True)
            return False
        return True

    async def on_timeout(self) -> None:
        await self.bot.db.treats.add(self.author.guild.id, self.author.id, 1)
        if not self.message: return
        try: await self.message.edit(content="Automatically declined after 3 minutes.", view=None)
        except: pass

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button[AcceptTreatView]) -> None:
        if interaction.user.id == self.author.id: return await interaction.response.send_message("You cant accept this, silly", ephemeral = True)
        self.stop()
        await interaction.response.edit_message(content=f"{interaction.user.mention} accepted the treat.", view=None)
        if not await self.treats_cog.sleep(interaction.user): return await interaction.response.send_message("You ate a treat, it was delicious, but nothing else happened", ephemeral = True)
        await interaction.response.send_message("You ate a treat, it was delicious, you feel really sleepy", ephemeral = True)
        # TODO: add locales later

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.red)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button[AcceptTreatView]) -> None:
        self.stop()
        await self.bot.db.treats.add(interaction.guild.id, self.author.id, 1)
        await interaction.response.edit_message(content=f"{interaction.user.mention} declined the treat.", view=None)

async def setup(bot: MeowBot):
    await bot.add_cog(Treats(bot))