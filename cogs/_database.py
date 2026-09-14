from sqlite3 import PARSE_DECLTYPES
from typing import cast

import aiosqlite
import discord
from discord.ext import commands

from main import MeowBot


class DataBase(commands.Cog):
    def __init__(self, bot):
        self.bot: MeowBot = cast(MeowBot, bot)

    @commands.Cog.listener()
    async def on_ready(self):
        print("Updating database..")

        for guild in self.bot.guilds:
            # Adds guilds to guilds table
            await self.bot.db.execute(
                "INSERT OR IGNORE INTO guilds (guild_id) VALUES (?)", (guild.id,)
            )

            for member in guild.members:
                if not member.bot:
                    # Adds non-bot members to users table
                    await self.bot.db.execute(
                        "INSERT OR IGNORE INTO users (user_id) VALUES (?)", (member.id,)
                    )
                    # Bridge guilds and members in guild_members table
                    await self.bot.db.execute(
                        "INSERT OR IGNORE INTO guild_members (guild_id, user_id) VALUES (?, ?)",
                        (guild.id, member.id),
                    )

        await self.bot.db.commit()

        print("Database updated!")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            return
        await self.bot.db.execute(
            "INSERT OR IGNORE INTO users (user_id) VALUES (?)", (member.id,)
        )
        await self.bot.db.execute(
            "INSERT OR IGNORE INTO guild_members (guild_id, user_id) VALUES (?, ?)",
            (member.guild.id, member.id),
        )
        await self.bot.db.commit()


async def setup(bot):
    bot.db = await aiosqlite.connect("database.db", detect_types=PARSE_DECLTYPES)

    await bot.db.execute("PRAGMA foreign_keys = ON;")
    bot.db.row_factory = aiosqlite.Row

    print("Setting up database tables...")

    await bot.db.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY
        )
    """)

    await bot.db.execute("""
    CREATE TABLE IF NOT EXISTS guilds (
        guild_id INTEGER PRIMARY KEY,
        msg_logs INTEGER,
        member_logs INTEGER,
        mod_logs INTEGER,
        sb_channel INTEGER
        )
    """)

    await bot.db.execute("""
    CREATE TABLE IF NOT EXISTS guild_members(
        guild_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,

        CONSTRAINT pk_guild_user PRIMARY KEY (guild_id, user_id),
        CONSTRAINT fk_gm_guild FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE,
        CONSTRAINT fk_gm_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
    """)

    await bot.db.execute("""
    CREATE TABLE IF NOT EXISTS warnings(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        moderator_id INTEGER NOT NULL,
        reason TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,

        CONSTRAINT fk_warn_guild FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE,
        CONSTRAINT fk_warn_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
    )
    """)

    await bot.db.execute("""
    CREATE TABLE IF NOT EXISTS starboard(
        message_id INTEGER PRIMARY KEY,
        guild_id INTEGER NOT NULL,
        starboard_message_id INTEGER NOT NULL,

        CONSTRAINT fk_gm_guild FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE
    )
    """)

    await bot.db.execute("""
    CREATE TABLE IF NOT EXISTS afk(
        guild_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        message TEXT NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        CONSTRAINT fk_warn_guild FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE,
        CONSTRAINT fk_warn_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,

        PRIMARY KEY (user_id, guild_id)
    )
    """)

    await bot.db.commit()
    print("Database tables ready!")

    await bot.add_cog(DataBase(bot))
