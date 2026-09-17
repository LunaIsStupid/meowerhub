import random
from io import BytesIO

import discord
from discord import app_commands
from discord.ext import commands
from petpetgif import petpet

from main import MeowBot

from . import _settings as settings


class Pets(commands.Cog):
    PET_REPLIES: list[str] = [
        "*\\*blows up\\**",
        "*\\*bites your hand\\**",
        "*\\*blep\\**",
        "*\\*paws at you\\**",
        ">w<",
        "^w^"
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

    REPLY_OVERRIDES = { # TODO: maybe move to db for runtime editing but ehhh idk it would have to check the thing like at max 4 times a !petpet, will think about it later
        416062410022191104: ["he is purring"], # zephyr
    }

    MAX_PETPET_COUNT = 4

    def __init__(self, bot: MeowBot):
        self.bot: MeowBot = bot

    @commands.command()
    async def pet(self, ctx):
        await ctx.reply(random.choice(self.PET_REPLIES))

    async def petpet_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        search = (current or "").lower().lstrip('@')
        choices = []
        if not current and current.lower() in interaction.user.display_name.lower() and interaction.channel and isinstance(interaction.channel, discord.abc.PrivateChannel): choices.append(app_commands.Choice(name=f"@{interaction.user.display_name}", value=interaction.user.mention))
        if interaction.channel and isinstance(interaction.channel, discord.abc.PrivateChannel): choices.extend([app_commands.Choice(name=f"@{member.display_name}", value=member.mention) for member in interaction.channel.recipients if member and member.display_name and (not search or search in member.display_name.lower())])
        elif interaction.guild: choices.extend([app_commands.Choice(name=f"@{member.display_name}", value=member.mention) for member in interaction.guild.members if member.display_name and (not search or search in member.display_name.lower())])
        return choices[:25]

    @commands.hybrid_command(name="petpet", description="Pet people!")
    @app_commands.describe(user1="Someone to pet!", user2="Someone to pet!", user3="I'm sure you get the idea", user4="Someone to pet!")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.autocomplete(user1=petpet_autocomplete, user2=petpet_autocomplete, user3=petpet_autocomplete, user4=petpet_autocomplete)
    async def petpet(self, ctx: commands.Context,
        user1: str | None = None,
        user2: str | None = None,
        user3: str | None = None,
        user4: str | None = None,
    ):
        targets: list[discord.User | str] = [u for u in (user1, user2, user3, user4) if u is not None]
        to_ping: list[str] = []
        files: list[discord.File] = []
        if not targets: return await ctx.send("Please mention at least one member.", ephemeral=True)

        await ctx.defer()
        for member in targets:
            if isinstance(member, str) and member not in settings.EVERYONE_PETPET: member = await self.bot.extract_user(ctx, member)
            if isinstance(member, discord.User | discord.Member | discord.ClientUser):
                to_ping.append(await self.process_message(ctx, member))
                files.append(discord.File(await self.process_member(member), filename=f"{member.name}-petpet.gif"))
            elif isinstance(member, str) and member in settings.EVERYONE_PETPET and ctx.guild:
                dest = await self.process_guild(ctx.guild)
                if not dest: continue
                to_ping.append(await self.process_message(ctx, ctx.guild))
                files.append(discord.File(dest, filename=f"{ctx.guild.name}-petpet.gif"))
            if len(to_ping) >= self.MAX_PETPET_COUNT: break
        if not to_ping: return await ctx.send("Please mention at least one member.", ephemeral=True)
        if len(to_ping) > 2: to_ping[-1] = "and " + to_ping[-1]

        message = f"{ctx.author.mention} has pet {", ".join(to_ping)}"
        await ctx.reply(
            content=message,
            files=files,
            allowed_mentions=discord.AllowedMentions(users=False,roles=False)
        )

    async def process_message(self, ctx: commands.Context, member: discord.User | discord.Member | discord.ClientUser | discord.Guild):
        mention = "error"
        if isinstance(member, discord.User | discord.Member | discord.ClientUser):
            mention = member.mention
            if member.id == self.bot.user.id: mention += f" ({random.choice(self.PET_REPLIES)})"
            elif member.id == ctx.message.author.id: mention += f" (you silly)"
            elif member.id in self.REPLY_OVERRIDES: mention += f" ({random.choice(self.REPLY_OVERRIDES[member.id])})"
        elif isinstance(member, discord.Guild) and ctx.guild:
            mention = f"the whole {ctx.guild.name}"
        return mention



    async def process_bytes(self, bytes: bytes):
        source = BytesIO(bytes)
        dest = BytesIO()
        petpet.make(source, dest)
        dest.seek(0)
        return dest

    async def process_member(self, member: discord.User | discord.Member | discord.ClientUser):
        return await self.process_bytes(await member.display_avatar.read())

    async def process_guild(self, guild: discord.Guild):
        if not guild or not guild.icon: return
        return await self.process_bytes(await guild.icon.read())


    @petpet.error
    async def peptet_error(self, ctx, error):
        await ctx.reply(error)


async def setup(bot: MeowBot):
    await bot.add_cog(Pets(bot))
