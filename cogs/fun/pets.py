import random
from calendar import c
from io import BytesIO

import discord
from discord import app_commands
from discord.ext import commands
from petpetgif import petpet

from main import MeowBot

from . import _settings as settings

import sys
sys.path.append("...")
from utils import reuse
from utils.locales import Locale
from utils.db import DB
from utils.asserted import Assert

class Pets(commands.Cog):
    PET_REPLIES: list[str] = [
        "*\\*blows up\\**",
        "*\\*bites your hand\\**",
        "*\\*blep\\**",
        "*\\*paws at you\\**",
        "*\\*licks you\\**",
        ">w<",
        "^w^",
        ">///<",
        ":3",
        "meow",
        "mmnrp",
        "purr",
        "purrrrrrrrr",
        "prrrrrr",
        "awawawawa",
        "mroow",
        "mrrrp",
        "mraow",
        "meawwww",
    ]

    MAX_PETPET_COUNT = 4
    MAX_MESSAGE_LENGTH = 20

    def __init__(self, bot: MeowBot):
        self.bot: MeowBot = bot
        self.cache: dict[tuple[int, int], str] = {}


    async def update_caches(self):
        self.cache = {}
        rows = await self.bot.db.pet.get_many()
        for row in rows:
            self.update_cache_entry(row["guild_id"], row["user_id"], row["message"])  # populate cache

    def update_cache_entry(self, guild_id: int, member_id: int, message: str):
        self.cache[guild_id, member_id] = message

    def delete_cache_entry(self, guild_id: int, member_id: int) -> str:
        return self.cache.pop((guild_id, member_id), "")

    async def set_pet_reply(self, guild_id: int, member_id: int, message: str) -> str:
        message = message[:self.MAX_MESSAGE_LENGTH]
        await self.bot.db.pet.upsert(guild_id, member_id, message)
        self.update_cache_entry(guild_id, member_id, message)
        return message

    async def reset_pet_reply(self, guild_id: int, member_id: int) -> str:
        await self.bot.db.pet.rem(guild_id, member_id)
        message = self.delete_cache_entry(guild_id, member_id)
        return message

    async def process_message(self, member: reuse.USER | discord.Guild, author_id: int | None = None, guild: discord.Guild | None = None):
        mention = "error"
        if isinstance(member, reuse.USER):
            mention = Locale.get("petpet.entry", petted = member.mention)
            custom = ""
            if member.id == self.bot.user.id: custom = random.choice(self.PET_REPLIES)
            elif member.id == author_id: custom = Locale.get("petpet.custom.self")
            elif guild and member.id and (guild.id, member.id) in self.cache: custom = self.cache[guild.id, member.id]
            if custom: mention = Locale.get("petpet.entry.custom", petted = mention, custom = custom)
        elif isinstance(member, discord.Guild):
            mention = Locale.get("petpet.entry.guild", petted = member.name)
        return mention

    async def process_bytes(self, bytes: bytes):
        source = BytesIO(bytes)
        dest = BytesIO()
        petpet.make(source, dest)
        dest.seek(0)
        return dest

    async def process_member(self, member: reuse.USER):
        return await self.process_bytes(await member.display_avatar.read())

    async def process_guild(self, guild: reuse.GUILD):
        if not guild or not guild.icon: return
        return await self.process_bytes(await guild.icon.read())


    @commands.command()
    async def pet(self, ctx):
        await ctx.reply(random.choice(self.PET_REPLIES))

    async def petpet_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]: # wrapper, cant directly call self.bot.user_autocomplete
        return await self.bot.user_autocomplete(interaction=interaction, current=current)

    async def petpet(self, ctx: commands.Context | None,
                    author_id: int, targets: list[reuse.USER | str],
                    guild: discord.Guild | None) -> tuple[list[str], list[discord.File]] | tuple[None, None]:
        to_ping: list[str] = []
        files: list[discord.File] = []

        for member in targets:
            if isinstance(member, str) and member not in settings.EVERYONE and ctx: member = await self.bot.extract_user(ctx, member)
            if isinstance(member, reuse.USER):
                to_ping.append(await self.process_message(member, author_id, guild))
                files.append(discord.File(await self.process_member(member), filename=f"{member.name}-petpet.gif"))
            elif isinstance(member, str) and member in settings.EVERYONE and guild:
                dest = await self.process_guild(guild)
                if not dest: continue
                to_ping.append(await self.process_message(guild))
                files.append(discord.File(dest, filename=f"{guild}-petpet.gif"))
            if len(to_ping) >= self.MAX_PETPET_COUNT: break
        if len(to_ping) > 2: to_ping[-1] = Locale.get("petpet.entry.join.last") + to_ping[-1]

        return to_ping, files


    @reuse.cmd("petpet")
    async def prefix_petpet(self, ctx: commands.Context,
        user1: str | None = None,
        user2: str | None = None,
        user3: str | None = None,
        user4: str | None = None,
    ):
        targets: list[reuse.USER | str] = [u for u in (user1, user2, user3, user4) if u is not None]
        if not targets: return await ctx.send(Locale.get("error.no_members_arg"), ephemeral=True)
        await ctx.defer()
        to_ping, files = await self.petpet(ctx, ctx.author.id, targets, ctx.guild)
        if not to_ping or not files: return await ctx.send(Locale.get("error.no_members_arg"), ephemeral=True)
        await ctx.reply(Locale.get("petpet.result", petter = ctx.author.mention, petted = Locale.get("petpet.entry.join").join(to_ping)), files=files, allowed_mentions=reuse.NO_MENTION)


    @reuse.app_cmd("petpet")
    @reuse.cmd_describe("petpet", ["user1", "user2", "user3", "user4"])
    @reuse.guild_and_app
    async def slash_petpet(self, interaction: discord.Interaction,
        user1: discord.User,
        user2: discord.User | None,
        user3: discord.User | None,
        user4: discord.User | None
    ):
        targets: list[reuse.USER | str] = [u for u in (user1,user2,user3,user4) if u is not None]
        if not targets: return await interaction.response.send_message(Locale.get("error.no_members_arg"), ephemeral=True)
        to_ping, files = await self.petpet(None, interaction.user.id, targets, interaction.guild)
        if not to_ping or not files: return await interaction.response.send_message(Locale.get("error.no_members_arg"), ephemeral=True)
        await interaction.response.send_message(Locale.get("petpet.result", petter = interaction.user.mention, petted = Locale.get("petpet.entry.join").join(to_ping)), files=files, allowed_mentions=reuse.NO_MENTION)


    @reuse.hybrid_cmd("setpetreply")
    @reuse.cmd_describe("setpetreply", ["message"])
    @reuse.guild_only
    async def setpetreply(self, ctx: commands.Context, *, message: str = ""):
        message = await self.set_pet_reply(ctx.guild.id, ctx.author.id, message)
        await ctx.reply(Locale.get("setpetreply."+("result" if message else "reset"), message = message), ephemeral=True)


    @reuse.hybrid_cmd("forcepetreply")
    @reuse.cmd_describe("forcepetreply", ["member", "message"])
    @reuse.guild_only
    @reuse.check_permissions(administrator = True)
    async def forcepetreply(self, ctx: commands.Context, member: discord.Member, *, message: str = ""):
        Assert.is_not_bot(member)
        message = await self.set_pet_reply(ctx.guild.id, member.id, message)
        await ctx.reply(Locale.get("forcepetreply."+("result" if message else "reset"), member = member, message = message), allowed_mentions=reuse.NO_MENTION, ephemeral=True)

    @slash_petpet.error
    async def slash_petpet_error(self, interaction: discord.Interaction, error):
        if interaction.response.is_done(): await interaction.edit_original_response(content = Locale.get("overall.fail", error = error))
        else: await interaction.response.send_message(Locale.get("overall.fail", error = error), ephemeral = True)

async def setup(bot: MeowBot):
    cog = Pets(bot)
    await cog.update_caches()
    await bot.add_cog(cog)
