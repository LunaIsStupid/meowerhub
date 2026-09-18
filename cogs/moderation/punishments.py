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


# TODO: think about setting up locales
class ModCommands(commands.Cog):
    UNIT_CONVERTERS = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}

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

        if not ctx.guild.me.guild_permissions.moderate_members: # TODO: make custom oneline assertion
            return await ctx.send(Locale.get("error.no_bot_perms", perm = "moderate members"), ephemeral = True)
        if member == ctx.author: return await ctx.send(Locale.get("error.author_user"), ephemeral = True) # TODO: make custom oneline assertion
        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner: # TODO: make custom oneline assertion
            return await ctx.send(Locale.get("error.user_role_lower"), ephemeral = True)
        if member.top_role >= ctx.guild.me.top_role: # TODO: make custom oneline assertion
            return await ctx.send(Locale.get("error.bot_role_lower"), ephemeral = True)

        duration_seconds: int = 0
        match = re.match(r"(\d+)([a-zA-Z])", duration)
        if match:
            number = int(match.group(1))
            unit = match.group(2)
            if unit not in self.UNIT_CONVERTERS:
                return await ctx.send(f"Unknown duration unit `{unit}`. Use s, m, h, d or w.", ephemeral = True)
            duration_seconds = number * self.UNIT_CONVERTERS[unit]
        else:
            duration_seconds = 2419200
            duration = "28d"
            reason = duration + " " + reason

        if duration_seconds > 2419200:
            await ctx.send("Duration capped at 28 days.")
            duration_seconds = 2419200

        try:
            await member.timeout(timedelta(seconds = duration_seconds), reason = reason)
            await ctx.send(Locale.get("mute.result", member = member.mention, duration = duration, reason = reason))
        except Exception as e:
            await ctx.send(Locale.get("mute.fail", error = f"\n-#{e}"), ephemeral = True)


    @reuse.hybrid_cmd("unmute")
    @reuse.cmd_describe("unmute", ["member"])
    @reuse.guild_only
    @reuse.check_permissions(moderate_members = True)
    async def unmute(self, ctx, member: discord.Member):
        """Unmutes a member.
        Usage:
        `!unmute <member>`"""

        if not ctx.guild.me.guild_permissions.moderate_members: # TODO: make custom oneline assertion
            return await ctx.send(Locale.get("error.no_bot_perms", perm = "moderate members"), ephemeral = True)
        if member == ctx.author: return await ctx.send(Locale.get("error.author_user"), ephemeral = True) # TODO: make custom oneline assertion
        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner: # TODO: make custom oneline assertion
            return await ctx.send(Locale.get("error.user_role_lower"), ephemeral = True)
        if member.top_role >= ctx.guild.me.top_role: # TODO: make custom oneline assertion
            return await ctx.send(Locale.get("error.bot_role_lower"), ephemeral = True)
        
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

        if not ctx.guild.me.guild_permissions.kick_members: # TODO: make custom oneline assertion
            return await ctx.send(Locale.get("error.no_bot_perms", perm = "kick members"), ephemeral = True)
        if member == ctx.author: return await ctx.send(Locale.get("error.author_user"), ephemeral = True) # TODO: make custom oneline assertion
        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner: # TODO: make custom oneline assertion
            return await ctx.send(Locale.get("error.user_role_lower"), ephemeral = True)
        if member.top_role >= ctx.guild.me.top_role: # TODO: make custom oneline assertion
            return await ctx.send(Locale.get("error.bot_role_lower"), ephemeral = True)    

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
        if not ctx.guild.me.guild_permissions.ban_members: # TODO: make custom oneline assertion
            return await ctx.send(Locale.get("error.no_bot_perms", perm = "ban members"), ephemeral = True)
        if member == ctx.author: return await ctx.send(Locale.get("error.author_user"), ephemeral = True) # TODO: make custom oneline assertion
        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner: # TODO: make custom oneline assertion
            return await ctx.send(Locale.get("error.user_role_lower"), ephemeral = True)
        if member.top_role >= ctx.guild.me.top_role: # TODO: make custom oneline assertion
            return await ctx.send(Locale.get("error.bot_role_lower"), ephemeral = True)

        delete_message_days: int = 0
        try: delete_message_days = min(7, max(0, int(days_str)))
        except ValueError: reason = days_str + " " + reason

        # guild_member: discord.Member | None = None
        # try: guild_member = await ctx.guild.fetch_member(member.id)
        # except discord.NotFound: return await ctx.send("Couldn't find the user")
        # except discord.HTTPException as e: return await ctx.send(f"Failed to fetch member for banning: \n-# {e}")
        #
        #
        # if guild_member and ctx.author.top_role.position <= member.top_role.position:
        #     return await ctx.send("You cannot ban a member with a higher role than you.")
        #   for now let it be commented, in case we really need it, but if its confirmed it works perfectly in any case, then drop that
        try:
            await ctx.guild.ban(member, delete_message_days = delete_message_days, reason = reason)
            await ctx.send(Locale.get("ban.result", member = member.mention, duration = f"{delete_message_days} days" if delete_message_days else "eternity", reason = reason))
        except Exception as e:
            await ctx.send(Locale.get("ban.fail", error = f"\n-#{e}"), ephemeral = True)


    @reuse.hybrid_cmd("unban")
    @reuse.cmd_describe("unban", ["member"])
    @reuse.guild_only
    @reuse.check_permissions(moderate_members = True)
    async def unban(self, ctx, member: discord.User):
        """Unbans a member.
        Usage:
        `!unban <member>`"""

        if not ctx.guild.me.guild_permissions.ban_members: # TODO: make custom oneline assertion
            return await ctx.send(Locale.get("error.no_bot_perms", perm = "ban members"), ephemeral = True)
        if member == ctx.author: return await ctx.send(Locale.get("error.author_user"), ephemeral = True) # TODO: make custom oneline assertion

        try:
            await ctx.guild.unban(member)
            await ctx.send(f"{member.mention} has been unbanned successfully.")
        except discord.HTTPException as e:
            await ctx.send(f"Could not unban member: \n-# {e}")

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
        if member.bot: return await ctx.send(Locale.get("error.bot_user"), ephemeral = True) # TODO: make custom oneline assertion
        if member == ctx.author: return await ctx.send(Locale.get("error.author_user"), ephemeral = True) # TODO: make custom oneline assertion
        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner: # TODO: make custom oneline assertion
            return await ctx.send(Locale.get("error.user_role_lower"), ephemeral = True)
        if member.top_role >= ctx.guild.me.top_role: # TODO: make custom oneline assertion
            return await ctx.send(Locale.get("error.bot_role_lower"), ephemeral = True)

        logger: commands.Cog | Logging | None = self.bot.get_cog("Logging")
        if not logger: return await ctx.send("Couldn't find logging command, warn failed.") # idk maybe move in locales
        if not hasattr(logger, "log_warn"): return await ctx.send("Expected the logging cog, got something else instead.")
        logger = cast(Logging, logger)
        await logger.log_warn(ctx, member, reason)
        await ctx.send(Locale.get("error.user_role_lower", member = member.mention, reason = reason))

    @mute.error
    @unmute.error
    @kick.error
    @ban.error
    @unban.error
    @warn.error
    async def error(self, ctx, error):
        await ctx.reply(Locale.get("overall.fail", error = error))
        # if you need custom behavior, then add new error function, no need to make separate functions for each command


async def setup(bot: MeowBot):
    cog = ModCommands(bot)
    await bot.add_cog(cog)
