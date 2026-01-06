import psycopg2.extras
from pkce import generate_code_verifier

from DB.db import connect


def db_new_user(id):
    code_verifier = generate_code_verifier(64)
    sql = f"""INSERT INTO users (vk_id, code_verifier) VALUES ({id}, '{code_verifier}');"""
    print(sql)
    conn = connect()
    conn.autocommit = True
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql)
        print(cur.rowcount)
        print(cur.rownumber)


def db_get_user(id):
    sql = f"""SELECT *, DATE_PART('YEAR',AGE(birthday)) as age FROM users WHERE vk_id = {id};"""
    print(sql)
    conn = connect()
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql)
        # print(cur.rowcount)
        if cur.rowcount:
            res = cur.fetchone()
            is_new = False
        else:
            db_new_user(id)
            res, is_new = db_get_user(id)
            is_new = True
    print(res)
    res = dict(res)
    # print(res)
    return res, is_new


def db_update_user(uid, fields):
    if not fields:
        return
    set_str = ""
    print(fields)
    for f in fields:
        set_str += f"{f['key']} = '{f['val']}' ,"
    sql = f"""UPDATE users SET {set_str[:-2]} WHERE vk_id = {uid};"""
    print(sql)
    conn = connect()
    conn.autocommit = True
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql)
        print(cur.rowcount)
        print(cur.rownumber)
