# for reused things that wont be changed like settings

from enum import Enum, auto  # in case we need them later

import discord
from discord.ext import commands

from utils.locales import Locale

# Source - https://stackoverflow.com/a/5409569
# Posted by Jochen Ritzel, modified by community. See post 'Timeline' for change history
# Retrieved 2026-09-17, License - CC BY-SA 2.5

def composed(*decs):
    def deco(f):
        for dec in reversed(decs):
            f = dec(f)
        return f
    return deco

def check_permissions(**kwargs):
    return composed(
        commands.has_permissions(**kwargs),
        discord.app_commands.default_permissions(**kwargs),
        discord.app_commands.checks.has_permissions(**kwargs)
    )

def hybrid_cmd(key: str):
    return commands.hybrid_command(name = key, description = Locale.getFormatted(f"{key}.desc"))

def app_cmd(key: str):
    return discord.app_commands.command(name = key, description = Locale.getFormatted(f"{key}.desc"))

def cmd(key: str):
    return commands.command(name = key, description = Locale.getFormatted(f"{key}.desc"))

def cmd_describe(key: str, args: list[str]):
    kwargs = {}
    for arg in args:
        kwargs[arg] = Locale.getFormatted(f"{key}.{arg}")
    return discord.app_commands.describe(**kwargs)

class IDS: # readability, add when needed
    ZEPHYR = 416062410022191104

USER = discord.User | discord.Member | discord.ClientUser
GUILD = discord.Guild
TEXT_CHANNEL = discord.TextChannel | discord.StageChannel | discord.VoiceChannel | discord.Thread

NO_MENTION = discord.AllowedMentions(users=False,roles=False)

guild_only = composed(
    discord.app_commands.allowed_installs(guilds=True, users=False),
    discord.app_commands.allowed_contexts(guilds=True, dms=False, private_channels=True),
    discord.app_commands.guild_only(),
    commands.guild_only()
)
app_only = composed(
    discord.app_commands.allowed_installs(guilds=False, users=True),
    discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
)
guild_and_app = composed(
    discord.app_commands.allowed_installs(guilds=True, users=True),
    discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
)
