import os
import sqlite3

DATABASE = os.getcwd()+'/databases/moderation.db'
TABLE = 'ServerModeration'


def index_replace(text, index=0, replacement=''):
    return '%s%s%s' % (text[:index], replacement, text[index + 1:])


class User:
    def __init__(self, bot, ctx, user=None):
        self.bot = bot
        self.guild = ctx.guild
        self.user = user if user else ctx.author

        self.history = None

        self.conn = None

        try:
            self.conn = sqlite3.connect(DATABASE)
        except sqlite3.Error as e:
            print(e)
        self.cursor = self.conn.cursor()

        self._create_table()
        self._get_server_info()

    def _create_table(self):
        query = f"""CREATE TABLE IF NOT EXISTS {TABLE} (id BIGINT, g_id BIGINT, history TEXT)"""
        self.cursor.execute(query)
        self.conn.commit()

    def _get_server_info(self):
        query = f"SELECT * FROM {TABLE} WHERE id = ? and g_id = ?"
        self.cursor.execute(query, (self.user.id, self.guild.id))
        info = self.cursor.fetchall()
        if info:
            self.id = info[0][0]
            self.g_id = info[0][1]
            self.history = eval(info[0][2])
        else:
            self._create_server()
            self._get_server_info()

    def _create_server(self):
        try:
            query = f"""INSERT INTO {TABLE} VALUES (?, ?, ?)"""
            self.cursor.execute(query, (self.user.id, self.guild.id, '{}'))
            self.conn.commit()
        except sqlite3.Error:
            pass

    def update_value(self, column, value):
        query = f"UPDATE {TABLE} SET {column} = ? WHERE id = ? and g_id = ?"
        self.cursor.execute(query, (value, self.user.id, self.guild.id))
        self.conn.commit()
        self._get_server_info()

    def add_history(self, event, reason, moderator, date):
        self.history = eval(self.history)
        if event not in self.history:
            self.history[event] = []
        self.history[event].append([reason, moderator.id, date])

        query = f"UPDATE {TABLE} SET history = ? WHERE id = ? and g_id = ?"
        self.cursor.execute(query, (f'{self.history}', self.user.id, self.guild.id))
        self.conn.commit()
        self._get_server_info()
