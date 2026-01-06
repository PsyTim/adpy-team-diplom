from DB.access import Access
import psycopg2.extras


def connect():
    conn = psycopg2.connect(
        host=Access.host,
        port=Access.port,
        database=Access.database,
        user=Access.user,
        password=Access.password,
    )
    return conn
