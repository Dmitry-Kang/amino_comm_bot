import threading
import sqlite3


conn = sqlite3.connect("db.db")
# conn.set_client_encoding("utf-8")
cursor = conn.cursor()

lock = threading.RLock()

def init(bot):
    pass

## KICKED_USERS
def add_kicked_users(userid):
    lock.acquire()
    try:
        global conn, cursor
        cursor.execute("INSERT INTO kicked_users(userid) values (\'{}\');".format(str(userid)))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise Exception(str(e))
    finally:
        lock.release()

def get_kicked_users(userid = None):
    try:
        global conn, cursor
        res = None
        if (userid is not None):
            res = cursor.execute("SELECT (userid) FROM kicked_users WHERE userid = \'{}\';".format(str(userid)))
        else:
            res = cursor.execute("SELECT (userid) FROM kicked_users;")
        rows = cursor.fetchall()
    except Exception as e:
        raise Exception(str(e))
    finally:
        pass
    res = []
    for x in rows:
        res.append(x[0])
    return res

def delete_kicked_users(userid):
    lock.acquire()
    try:
        global conn, cursor
        cursor.execute("DELETE FROM kicked_users WHERE userid = \'{}\';".format(str(userid)))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise Exception(str(e))
    finally:
        lock.release()

## STRIKED_USERS
# date "0" = пермач, any = до какойто даты
def add_striked_users(userid, date = 0):
    lock.acquire()
    try:
        global conn, cursor
        cursor.execute("INSERT INTO striked_users(userid,date) values (\'{}\', \'{}\');".format(str(userid), str(date)))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise Exception(str(e))
    finally:
        lock.release()

def get_striked_users(userid = None):
    try:
        global conn, cursor
        res = None
        if (userid is not None):
            res = cursor.execute("SELECT (userid,date) FROM striked_users WHERE userid = \'{}\';".format(str(userid)))
        else:
            res = cursor.execute("SELECT (userid,date) FROM striked_users;")
        rows = cursor.fetchall()
    except Exception as e:
        raise Exception(str(e))
    finally:
        pass
    res = []
    for x in rows:
        res.append({"userid": x[0], "date": x[1]})
    return res

def delete_striked_users(userid):
    lock.acquire()
    try:
        global conn, cursor
        cursor.execute("DELETE FROM striked_users WHERE userid = \'{}\';".format(str(userid)))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise Exception(str(e))
    finally:
        lock.release()

def update_striked_users(userid, date = 0):
    lock.acquire()
    try:
        global conn, cursor
        cursor.execute("UPDATE striked_users SET date = \'{}\' WHERE userid = \'{}\';".format(str(date), str(userid)))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise Exception(str(e))
    finally:
        lock.release()

## WHITELIST
def add_whitelist(userid):
    lock.acquire()
    try:
        global conn, cursor
        cursor.execute("INSERT INTO whitelist(userid) values (\'{}\');".format(str(userid)))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise Exception(str(e))
    finally:
        lock.release()

def get_whitelist(userid = None):
    try:
        global conn, cursor
        res = None
        if (userid is not None):
            res = cursor.execute("SELECT (userid) FROM whitelist WHERE userid = \'{}\';".format(str(userid)))
        else:
            res = cursor.execute("SELECT (userid) FROM whitelist;")
        rows = cursor.fetchall()
    except Exception as e:
        raise Exception(str(e))
    finally:
        pass
    res = []
    for x in rows:
        res.append(x[0])
    return res

def delete_whitelist(userid):
    lock.acquire()
    try:
        global conn, cursor
        cursor.execute("DELETE FROM whitelist WHERE userid = \'{}\';".format(str(userid)))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise Exception(str(e))
    finally:
        lock.release()