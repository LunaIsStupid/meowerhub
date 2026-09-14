# First custom cog for this bot...
import aiosqlite
import discord
from discord.ext import commands
from discord.state import RawReactionActionEvent

from main import MeowBot


class Starboard(commands.Cog):
    def __init__(self, bot: MeowBot):
        self.bot: MeowBot = bot

    async def _star(self, message: discord.Message):
        if not message.guild:
            return  # not in a guild
        reaction_count: int = 0
        reaction_emoji: str | None = None
        for reaction in message.reactions:
            users = [user async for user in reaction.users()]
            if reaction.emoji == "⭐":
                reaction_count = reaction.count
                reaction_emoji = "⭐"

            if message.author in users:
                reaction_count -= 1

        sb_message: discord.Message | None = None

        if reaction_count >= 3 and reaction_emoji:
            check_query = """
            SELECT guild_id, starboard_message_id FROM starboard WHERE message_id = ?
            """
            sb_message_row: aiosqlite.Row | None = None
            async with self.bot.db.execute(check_query, (message.id,)) as cursor:
                sb_message_row = await cursor.fetchone()

            if not sb_message_row:
                async with self.bot.db.execute(
                    "SELECT sb_channel FROM guilds WHERE guild_id = ?",
                    (message.guild.id,),
                ) as cursor:
                    sb_channel = await cursor.fetchone()

                if not sb_channel:
                    return  # cant send the starboard anywhere

                sb_channel_id = sb_channel["sb_channel"]

                channel = await message.guild.fetch_channel(sb_channel_id)

                if not channel:
                    return  # channel doesnt exist

                embed: discord.Embed = discord.Embed(
                    description=f"{message.content}\n[Jump!]({message.jump_url})",
                    url=message.jump_url,
                    color=discord.Color.pink(),
                    timestamp=message.created_at,
                )

                embed.set_author(
                    name=message.author.display_name,
                    icon_url=message.author.display_avatar,
                )

                embed.set_footer(text=f"{message.id} | meower's hub bot")

                attachment_count = 0
                files: list[discord.File] = []
                urls: str = ""
                if message.attachments:
                    for attachment in message.attachments:
                        if (
                            attachment.filename.endswith(".png")
                            or attachment.filename.endswith(".jpg")
                            and attachment_count != 1
                        ):
                            attachment_count += 1
                            urls = attachment.url
                        else:
                            try:
                                file: discord.File = await attachment.to_file(
                                    use_cached=True
                                )
                                files.append(file)
                            except (
                                discord.HTTPException,
                                discord.NotFound,
                                discord.Forbidden,
                            ):
                                print(
                                    f"Failed to grab an attachment... {attachment.filename}"
                                )

                embed.set_image(url=urls)

                if isinstance(channel, discord.abc.Messageable):
                    try:
                        sb_message = await channel.send(
                            content=f"⭐{reaction_count}", files=files, embed=embed
                        )
                    except discord.Forbidden:
                        return
                    except discord.HTTPException:
                        return

                create_query = """
                INSERT INTO starboard (message_id, guild_id, starboard_message_id)
                VALUES (?, ?, ?)
                """
                if not sb_message:
                    return

                await self.bot.db.execute(
                    create_query, (message.id, message.guild.id, sb_message.id)
                )
                return
            else:
                async with self.bot.db.execute(
                    "SELECT sb_channel FROM guilds WHERE guild_id = ?",
                    (message.guild.id,),
                ) as cursor:
                    sb_channel = await cursor.fetchone()

                if not sb_channel:
                    return  # no starboard which is weird
                guild_id, sb_message_id = sb_message_row

                if not guild_id or not sb_message_id:
                    return

                guild = message.guild
                if guild_id is not guild.id:
                    return  # Mismatch

                sb_channel = sb_channel["sb_channel"]

                sb_channel = await guild.fetch_channel(sb_channel)

                if not sb_channel:
                    return  # Couldn't get the channel

                if isinstance(sb_channel, discord.abc.Messageable):
                    sb_message = await sb_channel.fetch_message(sb_message_id)

                if not sb_message:
                    return  # No message to edit

                await sb_message.edit(content=f"⭐{reaction_count}")
        else:
            check_query = """
            SELECT guild_id, starboard_message_id FROM starboard WHERE message_id = ?
            """
            sb_message_row_to_delete: aiosqlite.Row | None = None
            async with self.bot.db.execute(check_query, (message.id,)) as cursor:
                sb_message_row_to_delete = await cursor.fetchone()
            if sb_message_row_to_delete:
                async with self.bot.db.execute(
                    "SELECT sb_channel FROM guilds WHERE guild_id = ?",
                    (message.guild.id,),
                ) as cursor:
                    sb_channel = await cursor.fetchone()

                if not sb_channel:
                    return  # no starboard which is weird
                guild_id, sb_message_id = sb_message_row_to_delete

                if not guild_id or not sb_message_id:
                    return

                guild = message.guild
                if guild_id is not guild.id:
                    return  # Mismatch

                sb_channel = sb_channel["sb_channel"]

                sb_channel = await guild.fetch_channel(sb_channel)

                if not sb_channel:
                    return  # Couldn't get the channel

                if isinstance(sb_channel, discord.abc.Messageable):
                    sb_message = await sb_channel.fetch_message(sb_message_id)

                if not sb_message:
                    return  # No message to remove

                await sb_message.delete()

                delete_query = "DELETE FROM starboard WHERE message_id = ?"
                await self.bot.db.execute(delete_query, (message.id,))
                await self.bot.db.commit()

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: RawReactionActionEvent):
        message_id = payload.message_id
        channel_id = payload.channel_id
        guild_id = payload.guild_id

        if not guild_id:
            return

        guild = await self.bot.fetch_guild(guild_id)
        channel = await guild.fetch_channel(channel_id)
        message = None
        if isinstance(channel, discord.abc.Messageable):
            message = await channel.fetch_message(message_id)

        if not message:
            return

        await self._star(message)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: RawReactionActionEvent):
        message_id = payload.message_id
        channel_id = payload.channel_id
        guild_id = payload.guild_id

        if not guild_id:
            return

        guild = await self.bot.fetch_guild(guild_id)
        channel = await guild.fetch_channel(channel_id)
        message = None
        if isinstance(channel, discord.abc.Messageable):
            message = await channel.fetch_message(message_id)

        if not message:
            return

        await self._star(message)

    @commands.Cog.listener()
    async def on_raw_reaction_clear(self, payload: RawReactionActionEvent):
        message_id = payload.message_id
        channel_id = payload.channel_id
        guild_id = payload.guild_id

        if not guild_id:
            return

        guild = await self.bot.fetch_guild(guild_id)
        channel = await guild.fetch_channel(channel_id)
        message = None
        if isinstance(channel, discord.abc.Messageable):
            message = await channel.fetch_message(message_id)

        if not message:
            return

        await self._star(message)

    @commands.Cog.listener()
    async def on_raw_reaction_clear_emoji(self, payload: RawReactionActionEvent):
        message_id = payload.message_id
        channel_id = payload.channel_id
        guild_id = payload.guild_id

        if not guild_id:
            return

        guild = await self.bot.fetch_guild(guild_id)
        channel = await guild.fetch_channel(channel_id)
        message = None
        if isinstance(channel, discord.abc.Messageable):
            message = await channel.fetch_message(message_id)

        if not message:
            return

        await self._star(message)


async def setup(bot: MeowBot):
    await bot.add_cog(Starboard(bot))
