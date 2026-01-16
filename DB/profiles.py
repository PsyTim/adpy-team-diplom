import psycopg2.extras
from pkce import generate_code_verifier

from DB.db import connect

# db_add_profiles(
#     to_insert,
#     {"domain", "birthday", "gender", "city_id", "city"},
# )


def db_add_profiles(user, profiles, update=[]):
    fields = list(profiles[0].keys())
    vals_str = ""
    for profile in profiles:
        val_str = "("
        for field in fields:
            val_str += f"'{profile[field]}', "
        val_str = val_str[:-2] + "), "
        vals_str += val_str + "\n"
    vals_str = vals_str[:-3]
    sql = f"""INSERT INTO profiles ({", ".join(fields)})\nVALUES {vals_str}"""
    if update:
        conflict_str = "\nON CONFLICT (vk_id) DO UPDATE SET\n"
        for field in update:
            conflict_str += f"{field} = EXCLUDED.{field}, \n"
    sql += conflict_str[:-3] + "\nRETURNING id;;"
    # print(sql)
    conn = connect()
    conn.autocommit = False
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql)
        # print(cur.rowcount)
        # print(cur.rownumber)
        res = cur.fetchall()
        # print(res)
        sql = f"""INSERT INTO users_profiles (user_id, profile_id) 
        VALUES"""

        # ({user.id}, {profile_id}, NOW())
        for r in res:
            sql += f"""({user.id}, {r["id"]}),\n"""
        sql = sql[:-2]
        sql += f"""\nON CONFLICT (user_id, profile_id) DO NOTHING"""
        # print(sql)
        # with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql)
        # print(cur.rowcount)
        # print(cur.rownumber)
        # res = cur.fetchall()
        # print(res)
        conn.commit()


def db_profile_to_fav(user, profile_id):
    sql = f"""INSERT INTO users_profiles (user_id, profile_id, viewed, favorit) 
        VALUES ({user.id}, {profile_id}, NOW(), NOW()) 
        ON CONFLICT (user_id, profile_id) 
        DO UPDATE SET viewed = NOW(), favorit = NOW();"""
    conn = connect()
    conn.autocommit = True
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql)
        # print(cur.rowcount)
        # print(cur.rownumber)


def db_profile_set_blacklisted(user, profile_id):
    sql = f"""INSERT INTO users_profiles (user_id, profile_id, viewed, blacklisted) 
        VALUES ({user.id}, {profile_id}, NULL, NOW()) 
        ON CONFLICT (user_id, profile_id) 
        DO UPDATE SET viewed = NULL, blacklisted = NOW();"""
    conn = connect()
    conn.autocommit = True
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql)
        # print(cur.rowcount)
        # print(cur.rownumber)


def db_profile_set_viewed(user, profile_id):
    sql = f"""INSERT INTO users_profiles (user_id, profile_id, viewed) 
        VALUES ({user.id}, {profile_id}, NOW()) 
        ON CONFLICT (user_id, profile_id) 
        DO UPDATE SET viewed = NOW();"""
    conn = connect()
    conn.autocommit = True
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql)
        # print(cur.rowcount)
        # print(cur.rownumber)


def db_profile_clean_bl(user):
    sql = f"""UPDATE users_profiles set viewed = NULL, blacklisted = NULL
            FROM (SELECT profiles.id as p_id FROM profiles
                LEFT JOIN users_profiles ON profiles.id = users_profiles.profile_id AND users_profiles.user_id = {user.id}
                WHERE {format_filter_where(user)} AND users_profiles.blacklisted IS NOT NULL 
                ORDER BY profiles.id
            ) AS subquery
            WHERE users_profiles.profile_id = subquery.p_id
        ;"""
    conn = connect()
    conn.autocommit = True
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql)
        # print(cur.rowcount)
        # print(cur.rownumber)


def db_profile_clean_viewed(user):
    sql = f"""UPDATE users_profiles set viewed = NULL
            FROM (SELECT profiles.id as p_id FROM profiles
                LEFT JOIN users_profiles ON profiles.id = users_profiles.profile_id AND users_profiles.user_id = {user.id}
                WHERE {format_filter_where(user)} AND users_profiles.blacklisted IS NULL and users_profiles.viewed IS NOT NULL 
                ORDER BY profiles.id
            ) AS subquery
            WHERE users_profiles.profile_id = subquery.p_id
        ;"""
    conn = connect()
    conn.autocommit = True
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql)
        # print(cur.rowcount)
        # print(cur.rownumber)


