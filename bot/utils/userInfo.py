import os
import sqlite3

DATABASE = os.getcwd()+'/bot/databases/userInfo.db'
TABLE = 'Users'


class User:
    def __init__(self, bot, ctx, user=None):
        self.bot = bot
        self.ctx = ctx
        self.user = user if user else ctx.author

        self.conn = None
        self.conn = sqlite3.connect(DATABASE)
        self.cursor = self.conn.cursor()

        self._create_table()
        self._get_user_info()

    def close(self):
        self.conn.close()
        del self

    def _create_table(self):
        query = f"""CREATE TABLE IF NOT EXISTS {TABLE} (id BIGINT PRIMARY KEY, warnings TEXT)"""
        self.cursor.execute(query)
        self.conn.commit()

    def _create_user(self):
        try:
            query = f"""INSERT INTO {TABLE} VALUES (?, ?)"""
            self.cursor.execute(query, (self.user.id, "{}"))
            self.conn.commit()
        except sqlite3.Error:
            pass

    def _get_user_info(self):
        query = f"SELECT * FROM {TABLE} WHERE id = ?"
        self.cursor.execute(query, (self.user.id,))
        info = self.cursor.fetchall()
        if info:
            self.id = info[0][0]
            self.warnings = info[0][1]
            self.warns = eval(self.warnings)
            while isinstance(self.warns, str):
                self.warns = eval(self.warns)
        else:
            self._create_user()
            self._get_user_info()

    def warn(self, warning):
        query = f"UPDATE {TABLE} SET warnings = ? WHERE id = ?"
        self.warns[str(len(self.warns))] = warning
        self.cursor.execute(query, (f'"{self.warns}"', self.user.id,))
        self.conn.commit()
        self._get_user_info()

    def remove(self, warn_id):
        self._get_user_info()
        query = f"UPDATE {TABLE} SET warnings = ? WHERE id = ?"
        del self.warns[str(warn_id)]
        self.cursor.execute(query, (f'"{self.warns}"', self.user.id,))
        self.conn.commit()
        self._get_user_info()
