from typing import cast

import discord
from discord.ext import commands

from main import MeowBot


class GlobalEvents(commands.Cog):
    def __init__(self, bot):
        self.bot: MeowBot = cast(MeowBot, bot)

    async def add_member(self, member: discord.Member):
        await self.bot.db.users.add(member.id, autocommit=False)

    async def add_guild(self, guild: discord.Guild):
        await self.bot.db.guilds.add(guild.id, autocommit=False)

        for member in guild.members:
            if not member.bot: await self.add_member(member)

    @commands.Cog.listener()
    async def on_ready(self):
        print("Updating database guilds..")
        for guild in self.bot.guilds:
            await self.add_guild(guild)
        await self.bot.db.commit()
        print("Database guilds updated!")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot: return
        await self.add_member(member)
        await self.bot.db.commit()

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        await self.add_guild(guild)
        await self.bot.db.commit()


async def setup(bot):
    await bot.add_cog(GlobalEvents(bot))
