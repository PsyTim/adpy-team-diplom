# import psycopg2.extras
import os

PATH = "DB/"

try:
    from DB.db import connect
except:
    from db import connect


def recreate_tables(path=os.path.split(os.path.realpath(__file__))[0] + "/"):
    with connect() as conn:
        with conn.cursor() as cursor:

            with open(f"{path}create.sql", "r", encoding="utf-8") as file:
                sql = file.read()
                cursor.execute(sql)
    print("Database recreated successfully.")


if __name__ == "__main__":

    # Python program to get the
    # path of the script

    # Get the current working
    # directory (CWD)
    cwd = os.getcwd()
    print("Current Directory:", cwd)

    # Get the directory of
    # script
    script = os.path.realpath(__file__, strict=True)
    print("Sсript path:", script)
    PATH = ""
    recreate_tables(os.path.split(script)[0] + "/")
