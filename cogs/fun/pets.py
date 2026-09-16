import random
from io import BytesIO

import discord
from discord.ext import commands
from petpetgif import petpet

from main import MeowBot

from . import _settings as settings


class Pets(commands.Cog):
    PET_REPLYS: list[str] = [
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

    MAX_PETPET_COUNT = 4

    def __init__(self, bot: MeowBot):
        self.bot: MeowBot = bot

    @commands.command()
    async def pet(self, ctx):
        await ctx.reply(random.choice(self.PET_REPLYS))

    @commands.hybrid_command(name="petpet", description="Pet people!")
    @discord.app_commands.describe(users="List of users to pet.")
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def petpet(self, ctx: commands.Context, *, users: str):
        if not users: return await ctx.send("Please mention at least one member.", ephemeral=True)
        to_ping: list[str] = []
        files: list[discord.File] = []

        await ctx.defer() # May time out, defer here so we can send error message later.
        for member in users.split():
            member = await self.bot.extract_user(ctx, member)
            if isinstance(member, discord.User | discord.Member):
                mention = member.mention
                if member.id == self.bot.user.id: mention += f" ({random.choice(self.PET_REPLYS)})"
                elif member.id == ctx.message.author.id: mention += f" (you silly)"
                to_ping.append(mention)
                files.append(discord.File(await self.process_member(member), filename=f"{member.name}-petpet.gif"))
            elif member in settings.EVERYONE_PETPET and ctx.guild:
                dest = await self.process_guild(ctx.guild)
                if not dest: continue
                to_ping.append(f"the whole {ctx.guild.name}")
                files.append(discord.File(dest, filename=f"{ctx.guild.name}-petpet.gif"))
            if len(to_ping) >= self.MAX_PETPET_COUNT: break
        if not to_ping: return await ctx.send("Please mention at least one member.", ephemeral=True)
        message = f"{ctx.author.mention} has pet {", ".join(to_ping)}"
        await ctx.reply(
            content=message,
            files=files,
            allowed_mentions=discord.AllowedMentions(users=False,roles=False)
        )

    async def process_bytes(self, bytes: bytes):
        source = BytesIO(bytes)
        dest = BytesIO()
        petpet.make(source, dest)
        dest.seek(0)
        return dest

    async def process_member(self, member: discord.User | discord.Member):
        return await self.process_bytes(await member.display_avatar.read())

    async def process_guild(self, guild: discord.Guild):
        if not guild or not guild.icon: return
        return await self.process_bytes(await guild.icon.read())


    @petpet.error
    async def peptet_error(self, ctx, error):
        await ctx.reply(error)


async def setup(bot: MeowBot):
    await bot.add_cog(Pets(bot))
