import datetime
from multiprocessing import Event
from textwrap import dedent
from typing import TypedDict

from aiosqlite import Row
import discord
from discord.colour import Color
from discord.ext import commands, tasks

from main import MeowBot
from utils import reuse

from . import _settings as settings


class EventRegisterView(discord.ui.View):
    def __init__(self, bot: MeowBot) -> None:
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(
        label="Sign Up",
        style=discord.ButtonStyle.success,
        custom_id="signup_system:btn",
    )
    async def signup_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if not interaction.guild:
            return interaction.response.send_message(
                "Can't sign you up to a guild that doesn't exist"
            )
        await self.bot.db.events.upsert(interaction.guild.id, interaction.user.id)
        await interaction.response.send_message("Signed up MRAOOOW!!", ephemeral=True)

class EventRoles(TypedDict):
    event_host_id: int
    event_ping_id: int


class Events(commands.Cog):
    MIDNIGHT_UTC = datetime.time(
        hour=0, minute=0, second=0, tzinfo=datetime.timezone.utc
    )

    def __init__(self, bot: MeowBot) -> None:
        self.bot = bot
        self.ping_ids: dict[str, EventRoles] = {}
        super().__init__()

    async def set_roles(self, row):
        data: EventRoles = {
            "event_host_id": row["event_host_id"],
            "event_ping_id": row["event_ping_id"]
        }
        self.ping_ids[str(row["guild_id"])] = data

    async def populate_roles(self):
        rows = await self.bot.db.guilds.get_many()
        for row in rows: await self.set_roles(row)

    async def update_roles(self, guild_id: int):
        row = await self.bot.db.events.get(guild_id)
        if row: await self.set_roles(row)

    @commands.Cog.listener()
    async def on_ready(self):
        await self.populate_roles()

    @tasks.loop(time=MIDNIGHT_UTC)
    async def get_new_host(self, manual: bool = False):
        now = datetime.datetime.now(datetime.timezone.utc)
        if manual or now.weekday() == 6:
            guild_settings_list = await self.bot.db.guilds.get_many()
            for settings_data in guild_settings_list:
                try: await self._process_guild_host_update(settings_data)
                except Exception as e: print(e)

    async def _process_guild_host_update(self, guild_settings: Row):
        guild_id = guild_settings["guild_id"]
        role_id = guild_settings["event_host_id"]
        if not guild_id or not role_id: return
        guild = self.bot.get_guild(int(guild_id)) or await self.bot.fetch_guild(int(guild_id))
        if not guild: return
        event_host_role = guild.get_role(int(role_id))
        if not event_host_role: return
        new_host_row = await self.bot.db.events.get(guild_id)
        if not new_host_row: return
        user_id = new_host_row["user_id"]
        new_host = guild.get_member(user_id) or await guild.fetch_member(user_id)
        if not new_host: return
        for member in event_host_role.members: await member.remove_roles(event_host_role)
        await new_host.add_roles(event_host_role)
        dm_content = dedent(f"""
            You are the new host for this week in {guild.name}!
            You have been given the proper roles, use !eventping to ping people when needed!
            -# Abuse of the commands given to you will result in severe punishment
        """).strip()
        try: await new_host.send(content=dm_content)
        except discord.HTTPException: pass
        await self.bot.db.events.reset(guild_id)
        channel_id = guild_settings["event_announcements"]
        if not channel_id: return
        channel = guild.get_channel(int(channel_id))
        if not isinstance(channel, discord.TextChannel): return
        color = new_host.color if new_host.color.value != 0 else settings.DEFAULT_COLOR
        embed = discord.Embed(
            title="New event host!",
            description=f"{new_host.mention} is this week's event host!",
            color=color
        )
        embed.set_thumbnail(url=new_host.display_avatar.url)
        await channel.send(embed=embed)

    @reuse.cmd("event_button", hidden=True)
    @commands.has_permissions(administrator=True)
    async def event_button(self, ctx: commands.Context):
        embed: discord.Embed = discord.Embed(
            title="Event Host",
            description="Sign up to potentially become an event host next week!",
            color=settings.DEFAULT_COLOR,
        )
        await ctx.send(embed=embed, view=EventRegisterView(self.bot))

    @reuse.cmd("force_select", hidden=True)
    @commands.has_permissions(administrator=True)
    async def force_select(self, ctx: commands.Context):
        await self.get_new_host(True)
        return await ctx.reply("Ran!")

    @reuse.hybrid_cmd("eventping")
    @reuse.guild_only
    async def eventping(self, ctx: commands.Context):
        """Pings the role for notifying events
        Usage:
        `!eventping`
        """
        if not ctx.guild: return await ctx.reply("Can't find guild!", ephemeral=True)
        if not self.ping_ids[str(ctx.guild.id)]: return
        try:
            member = await ctx.guild.fetch_member(ctx.author.id)
            event_host_role = await ctx.guild.fetch_role(self.ping_ids[str(ctx.guild.id)]["event_host_id"])
            role = await ctx.guild.fetch_role(self.ping_ids[str(ctx.guild.id)]["event_ping_id"])
        except discord.DiscordException as e:
            return await ctx.reply(f"Erorr: {e}")
        if not event_host_role in member.roles: return await ctx.reply("Need the event host role to ping...", ephemeral=True)
        await ctx.send(content=f"ping!! {role.mention}", allowed_mentions=discord.AllowedMentions(users=False,roles=True))

    @event_button.error
    @eventping.error
    @force_select.error
    async def error(self, ctx, error):
        return await ctx.reply(error)


async def setup(bot: MeowBot):
    await bot.add_cog(Events(bot))
