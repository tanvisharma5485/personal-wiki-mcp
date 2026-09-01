import os

import psycopg2
from dotenv import load_dotenv


load_dotenv()


def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )


def list_threads():
    conn = get_db_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    t.thread_id,
                    t.thread_name,
                    t.user_name,
                    t.created_at,
                    t.updated_at,
                    COUNT(m.id) AS message_count
                FROM threads t
                LEFT JOIN thread_messages m
                    ON t.thread_id = m.thread_id
                GROUP BY
                    t.thread_id,
                    t.thread_name,
                    t.user_name,
                    t.created_at,
                    t.updated_at
                ORDER BY t.updated_at DESC;
                """
            )

            rows = cursor.fetchall()

    finally:
        conn.close()

    if not rows:
        print("No saved threads found.")
        return

    print()
    print("=" * 90)
    print("SAVED THREADS")
    print("=" * 90)

    for row in rows:
        (
            thread_id,
            thread_name,
            user_name,
            created_at,
            updated_at,
            message_count,
        ) = row

        print()
        print(f"Thread Name : {thread_name}")
        print(f"Thread ID   : {thread_id}")
        print(f"User        : {user_name}")
        print(f"Messages    : {message_count}")
        print(f"Created     : {created_at}")
        print(f"Updated     : {updated_at}")
        print("-" * 90)


if __name__ == "__main__":
    list_threads()