import os
import sqlite3

DATABASE = os.getcwd()+'/bot/databases/donations.db'
TABLE = 'DataLogs'


class Donation:
    def __init__(self):
        self.txn_id = None
        self.buyer_email = None
        self.price = None
        self.currency = None
        self.buyer_id = None
        self.item_id = None
        self.guild_id = None
        self.recurring = None
        self.status = None

        self.conn = None

        try:
            self.conn = sqlite3.connect(DATABASE)
        except sqlite3.Error as e:
            print(e)
        self.cursor = self.conn.cursor()

        self._create_table()

    def _create_table(self):
        query = f"""CREATE TABLE IF NOT EXISTS {TABLE} (txn_id TEXT, buyer_email TEXT, price TEXT, currency TEXT, buyer_id TEXT, item_id TEXT, guild_id TEXT, recurring BOOLEAN, status TEXT)"""
        self.cursor.execute(query)
        self.conn.commit()

    def get_info(self, txn_id):
        query = f"SELECT * FROM {TABLE} WHERE txn_id = ?"
        self.cursor.execute(query, (txn_id,))
        info = self.cursor.fetchall()
        if info:
            self.txn_id = info[0][0]
            self.buyer_email = info[0][1]
            self.price = info[0][2]
            self.currency = info[0][3]
            self.buyer_id = info[0][4]
            self.item_id = info[0][5]
            self.guild_id = info[0][6]
            self.recurring = info[0][7]
            self.status = info[0][8]

            return info
        else:
            return False

    def listen(self):
        query = f"SELECT * FROM {TABLE}"
        self.cursor.execute(query)
        info = self.cursor.fetchall()
        return info

    def create_data(self, txn_id, buyer_email, price, currency, buyer_id, role_id, guild_id, recurring, status):
        query = f"""INSERT INTO {TABLE} VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"""
        self.cursor.execute(query, (txn_id, buyer_email, price, currency, buyer_id, role_id, guild_id, recurring, status))
        self.conn.commit()


class Vote:
    pass
