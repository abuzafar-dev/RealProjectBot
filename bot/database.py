"""SQLite bilan ishlash qatlami (aiosqlite orqali asinxron)."""

from dataclasses import dataclass

import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id         INTEGER PRIMARY KEY,
    full_name  TEXT    NOT NULL,
    created_at TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tasks (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    title      TEXT    NOT NULL,
    is_done    INTEGER NOT NULL DEFAULT 0,
    created_at TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    done_at    TEXT
);

CREATE INDEX IF NOT EXISTS idx_tasks_user ON tasks (user_id, is_done);
"""


@dataclass(frozen=True, slots=True)
class Task:
    id: int
    user_id: int
    title: str
    is_done: bool
    created_at: str
    done_at: str | None


@dataclass(frozen=True, slots=True)
class Stats:
    total: int
    done: int

    @property
    def left(self) -> int:
        return self.total - self.done

    @property
    def percent(self) -> int:
        return round(self.done * 100 / self.total) if self.total else 0


def _to_task(row: aiosqlite.Row) -> Task:
    return Task(
        id=row['id'],
        user_id=row['user_id'],
        title=row['title'],
        is_done=bool(row['is_done']),
        created_at=row['created_at'],
        done_at=row['done_at'],
    )


class Database:
    def __init__(self, path: str) -> None:
        self.path = str(path)
        self._conn: aiosqlite.Connection | None = None

    @property
    def conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError('Database.connect() chaqirilmagan')
        return self._conn

    async def connect(self) -> None:
        self._conn = await aiosqlite.connect(self.path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute('PRAGMA foreign_keys = ON')
        await self._conn.execute('PRAGMA journal_mode = WAL')
        await self._migrate()

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    async def _migrate(self) -> None:
        await self.conn.executescript(SCHEMA)
        # Eski bazalarda done_at ustuni bo'lmasligi mumkin
        async with self.conn.execute('PRAGMA table_info(tasks)') as cursor:
            columns = {row['name'] for row in await cursor.fetchall()}
        if 'done_at' not in columns:
            await self.conn.execute('ALTER TABLE tasks ADD COLUMN done_at TEXT')
        await self.conn.commit()

    async def _write(self, sql: str, params: tuple = ()) -> int:
        async with self.conn.execute(sql, params) as cursor:
            rowcount = cursor.rowcount
        await self.conn.commit()
        return rowcount

    # --- users ---

    async def add_user(self, user_id: int, full_name: str) -> None:
        await self._write(
            'INSERT INTO users (id, full_name) VALUES (?, ?) '
            'ON CONFLICT (id) DO UPDATE SET full_name = excluded.full_name',
            (user_id, full_name),
        )

    async def count_users(self) -> int:
        async with self.conn.execute('SELECT COUNT(*) FROM users') as cursor:
            (count,) = await cursor.fetchone()
        return count

    # --- tasks ---

    async def add_task(self, user_id: int, title: str) -> int:
        async with self.conn.execute(
            'INSERT INTO tasks (user_id, title) VALUES (?, ?)', (user_id, title)
        ) as cursor:
            task_id = cursor.lastrowid
        await self.conn.commit()
        return task_id

    async def get_tasks(self, user_id: int, limit: int = -1, offset: int = 0) -> list[Task]:
        """Avval bajarilmaganlar, keyin bajarilganlar; har guruhda yangilari tepada."""
        async with self.conn.execute(
            'SELECT * FROM tasks WHERE user_id = ? ORDER BY is_done, id DESC LIMIT ? OFFSET ?',
            (user_id, limit, offset),
        ) as cursor:
            return [_to_task(row) for row in await cursor.fetchall()]

    async def get_task(self, task_id: int, user_id: int) -> Task | None:
        async with self.conn.execute(
            'SELECT * FROM tasks WHERE id = ? AND user_id = ?', (task_id, user_id)
        ) as cursor:
            row = await cursor.fetchone()
        return _to_task(row) if row else None

    async def mark_done(self, task_id: int, user_id: int) -> bool:
        changed = await self._write(
            'UPDATE tasks SET is_done = 1, done_at = CURRENT_TIMESTAMP '
            'WHERE id = ? AND user_id = ? AND is_done = 0',
            (task_id, user_id),
        )
        return changed > 0

    async def delete_task(self, task_id: int, user_id: int) -> bool:
        changed = await self._write(
            'DELETE FROM tasks WHERE id = ? AND user_id = ?', (task_id, user_id)
        )
        return changed > 0

    async def get_stats(self, user_id: int) -> Stats:
        async with self.conn.execute(
            'SELECT COUNT(*), COALESCE(SUM(is_done), 0) FROM tasks WHERE user_id = ?',
            (user_id,),
        ) as cursor:
            total, done = await cursor.fetchone()
        return Stats(total=total, done=done)
