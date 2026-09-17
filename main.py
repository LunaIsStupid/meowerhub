#!/usr/bin/env ./.venv/bin/python

import argparse
import asyncio
import inspect
import logging
import os
import pathlib

import aiosqlite
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

from help import MeowHelp

from locales import Locale

load_dotenv()


class MeowBot(commands.Bot):
    _watcher: asyncio.Task
    db: aiosqlite.Connection

    def __init__(self, ext_dir: str, intents, **options) -> None:
        super().__init__(intents=intents, **options)
        self.ext_dir = pathlib.Path(ext_dir)

    async def _load_extensions(self):
        print("[meowerhub] Loading extensions...")
        try:
            await self.load_extension("cogs.manager")
            print("[meowerhub] Loaded manager cog")
        except commands.ExtensionError as e:
            print(f"[meowerhub] Failed to load manager: {e}")

    async def setup_hook(self):
        await self._load_extensions()
        await self.tree.sync()
        Locale.loadLocales()

    async def close(self):
        for cog_name, cog in self.cogs.items():
            if hasattr(cog, "cog_unload"):
                print(f"[Shutdown] Unloading and cleaning up cog: {cog_name}")
                if inspect.iscoroutinefunction(cog.cog_unload):
                    await cog.cog_unload()
        await self.db.close()
        await super().close()

    async def extract_user(self, ctx: commands.Context, string: str) -> discord.User | discord.Member | str:
        if ctx.guild:
            try:
                await self.fetch_guild(ctx.guild.id) # This will throw a 404 quickly
                return await commands.MemberConverter().convert(ctx, string) # This will take too long and expire app commands
            except commands.MemberNotFound, discord.NotFound: pass
        try: return await commands.UserConverter().convert(ctx, string)
        except commands.UserNotFound: pass
        return string

    async def user_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        search = (current or "").lower().lstrip('@')
        choices = []
        if not current and current.lower() in interaction.user.display_name.lower() and interaction.channel and isinstance(interaction.channel, discord.abc.PrivateChannel):
            choices.append(app_commands.Choice(name=f"@{interaction.user.display_name}", value=interaction.user.mention))
            choices.append(app_commands.Choice(name=f"@{interaction.client.user.display_name}", value=interaction.user.mention))
        if interaction.channel and isinstance(interaction.channel, discord.abc.PrivateChannel):
            choices.extend([
                app_commands.Choice(name=f"@{member.display_name}", value=member.mention)
                for member in interaction.channel.recipients
                if member and member.display_name and (not search or search in member.display_name.lower())
            ])
        elif interaction.guild:
            choices.extend([
                app_commands.Choice(name=f"@{member.display_name}", value=member.mention)
                for member in interaction.guild.members
                if member.display_name and (not search or search in member.display_name.lower())
            ])
        return choices[:25]


def main():
    parser = argparse.ArgumentParser(
        description="Run project instance with dev or prod tokens."
    )
    parser.add_argument(
        "--prod",
        action="store_true",
        help="Run the instance using the production token instead of dev.",
    )

    args = parser.parse_args()

    intents = discord.Intents.all()

    client = MeowBot(
        ext_dir="cogs", intents=intents, command_prefix="!", help_command=MeowHelp(), allowed_mentions=discord.AllowedMentions(roles=False, users=False, everyone=False)
    )
    handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")
    token: str | None

    if args.prod:
        print("starting using main token")
        token = os.getenv("DISCORD_TOK_PROD")
    else:
        token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("\n[meowerhub] Token not found please configure your .env properly.")
        return
    client.run(token, log_handler=handler)


if __name__ == "__main__":
    main()
