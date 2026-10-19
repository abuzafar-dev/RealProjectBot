import sqlite3


class Database:
    def __init__(self, path):
        self.path = path
        self.create_tables()

    def connect(self):
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def execute(self, sql, params=(), fetchone=False, fetchall=False):
        connection = self.connect()
        try:
            with connection:
                cursor = connection.execute(sql, params)
                if fetchone:
                    return cursor.fetchone()
                if fetchall:
                    return cursor.fetchall()
                return cursor.rowcount
        finally:
            connection.close()

    def create_tables(self):
        self.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                full_name TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users (id),
                title TEXT NOT NULL,
                is_done INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

    def add_user(self, user_id, full_name):
        self.execute(
            'INSERT INTO users (id, full_name) VALUES (?, ?) ON CONFLICT (id) DO UPDATE SET full_name = excluded.full_name',
            (user_id, full_name),
        )

    def add_task(self, user_id, title):
        self.execute('INSERT INTO tasks (user_id, title) VALUES (?, ?)', (user_id, title))

    def get_tasks(self, user_id):
        return self.execute(
            'SELECT * FROM tasks WHERE user_id = ? ORDER BY is_done, id DESC',
            (user_id,),
            fetchall=True,
        )

    def get_task(self, task_id, user_id):
        return self.execute(
            'SELECT * FROM tasks WHERE id = ? AND user_id = ?',
            (task_id, user_id),
            fetchone=True,
        )

    def mark_done(self, task_id, user_id):
        return self.execute('UPDATE tasks SET is_done = 1 WHERE id = ? AND user_id = ?', (task_id, user_id))

    def delete_task(self, task_id, user_id):
        return self.execute('DELETE FROM tasks WHERE id = ? AND user_id = ?', (task_id, user_id))

    def get_stats(self, user_id):
        row = self.execute(
            'SELECT COUNT(*) AS total, COALESCE(SUM(is_done), 0) AS done FROM tasks WHERE user_id = ?',
            (user_id,),
            fetchone=True,
        )
        return row['total'], row['done']

    def count_users(self):
        return self.execute('SELECT COUNT(*) AS total FROM users', fetchone=True)['total']
