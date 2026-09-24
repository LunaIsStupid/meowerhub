import re
import sys
from datetime import timedelta
from typing import cast

import discord
from discord.ext import commands

from cogs.moderation.logging import Logging
from main import MeowBot

sys.path.append("...")
from utils import reuse
from utils.locales import Locale
from utils import timed
from utils.asserted import *

# TODO: think about setting up locales
class ModCommands(commands.Cog):
    UNIT_CONVERTERS = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}
    MAX_MUTE_SECONDS = 2419200

    def __init__(self, bot: MeowBot):
        self.bot: MeowBot = bot

    @reuse.hybrid_cmd("mute")
    @reuse.cmd_describe("mute", ["member", "duration", "reason"])
    @reuse.guild_only
    @reuse.check_permissions(moderate_members = True)
    async def mute(
        self, ctx: commands.Context, member: discord.Member,
        duration: str = "28d", *, reason: str = "No reason provided.",
    ):
        """Kicks a member.
        Usage:
        `!mute <user> <duration> <reason>`
        """

        Assert.is_not_author(ctx, member)
        Assert.has_permissions(ctx, moderate_members = True)
        Assert.has_permissions(ctx, ctx.author, moderate_members = True)
        Assert.can_moderate(ctx.author, member)

        seconds, duration, reason = timed.extract(duration + " " + reason)
        reason = reason or "No reason provided." # TODO: locales

        if not seconds:
            seconds = self.MAX_MUTE_SECONDS
            duration = "28 days"

        if seconds > self.MAX_MUTE_SECONDS:
            await ctx.send("Duration capped at 28 days.") # TODO: locales
            duration = "28 days"
            seconds = self.MAX_MUTE_SECONDS

        try:
            await member.timeout(timedelta(seconds = seconds), reason = reason)
            await ctx.send(Locale.get("mute.result", member = member.mention, duration = duration, reason = reason))
        except Exception as e:
            await ctx.send(Locale.get("mute.fail", error = f"\n-#{e}"), ephemeral = True)


    @reuse.hybrid_cmd("unmute")
    @reuse.cmd_describe("unmute", ["member"])
    @reuse.guild_only
    @reuse.check_permissions(moderate_members = True)
    async def unmute(self, ctx: commands.Context, member: discord.Member):
        """Unmutes a member.
        Usage:
        `!unmute <member>`"""

        Assert.is_not_author(ctx, member)
        Assert.has_permissions(ctx, moderate_members = True)
        Assert.has_permissions(ctx, ctx.author, moderate_members = True)
        Assert.can_moderate(ctx.author, member)

        try:
            await member.timeout(None)
            await ctx.send(Locale.get("unmute.result", member = member.mention))
        except Exception as e:
            await ctx.send(Locale.get("unmute.fail", error = f"\n-#{e}"), ephemeral = True)


    @reuse.hybrid_cmd("kick")
    @reuse.cmd_describe("kick", ["member", "reason"])
    @reuse.guild_only
    @reuse.check_permissions(moderate_members = True)
    async def kick(
        self, ctx, member: discord.Member,
        *, reason: str = "No reason provided."
    ):
        """Kicks a member.
        Usage:
        `!kick <user> <reason>`
        """

        Assert.is_not_author(ctx, member)
        Assert.has_permissions(ctx, kick_members = True)
        Assert.has_permissions(ctx, ctx.author, kick_members = True)
        Assert.can_moderate(ctx.author, member)

        try:
            await member.kick(reason = reason)
            await ctx.send(Locale.get("kick.result", member = member.mention, reason = reason))
        except Exception as e:
            await ctx.send(Locale.get("kick.fail", error = f"\n-#{e}"), ephemeral = True)


    @reuse.hybrid_cmd("ban")
    @reuse.cmd_describe("ban", ["member", "days_str", "reason"])
    @reuse.guild_only
    @reuse.check_permissions(moderate_members = True)
    async def ban(
        self, ctx, member: discord.Member, days_str: str = "0",
        *, reason: str = "No reason provided."
    ):
        """Bans a member.
        Usage:
        `!ban <user> <days to purge> <reason>`
        """

        Assert.is_not_author(ctx, member)
        Assert.has_permissions(ctx, ban_members = True)
        Assert.has_permissions(ctx, ctx.author, ban_members = True)
        Assert.can_moderate(ctx.author, member)

        delete_message_days: int = 0
        try: delete_message_days = min(7, max(0, int(days_str)))
        except ValueError: reason = days_str + " " + reason

        try:
            await ctx.guild.ban(member, delete_message_days = delete_message_days, reason = reason)
            await ctx.send(Locale.get("ban.result", member = member.mention, duration = f"{delete_message_days} days" if delete_message_days else "eternity", reason = reason))
        except Exception as e:
            await ctx.send(Locale.get("ban.fail", error = f"\n-#{e}"), ephemeral = True)


    @reuse.hybrid_cmd("unban")
    @reuse.cmd_describe("unban", ["member"])
    @reuse.guild_only
    @reuse.check_permissions(moderate_members = True)
    async def unban(self, ctx: commands.Context, member: discord.User):
        """Unbans a member.
        Usage:
        `!unban <member>`"""

        Assert.is_not_author(ctx, member)
        Assert.has_permissions(ctx, ban_members = True)
        Assert.has_permissions(ctx, ctx.author, ban_members = True)

        try:
            await ctx.guild.unban(member)
            await ctx.send(Locale.get("unban.result", member = member.mention))
        except discord.HTTPException as e:
            await ctx.send(Locale.get("unban.fail", error = f"\n-#{e}"), ephemeral = True)

    @reuse.hybrid_cmd("warn")
    @reuse.cmd_describe("warn", ["member", "reason"])
    @reuse.guild_only
    @reuse.check_permissions(moderate_members = True)
    async def warn(
        self, ctx: commands.Context, member: discord.Member,
        *, reason: str = "No reason provided."
    ):
        """Warns a member.
        Usage:
        `!warn <member> [reason]`"""
        # Passthrough method so it gets grouped with the moderation commands, but logs the warn.

        Assert.is_not_bot(member)
        Assert.is_not_author(ctx, member)
        Assert.can_moderate(ctx.author, member)

        warning_id = await self.bot.db.warnings.add(ctx.guild.id, member.id, ctx.author.id, reason)
        logger: commands.Cog | Logging | None = self.bot.get_cog("Logging")
        if not logger: return await ctx.send("Couldn't find logging command, warn failed.") # idk maybe move in locales
        if not hasattr(logger, "log_warn"): return await ctx.send("Expected the logging cog, got something else instead.")
        logger = cast(Logging, logger)
        await logger.log_warn(ctx, member, reason, warning_id)
        await ctx.send(Locale.get("warn.result", member = member.mention, reason = reason, id = warning_id))

    @reuse.hybrid_cmd("purge")
    @reuse.cmd_describe("purge", ["count"])
    @reuse.guild_only
    @reuse.check_permissions(manage_messages = True)
    async def purge(self, ctx: commands.Context, count: int):
        if not isinstance(ctx.channel, discord.Thread | discord.ForumChannel | discord.TextChannel): return await ctx.reply("cant do it here", ephemeral = True)
        # TODO: reuse.GUILD_TEXT_CHANNEL
        # TODO: locales

        Assert.has_permissions(ctx, manage_messages = True)
        Assert.has_permissions(ctx, ctx.author, manage_messages = True)

        try:
            messages = await ctx.channel.purge(limit=count)
            logger: commands.Cog | Logging | None = self.bot.get_cog("Logging")
            if not logger: return await ctx.send("Couldn't find logging command, warn failed.") # idk maybe move in locales
            if not hasattr(logger, "log_warn"): return await ctx.send("Expected the logging cog, got something else instead.")
            logger = cast(Logging, logger)
            await logger.log_purge(ctx, ctx.author, messages)
            await ctx.send(Locale.get("purge.result", count = count))
        except discord.HTTPException as e:
            await ctx.send(Locale.get("purge.fail", error = f"\n-#{e}"), ephemeral = True)


async def setup(bot: MeowBot):
    cog = ModCommands(bot)
    await bot.add_cog(cog)
