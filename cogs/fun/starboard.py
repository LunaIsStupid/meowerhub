# First custom cog for this bot...
import aiosqlite
import discord
from discord.ext import commands
from discord.state import RawReactionActionEvent

from main import MeowBot

from . import _settings as settings


class Starboard(commands.Cog):
    EMOJI = "⭐"
    REQUIRED = 3
    ALLOW_SELF_REACTION = False

    CHECK_QUERY = """
        SELECT guild_id, starboard_message_id FROM starboard WHERE message_id = ?
        """
    CREATE_QUERY = """
        INSERT INTO starboard (message_id, guild_id, starboard_message_id)
        VALUES (?, ?, ?)
    """
    DELETE_QUERY = """
        DELETE FROM starboard WHERE message_id = ?
    """
    CHECK_SB_CHANNEL_QUERY = """
        SELECT sb_channel FROM guilds WHERE guild_id = ?
    """

    def __init__(self, bot: MeowBot):
        self.bot: MeowBot = bot

    async def get_stars(self, message: discord.Message) -> int:
        reaction_count: int = 0
        for reaction in message.reactions:
            users = [user async for user in reaction.users()]
            if reaction.emoji == self.EMOJI:
                reaction_count = reaction.count
                if not self.ALLOW_SELF_REACTION and message.author in users: reaction_count -= 1
                break

        return reaction_count

    async def generate_starboard_message(self, message: discord.Message, star_count: int) -> str | None: # message in case we need it later on
        return f"{self.EMOJI}{star_count}"

    async def generate_starboard_attachments(self, message: discord.Message, star_count: int) -> tuple[list[discord.File], list[discord.Embed]] | None: # star_count in case we need it later on
        if not message.guild: return # not in guild

        try:
            member: discord.Member = await message.guild.fetch_member(message.author.id)
            color = member.color
        except:
            color = None

        embed: discord.Embed = discord.Embed(
            description=f"{message.content}\n[Jump!]({message.jump_url})",
            url=message.jump_url,
            color=color if color and color != discord.Colour(0) else settings.DEFAULT_COLOR,
            timestamp=message.created_at,
        )

        embed.set_author(
            name=message.author.display_name,
            icon_url=message.author.display_avatar,
        )

        embed.set_footer(text=f"{message.id} | meower's hub bot")

        attachment_count = 0
        files: list[discord.File] = []
        urls = ""
        if message.attachments:
            for attachment in message.attachments:
                if (
                    attachment.filename.endswith(".png")
                    or attachment.filename.endswith(".jpg")
                    or attachment.filename.endswith(".jpeg")
                    and attachment_count != 1
                ):
                    attachment_count += 1
                    urls = attachment.url
                else:
                    try:
                        file: discord.File = await attachment.to_file(use_cached=False)
                        files.append(file)
                    except (
                        discord.HTTPException,
                        discord.NotFound,
                        discord.Forbidden,
                    ):
                        print(f"Failed to grab an attachment... {attachment.filename}")

        embed.set_image(url=urls)
        message.embeds.append(embed)

        return files, message.embeds

    async def get_starboard_channel(self, guild: discord.Guild):
        async with self.bot.db.execute(self.CHECK_SB_CHANNEL_QUERY, (guild.id,),) as cursor:
            row = await cursor.fetchone()
            if not row: return # no starboard channel row for current server
            return await guild.fetch_channel(row["sb_channel"])

    async def get_starboard_message_row(self, message_id: int) -> aiosqlite.Row | None:
        async with self.bot.db.execute(self.CHECK_QUERY, (message_id,)) as cursor:
            return await cursor.fetchone()

    async def get_starboard_message(self, channel, row: aiosqlite.Row):
        guild_id, sb_message_id = row
        if not guild_id or not sb_message_id: return # invalid message row data
        return await channel.fetch_message(sb_message_id)

    async def process_starred(self, message: discord.Message):
        if not message.guild: return
        if message.author.id == self.bot.user.id: return # is current bot's message

        starboard_channel = await self.get_starboard_channel(message.guild)
        if not starboard_channel: return # starboard channel is invalid
        if not isinstance(starboard_channel, discord.abc.Messageable): return # cant send messages in starboard
        if message.channel.id == starboard_channel.id: return # no starring in starboard

        stars = await self.get_stars(message)

        starboard_message_row = await self.get_starboard_message_row(message.id)
        if not starboard_message_row and stars >= self.REQUIRED:
            attachments = await self.generate_starboard_attachments(message, stars)
            content = await self.generate_starboard_message(message, stars)
            if not attachments or not content: return # invalid content or attachments

            try: sent_message = await starboard_channel.send(content=content, files=attachments[0], embeds=attachments[1])
            except discord.Forbidden: return
            except discord.HTTPException: return
            if not sent_message: return # didnt sent message for some reason

            await self.bot.db.execute(self.CREATE_QUERY, (message.id, message.guild.id, sent_message.id))
            await self.bot.db.commit()
        elif starboard_message_row and stars <= 0:
            starboard_message = await self.get_starboard_message(starboard_channel, starboard_message_row)
            if not starboard_message: return # no starboard message to remove

            await starboard_message.delete()

            await self.bot.db.execute(self.DELETE_QUERY, (message.id,))
            await self.bot.db.commit()
        elif starboard_message_row:
            starboard_message = await self.get_starboard_message(starboard_channel, starboard_message_row)
            if not starboard_message: return # no starboard message to edit

            content = await self.generate_starboard_message(message, stars)
            if not content: return # invalid content

            await starboard_message.edit(content=content)

    async def on_reactions_changed(self, payload):
        message_id = payload.message_id
        channel_id = payload.channel_id
        guild_id = payload.guild_id

        if not guild_id: return

        guild = await self.bot.fetch_guild(guild_id)
        channel = await guild.fetch_channel(channel_id)
        message = None
        if isinstance(channel, discord.abc.Messageable):
            message = await channel.fetch_message(message_id)

        if not message: return

        await self.process_starred(message)


    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: RawReactionActionEvent):
        await self.on_reactions_changed(payload)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: RawReactionActionEvent):
        await self.on_reactions_changed(payload)

    @commands.Cog.listener()
    async def on_raw_reaction_clear(self, payload: RawReactionActionEvent):
        await self.on_reactions_changed(payload)

    @commands.Cog.listener()
    async def on_raw_reaction_clear_emoji(self, payload: RawReactionActionEvent):
        await self.on_reactions_changed(payload)


async def setup(bot: MeowBot):
    await bot.add_cog(Starboard(bot))
