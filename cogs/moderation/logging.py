import datetime
import time
import io
from typing import TypedDict

import discord
from discord.ext import commands

import sys
sys.path.append("..")
from main import MeowBot
from utils import reuse

class LogChannels(TypedDict):
    msg_logs: int | None
    member_logs: int | None
    mod_logs: int | None


class Logging(commands.Cog):
    def __init__(self, bot):
        self.bot: MeowBot = bot
        self.channels: dict[str, LogChannels] = {}
        self.message_counter: dict[str, int] = {}

    async def fetch_log_channel(self, guild: discord.Guild, name: str) -> reuse.TEXT_CHANNEL | None:
        guild_channels = self.channels.get(str(guild.id), {})
        channel_id = guild_channels.get(name)
        if not channel_id: return # nowhere to log
        channel = await guild.fetch_channel(channel_id)
        if not isinstance(channel, discord.abc.Messageable): return # cant send anything here
        return channel

    async def fetch_log_channel_or_fallback(self, guild: discord.Guild, name: str, fallback_name: str | None = None) -> reuse.TEXT_CHANNEL | None:
        return await self.fetch_log_channel(guild, name) or (await self.fetch_log_channel(guild, fallback_name) if fallback_name else None)

    def set_channels_data(self, row):
        data: LogChannels = {
            "msg_logs": row["msg_logs"],
            "member_logs": row["member_logs"],
            "mod_logs": row["mod_logs"],
        }
        self.channels[str(row["guild_id"])] = data

    async def populate_channels(self):
        """This populates the self.channels cache and refills it with the data from the DB"""
        if not self.channels:
            rows = await self.bot.db.guilds.get_many()
            for row in rows: self.set_channels_data(row)


    async def update_channels(self, guild_id: int):
        """This updates self.channels when a change is made with the setup command."""
        row = await self.bot.db.guilds.get(guild_id)
        if row: self.set_channels_data(row)

    @commands.Cog.listener()
    async def on_ready(self):
        await self.populate_channels()

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        # considering using raw_message_delete but we dont have the message in that case anyways so /shrug
        """Log deleted messages"""
        if not message.guild: return # not guild message
        if message.author.bot: return

        channel = await self.fetch_log_channel_or_fallback(message.guild, "msg_logs", "mod_logs")
        if not channel: return # cant log anywhere

        embed: discord.Embed = discord.Embed(timestamp=datetime.datetime.now(datetime.UTC), color=discord.Color.red())
        embed.set_author(
            name=f"{message.author.name} ({message.author.id})",
            icon_url=message.author.display_avatar.url,
        )

        deleter: discord.User | discord.Member | None = None

        async for entry in message.guild.audit_logs(action=discord.AuditLogAction.message_delete, limit=1):
            if entry.target and entry.target.id != message.author.id: continue

            entry_channel_id = getattr(getattr(entry.extra, "channel", None), "id", None)
            delete_count = getattr(entry.extra, "count", None)

            if entry_channel_id != message.channel.id: continue

            if entry.user:
                self.message_counter.setdefault(str(entry.user.id), 0)

                if (delete_count and self.message_counter[str(entry.user.id)] != delete_count):
                    self.message_counter[str(entry.user.id)] = +1
                    deleter = entry.user

            time_difference = (datetime.datetime.now(datetime.timezone.utc) - entry.created_at)

            if time_difference.total_seconds() < 15: deleter = entry.user

        async for entry in message.guild.audit_logs(action=discord.AuditLogAction.message_bulk_delete, limit=1):
            if entry.target and entry.target.id != message.author.id: continue

            entry_channel_id = getattr(getattr(entry.extra, "channel", None), "id", None)
            delete_count = getattr(entry.extra, "count", None)

            if entry_channel_id != message.channel.id: continue

            if self.message_counter[str(message.author.id)] != delete_count:
                self.message_counter[str(message.author.id)] = +1
                deleter = entry.user

            time_difference = (datetime.datetime.now(datetime.timezone.utc) - entry.created_at)

            if time_difference.total_seconds() < 15: deleter = entry.user

        if deleter:
            if deleter.display_avatar.url is not None:
                embed.set_footer(
                    text=f"{message.id}, deleted by {deleter.name}",
                    icon_url=deleter.display_avatar.url,
                )
            else: embed.set_footer(text=f"{message.id}, deleted by {deleter.name}")
        else: embed.set_footer(text=f"{message.id}")

        embed.add_field(name="Deleted Message", value=message.content)

        files: list[discord.File] = []
        if message.attachments:
            for attachment in message.attachments:
                try: files.append(await attachment.to_file(use_cached=True))
                except (discord.HTTPException, discord.NotFound, discord.Forbidden):
                    print(f"Failed to grab an attachment... {attachment.filename}")
        
        try: await channel.send(embed=embed, files=files[:10])  # cap to 10
        except discord.Forbidden: return  # cant send the message
        except discord.HTTPException: return  # cant send the exception anywhere

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        # same here
        """Log edited messages"""
        if not before.guild or not after.guild: return  # Not a guild message
        if before.author.bot: return
        if before.content == after.content: return

        channel = await self.fetch_log_channel_or_fallback(before.guild, "msg_logs", "mod_logs")
        if not channel: return # cant log anywhere

        embed = discord.Embed(timestamp=datetime.datetime.now(datetime.UTC), color=discord.Color.blue())
        embed.set_author(
            name=f"{before.author.name} ({before.author.id})",
            icon_url=before.author.display_avatar.url,
        )
        embed.set_footer(text=f"{before.id}")
        embed.add_field(name="Before", value=before.content, inline=True)
        embed.add_field(name="After", value=after.content, inline=True)

        try: await channel.send(embed=embed)
        except discord.Forbidden: return  # cant send the message
        except discord.HTTPException: return  # cant send the exception anywhere

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        """Log banned member"""

        channel = await self.fetch_log_channel(guild, "mod_logs")
        if not channel: return # cant log anywhere

        banner = None
        reason = None
        async for entry in guild.audit_logs(action=discord.AuditLogAction.ban, limit=1):
            if not entry.target or entry.target.id != user.id: continue  # missing audit log entry

            time_difference = (datetime.datetime.now(datetime.timezone.utc) - entry.created_at)

            if time_difference.total_seconds() < 15:
                banner = entry.user
                reason = entry.reason or "No reason provided"

        embed = discord.Embed(
            title="Member Banned",
            timestamp=datetime.datetime.now(datetime.UTC),
            color=discord.Color.red(),
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_author(name=f"{user.name}", icon_url=user.display_avatar.url)
        embed.set_footer(text=f"{user.id}")
        embed.add_field(name="Reason:", value=reason, inline=True)

        if banner: embed.add_field(name="Punished By:", value=f"{banner.mention}", inline=True)

        try: await channel.send(embed=embed)
        except discord.Forbidden: return  # cant send the message
        except discord.HTTPException: return  # cant send the exception anywhere

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        channel = await self.fetch_log_channel_or_fallback(member.guild, "member_logs", "mod_logs")
        if not channel: return # cant log anywhere

        if before.channel and after.channel and before.channel.id is after.channel.id: return # same channel dont log

        embed = discord.Embed(title=member.display_name, color=discord.Color.blurple())
        if not before.channel and after.channel: embed.description = f"Joined `{after.channel.name}` at <t:{int(time.time())}:t>"
        elif not after.channel and before.channel: embed.description = f"Left `{before.channel.name}` at <t:{int(time.time())}:t>"
        elif after.channel and before.channel: embed.description = f"Switched from `{before.channel.name}` to `{after.channel.name}` at <t:{int(time.time())}:t>"
        else: return
        embed.set_footer(text="meower's hub")

        try: await channel.send(embed=embed)
        except discord.Forbidden: return  # cant send the message
        except discord.HTTPException: return  # cant send the exception anywhere

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        """Log unbanned member"""
        channel = await self.fetch_log_channel(guild, "mod_logs")
        if not channel: return # cant log anywhere

        unbanner = None
        reason = None
        async for entry in guild.audit_logs(action=discord.AuditLogAction.ban, limit=1):
            if not entry.target or entry.target.id != user.id: continue  # missing audit log entry

            time_difference = (datetime.datetime.now(datetime.timezone.utc) - entry.created_at)

            if time_difference.total_seconds() < 15:
                unbanner = entry.user
                reason = entry.reason or "No reason provided"

        embed = discord.Embed(
            title="Member Unbanned",
            timestamp=datetime.datetime.now(datetime.UTC),
            color=discord.Color.green(),
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_author(name=f"{user.name}", icon_url=user.display_avatar.url)
        embed.set_footer(text=f"{user.id}")
        embed.add_field(name="Reason:", value=reason, inline=True)
        if unbanner: embed.add_field(name="Pardoned By:", value=f"{unbanner.mention}", inline=True)

        try: await channel.send(embed=embed)
        except discord.Forbidden: return  # cant send the message
        except discord.HTTPException: return  # cant send the exception anywhere

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """Log a member leaving, both kicked and of own accord."""

        member_logs_channel = await self.fetch_log_channel_or_fallback(member.guild, "member_logs", "mod_logs")
        mod_logs_channel = await self.fetch_log_channel(member.guild, "mod_logs")

        if member_logs_channel:
            embed: discord.Embed = discord.Embed(
                title="Member Left",
                timestamp=datetime.datetime.now(datetime.UTC),
                color=discord.Colour(0x555555),
            )

            if member.display_avatar.url:
                if member.global_name:
                    embed.set_author(
                        icon_url=member.display_avatar.url,
                        name=f"{member.global_name} ({member.name})",
                    )
                else:
                    embed.set_author(
                        icon_url=member.display_avatar.url,
                        name=f"{member.name}"
                    )
                embed.set_thumbnail(url=member.display_avatar.url)
                embed.set_footer(text=f"{member.id}", icon_url=member.display_avatar.url)

            if len(member.roles) > 1:
                long_ass_mention_string: str = ""
                for role in member.roles:
                    if role.is_default(): continue
                    long_ass_mention_string += f"{role.mention} "

                embed.add_field(name="Roles:", value=long_ass_mention_string, inline=True)
            else: embed.add_field(name="Roles:", value="Member had no roles.")

            try: await member_logs_channel.send(embed=embed)
            except discord.Forbidden: return  # cant send the message
            except discord.HTTPException: return  # cant send the exception anywhere

        if not mod_logs_channel: return

        kicker = None
        reason = None
        async for entry in member.guild.audit_logs(action=discord.AuditLogAction.kick, limit=1):
            if entry.target and entry.target.id != member.id: continue  # missing audit log entry
            kicker = entry.user
            reason = entry.reason or "No reason provided"
        if not kicker: return

        kick_embed: discord.Embed = discord.Embed(
            title="Member Kicked",
            timestamp=datetime.datetime.now(datetime.UTC),
            color=discord.Colour(0x555555),
        )
        if kicker.display_avatar.url: kick_embed.set_thumbnail(url=kicker.display_avatar.url)
        if member.display_avatar.url:
            kick_embed.set_author(
                name=f"{member.name}",
                icon_url=member.display_avatar.url
            )
        kick_embed.set_footer(text=f"{member.id}")
        kick_embed.add_field(name="Reason:", value=reason, inline=True)
        if kicker: kick_embed.add_field(name="Punished By:", value=f"{kicker.mention}", inline=True)

        try: await mod_logs_channel.send(embed=kick_embed)
        except discord.Forbidden: return  # cant send the message
        except discord.HTTPException: return  # cant send the exception anywhere

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """Log timeouts"""
        if not before.is_timed_out() and not after.is_timed_out(): return  # nothing to log...
        if before.bot: return

        channel = await self.fetch_log_channel(before.guild, "mod_logs")
        if not channel: return # cant log anywhere

        timer = None
        reason: str = "No reason provided"
        async for entry in before.guild.audit_logs(action=discord.AuditLogAction.member_update, limit=1):
            if entry.target and entry.target.id != before.id: continue  # missing audit log entry
            timer: discord.User | discord.Member | None = entry.user
            reason = entry.reason or "No reason provided"

        embed: discord.Embed
        if not before.is_timed_out() and after.is_timed_out():
            embed = discord.Embed(
                title="Member Muted",
                timestamp=datetime.datetime.now(datetime.UTC),
                color=discord.Color.red(),
            )
            embed.set_author(name=f"{before.name}", icon_url=before.display_avatar.url)
            embed.set_footer(text=f"{before.id}")
            if not after.timed_out_until: embed.add_field(name="Reason:", value=reason + "\n**Until**: Unknown", inline=True)
            else: embed.add_field(name="Reason:", value=reason + f"\n**Until**: <t:{int(after.timed_out_until.timestamp())}:t>", inline=True)
            embed.set_thumbnail(url=before.display_avatar.url)
            if timer: embed.add_field(name="Punished By:", value=timer.mention)
        elif not after.is_timed_out() and before.is_timed_out():
            embed = discord.Embed(
                title="Member Unmuted",
                timestamp=datetime.datetime.now(datetime.UTC),
                color=discord.Color.green(),
            )
            embed.set_footer(text=f"{before.id}")
            embed.add_field(name="Reason:", value=reason, inline=True)
            embed.set_author(name=f"{before.name}", icon_url=before.display_avatar.url)
            embed.set_thumbnail(url=before.display_avatar.url)
            if timer: embed.add_field(name="Pardoned By:", value=timer.mention)
        else: return  # timeout state didnt change, nothing to log

        try: await channel.send(embed=embed)
        except discord.Forbidden: return  # cant send the message
        except discord.HTTPException: return  # cant send anywhere

    async def log_warn(self, ctx, member: discord.Member, reason: str, warning_id):
        """Logger of the warn command"""

        try: await member.send(f"You were warned in {ctx.guild.name} for `{reason}`\nWarning ID: `{warning_id}`")
        except discord.Forbidden: pass  # cant dm the member

        channel = await self.fetch_log_channel(member.guild, "mod_logs")
        if not channel: return # cant log anywhere

        embed = discord.Embed(
            title="Member Warned",
            timestamp=datetime.datetime.now(datetime.UTC),
            color=discord.Color.blurple(),
        )
        embed.set_author(name=f"{member.name}", icon_url=member.display_avatar.url)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Reason:", value=reason, inline=True)
        embed.add_field(name="Punished By:", value=ctx.author.mention)
        embed.set_footer(text=f"№{warning_id} - {member.id}")

        try: await channel.send(embed=embed)
        except discord.Forbidden: return  # cant send the message
        except discord.HTTPException: return  # cant send anywhere

    async def log_purge(self, ctx: commands.Context, executor: discord.Member, messages: list[discord.Message]):
        """Logger of the warn command"""

        channel = await self.fetch_log_channel(executor.guild, "mod_logs")
        if not channel: return # cant log anywhere

        embed = discord.Embed(
            title="Purrrge",
            timestamp=datetime.datetime.now(datetime.UTC),
            color=discord.Color.blurple(),
        )
        embed.set_author(name=f"{executor.name}", icon_url=executor.display_avatar.url)
        embed.set_thumbnail(url=executor.display_avatar.url)
        embed.add_field(name="Amount:", value=len(messages), inline=True)
        embed.add_field(name="At:", value=ctx.channel.mention)

        text = ""
        for message in messages:
            text += f"{message.created_at} {message.author.name} {message.content} {"(edited "+str(message.edited_at)+")" if message.edited_at else ""}\n"

        files = []
        if text: files.append(discord.File(io.BytesIO(text.encode("utf-8")), filename="purrrged.txt"))

        try: await channel.send(embed=embed, files = files)
        except discord.Forbidden: return  # cant send the message
        except discord.HTTPException: return  # cant send anywhere



async def setup(bot):
    await bot.add_cog(Logging(bot))
