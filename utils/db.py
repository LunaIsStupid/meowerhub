import aiosqlite
from sqlite3 import PARSE_DECLTYPES

class Users:
    def __init__(self, db: aiosqlite.Connection) -> None:
        self.db = db

    async def setup(self):
        await self.db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY
        )
        """)
        await self.db.commit()
        print("Users...")
        return self

    async def get(self, user_id: int):
        async with self.db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            return await cursor.fetchone()

    async def get_many(self, count: int = 0):
        async with self.db.execute("SELECT * FROM users") as cursor:
            if count <= 0: return await cursor.fetchall()
            else: return await cursor.fetchmany(count)

    async def add(self, user_id: int, autocommit: bool = True):
        await self.db.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        if autocommit: await self.db.commit()

    async def rem(self, user_id: int, autocommit: bool = True):
        await self.db.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        if autocommit: await self.db.commit()


class Guilds:
    def __init__(self, db: aiosqlite.Connection) -> None:
        self.db = db

    async def setup(self):
        await self.db.execute("""
        CREATE TABLE IF NOT EXISTS guilds (
            guild_id INTEGER PRIMARY KEY,
            msg_logs INTEGER,
            member_logs INTEGER,
            mod_logs INTEGER,
            sb_channel INTEGER
        )
        """)
        try: await self.db.execute("ALTER TABLE guilds ADD COLUMN event_ping_id INTEGER")
        except: pass
        try: await self.db.execute("ALTER TABLE guilds ADD COLUMN event_host_id INTEGER")
        except: pass
        try: await self.db.execute("ALTER TABLE guilds ADD COLUMN event_announcements INTEGER")
        except: pass
        await self.db.commit()
        print("Guilds...")
        return self

    async def get(self, guild_id: int):
        async with self.db.execute("SELECT * FROM guilds WHERE guild_id = ?", (guild_id,)) as cursor:
            return await cursor.fetchone()

    async def get_many(self, count: int = 0):
        async with self.db.execute("SELECT * FROM guilds") as cursor:
            if count <= 0: return await cursor.fetchall()
            else: return await cursor.fetchmany(count)

    async def add(
            self, guild_id: int,
            msg_logs: int | None = None, member_logs: int | None = None,
            mod_logs: int | None = None, sb_channel: int | None = None,
            event_ping_id: int | None = None, event_host_id: int | None = None,
            event_announcements: int | None = None,
            autocommit: bool = True
        ):
        await self.db.execute("""
            INSERT OR IGNORE INTO guilds (guild_id, msg_logs, member_logs, mod_logs, sb_channel, event_ping_id, event_host_id, event_announcements)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (guild_id, msg_logs, member_logs, mod_logs, sb_channel, event_ping_id, event_host_id, event_announcements)
        )
        if autocommit: await self.db.commit()

    async def upd(
            self, guild_id: int,
            msg_logs: int | None = None, member_logs: int | None = None,
            mod_logs: int | None = None, sb_channel: int | None = None,
            event_ping_id: int | None = None, event_host_id: int | None = None,
            event_announcements: int | None = None,
            autocommit: bool = True
        ):
        await self.db.execute("""
            UPDATE guilds SET
                msg_logs = COALESCE(?, msg_logs),
                member_logs = COALESCE(?, member_logs),
                mod_logs = COALESCE(?, mod_logs),
                sb_channel = COALESCE(?, sb_channel),
                event_ping_id = COALESCE(?, event_ping_id),
                event_host_id = COALESCE(?, event_host_id),
                event_announcements = COALESCE(?, event_announcements)
            WHERE guild_id = ?
            """, (msg_logs, member_logs, mod_logs, sb_channel, event_ping_id, event_host_id, event_announcements, guild_id)
        )
        if autocommit: await self.db.commit()

    async def rem(self, guild_id: int, autocommit: bool = True):
        await self.db.execute("DELETE FROM guilds WHERE guild_id = ?", (guild_id,))
        if autocommit: await self.db.commit()


