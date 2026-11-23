"""SQLite bilan ishlash qatlami (aiosqlite orqali asinxron)."""

from dataclasses import dataclass
from datetime import date, datetime, time

import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id         INTEGER PRIMARY KEY,
    full_name  TEXT    NOT NULL,
    created_at TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_digest TEXT,               -- ertalabki reja oxirgi yuborilgan sana
    digest_hour INTEGER,            -- shaxsiy reja soati; NULL — umumiy (DIGEST_HOUR)
    weekly      INTEGER NOT NULL DEFAULT 1,  -- haftalik hisobot yoqilganmi
    lead_minutes INTEGER,           -- necha daqiqa oldin ogohlantirish; NULL — o'chiq
    last_weekly TEXT                -- haftalik hisobot oxirgi yuborilgan sana
);

CREATE TABLE IF NOT EXISTS tasks (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    title      TEXT    NOT NULL,
    is_done    INTEGER NOT NULL DEFAULT 0,
    created_at TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    done_at    TEXT,
    due_date   TEXT,                -- YYYY-MM-DD, ixtiyoriy
    due_time   TEXT,                -- HH:MM, bo'lsa shu vaqtda eslatma yuboriladi
    reminded   INTEGER NOT NULL DEFAULT 0,
    repeat     TEXT,                -- 'daily' | 'weekly' | 'weekdays'; bajarilganda keyingisi
    important  INTEGER NOT NULL DEFAULT 0,      -- ⭐ bo'limi ichida tepada turadi
    pre_reminded INTEGER NOT NULL DEFAULT 0     -- oldindan ogohlantirish yuborilganmi
);

