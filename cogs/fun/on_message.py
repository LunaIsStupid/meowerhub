import os
import random

import discord
from discord.ext import commands

from main import MeowBot

from . import _settings as settings

import sys
sys.path.append("...")
from utils import reuse
from utils.locales import Locale

class OnMessage(commands.Cog):
    DICE_MAX_MULT = 8193
    DICE_MAX_DICE = 8193
    MENTION_REPLY = os.getenv("MENTION_REPLY") or "haii"

    def __init__(self, bot: MeowBot):
        self.bot: MeowBot = bot

    def parse_dice(self, string, prefix):
        mult, chips = string[len(prefix):].replace(" ", "").lower().split("d")  # haha balatro im so funny
        chips, *adv = chips.replace("-", "+-").split("+")
        return int(mult) if mult else 1, int(chips), sum(int(p) for p in adv)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot: return

        # on mentioned
        if self.bot.user in message.mentions and "hi" in message.content.lower().split():
            return await message.reply(self.MENTION_REPLY)

        # dice
        mult, dice, adv = self.parse_dice(message.content, self.bot.command_prefix)
        if mult and 0 < mult < self.DICE_MAX_MULT and dice and 0 < dice < self.DICE_MAX_DICE:
            a = 0
            for i in range(mult):
                a+=min(dice, max(1, random.randint(1, dice)+adv))
            return await message.reply(str(a))

async def setup(bot: MeowBot):
    await bot.add_cog(OnMessage(bot))
