import discord
from discord.ext import commands

class AssertExc(Exception):
    def __init__(self, key, autosend = True, **kwargs) -> None:
        super().__init__()
        self.key = key
        self.kwargs = kwargs
        self.autosend = autosend

class Assert:
    @classmethod
    def a(cls, condition: bool, key: str, autosend: bool = True, **kwargs):
        if not condition: raise AssertExc(key, autosend, **kwargs)

    @classmethod
    def is_not_author(cls, ctx: commands.Context, member: discord.Member | discord.User, autosend = True):
        cls.a(member != ctx.author, "error.author_user", autosend)

    @classmethod
    def is_not_bot(cls, member: discord.Member | discord.User, autosend = True):
        cls.a(not member.bot, "error.author_user", autosend)

    @classmethod
    def has_permissions(cls, ctx: commands.Context, member: discord.Member | None = None, autosend = True, **kwargs):
        if discord.Permissions(**kwargs) > ctx.channel.permissions_for(member or ctx.guild.me): raise AssertExc("error.no_user_perms" if member else "error.no_bot_perms", autosend = autosend, perm = ", ".join(list(kwargs.keys())))    
    
    @classmethod
    def can_moderate(cls, moderator: discord.Member, target: discord.Member, autosend = True):
        "Checks if target is not guild owner, target is lesser role than moderator, and target is lesser role than bot"
        cls.a(target != target.guild.owner, "error.owner_user", autosend)
        cls.a(moderator == target.guild.owner or moderator.top_role > target.top_role, "error.user_role_lower", autosend)
        cls.a(target.guild.me.top_role > target.top_role, "error.bot_role_lower", autosend)