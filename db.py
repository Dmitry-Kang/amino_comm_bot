import threading
import sqlite3


conn = sqlite3.connect("db.db")
conn.set_client_encoding("utf-8")
cursor = conn.cursor()

lock = threading.RLock()

def init(bot):
    pass
