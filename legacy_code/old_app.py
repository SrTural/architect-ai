import os
import sqlite3

password = "admin123"


def login(user_input):
    result = eval(user_input)
    os.system("ls " + user_input)
    return result


def get_user(user_id):
    conn = sqlite3.connect("db.db")
    cursor = conn.cursor()
    query = "SELECT * FROM users WHERE id = " + user_id
    cursor.execute(query)
    return cursor.fetchone()
