import re
from datetime import timedelta
from typing import cast

import discord
from discord import app_commands
from discord.ext import commands

from cogs.moderation.logging import Logging
from main import MeowBot


class ModCommands(commands.Cog):
    def __init__(self, bot: MeowBot):
        self.bot: MeowBot = bot

    @commands.hybrid_command(name="mute", description="Mute a member")
    @app_commands.describe(
        member="The member to mute",
        duration="Duration (e.g., 10m, 1h, 7d), defaults to 28d",
        reason="Reason for the mute",
    )
    @app_commands.guild_only()
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.allowed_contexts(guilds=True,dms=False,private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=False)
    @commands.has_permissions(moderate_members=True)
    @commands.guild_only()
    async def mute(
        self,
        ctx,
        member: discord.Member,
        duration: str = "28d",
        *,
        reason: str = "No reason provided.",
    ):
        """Kicks a member.
        Usage:
        `!mute <user> <duration> <reason>`
        """
        if not ctx.guild.me.guild_permissions.moderate_members:
            await ctx.send(
                "I do not have the `moderate members` permission required for this."
            )
            return

        match = re.match(r"(\d+)([a-zA-Z])", duration)
        if ctx.author.top_role.position <= member.top_role.position:
            await ctx.send("You cannot mute a member with a higher role than you.")
            return

        duration_seconds: int = 0

        if not match:
            duration_seconds = 2419200
            duration = "28d"
            reason = duration + " " + reason

        if match:
            number = int(match.group(1))
            unit = match.group(2)

            unit_converters = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}

            if unit not in unit_converters:
                await ctx.send(f"Unknown duration unit `{unit}`. Use s, m, h, d or w.")
                return

            duration_seconds = number * unit_converters[unit]

        if duration_seconds > 2419200:
            await ctx.send("Duration capped at 28 days.")
            duration_seconds = 2419200

        try:
            await member.timeout(timedelta(seconds=duration_seconds), reason=reason)
            await ctx.send(f"{member.mention} muted for {duration}. Reason: {reason}")
        except discord.Forbidden:
            await ctx.send("I don't have permission to mute that member.")
        except discord.HTTPException as e:
            await ctx.send(f"Could not mute member: \n-#{e}")

    @mute.error
    async def mute_error(self, ctx, error):
        await ctx.reply(error)

    @commands.hybrid_command(name="unmute", description="Unmute a member")
    @app_commands.describe(
        member="The member to unmute",
    )
    @app_commands.guild_only()
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.allowed_contexts(guilds=True,dms=False,private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=False)
    @commands.has_permissions(moderate_members=True)
    @commands.guild_only()
    async def unmute(self, ctx, member: discord.Member):
        """Unmutes a member.
        Usage:
        `!unmute <member>`"""
        if not ctx.guild.me.guild_permissions.moderate_members:
            await ctx.send(
                "I do not have the `moderate members` permission required for this."
            )
            return

        try:
            await member.timeout(None)
            await ctx.send(f"{member.mention} successfully unmuted.")
        except discord.Forbidden:
            await ctx.send("I don't have permission to unmute that member.")
        except discord.HTTPException as e:
            await ctx.send(f"Could not unmute member: \n-#{e}")

    @unmute.error
    async def unmute_error(self, ctx, error):
        await ctx.reply(error)

    @commands.hybrid_command(name="kick", description="Kick a member")
    @app_commands.describe(member="The member to kick", reason="Reason for the kick")
    @app_commands.guild_only()
    @app_commands.default_permissions(kick_members=True)
    @app_commands.checks.has_permissions(kick_members=True)
    @app_commands.allowed_contexts(guilds=True,dms=False,private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=False)
    @commands.has_permissions(kick_members=True)
    @commands.guild_only()
    async def kick(
        self, ctx, member: discord.Member, *, reason: str = "No reason provided."
    ):
        """Kicks a member.
        Usage:
        `!kick <user> <reason>`
        """
        if not ctx.guild.me.guild_permissions.kick_members:
            await ctx.send(
                "I do not have the `kick members` permission required for this."
            )
            return

        if ctx.author.top_role.position <= member.top_role.position:
            await ctx.send("You cannot kick a member with a higher role than you.")
            return
        try:
            await member.kick(reason=reason)
            await ctx.send(f"{member.mention} has been kicked. Reason: {reason}")
        except discord.Forbidden:
            await ctx.send("I don't have permission to kick that member.")
        except discord.HTTPException as e:
            await ctx.send(f"Could not kick member: \n-#{e}")

    @kick.error
    async def kick_error(self, ctx, error):
        await ctx.reply(error)

    @commands.hybrid_command(name="ban", description="Ban a member")
    @app_commands.describe(
        member="The member to ban",
        days_str="The number of days worth of messages to delete from the user in a range of 0 to 7 days. Defaults to 0 days",
        reason="Reason for the ban",
    )
    @app_commands.default_permissions(ban_members=True)
    @app_commands.checks.has_permissions(ban_members=True)
    @app_commands.allowed_contexts(guilds=True,dms=False,private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=False)
    @commands.has_permissions(ban_members=True)
    @commands.guild_only()
    async def ban(
        self,
        ctx,
        member: discord.Member,
        days_str: str = "0",
        *,
        reason: str = "No reason provided.",
    ):
        """Bans a member.
        Usage:
        `!ban <user> <days to purge> <reason>`
        """
        delete_message_days: int
        try:
            delete_message_days = int(days_str)
        except ValueError:
            delete_message_days = 0
            reason = days_str + " " + reason

        if delete_message_days < 0:
            delete_message_days = 0
        elif delete_message_days > 7:
            delete_message_days = 7

        if not ctx.guild.me.guild_permissions.ban_members:
            await ctx.send(
                "I do not have the `ban members` permission required for this."
            )
            return

        guild_member: discord.Member | None = None
        try:
            guild_member = await ctx.guild.fetch_member(member.id)
        except discord.NotFound:
            await ctx.send("Couldn't find the user")
            return
        except discord.HTTPException as e:
            await ctx.send(f"Failed to fetch member for banning: \n-# {e}")
            return

        if guild_member and ctx.author.top_role.position <= member.top_role.position:
            await ctx.send("You cannot ban a member with a higher role than you.")
            return

        try:
            await ctx.guild.ban(
                member, delete_message_days=delete_message_days, reason=reason
            )
            await ctx.send(f"{member.mention} has been banned. Reason: {reason}")
        except discord.Forbidden:
            await ctx.send("I do not have permission to ban that member.")
        except discord.HTTPException as e:
            await ctx.send(f"Could not ban member: \n-# {e}")

    @ban.error
    async def ban_error(self, ctx, error):
        await ctx.reply(error)

    @commands.hybrid_command(name="unban", description="Unbans a member")
    @app_commands.describe(
        member="The member to unban",
    )
    @app_commands.guild_only()
    @app_commands.default_permissions(ban_members=True)
    @app_commands.checks.has_permissions(ban_members=True)
    @app_commands.allowed_contexts(guilds=True,dms=False,private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=False)
    @commands.has_permissions(ban_members=True)
    @commands.guild_only()
    async def unban(self, ctx, member: discord.User):
        """Unbans a member.
        Usage:
        `!unban <member>`"""
        if not ctx.guild.me.guild_permissions.ban_members:
            await ctx.send(
                "I do not have the `ban members` permission required for this."
            )
            return

        try:
            await ctx.guild.unban(member)
            await ctx.send(f"{member.mention} has been unbanned successfully.")
        except discord.Forbidden:
            await ctx.send("I do not have permission to unban that member.")
        except discord.HTTPException as e:
            await ctx.send(f"Could not unban member: \n-# {e}")

    @unban.error
    async def unban_error(self, ctx, error):
        await ctx.reply(error)

    @commands.hybrid_command(name="warn", description="Warns a member, irreversable")
    @app_commands.describe(
        member="The member to warn",
        reason="Reason for the warn",
    )
    @app_commands.guild_only()
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.allowed_contexts(guilds=True,dms=False,private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=False)
    @commands.has_permissions(moderate_members=True)
    @commands.guild_only()
    async def warn(
        self, ctx, member: discord.Member, reason: str = "No reason provided."
    ):
        """Warns a member.
        Usage:
        `!warn <member> [reason]`"""
        # Passthrough method so it gets grouped with the moderation commands, but logs the warn.
        if member.bot:
            return await ctx.send("You cannot warn a bot.", ephemeral=True)

        if member == ctx.author:
            return await ctx.send("You cannot warn yourself.", ephemeral=True)

        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            return await ctx.send(
                "You cannot warn someone with an equal or higher role than you.",
                ephemeral=True,
            )

        logger: commands.Cog | Logging | None = self.bot.get_cog("Logging")
        if logger:
            if hasattr(logger, "log_warn"):
                logger = cast(Logging, logger)
                await logger.log_warn(ctx, member, reason)
                await ctx.send(f"Successfully warned member for reason: `{reason}`")
            else:
                await ctx.send("Expected the logging cog, got something else instead.")
        else:
            await ctx.send("Couldn't find logging command, warn failed.")

    @warn.error
    async def warn_error(self, ctx, error):
        await ctx.reply(error)


async def setup(bot: MeowBot):
    cog = ModCommands(bot)
    await bot.add_cog(cog)
