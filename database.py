import sqlite3
from datetime import datetime, timezone


class Database:
    def __init__(self, path: str) -> None:
        self.path = path
        with sqlite3.connect(self.path) as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS moderation_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    channel_id INTEGER NOT NULL,
                    message_id INTEGER NOT NULL UNIQUE,
                    user_id INTEGER NOT NULL,
                    score REAL NOT NULL,
                    flagged INTEGER NOT NULL,
                    categories TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    action TEXT DEFAULT 'pending'
                )
            """)

    async def log_result(self, message, result) -> None:
        categories = result.category_summary.replace("'", "''")
        with sqlite3.connect(self.path) as db:
            db.execute(
                "INSERT OR REPLACE INTO moderation_logs (guild_id, channel_id, message_id, user_id, score, flagged, categories, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (message.guild.id, message.channel.id, message.id, message.author.id, result.score, int(result.flagged), categories, datetime.now(timezone.utc).isoformat()),
            )

    async def set_action(self, message_id: int, action: str) -> None:
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE moderation_logs SET action=? WHERE message_id=?", (action, message_id))
