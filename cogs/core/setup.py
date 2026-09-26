from typing import cast

import aiosqlite
import discord
from discord.ext import commands

from cogs.fun.events import Events
from main import MeowBot
from utils.locales import Locale

from ..moderation.logging import Logging

import sys
sys.path.append("...")
from utils.db import DB

async def embed_helper(
    db: DB, ctx: commands.Context
) -> discord.Embed | None:
    embed = discord.Embed(
        title="Setup Panel",
        description="Use the menu below to change your server settings.",
        color=discord.Color.blue(),
    )
    if not ctx.guild: return  # Cannot continue, bail.

    row = await db.guilds.get(ctx.guild.id)
    if not row: return  # bail out

    items = dict(zip(row.keys(), row))
    items.pop("guild_id", None)
    for setting, value in items.items():
        setting_pretty = Locale.get(f"setup.{setting}")
        if value:
            try:
                channel = await ctx.guild.fetch_channel(value)
                channel_pretty = channel.mention
            except discord.NotFound:
                try:
                    role = await ctx.guild.fetch_role(value)
                    channel_pretty = role.mention
                except discord.NotFound:
                    channel_pretty = f"Missing Channel \n-# `{value}`"
            except discord.Forbidden:
                channel_pretty = f"Inaccessible channel \n-# `{value}`"
            except ValueError:
                channel_pretty = f"Invalid ID format\n-# `{value}`"
        else:
            channel_pretty = "None set yet."
        embed.add_field(name=setting_pretty, value=channel_pretty, inline=True)

    return embed


class ChannelModal(discord.ui.Modal, title="Set Channel"):
    def __init__(self, setting, guild_id, view, bot: MeowBot):
        super().__init__()
        self.setting = setting
        self.guild_id = guild_id
        self.view = view
        self.bot = bot

    channel_input = discord.ui.TextInput(
        label="Channel",
        placeholder="Enter #general, channel ID, or name...",
        required=True,
    )

    async def on_submit(self, interaction: discord.Interaction):
        if (
            isinstance(interaction.user, discord.Member)
            and not interaction.user.guild_permissions.administrator
            and not interaction.user.guild_permissions.manage_guild
        ):
            await interaction.response.send_message(
                "You need the 'Manage Server' or 'Administrator' permission to edit settings.",
                ephemeral=True,
            )
            return
        await interaction.response.defer(ephemeral=True)

        client: MeowBot | None = None
        if hasattr(interaction.client, "db"):
            client = cast(MeowBot, interaction.client)

        if not client:
            await interaction.edit_original_response(content="Couldn't get the database!")
            return
        if not interaction.message:
            await interaction.edit_original_response(content="No message... idk....")
            return
        ctx = await client.get_context(interaction.message)
        if not ctx.guild:
            await interaction.edit_original_response(content="Not a guild.")
            return
        try:
            channel = await commands.TextChannelConverter().convert(
                ctx, self.channel_input.value
            )

            permissions = channel.permissions_for(ctx.guild.me)

            if not permissions.view_channel:
                await interaction.edit_original_response(content="I cannot access that channel!")
                return
            if not permissions.send_messages:
                await interaction.edit_original_response(content=
                    "I cannot send messages in that channel!"
                )
                return
        except commands.BadArgument:
            try:
                channel = await commands.RoleConverter().convert(
                    ctx, self.channel_input.value
                )

            except commands.BadArgument:
                await interaction.edit_original_response(content=
                    "Invalid channel or role. Please use a mention, ID, or name."
                )
                return

        await client.db.guilds.upd(self.guild_id, autocommit=True, **{self.setting: channel.id})

        logging_cog: Logging | commands.Cog | None = self.bot.get_cog("Logging")

        if logging_cog and hasattr(logging_cog, "update_channels"):
            logging_cog = cast(Logging, logging_cog)
            await logging_cog.update_channels(guild_id=ctx.guild.id)
        else:
            print("Could not fetch logging cog correctly")

        events_cog: Events | None = self.bot.get_cog_by_class(Events)
        if events_cog:
            await events_cog.update_roles(guild_id=ctx.guild.id)
        else:
            print("Could not fetch Events cog correctly")


        embed = await embed_helper(client.db, ctx)
        if not embed:
            await interaction.edit_original_response(content=
                "Failed to make embed! Report this issue as soon as possible"
            )
            return

        await interaction.edit_original_response(embed=embed)
        await interaction.followup.send(
            f"**{self.setting}** set to {channel.mention}", ephemeral=True
        )


class SetupView(discord.ui.View):
    def __init__(self, bot: MeowBot):
        super().__init__()
        self.selected_setting = None
        self.bot = bot

    @discord.ui.select(
        placeholder="Choose a setting",
        options=[
            discord.SelectOption(label="Message Logs", value="msg_logs"),
            discord.SelectOption(label="Member Logs", value="member_logs"),
            discord.SelectOption(label="Moderation Logs", value="mod_logs"),
            discord.SelectOption(label="Starboard Channel", value="sb_channel"),
            discord.SelectOption(label="Event Ping Role ID", value="event_ping_id"),
            discord.SelectOption(label="Event Host Role ID", value="event_host_id"),
            discord.SelectOption(label="Event Announcements", value="event_announcements")
        ],
    )
    async def setting_dropdown(
        self, interaction: discord.Interaction, select: discord.ui.Select
    ):
        self.selected_setting = select.values[0]
        if interaction.guild is not None:
            await interaction.response.send_modal(
                ChannelModal(self.selected_setting, interaction.guild.id, self, self.bot)
            )
        else:
            await interaction.response.send_message("Not a discord server!")


class Setup(commands.Cog):
    def __init__(self, bot: MeowBot):
        self.bot = bot
        self.db = bot.db

    @commands.command()
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def setup(self, ctx: commands.Context):
        """Set server settings"""
        embed = await embed_helper(self.db, ctx)

        if not embed:
            await ctx.send("Failed to make embed!")
            return

        view = SetupView(self.bot)
        await ctx.send(embed=embed, view=view, ephemeral=True)


async def setup(bot: MeowBot):
    await bot.add_cog(Setup(bot))
