#!/usr/bin/env ./.venv/bin/python
import difflib
import pathlib

import discord
from discord.ext import commands


class CogManager(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cog_dir = pathlib.Path("cogs")

    async def cog_load(self):
        print("[Manager] Loaded, attempting to load other cogs.")
        await self._auto_load()

    async def _auto_load(self):
        await self.bot.load_extension("cogs._database")
        for file in sorted(self.cog_dir.rglob("*.py")):
            if file.stem.startswith("_") or file.stem == "manager":
                continue
            ext = str(file.with_suffix("")).replace("\\", ".").replace("/", ".")
            try:
                await self.bot.load_extension(ext)
                print(f"[manager] Loaded cog: {file.stem}")
            except discord.DiscordException as e:
                print(f"[manager] Failed to load {file.stem}: {e}")

    def _find_closest_cog(
        self, query: str, include_disabled: bool = False
    ) -> str | None:
        """Finds exact match or closest fuzzy match for a cog name."""
        query_clean = query.strip().lower()
        candidates = {}
        for file in self.cog_dir.rglob("*.py"):
            rel_path = file.relative_to(self.cog_dir.parent)
            parts = list(rel_path.with_suffix("").parts)
            filename = parts[-1]

            if filename == "manager":
                continue

            is_disabled = filename.startswith("_")
            if is_disabled:
                if not include_disabled:
                    continue
                parts[-1] = filename[1:]

            ext_path = ".".join(parts)
            rel_dot_path = ".".join(parts[1:])
            short_name = parts[-1]
            candidates[ext_path.lower()] = ext_path
            candidates[rel_dot_path.lower()] = ext_path
            candidates[short_name.lower()] = ext_path

        if query_clean in candidates:
            return candidates[query_clean]

        matches = difflib.get_close_matches(
            query_clean, candidates.keys(), n=1, cutoff=0.6
        )
        return candidates[matches[0]] if matches else None

    @commands.group()
    @commands.has_permissions(manage_guild=True)
    async def cog(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.message.reply("wrong")

    @cog.group()
    @commands.has_permissions(manage_guild=True)
    async def load(self, ctx, *, cog_name: str):
        matched = self._find_closest_cog(cog_name)
        if not matched:
            await ctx.send(f"Could not find a cog matching `{cog_name}`.")
            return

        ext = matched
        try:
            await self.bot.load_extension(ext)
            await ctx.send(f"Loaded `{matched}`")
        except discord.DiscordException as e:
            await ctx.send(f"Failed to load `{matched}`: {e}")

    @cog.group()
    @commands.has_permissions(manage_guild=True)
    async def unload(self, ctx, *, cog_name: str):
        matched = self._find_closest_cog(cog_name)
        if not matched:
            await ctx.send(f"Could not find a cog matching `{cog_name}`.")
            return

        ext = matched
        try:
            await self.bot.unload_extension(ext)
            await ctx.send(f"Unloaded `{matched}`")
        except discord.DiscordException as e:
            await ctx.send(f"Failed to unload `{matched}`: {e}")

    @cog.group()
    @commands.has_permissions(manage_guild=True)
    async def reload(self, ctx, *, cog_name: str):
        matched = self._find_closest_cog(cog_name)
        if not matched:
            await ctx.send(f"Could not find a cog matching `{cog_name}`.")
            return

        ext = matched
        try:
            await self.bot.unload_extension(ext)
        except discord.DiscordException as e:
            await ctx.send(f"Failed to unload `{matched}`: {e}")
        try:
            await self.bot.load_extension(ext)
            await ctx.send(f"Reloaded `{matched}`")
        except discord.DiscordException as e:
            await ctx.send(f"Failed to load `{matched}`: {e}")

    @cog.group()
    @commands.has_permissions(manage_guild=True)
    async def disable(self, ctx, *, cog_name: str):
        matched = self._find_closest_cog(cog_name, include_disabled=True)
        if not matched:
            await ctx.send(f"Could not find a cog matching `{cog_name}`.")
            return

        ext = matched
        if ext == "cogs.manager":
            await ctx.send("Cannot disable the manager cog")
            return
        ext = f"cogs.{cog_name}"
        try:
            await self.bot.unload_extension(ext)
        except discord.DiscordException:
            pass
        src = self.cog_dir / f"{cog_name}.py"
        dst = self.cog_dir / f"_{cog_name}.py"
        if not src.exists():
            await ctx.send(f"Cog `{cog_name}` not found")
            return
        src.rename(dst)
        await ctx.send(f"Disabled `{matched}`")

    @cog.group()
    @commands.has_permissions(manage_guild=True)
    async def enable(self, ctx, *, cog_name: str):
        matched = self._find_closest_cog(cog_name, include_disabled=True)
        if not matched:
            await ctx.send(f"Could not find a disabled cog matching `{cog_name}`.")
            return

        src = self.cog_dir / f"_{matched}.py"
        dst = self.cog_dir / f"{matched}.py"
        if not src.exists():
            await ctx.send(f"Disabled cog `{matched}` not found")
            return
        src.rename(dst)
        ext = f"cogs.{matched}"
        try:
            await self.bot.load_extension(ext)
            await ctx.send(f"Enabled `{matched}`")
        except discord.DiscordException as e:
            await ctx.send(f"Failed to enable `{matched}`: {e}")

    @commands.command()
    @commands.has_permissions(manage_guild=True)
    async def sync(self, ctx: commands.Context):
        """Sync slash commands to Discord."""
        async with ctx.typing():
            await self.bot.tree.sync()
        await ctx.send("Slash commands synced!")


async def setup(bot: commands.Bot):
    await bot.add_cog(CogManager(bot))