def db_profile_del(user, id):
    sql = f"""DELETE FROM users_profiles WHERE profile_id={id};"""
    conn = connect()
    conn.autocommit = False
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql)
        # print(cur.rowcount)
        # print(cur.rownumber)
        sql = f"""DELETE FROM profiles WHERE id={id};"""
        cur.execute(sql)
        # print(cur.rowcount)
        # print(cur.rownumber)
        conn.commit()


def format_filter_where_id(user):
    return f"{user.id} = users_profiles.user_id"


def format_filter_where(user):
    res = f"{user.filter_age_to} >= DATE_PART('YEAR',AGE(birthday)) AND DATE_PART('YEAR',AGE(birthday)) >= {user.filter_age_from} AND city_id={user.filter_city_id}"
    if user.filter_gender in (1, 2):
        res += f" AND gender={user.filter_gender}"
    return res


def db_count_filter_profiles(user):
    sql = f"""SELECT COUNT(*) FROM profiles
        LEFT JOIN users_profiles on profiles.id = users_profiles.profile_id AND users_profiles.user_id = {user.id}
        WHERE {format_filter_where(user)} and users_profiles.blacklisted IS null and users_profiles.viewed IS null;"""
    # print(sql)
    conn = connect()
    res = None
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql)
        # print(cur.rowcount)
        if cur.rowcount:
            res = cur.fetchone()
            res = dict(res)
    # print(res)
    return res


def db_count_filter_fav(user):
    sql = f"""SELECT COUNT(*) FROM profiles
        LEFT JOIN users_profiles on profiles.id = users_profiles.profile_id AND users_profiles.user_id = {user.id}
        WHERE {format_filter_where(user)} and users_profiles.blacklisted IS null and users_profiles.favorit IS NOT null;"""
    # print(sql)
    conn = connect()
    res = None
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql)
        # print(cur.rowcount)
        if cur.rowcount:
            res = cur.fetchone()
            res = dict(res)
    # print(res)
    return res


def count_fav_total(user):
    sql = f"""SELECT COUNT(*) FROM profiles
        LEFT JOIN users_profiles on profiles.id = users_profiles.profile_id AND users_profiles.user_id = {user.id}
        WHERE {format_filter_where_id(user)} and users_profiles.blacklisted IS null and users_profiles.favorit IS NOT null;"""
    # print(sql)
    conn = connect()
    res = None
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql)
        # print(cur.rowcount)
        if cur.rowcount:
            res = cur.fetchone()
            res = dict(res)
    # print(res)
    return res


def db_get_profile(user):
    sql = f"""SELECT profiles.*, DATE_PART('YEAR',AGE(birthday)) as age FROM profiles
        LEFT JOIN users_profiles on profiles.id = users_profiles.profile_id AND users_profiles.user_id = {user.id}
        where {format_filter_where(user)} and users_profiles.blacklisted IS NULL and users_profiles.viewed IS NULL ORDER BY profiles.id LIMIT 1;"""
    # print(sql)
    conn = connect()
    res = None
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql)
        # print(cur.rowcount)
        if cur.rowcount:
            res = cur.fetchone()
            res = dict(res)
    # print(res)
    return res


def get_fav(user):
    sql = f"""SELECT profiles.*, DATE_PART('YEAR',AGE(birthday)) as age, users_profiles.favorit FROM profiles
        LEFT JOIN users_profiles on profiles.id = users_profiles.profile_id AND users_profiles.user_id = {user.id}
        where {format_filter_where(user)} and users_profiles.blacklisted IS NULL and users_profiles.favorit IS NOT NULL ORDER BY users_profiles.favorit LIMIT 1;"""
    # print(sql)
    conn = connect()
    res = None
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql)
        # print(cur.rowcount)
        if cur.rowcount:
            res = cur.fetchone()
            res = dict(res)
    # print(res)
    return res


def db_count_filter_profiles_blacklisted(user):
    sql = f"""SELECT COUNT(*) FROM profiles
        LEFT JOIN users_profiles on profiles.id = users_profiles.profile_id AND users_profiles.user_id = {user.id}
        where {format_filter_where(user)} AND users_profiles.blacklisted IS NOT NULL;"""
    # print(sql)
    conn = connect()
    res = None
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql)
        # print(cur.rowcount)
        if cur.rowcount:
            res = cur.fetchone()
            res = dict(res)
    # print(res)
    return res


def db_count_filter_profiles_viewed(user):
    sql = f"""SELECT COUNT(*) FROM profiles
        LEFT JOIN users_profiles on profiles.id = users_profiles.profile_id AND users_profiles.user_id = {user.id}
        where {format_filter_where(user)} AND users_profiles.viewed IS NOT NULL;"""
    # print(sql)
    conn = connect()
    res = None
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql)
        # print(cur.rowcount)
        if cur.rowcount:
            res = cur.fetchone()
            res = dict(res)
    # print(res)
    return res
