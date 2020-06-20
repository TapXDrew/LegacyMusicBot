import json
import os
import sqlite3

DATABASE = os.getcwd()+'/bot/databases/servers.db'
TABLE = 'ServerInfo'


def index_replace(text, index=0, replacement=''):
    return '%s%s%s' % (text[:index], replacement, text[index + 1:])


class Server:
    def __init__(self, bot, guild):
        self.bot = bot
        self.guild = guild

        self.config = json.load(open(self.bot.home_dir + '/bot/config/config.json'))

        self.conn = None

        try:
            self.conn = sqlite3.connect(DATABASE)
        except sqlite3.Error as e:
            print(e)
        self.cursor = self.conn.cursor()

        self._create_table()
        self._get_server_info()

    def _create_table(self):
        query = f"""CREATE TABLE IF NOT EXISTS {TABLE} (id BIGINT, auto_connect BIGINT, locked TEXT, prefix TEXT, AutoPlaylist BIGINT, PermissionSystem BIGINT, VerificationSystem BIGINT)"""
        self.cursor.execute(query)
        self.conn.commit()

    def _get_server_info(self):
        query = f"SELECT * FROM {TABLE} WHERE id = ?"
        self.cursor.execute(query, (self.guild.id,))
        info = self.cursor.fetchall()
        if info:
            self.id = info[0][0]
            self.auto_connect = info[0][1]
            self.locked = [int(server_id) for server_id in info[0][2].split(" ")] if info[0][2].split(" ") != [''] else []
            self.locked_raw = info[0][2]
            self.prefix = info[0][3]
            self.ap = info[0][4]
            self.ps = info[0][5]
            self.vs = info[0][6]
        else:
            self._create_server()
            self._get_server_info()

    def _create_server(self):
        try:
            query = f"""INSERT INTO {TABLE} VALUES (?, ?, ?, ?, ?, ?, ?)"""
            self.cursor.execute(query, (self.guild.id, None, '', self.config['Bot']['Prefix'], 1, 1, 1))
            self.conn.commit()
        except sqlite3.Error:
            pass

    def update_value(self, column, value):
        query = f"UPDATE {TABLE} SET {column} = ? WHERE id = ?"
        self.cursor.execute(query, (value, self.guild.id))
        self.conn.commit()
        self._get_server_info()

    def add_whitelist(self, channel):
        if channel.id in self.locked:
            return True

        self.locked.append(channel.id)

        query = f"UPDATE {TABLE} SET locked = ? WHERE id = ?"
        self.cursor.execute(query, (' '.join([str(channel_id) for channel_id in self.locked]), self.guild.id))
        self.conn.commit()
        self._get_server_info()
        return True

    def remove_whitelist(self, channel):
        if channel.id not in self.locked:
            return True

        self.locked.pop(self.locked.index(channel.id))

        query = f"UPDATE {TABLE} SET locked = ? WHERE id = ?"
        self.cursor.execute(query, (' '.join([str(channel_id) for channel_id in self.locked]), self.guild.id))
        self.conn.commit()
        self._get_server_info()
        return True

    def updatePrefix(self, prefix):
        query = f"UPDATE {TABLE} SET prefix = ? WHERE id = ?"
        self.cursor.execute(query, (prefix, self.guild.id))
        self.conn.commit()
        self._get_server_info()
