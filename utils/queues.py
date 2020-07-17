import os
import sqlite3

DATABASE = os.getcwd()+'/databases/saved_queues.db'
TABLE = 'Playlists'


class SavedQueues:
    def __init__(self, bot, ctx):
        self.bot = bot
        self.ctx = ctx
        self.queues = None

        self.conn = None

        try:
            self.conn = sqlite3.connect(DATABASE)
        except sqlite3.Error as e:
            print(e)
        self.cursor = self.conn.cursor()

        self._create_table()
        self.get_saved_queues()

    def _create_table(self):
        query = f"""CREATE TABLE IF NOT EXISTS {TABLE} (id BIGINT, queues TEXT)"""
        self.cursor.execute(query)
        self.conn.commit()

    def _create_saved_queues(self):
        query = f"""INSERT INTO {TABLE} (id, queues) VALUES (?, ?)"""
        self.cursor.execute(query, (self.ctx.guild.id, '{}'))
        self.conn.commit()

    def get_saved_queues(self):
        query = f"""SELECT * FROM {TABLE} WHERE id = ?"""
        self.cursor.execute(query, (self.ctx.guild.id,))
        info = self.cursor.fetchall()
        if info:
            self.queues = info[0][1]
        else:
            self._create_saved_queues()
        return self.queues

    def update(self, saved_queue_list):
        try:
            query = f"""UPDATE {TABLE} SET queues = ? WHERE id = ?"""
            self.cursor.execute(query, (f'{saved_queue_list}', self.ctx.guild.id))
            self.conn.commit()
        except sqlite3.Error:
            pass
        self.get_saved_queues()
