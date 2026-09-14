import datetime
from typing import TypedDict

import discord
from discord.ext import commands


class LogChannels(TypedDict):
    msg_logs: int | None
    member_logs: int | None
    mod_logs: int | None


class Logging(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.channels: dict[str, LogChannels] = {}
        self.message_counter: dict[str, int] = {}

    async def populate_channels(self):
        """This populates the self.channels cache and refills it with the data from the DB"""
        if not self.channels:
            async with self.bot.db.execute("SELECT * FROM guilds") as cursor:
                rows = await cursor.fetchall()
                for row in rows:
                    data: LogChannels = {
                        "msg_logs": row["msg_logs"],
                        "member_logs": row["member_logs"],
                        "mod_logs": row["mod_logs"],
                    }
                    guild_id: str = str(row["guild_id"])
                    self.channels[guild_id] = data

    async def update_channels(self, guild_id: str):
        """This updates self.channels when a change is made with the setup command."""
        async with self.bot.db.execute(
            "SELECT * FROM guilds WHERE guild_id = ?", (guild_id,)
        ) as cursor:
            row = await cursor.fetchone()
            data: LogChannels = {
                "msg_logs": row["msg_logs"],
                "member_logs": row["member_logs"],
                "mod_logs": row["mod_logs"],
            }
            guild_id = str(row["guild_id"])
            self.channels[guild_id] = data

    @commands.Cog.listener()
    async def on_ready(self):
        await self.populate_channels()

    @commands.Cog.listener()
    async def on_message_delete(
        self, message: discord.Message
    ):  # considering using raw_message_delete but we dont have the message in that case anyways so /shrug
        """Log deleted messages"""
        if not message.guild:
            return
        guild_channels = self.channels.get(str(message.guild.id))

        if guild_channels is None or guild_channels.get("msg_logs") is None:
            return  # no channel to log to

        if message.author.bot:
            return

        embed: discord.Embed = discord.Embed(
            timestamp=datetime.datetime.now(datetime.UTC), color=discord.Color.red()
        )

        embed.set_author(
            name=f"{message.author.name} ({message.author.id})",
            icon_url=message.author.display_avatar.url,
        )

        deleter: discord.User | discord.Member | None = None

        async for entry in message.guild.audit_logs(
            action=discord.AuditLogAction.message_delete, limit=1
        ):
            if entry.target is not None and entry.target.id != message.author.id:
                continue

            entry_channel_id = getattr(
                getattr(entry.extra, "channel", None), "id", None
            )
            delete_count = getattr(entry.extra, "count", None)

            if entry_channel_id != message.channel.id:
                continue

            if entry.user:
                self.message_counter.setdefault(str(entry.user.id), 0)

                if (
                    delete_count
                    and self.message_counter[str(entry.user.id)] != delete_count
                ):
                    self.message_counter[str(entry.user.id)] = +1
                    deleter = entry.user

            time_difference = (
                datetime.datetime.now(datetime.timezone.utc) - entry.created_at
            )

            if time_difference.total_seconds() < 15:
                deleter = entry.user

        async for entry in message.guild.audit_logs(
            action=discord.AuditLogAction.message_bulk_delete, limit=1
        ):
            if entry.target is not None and entry.target.id != message.author.id:
                continue

            entry_channel_id = getattr(
                getattr(entry.extra, "channel", None), "id", None
            )
            delete_count = getattr(entry.extra, "count", None)

            if entry_channel_id != message.channel.id:
                continue

            if self.message_counter[str(message.author.id)] != delete_count:
                self.message_counter[str(message.author.id)] = +1
                deleter = entry.user

            time_difference = (
                datetime.datetime.now(datetime.timezone.utc) - entry.created_at
            )

            if time_difference.total_seconds() < 15:
                deleter = entry.user

        if deleter:
            if deleter.display_avatar.url is not None:
                embed.set_footer(
                    text=f"{message.id}, deleted by {deleter.name}",
                    icon_url=deleter.display_avatar.url,
                )
            else:
                embed.set_footer(text=f"{message.id}, deleted by {deleter.name}")
        else:
            embed.set_footer(text=f"{message.id}")

        embed.add_field(name="Deleted Message", value=message.content)
        guild_id = guild_channels.get("msg_logs")
        channel: (
            discord.TextChannel | discord.Thread | discord.abc.GuildChannel | None
        ) = None
        if not guild_id:
            return
        channel = await message.guild.fetch_channel(guild_id)
        if message.attachments:
            files: list[discord.File] = []
            for attachment in message.attachments:
                try:
                    file: discord.File = await attachment.to_file(use_cached=True)
                    files.append(file)
                except (discord.HTTPException, discord.NotFound, discord.Forbidden):
                    print(f"Failed to grab an attachment... {attachment.filename}")
            if isinstance(channel, discord.abc.Messageable):
                try:
                    await channel.send(embed=embed, files=files[:10])  # cap to 10
                except discord.Forbidden:
                    return  # cant send the message
                except discord.HTTPException:
                    return  # cant send the exception anywhere
            else:
                return
        else:
            if isinstance(channel, discord.abc.Messageable):
                try:
                    await channel.send(embed=embed)
                except discord.Forbidden:
                    return  # cant send the message
                except discord.HTTPException:
                    return  # cant send the exception anywhere
            else:
                return

    @commands.Cog.listener()
    async def on_message_edit(
        self, before: discord.Message, after: discord.Message
    ):  # same here
        """Log edited messages"""
        if not before.guild or after.guild:
            return  # Not a guild message
        guild_channels = self.channels.get(str(before.guild.id))

        if guild_channels is None or guild_channels.get("msg_logs") is None:
            return  # no channel to log to

        if before.author.bot:
            return

        if before.content == after.content:
            return

        embed: discord.Embed = discord.Embed(
            timestamp=datetime.datetime.now(datetime.UTC), color=discord.Color.blue()
        )

        embed.set_author(
            name=f"{before.author.name} ({before.author.id})",
            icon_url=before.author.display_avatar.url,
        )

        embed.set_footer(text=f"{before.id}")

        embed.add_field(name="Before", value=before.content, inline=True)
        embed.add_field(name="After", value=after.content, inline=True)

        channel_id = guild_channels.get("msg_logs")
        if not channel_id:
            return
        channel = await before.guild.fetch_channel(channel_id)

        if isinstance(channel, discord.abc.Messageable):
            try:
                await channel.send(embed=embed)
            except discord.Forbidden:
                return  # cant send the message
            except discord.HTTPException:
                return  # cant send the exception anywhere
        else:
            return

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        """Log banned member"""
        guild_channels = self.channels.get(str(guild.id))

        if guild_channels is None or guild_channels.get("mod_logs") is None:
            return  # no channel to log to

        banner = None
        reason = None
        async for entry in guild.audit_logs(action=discord.AuditLogAction.ban, limit=1):
            if entry.target is None or entry.target.id != user.id:
                continue  # missing audit log entry

            time_difference = (
                datetime.datetime.now(datetime.timezone.utc) - entry.created_at
            )

            if time_difference.total_seconds() < 15:
                banner = entry.user
                reason = entry.reason or "No reason provided"

        embed: discord.Embed = discord.Embed(
            title="Member Banned",
            timestamp=datetime.datetime.now(datetime.UTC),
            color=discord.Color.red(),
        )

        if banner is not None:
            embed.set_thumbnail(url=banner.display_avatar.url)

        embed.set_author(name=f"{user.name}", icon_url=user.display_avatar.url)

        embed.set_footer(text=f"{user.id}")

        embed.add_field(name="Reason:", value=reason, inline=True)

        if banner:
            embed.add_field(name="Punished By:", value=f"{banner.mention}", inline=True)

        channel_id = guild_channels.get("mod_logs")
        if not channel_id:
            return
        channel = await guild.fetch_channel(channel_id)

        if isinstance(channel, discord.abc.Messageable):
            try:
                await channel.send(embed=embed)
            except discord.Forbidden:
                return  # cant send the message
            except discord.HTTPException:
                return  # cant send the exception anywhere
        else:
            return

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        """Log unbanned member"""
        guild_channels = self.channels.get(str(guild.id))

        if guild_channels is None or guild_channels.get("mod_logs") is None:
            return  # no channel to log to

        unbanner = None
        reason = None
        async for entry in guild.audit_logs(action=discord.AuditLogAction.ban, limit=1):
            if entry.target is None or entry.target.id != user.id:
                continue  # missing audit log entry

            time_difference = (
                datetime.datetime.now(datetime.timezone.utc) - entry.created_at
            )

            if time_difference.total_seconds() < 15:
                unbanner = entry.user
                reason = entry.reason or "No reason provided"

        embed: discord.Embed = discord.Embed(
            title="Member Unbanned",
            timestamp=datetime.datetime.now(datetime.UTC),
            color=discord.Color.green(),
        )

        if unbanner is not None:
            embed.set_thumbnail(url=unbanner.display_avatar.url)

        embed.set_author(name=f"{user.name}", icon_url=user.display_avatar.url)

        embed.set_footer(text=f"{user.id}")

        embed.add_field(name="Reason:", value=reason, inline=True)

        if unbanner:
            embed.add_field(
                name="Pardoned By:", value=f"{unbanner.mention}", inline=True
            )

        channel_id = guild_channels.get("mod_logs")
        if not channel_id:
            return
        channel = await guild.fetch_channel(channel_id)

        if isinstance(channel, discord.abc.Messageable):
            try:
                await channel.send(embed=embed)
            except discord.Forbidden:
                return  # cant send the message
            except discord.HTTPException:
                return  # cant send the exception anywhere
        else:
            return

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """Log a member leaving, both kicked and of own accord."""
        guild: discord.Guild = member.guild

        guild_channels = self.channels.get(str(guild.id))

        if guild_channels is None:
            return

        member_log_channel_id = guild_channels.get("member_logs")
        if member_log_channel_id:
            embed: discord.Embed = discord.Embed(
                title="Member Left",
                timestamp=datetime.datetime.now(datetime.UTC),
                color=discord.Color.from_str("#555555"),
            )

            if member.display_avatar.url is not None:
                if member.global_name is not None:
                    embed.set_author(
                        icon_url=member.display_avatar.url,
                        name=f"{member.global_name} ({member.name})",
                    )
                else:
                    embed.set_author(
                        icon_url=member.display_avatar.url, name=f"{member.name}"
                    )
                embed.set_thumbnail(url=member.display_avatar.url)
                embed.set_footer(
                    text=f"{member.id}", icon_url=member.display_avatar.url
                )

            if len(member.roles) != 1:
                long_ass_mention_string: str = ""
                for role in member.roles:
                    if "everyone" in role.name:
                        continue
                    long_ass_mention_string += f"{role.mention} "

                embed.add_field(
                    name="Roles:", value=long_ass_mention_string, inline=True
                )
            else:
                embed.add_field(name="Roles:", value="Member had no roles.")

            channel = await guild.fetch_channel(member_log_channel_id)

            if isinstance(channel, discord.abc.Messageable):
                try:
                    await channel.send(embed=embed)
                except discord.Forbidden:
                    return  # cant send the message
                except discord.HTTPException:
                    return  # cant send the exception anywhere
            else:
                return

        if guild_channels.get("mod_logs") is None:
            return  # no channel to log to

        kicker = None
        reason = None
        async for entry in guild.audit_logs(
            action=discord.AuditLogAction.kick, limit=1
        ):
            if entry.target is not None and entry.target.id != member.id:
                continue  # missing audit log entry

            kicker = entry.user

            reason = entry.reason or "No reason provided"

        if kicker:  # make sure they were kicked
            kick_embed: discord.Embed = discord.Embed(
                title="Member Kicked",
                timestamp=datetime.datetime.now(datetime.UTC),
                color=discord.Color.from_str("#555555"),
            )

            if kicker.display_avatar.url is not None:
                kick_embed.set_thumbnail(url=kicker.display_avatar.url)

            if member.display_avatar.url is not None:
                kick_embed.set_author(
                    name=f"{member.name}", icon_url=member.display_avatar.url
                )

            kick_embed.set_footer(text=f"{member.id}")

            kick_embed.add_field(name="Reason:", value=reason, inline=True)

            if kicker:
                kick_embed.add_field(
                    name="Punished By:", value=f"{kicker.mention}", inline=True
                )
            mod_channel_id = guild_channels.get("mod_logs")
            if not mod_channel_id:
                return
            mod_channel = await guild.fetch_channel(mod_channel_id)
            if isinstance(mod_channel, discord.abc.Messageable):
                try:
                    await mod_channel.send(embed=kick_embed)
                except discord.Forbidden:
                    return  # cant send the message
                except discord.HTTPException:
                    return  # cant send the exception anywhere
            else:
                return

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """Log timeouts"""

        if before.is_timed_out() is not True and after.is_timed_out() is not True:
            return  # nothing to log...

        guild: discord.Guild = before.guild

        guild_channels = self.channels.get(str(guild.id))

        if guild_channels is None or guild_channels.get("mod_logs") is None:
            return  # no where to log to....

        timer = None
        reason: str = "No reason provided"
        async for entry in guild.audit_logs(
            action=discord.AuditLogAction.member_update, limit=1
        ):
            if entry.target is not None and entry.target.id != before.id:
                continue  # missing audit log entry

            timer: discord.User | discord.Member | None = entry.user

            reason = entry.reason or "No reason provided"

        channel_id = guild_channels.get("mod_logs")
        if not channel_id:
            return
        channel = await before.guild.fetch_channel(channel_id)
        embed: discord.Embed
        if not before.is_timed_out() and after.is_timed_out():
            embed = discord.Embed(
                title="Member Muted",
                timestamp=datetime.datetime.now(datetime.UTC),
                color=discord.Color.red(),
            )

            embed.set_author(name=f"{before.name}", icon_url=before.display_avatar.url)

            embed.set_footer(text=f"{before.id}")

            embed.add_field(name="Reason:", value=reason, inline=True)

            if timer:
                embed.set_thumbnail(url=timer.display_avatar.url)
                embed.add_field(name="Punished By:", value=timer.mention)
        elif not after.is_timed_out() and before.is_timed_out():
            embed = discord.Embed(
                title="Member Unmuted",
                timestamp=datetime.datetime.now(datetime.UTC),
                color=discord.Color.green(),
            )

            embed.set_footer(text=f"{before.id}")

            embed.add_field(name="Reason:", value=reason, inline=True)

            embed.set_author(name=f"{before.name}", icon_url=before.display_avatar.url)

            if timer:
                embed.set_thumbnail(url=timer.display_avatar.url)
                embed.add_field(name="Pardoned By:", value=timer.mention)
        else:
            return  # timeout state didnt change nothing to log

        if isinstance(channel, discord.abc.Messageable):
            try:
                await channel.send(embed=embed)
            except discord.Forbidden:
                return  # cant send the message
            except discord.HTTPException:
                return  # cant send the exception anywhere
        else:
            return

    async def log_warn(self, ctx, member: discord.Member, reason: str):
        """Core of the warn command"""
        query = """
            INSERT INTO warnings (guild_id, user_id, moderator_id, reason)
            VALUES (?, ?, ?, ?)
        """
        async with self.bot.db.cursor() as cursor:
            await cursor.execute(
                query, (ctx.guild.id, member.id, ctx.author.id, reason)
            )
            warning_id = cursor.lastrowid
        await self.bot.db.commit()

        try:
            await member.send(
                f"You were warned in {ctx.guild.name} for `{reason}`\nWarning ID: `{warning_id}`"
            )
        except discord.Forbidden:
            pass  # cant dm the member

        guild: discord.Guild = ctx.guild

        guild_channels = self.channels.get(str(guild.id))

        if guild_channels is None or guild_channels.get("mod_logs") is None:
            return  # no channel

        embed = discord.Embed(
            title="Member Warned",
            timestamp=datetime.datetime.now(datetime.UTC),
            color=discord.Color.blurple(),
        )

        embed.set_author(name=f"{member.name}", icon_url=member.display_avatar.url)

        embed.set_footer(text=f"{member.id}")

        embed.add_field(name="Reason:", value=reason, inline=True)

        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.add_field(name="Punished By:", value=ctx.author.mention)

        channel_id = guild_channels.get("mod_logs")
        if not channel_id:
            return
        channel = await ctx.guild.fetch_channel(channel_id)

        if isinstance(channel, discord.abc.Messageable):
            try:
                await channel.send(embed=embed)
            except discord.Forbidden:
                return  # cant send the message
            except discord.HTTPException:
                return  # cant send the exception anywhere
        else:
            return


async def setup(bot):
    await bot.add_cog(Logging(bot))
