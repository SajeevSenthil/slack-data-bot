import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


def run_query(sql):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    cur.execute(sql)

    rows = cur.fetchall()
    columns = [desc[0] for desc in cur.description]

    cur.close()
    conn.close()

    return columns, rows