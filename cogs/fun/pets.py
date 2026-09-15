import asyncio
import os
import random
from io import BytesIO

import aiohttp
import discord
from discord.ext import commands
from PIL import Image, ImageSequence

from main import MeowBot

FRAMES = 10


class Pets(commands.Cog):
    PET_REPLYS: list[str] = [
        "meow",
        "mmnrp",
        "purr",
        "*\\*blows up\\**",
        "awawawawa",
        "*\\*bites your hand\\**",
        "mroow",
        ">w<",
        "mrrrp",
        "mraow",
        "meawwww",
    ]

    def __init__(self, bot: MeowBot):
        self.bot: MeowBot = bot

    @commands.command()
    async def pet(self, ctx):
        await ctx.reply(random.choice(self.PET_REPLYS))

    @commands.command()
    async def petpet(self, ctx: commands.Context, members: commands.Greedy[discord.Member]):
        if not members: return await ctx.send("Please mention at least one member.")

        capped_members = members[:4]

        message = f"{ctx.author.mention} has pet {", ".join([member.mention for member in capped_members])}"
        
        gifs = await asyncio.gather(*[self.process_member(ctx, member) for member in capped_members])

        files: list[discord.File] = [
            discord.File(gif, filename=f"{member.name}-petpet.gif")
            for member, gif in zip(capped_members, gifs)
        ]

        await ctx.reply(
            content=message,
            files=files,
            allowed_mentions=discord.AllowedMentions(users=False,roles=False)
        )

    async def process_member(self, ctx, member: discord.Member):
        avatar_url = member.display_avatar.url
        async with aiohttp.ClientSession() as session, session.get(avatar_url) as resp:
            if resp.status != 200: return await ctx.send("Failed to download image.")
            image_data = await resp.read()

        source = BytesIO(image_data)
        dest = BytesIO()

        petpet = Image.open(os.path.join(".", "resources", "petpet.gif"))

        images = []

        frames = [frame.copy().convert("RGBA") for frame in ImageSequence.Iterator(petpet)]

        frames = [frame.resize((128, 128)) for frame in frames]

        for i, frame in enumerate(frames):
            frame = Image.new("RGBA", (128, 128), (0, 0, 0, 0))

            squish = i if i < FRAMES / 2 else FRAMES - i
            width = int(128 * (0.8 + squish * 0.02))
            height = int(128 * (0.8 - squish * 0.05))

            offset_x = int((128 - width) * 0.5 + 0.03 * 128)
            offset_y = int(128 - height - 0.08 * 128)

            downscaled_avatar = (
                Image.open(source)
                .convert("RGBA")
                .resize((width, height), Image.Resampling.LANCZOS)
            )

            frame.paste(downscaled_avatar, (offset_x, offset_y), downscaled_avatar)

            petpet.seek(i)
            petpet_frame = petpet.convert("RGBA").resize((128, 128), Image.Resampling.LANCZOS)
            frame.paste(petpet_frame, (0, 0), petpet_frame)

            images.append(frame)

        images[0].save(
            dest,
            format="GIF",
            save_all=True,
            append_images=images[1:],
            duration=20,
            loop=0,
            disposal=2,
            optimize=False,
        )
        dest.seek(0)

        return dest

    @petpet.error
    async def peptet_error(self, ctx, error):
        await ctx.reply(error)


async def setup(bot: MeowBot):
    await bot.add_cog(Pets(bot))
