import ctypes
import os
import random
import sys
from pathlib import Path

import discord
from discord.ext import commands

from main import MeowBot

from . import _settings as settings

sys.path.append("...")
from utils import reuse
from utils.locales import Locale

class OnMessage(commands.Cog):
    DICE_MAX_MULT = 18446744073709551600
    DICE_MAX_DICE = 18446744073709551600
    MENTION_REPLY = os.getenv("MENTION_REPLY") or "haii"

    def __init__(self, bot: MeowBot):
        self.bot: MeowBot = bot
        self.dicelib = ctypes.CDLL(Path() / "utils" / "native" / "libdice.so")
        self.dicelib.dice.argtypes =  [ctypes.c_uint64, ctypes.c_uint64, ctypes.c_uint64, ctypes.POINTER(ctypes.c_uint64), ctypes.POINTER(ctypes.c_uint64)]
        self.dicelib.dice.restype = None

    def parse_dice(self, string, prefix):
        mult, chips = string[len(prefix):].split("d") # haha balatro im so funny
        return int(mult) if mult else 1, int(chips)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot: return

        # on mentioned
        if self.bot.user in message.mentions and "hi" in message.content.lower().split():
            return await message.reply(self.MENTION_REPLY)

        # dice
        mult, dice = self.parse_dice(message.content, self.bot.command_prefix)
        if mult and 0 < mult <= self.DICE_MAX_MULT and dice and 0 < dice <= self.DICE_MAX_DICE:
            result = await self.roll(mult,dice)
            return await message.reply(str(result))


    async def roll(self, n: int, d: int) -> int:
        if not (0 <= n < 0xFFFFFFFFFFFFFFFF and 0 <= d < 0xFFFFFFFFFFFFFFFF):
            raise ValueError("Inputs exceed uint64 bounds")
        seed = random.getrandbits(64)
        out_l = ctypes.c_uint64()
        out_u = ctypes.c_uint64()
        self.dicelib.dice(seed, n, d, ctypes.byref(out_l), ctypes.byref(out_u), )
        return (out_u.value << 64) | out_l.value


async def setup(bot: MeowBot):
    await bot.add_cog(OnMessage(bot))
