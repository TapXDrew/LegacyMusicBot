import os
import sqlite3
import json

DATABASE = os.getcwd()+'/databases/permissions.db'
TABLE = 'UserPermissions'
perms = json.load(open(os.getcwd()+"/utils/permissions.json"))


def index_replace(text, index=0, replacement=''):
    return '%s%s%s' % (text[:index], replacement, text[index + 1:])


class User:
    def __init__(self, bot, ctx, user=None):
        self.bot = bot
        self.ctx = ctx
        self.user = ctx.author if not user else user

        self.conn = None

        try:
            self.conn = sqlite3.connect(DATABASE)
        except sqlite3.Error as e:
            print(e)
        self.cursor = self.conn.cursor()

        self._create_table()
        self._get_user_info()

    def _create_table(self):
        query = f"""CREATE TABLE IF NOT EXISTS {TABLE} (id BIGINT, g_id BIGINT, permissions TEXT)"""
        self.cursor.execute(query)
        self.conn.commit()

    def _get_user_info(self):
        query = f"SELECT * FROM {TABLE} WHERE id = ? AND g_id = ?"
        self.cursor.execute(query, (self.user.id, self.ctx.guild.id))
        info = self.cursor.fetchall()
        if info:
            self.id = info[0][0]
            self.perms = [item for item in info[0][2].split(" ")]
            self.permissions = info[0][2]
        else:
            self._create_user()
            self._get_user_info()

    def _create_user(self):
        try:
            query = f"""INSERT INTO {TABLE} VALUES (?, ?, ?)"""
            self.cursor.execute(query, (self.user.id, self.ctx.guild.id, ''))
            self.conn.commit()
        except sqlite3.Error:
            pass

    def update_value(self, column, value):
        query = f"UPDATE {TABLE} SET {column} = ? WHERE id = ?"
        self.cursor.execute(query, (value, self.user.id))
        self.conn.commit()
        self._get_user_info()

    def add_permission(self, permission):
        if permission.lower() not in perms['Permissions']['CommandBypasses'].keys():
            return False
        if permission.lower() in self.perms:
            return True

        new_perms = (self.permissions + ' ' + permission.lower()) if len(self.permissions) > 2 else permission.lower()

        query = f"UPDATE {TABLE} SET permissions = ? WHERE id = ?"
        self.cursor.execute(query, (new_perms, self.user.id))
        self.conn.commit()
        self._get_user_info()
        return True