class Warnings:
    def __init__(self, db: aiosqlite.Connection) -> None:
        self.db = db

    async def setup(self):
        await self.db.execute("""
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
        await self.db.commit()
        print("Warnings...")
        return self

    async def get(self, warning_id: int):
        async with self.db.execute("SELECT * FROM warnings WHERE id = ?", (warning_id,)) as cursor:
            return await cursor.fetchone()

    async def get_many(self, guild_id: int, user_id: int, count: int = 0):
        async with self.db.execute("SELECT * FROM warnings WHERE guild_id = ? AND user_id = ?", (guild_id, user_id)) as cursor:
            if count <= 0: return await cursor.fetchall()
            else: return await cursor.fetchmany(count)

    async def add(self, guild_id: int, user_id: int, moderator_id: int, reason: str | None = None, autocommit: bool = True):
        cursor = await self.db.execute("""
            INSERT INTO warnings (guild_id, user_id, moderator_id, reason)
            VALUES (?, ?, ?, ?)
            """, (guild_id, user_id, moderator_id, reason)
        )
        if autocommit: await self.db.commit()
        return cursor.lastrowid

    async def upd(self, warning_id: int, reason: str | None, autocommit: bool = True):
        await self.db.execute("UPDATE warnings SET reason = ? WHERE id = ?", (reason, warning_id))
        if autocommit: await self.db.commit()

    async def rem(self, warning_id: int, autocommit: bool = True):
        await self.db.execute("DELETE FROM warnings WHERE id = ?", (warning_id,))
        if autocommit: await self.db.commit()


class Starboard:
    def __init__(self, db: aiosqlite.Connection) -> None:
        self.db = db

    async def setup(self):
        await self.db.execute("""
        CREATE TABLE IF NOT EXISTS starboard(
            message_id INTEGER PRIMARY KEY,
            guild_id INTEGER NOT NULL,
            starboard_message_id INTEGER NOT NULL,

            CONSTRAINT fk_sb_guild FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE
        )
        """)
        await self.db.commit()
        print("Starboard...")
        return self

    async def get(self, message_id: int):
        async with self.db.execute("SELECT * FROM starboard WHERE message_id = ?", (message_id,)) as cursor:
            return await cursor.fetchone()

    async def get_many(self, guild_id: int, count: int = 0):
        async with self.db.execute("SELECT * FROM starboard WHERE guild_id = ?", (guild_id,)) as cursor:
            if count <= 0: return await cursor.fetchall()
            else: return await cursor.fetchmany(count)

    async def add(self, message_id: int, guild_id: int, starboard_message_id: int, autocommit: bool = True):
        await self.db.execute("""
            INSERT OR IGNORE INTO starboard (message_id, guild_id, starboard_message_id)
            VALUES (?, ?, ?)
            """, (message_id, guild_id, starboard_message_id)
        )
        if autocommit: await self.db.commit()

    async def upd(self, message_id: int, starboard_message_id: int, autocommit: bool = True):
        await self.db.execute(
            "UPDATE starboard SET starboard_message_id = ? WHERE message_id = ?",
            (starboard_message_id, message_id)
        )
        if autocommit: await self.db.commit()

    async def rem(self, message_id: int, autocommit: bool = True):
        await self.db.execute("DELETE FROM starboard WHERE message_id = ?", (message_id,))
        if autocommit: await self.db.commit()


class Afk:
    def __init__(self, db: aiosqlite.Connection) -> None:
        self.db = db

    async def setup(self):
        await self.db.execute("""
        CREATE TABLE IF NOT EXISTS afk(
            guild_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            CONSTRAINT fk_afk_guild FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE,
            CONSTRAINT fk_afk_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,

            PRIMARY KEY (user_id, guild_id)
        )
        """)
        await self.db.commit()
        print("Afk...")
        return self

    async def get(self, guild_id: int, user_id: int):
        async with self.db.execute("SELECT * FROM afk WHERE guild_id = ? AND user_id = ?", (guild_id, user_id)) as cursor:
            return await cursor.fetchone()

    async def get_many(self, count: int = 0):
        async with self.db.execute("SELECT * FROM afk") as cursor:
            if count <= 0: return await cursor.fetchall()
            else: return await cursor.fetchmany(count)

    async def upsert(self, guild_id: int, user_id: int, message: str, autocommit: bool = True):
        await self.db.execute("""
            INSERT INTO afk (guild_id, user_id, message)
            VALUES (?, ?, ?)
            ON CONFLICT (user_id, guild_id) DO UPDATE SET
                message = excluded.message,
                updated_at = CURRENT_TIMESTAMP
            """, (guild_id, user_id, message)
        )
        if autocommit: await self.db.commit()

    async def rem(self, guild_id: int, user_id: int, autocommit: bool = True):
        await self.db.execute("DELETE FROM afk WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
        if autocommit: await self.db.commit()


class Pet:
    def __init__(self, db: aiosqlite.Connection) -> None:
        self.db = db

    async def setup(self):
        await self.db.execute("""
        CREATE TABLE IF NOT EXISTS pet(
            guild_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            message TEXT NOT NULL,

            CONSTRAINT fk_pet_guild FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE,
            CONSTRAINT fk_pet_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,

            PRIMARY KEY (user_id, guild_id)
        )
        """)
        await self.db.commit()
        print("Pet...")
        return self

    async def get(self, guild_id: int, user_id: int):
        async with self.db.execute("SELECT * FROM pet WHERE guild_id = ? AND user_id = ?", (guild_id, user_id)) as cursor:
            return await cursor.fetchone()

    async def get_many(self, count: int = 0):
        async with self.db.execute("SELECT * FROM pet") as cursor:
            if count <= 0: return await cursor.fetchall()
            else: return await cursor.fetchmany(count)

    async def upsert(self, guild_id: int, user_id: int, message: str, autocommit: bool = True):
        await self.db.execute("""
            INSERT INTO pet (guild_id, user_id, message)
            VALUES (?, ?, ?)
            ON CONFLICT (user_id, guild_id) DO UPDATE SET
                message = excluded.message
            """, (guild_id, user_id, message)
        )
        if autocommit: await self.db.commit()

    async def rem(self, guild_id: int, user_id: int, autocommit: bool = True):
        await self.db.execute("DELETE FROM pet WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
        if autocommit: await self.db.commit()

class Events:
    def __init__(self, db: aiosqlite.Connection) -> None:
        self.db = db

    async def setup(self):
        await self.db.execute("""
        CREATE TABLE IF NOT EXISTS events(
            guild_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,

            CONSTRAINT fk_event_guild FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE,
            CONSTRAINT fk_pet_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,

            PRIMARY KEY (guild_id, user_id)
        )
        """)
        await self.db.commit()
        print("Events...")
        return self

    async def get(self, guild_id: int, user_id: int | None = None):
        if not user_id:
            async with self.db.execute("SELECT user_id FROM events WHERE guild_id = ? ORDER BY RANDOM() LIMIT 1", (guild_id,)) as cursor:
                return await cursor.fetchone()
        async with self.db.execute("SELECT * FROM events WHERE guild_id = ? AND user_id = ?", (guild_id, user_id)) as cursor:
            return await cursor.fetchone()

    async def upsert(self, guild_id: int, user_id: int, autocommit: bool = True):
        await self.db.execute("""
            INSERT OR IGNORE INTO events (guild_id, user_id) VALUES (?, ?)
            """, (guild_id, user_id)
        )
        if autocommit: await self.db.commit()

    async def rem(self, guild_id: int, user_id: int, autocommit: bool = True):
        await self.db.execute("DELETE FROM events WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
        if autocommit: await self.db.commit()

    async def reset(self, guild_id: int, autocommit: bool = True):
        await self.db.execute("DELETE FROM events WHERE guild_id = ?", (guild_id,))
        if autocommit: await self.db.commit()


class DB:
    db: aiosqlite.Connection
    users: Users
    guilds: Guilds
    warnings: Warnings
    starboard: Starboard
    afk: Afk
    pet: Pet
    events: Events

    async def setup(self, path = "database.db"):
        print("Setting up database...")
        self.db = await aiosqlite.connect(path, detect_types=PARSE_DECLTYPES)

        await self.db.execute("PRAGMA foreign_keys = ON;")
        self.db.row_factory = aiosqlite.Row

        self.users = await Users(self.db).setup()
        self.guilds = await Guilds(self.db).setup()
        self.warnings = await Warnings(self.db).setup()
        self.starboard = await Starboard(self.db).setup()
        self.afk = await Afk(self.db).setup()
        self.pet = await Pet(self.db).setup()
        self.events = await Events(self.db).setup()
        print("Database ready!")

        return self

    async def commit(self):
        await self.db.commit()

    async def close(self):
        await self.db.close()
