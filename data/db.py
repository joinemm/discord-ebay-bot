import sqlite3
from datetime import datetime


SQLDATABASE = 'data/database.db'


def query(command, parameters=()):
    connection = sqlite3.connect(SQLDATABASE)
    cursor = connection.cursor()
    cursor.execute(command, parameters)
    data = cursor.fetchall()
    if len(data) == 0:
        return None
    result = data
    connection.close()
    return result


def execute(command, parameters=()):
    connection = sqlite3.connect(SQLDATABASE)
    cursor = connection.cursor()
    cursor.execute(command, parameters)
    connection.commit()
    connection.close()


def get_keywords():
    data = query("""SELECT DISTINCT keyword FROM keywords""")
    return data


def add_keyword(guild_id, channel_id, keyword, is_dm):
    execute("""REPLACE INTO keywords (guild_id, channel_id, keyword, added_on, is_dm) VALUES (?, ?, ?, ?, ?)""",
            (guild_id, channel_id, keyword, datetime.now().timestamp(), 1 if is_dm else None))


def remove_keyword(channel_id, keyword):
    execute("""DELETE FROM keywords WHERE channel_id = ? AND keyword = ?""",
            (channel_id, keyword))


def last_scrape_for(keyword):
    data = query("""SELECT timestamp FROM keywords WHERE keyword = ?""", (keyword,))
    return data[0][0] if data is not None else None


def update_timestamp(timestamp, keyword):
    execute("""UPDATE keywords SET timestamp = ? WHERE keyword = ?""",
            (timestamp, keyword))