CREATE INDEX IF NOT EXISTS idx_tasks_user ON tasks (user_id, is_done);
"""

# (jadval, ustun, ta'rif) — eski bazani yangilash uchun
MIGRATIONS = [
    ('tasks', 'done_at', 'TEXT'),
    ('tasks', 'due_date', 'TEXT'),
    ('tasks', 'due_time', 'TEXT'),
    ('tasks', 'reminded', 'INTEGER NOT NULL DEFAULT 0'),
    ('users', 'last_digest', 'TEXT'),
    ('tasks', 'repeat', 'TEXT'),
    ('users', 'digest_hour', 'INTEGER'),
    ('users', 'weekly', 'INTEGER NOT NULL DEFAULT 1'),
    ('users', 'last_weekly', 'TEXT'),
    ('users', 'lead_minutes', 'INTEGER'),
    ('tasks', 'important', 'INTEGER NOT NULL DEFAULT 0'),
    ('tasks', 'pre_reminded', 'INTEGER NOT NULL DEFAULT 0'),
]


@dataclass(frozen=True, slots=True)
class Task:
    id: int
    user_id: int
    title: str
    is_done: bool
    created_at: str
    done_at: str | None
    due_date: date | None = None
    due_time: time | None = None
    repeat: str | None = None
    important: bool = False


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


@dataclass(frozen=True, slots=True)
class UserSettings:
    digest_hour: int | None  # None — umumiy soat
    weekly: bool
    lead_minutes: int | None = None  # None — oldindan ogohlantirish o'chiq


@dataclass(frozen=True, slots=True)
class WeekSummary:
    done: int
    overdue: int
    planned: int  # kelgusi 7 kunga rejalashtirilgan ochiq vazifalar


@dataclass(frozen=True, slots=True)
class GlobalStats:
    users: int
    active_users: int  # bajarilmagan vazifasi borlar
    tasks: int
    done: int
    pending_reminders: int


def _to_task(row: aiosqlite.Row) -> Task:
    return Task(
        id=row['id'],
        user_id=row['user_id'],
        title=row['title'],
        is_done=bool(row['is_done']),
        created_at=row['created_at'],
        done_at=row['done_at'],
        due_date=date.fromisoformat(row['due_date']) if row['due_date'] else None,
        due_time=time.fromisoformat(row['due_time']) if row['due_time'] else None,
        repeat=row['repeat'],
        important=bool(row['important']),
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
        # Eski bazalarda keyin qo'shilgan ustunlar bo'lmasligi mumkin — ma'lumot yo'qolmaydi
        for table, column, ddl in MIGRATIONS:
            async with self.conn.execute(f'PRAGMA table_info({table})') as cursor:
                columns = {row['name'] for row in await cursor.fetchall()}
            if column not in columns:
                await self.conn.execute(f'ALTER TABLE {table} ADD COLUMN {column} {ddl}')
        # Ustunlar migratsiyadan keyin aniq bor, shuning uchun indeks shu yerda
        await self.conn.execute(
            'CREATE INDEX IF NOT EXISTS idx_tasks_due ON tasks (is_done, due_date)'
        )
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

    async def get_settings(self, user_id: int) -> UserSettings:
        async with self.conn.execute(
            'SELECT digest_hour, weekly, lead_minutes FROM users WHERE id = ?', (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
        if row is None:
            return UserSettings(digest_hour=None, weekly=True)
        return UserSettings(
            digest_hour=row['digest_hour'],
            weekly=bool(row['weekly']),
            lead_minutes=row['lead_minutes'],
        )

    async def set_lead_minutes(self, user_id: int, minutes: int | None) -> None:
        await self._write('UPDATE users SET lead_minutes = ? WHERE id = ?', (minutes, user_id))

    async def digest_hour_for(self, user_id: int, default: int) -> int:
        return (await self.get_settings(user_id)).digest_hour or default

    async def set_digest_hour(self, user_id: int, hour: int) -> None:
        await self._write('UPDATE users SET digest_hour = ? WHERE id = ?', (hour, user_id))

    async def toggle_weekly(self, user_id: int) -> bool:
        await self._write('UPDATE users SET weekly = 1 - weekly WHERE id = ?', (user_id,))
        return (await self.get_settings(user_id)).weekly

    async def count_users(self) -> int:
        async with self.conn.execute('SELECT COUNT(*) FROM users') as cursor:
            (count,) = await cursor.fetchone()
        return count

    # --- tasks ---

    async def add_task(
        self,
        user_id: int,
        title: str,
        due_date: date | None = None,
        due_time: time | None = None,
        repeat: str | None = None,
    ) -> int:
        async with self.conn.execute(
            'INSERT INTO tasks (user_id, title, due_date, due_time, repeat) VALUES (?, ?, ?, ?, ?)',
            (
                user_id,
                title,
                due_date.isoformat() if due_date else None,
                due_time.strftime('%H:%M') if due_time else None,
                repeat,
            ),
        ) as cursor:
            task_id = cursor.lastrowid
        await self.conn.commit()
        return task_id

    async def get_tasks(self, user_id: int, limit: int = -1, offset: int = 0) -> list[Task]:
        """Bajarilmaganlar tepada, eng yaqin muddatlisi birinchi; muddatsizlar — yangisi tepada."""
        async with self.conn.execute(
            'SELECT * FROM tasks WHERE user_id = ? '
            'ORDER BY is_done, due_date IS NULL, due_date, due_time IS NULL, due_time, id DESC '
            'LIMIT ? OFFSET ?',
            (user_id, limit, offset),
        ) as cursor:
            return [_to_task(row) for row in await cursor.fetchall()]

    async def get_open_tasks(
        self, user_id: int, today: date, limit: int = -1, offset: int = 0
    ) -> list[Task]:
        """Bajarilmaganlar bo'limlar tartibida: muddati o'tgan → bugun → keyingi → muddatsiz.

        Har bir bo'lim ichida ⭐ muhimlari tepada, keyin eng yaqin muddat.
        """
        day = today.isoformat()
        async with self.conn.execute(
            'SELECT * FROM tasks WHERE user_id = ? AND is_done = 0 ORDER BY '
            'CASE WHEN due_date IS NULL THEN 3 WHEN due_date < ? THEN 0 '
            'WHEN due_date = ? THEN 1 ELSE 2 END, '
            'important DESC, due_date, due_time IS NULL, due_time, id DESC '
            'LIMIT ? OFFSET ?',
            (user_id, day, day, limit, offset),
        ) as cursor:
            return [_to_task(row) for row in await cursor.fetchall()]

    async def get_task(self, task_id: int, user_id: int) -> Task | None:
        async with self.conn.execute(
            'SELECT * FROM tasks WHERE id = ? AND user_id = ?', (task_id, user_id)
        ) as cursor:
            row = await cursor.fetchone()
        return _to_task(row) if row else None

    async def mark_done(self, task_id: int, user_id: int, now: datetime | None = None) -> bool:
        """now — foydalanuvchi vaqt zonasidagi vaqt (statistika kunlari to'g'ri chiqishi uchun)."""
        done_at = now.strftime('%Y-%m-%d %H:%M:%S') if now else None
        changed = await self._write(
            'UPDATE tasks SET is_done = 1, done_at = COALESCE(?, CURRENT_TIMESTAMP) '
            'WHERE id = ? AND user_id = ? AND is_done = 0',
            (done_at, task_id, user_id),
        )
        return changed > 0

    async def toggle_important(self, task_id: int, user_id: int) -> bool | None:
        """⭐ belgisini almashtiradi; yangi holatni (yoki topilmasa None) qaytaradi."""
        changed = await self._write(
            'UPDATE tasks SET important = 1 - important '
            'WHERE id = ? AND user_id = ? AND is_done = 0',
            (task_id, user_id),
        )
        if not changed:
            return None
        return (await self.get_task(task_id, user_id)).important

    async def search_tasks(self, user_id: int, query: str, limit: int = 10) -> list[Task]:
        """Nomida so'z bor vazifalar: ochiqlari tepada."""
        pattern = '%' + query.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%'
        async with self.conn.execute(
            "SELECT * FROM tasks WHERE user_id = ? AND title LIKE ? ESCAPE '\\' "
            'ORDER BY is_done, due_date IS NULL, due_date, id DESC LIMIT ?',
            (user_id, pattern, limit),
        ) as cursor:
            return [_to_task(row) for row in await cursor.fetchall()]

    async def rename_task(self, task_id: int, user_id: int, title: str) -> bool:
        changed = await self._write(
            'UPDATE tasks SET title = ? WHERE id = ? AND user_id = ? AND is_done = 0',
            (title, task_id, user_id),
        )
        return changed > 0

    async def count_done_since(self, user_id: int, since: date) -> int:
        async with self.conn.execute(
            'SELECT COUNT(*) FROM tasks WHERE user_id = ? AND is_done = 1 AND done_at >= ?',
            (user_id, since.isoformat()),
        ) as cursor:
            (count,) = await cursor.fetchone()
        return count

    async def get_done_days(self, user_id: int) -> set[date]:
        """Vazifa bajarilgan kunlar (ketma-ketlikni hisoblash uchun)."""
        async with self.conn.execute(
            'SELECT DISTINCT substr(done_at, 1, 10) FROM tasks '
            'WHERE user_id = ? AND is_done = 1 AND done_at IS NOT NULL',
            (user_id,),
        ) as cursor:
            return {date.fromisoformat(row[0]) for row in await cursor.fetchall()}

    async def reschedule(
        self,
        task_id: int,
        user_id: int,
        due_date: date,
        due_time: time | None,
        *,
        snoozed: bool = False,
    ) -> bool:
        """Muddatni ko'chirish/kechiktirish: yangi vaqtda eslatma qayta yuboriladi.

        snoozed — foydalanuvchi eslatmani hozirgina ko'rdi, oldindan ogohlantirish shart emas.
        """
        changed = await self._write(
            'UPDATE tasks SET due_date = ?, due_time = ?, reminded = 0, pre_reminded = ? '
            'WHERE id = ? AND user_id = ? AND is_done = 0',
            (
                due_date.isoformat(),
                due_time.strftime('%H:%M') if due_time else None,
                int(snoozed),
                task_id,
                user_id,
            ),
        )
        return changed > 0

    async def update_due(
        self,
        task_id: int,
        user_id: int,
        due_date: date | None,
        due_time: time | None,
        repeat: str | None,
    ) -> bool:
        """Muddatni to'liq almashtirish (kartadagi «Vaqtini o'zgartirish»)."""
        changed = await self._write(
            'UPDATE tasks SET due_date = ?, due_time = ?, repeat = ?, reminded = 0, '
            'pre_reminded = 0 WHERE id = ? AND user_id = ? AND is_done = 0',
            (
                due_date.isoformat() if due_date else None,
                due_time.strftime('%H:%M') if due_time else None,
                repeat,
                task_id,
                user_id,
            ),
        )
        return changed > 0

    async def clear_done(self, user_id: int) -> int:
        return await self._write('DELETE FROM tasks WHERE user_id = ? AND is_done = 1', (user_id,))

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

    async def get_global_stats(self) -> GlobalStats:
        async with self.conn.execute(
            'SELECT '
            '(SELECT COUNT(*) FROM users), '
            '(SELECT COUNT(DISTINCT user_id) FROM tasks WHERE is_done = 0), '
            '(SELECT COUNT(*) FROM tasks), '
            '(SELECT COUNT(*) FROM tasks WHERE is_done = 1), '
            '(SELECT COUNT(*) FROM tasks WHERE is_done = 0 AND reminded = 0 '
            'AND due_time IS NOT NULL)'
        ) as cursor:
            row = await cursor.fetchone()
        return GlobalStats(*row)

    async def count_overdue(self, user_id: int, today: date) -> int:
        async with self.conn.execute(
            'SELECT COUNT(*) FROM tasks WHERE user_id = ? AND is_done = 0 AND due_date < ?',
            (user_id, today.isoformat()),
        ) as cursor:
            (count,) = await cursor.fetchone()
        return count

    # --- eslatmalar ---

    async def get_due_reminders(self, now: datetime) -> list[Task]:
        """Vaqti kelgan, hali yuborilmagan va bajarilmagan vaqtli vazifalar."""
        async with self.conn.execute(
            'SELECT * FROM tasks WHERE is_done = 0 AND reminded = 0 AND due_time IS NOT NULL '
            "AND due_date || ' ' || due_time <= ? ORDER BY due_date, due_time",
            (now.strftime('%Y-%m-%d %H:%M'),),
        ) as cursor:
            return [_to_task(row) for row in await cursor.fetchall()]

    async def get_pre_reminders(self, now: datetime) -> list[tuple[Task, int]]:
        """Oldindan ogohlantirish vaqti kelgan vazifalar (vazifa, necha daqiqa qolgani)."""
        stamp = now.strftime('%Y-%m-%d %H:%M')
        async with self.conn.execute(
            'SELECT t.* FROM tasks t JOIN users u ON u.id = t.user_id '
            'WHERE t.is_done = 0 AND t.reminded = 0 AND t.pre_reminded = 0 '
            'AND t.due_time IS NOT NULL AND u.lead_minutes IS NOT NULL '
            "AND strftime('%Y-%m-%d %H:%M', t.due_date || ' ' || t.due_time, "
            "'-' || u.lead_minutes || ' minutes') <= ? "
            "AND t.due_date || ' ' || t.due_time > ? "
            'ORDER BY t.due_date, t.due_time',
            (stamp, stamp),
        ) as cursor:
            tasks = [_to_task(row) for row in await cursor.fetchall()]
        result = []
        for task in tasks:
            left = datetime.combine(task.due_date, task.due_time) - now.replace(tzinfo=None)
            result.append((task, int(left.total_seconds() // 60)))
        return result

    async def mark_pre_reminded(self, task_id: int) -> None:
        await self._write('UPDATE tasks SET pre_reminded = 1 WHERE id = ?', (task_id,))

    async def mark_reminded(self, task_id: int) -> None:
        await self._write('UPDATE tasks SET reminded = 1 WHERE id = ?', (task_id,))

    async def get_digest_users(self, now: datetime, default_hour: int) -> list[int]:
        """Reja soati kelgan, bugun reja olmagan va bugungi/muddati o'tgan vazifasi borlar."""
        day = now.date().isoformat()
        async with self.conn.execute(
            'SELECT DISTINCT u.id FROM users u JOIN tasks t ON t.user_id = u.id '
            'WHERE t.is_done = 0 AND t.due_date <= ? '
            'AND (u.last_digest IS NULL OR u.last_digest < ?) '
            'AND COALESCE(u.digest_hour, ?) <= ?',
            (day, day, default_hour, now.hour),
        ) as cursor:
            return [row['id'] for row in await cursor.fetchall()]

    async def get_digest_tasks(self, user_id: int, today: date) -> list[Task]:
        async with self.conn.execute(
            'SELECT * FROM tasks WHERE user_id = ? AND is_done = 0 AND due_date <= ? '
            'ORDER BY due_date, due_time IS NULL, due_time',
            (user_id, today.isoformat()),
        ) as cursor:
            return [_to_task(row) for row in await cursor.fetchall()]

    # --- haftalik hisobot ---

    async def get_weekly_users(self, today: date) -> list[int]:
        """Hisobot yoqilgan, bu hafta hali olmagan va kamida bitta vazifasi borlar."""
        async with self.conn.execute(
            'SELECT u.id FROM users u WHERE u.weekly = 1 '
            'AND (u.last_weekly IS NULL OR u.last_weekly < ?) '
            'AND EXISTS (SELECT 1 FROM tasks t WHERE t.user_id = u.id)',
            (today.isoformat(),),
        ) as cursor:
            return [row['id'] for row in await cursor.fetchall()]

    async def get_week_summary(self, user_id: int, week_start: date, today: date) -> WeekSummary:
        day = today.isoformat()
        async with self.conn.execute(
            'SELECT '
            '(SELECT COUNT(*) FROM tasks WHERE user_id = ? AND is_done = 1 AND done_at >= ?), '
            '(SELECT COUNT(*) FROM tasks WHERE user_id = ? AND is_done = 0 AND due_date < ?), '
            '(SELECT COUNT(*) FROM tasks WHERE user_id = ? AND is_done = 0 '
            "AND due_date > ? AND due_date <= date(?, '+7 days'))",
            (user_id, week_start.isoformat(), user_id, day, user_id, day, day),
        ) as cursor:
            done, overdue, planned = await cursor.fetchone()
        return WeekSummary(done=done, overdue=overdue, planned=planned)

    async def set_weekly_sent(self, user_id: int, today: date) -> None:
        await self._write(
            'UPDATE users SET last_weekly = ? WHERE id = ?', (today.isoformat(), user_id)
        )

    async def set_digest_sent(self, user_id: int, today: date) -> None:
        await self._write(
            'UPDATE users SET last_digest = ? WHERE id = ?', (today.isoformat(), user_id)
        )
