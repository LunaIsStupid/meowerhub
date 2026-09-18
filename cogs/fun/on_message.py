import bisect
import random

import discord
from discord.ext import commands

from main import MeowBot

from . import _settings as settings

import sys
sys.path.append("...")
import reuse
from locales import Locale

class OnMessage(commands.Cog):
    DICE_MAX_MULT = 8193
    DICE_MAX_DICE = 8193
    MENTION_REPLY = "<a:wavey:1550519578344554616>"

    def __init__(self, bot: MeowBot):
        self.bot: MeowBot = bot

    def parse_dice(self, string, prefix):
        mult, chips = string[len(prefix):].split("d") # haha balatro im so funny
        return int(mult) if mult else 1, int(chips)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot: return

        # on mentioned
        if self.bot.user in message.mentions and message.content.startswith("hi"):
            return await message.reply(self.MENTION_REPLY)

        # dice
        mult, dice = self.parse_dice(message.content, self.bot.command_prefix)
        if mult and 0 < mult < self.DICE_MAX_MULT and dice and 0 < dice < self.DICE_MAX_DICE:
            a = 0
            for i in range(mult):
                a+=random.randint(1, dice)
            return await message.reply(str(a))

async def setup(bot: MeowBot):
    await bot.add_cog(OnMessage(bot))
