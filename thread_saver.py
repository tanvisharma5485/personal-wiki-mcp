from pathlib import Path
from datetime import datetime
import os

import psycopg2
from dotenv import load_dotenv


load_dotenv()


# --------------------------------------------------
# STORAGE SETTINGS
# --------------------------------------------------

THREADS_DIR = Path(
    os.getenv("THREADS_DIR", "threads")
)

SAVE_MARKDOWN = (
    os.getenv("SAVE_MARKDOWN", "true")
    .strip()
    .lower()
    in ("1", "true", "yes", "on")
)

if SAVE_MARKDOWN:
    THREADS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )


# --------------------------------------------------
# DATABASE CONNECTION
# --------------------------------------------------

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )


# --------------------------------------------------
# SAFE FILE NAME
# --------------------------------------------------

def make_safe_name(value: str) -> str:
    safe = ""

    for char in value.strip():
        if char.isalnum():
            safe += char
        elif char in (" ", "-", "_"):
            safe += "_"

    while "__" in safe:
        safe = safe.replace("__", "_")

    return safe.strip("_") or "thread"


# --------------------------------------------------
# GET EXISTING THREAD NAME
# --------------------------------------------------

def get_existing_thread_name(
    thread_id: str,
) -> str | None:

    conn = get_db_connection()

    try:
        cur = conn.cursor()

        cur.execute(
            """
            SELECT thread_name
            FROM threads
            WHERE thread_id = %s
            """,
            (thread_id,),
        )

        row = cur.fetchone()

        cur.close()

        if row:
            return row[0]

        return None

    finally:
        conn.close()


# --------------------------------------------------
# FIND EXISTING MARKDOWN FILE
# --------------------------------------------------

def find_existing_thread_file(
    thread_id: str,
) -> Path | None:

    if not SAVE_MARKDOWN:
        return None

    if not THREADS_DIR.exists():
        return None

    for file_path in THREADS_DIR.glob("*.md"):

        try:
            with file_path.open(
                "r",
                encoding="utf-8",
            ) as file:

                for _ in range(10):
                    line = file.readline()

                    if not line:
                        break

                    if (
                        line.strip()
                        == f"Thread ID: {thread_id}"
                    ):
                        return file_path

        except OSError:
            continue

    return None


# --------------------------------------------------
# DUPLICATE CHECK
# --------------------------------------------------

def message_already_exists(
    conn,
    thread_id: str,
    user_prompt: str,
    ai_response: str,
) -> bool:

    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT 1
            FROM thread_messages
            WHERE thread_id = %s
              AND user_prompt = %s
              AND ai_response = %s
            LIMIT 1
            """,
            (
                thread_id,
                user_prompt,
                ai_response,
            ),
        )

        return cur.fetchone() is not None

    finally:
        cur.close()


# --------------------------------------------------
# BUILD MARKDOWN FILE PATH
# --------------------------------------------------

def build_thread_file_path(
    user_name: str,
    thread_name: str,
    thread_id: str,
    created_at,
) -> Path:

    safe_user = make_safe_name(
        user_name
    )

    safe_thread = make_safe_name(
        thread_name
    )

    date_text = created_at.strftime(
        "%Y-%m-%d"
    )

    return THREADS_DIR / (
        f"{safe_user}-"
        f"{safe_thread}-"
        f"{thread_id}-"
        f"{date_text}.md"
    )


# --------------------------------------------------
# REBUILD MARKDOWN FROM POSTGRESQL
# --------------------------------------------------

def rebuild_thread_markdown(
    conn,
    thread_id: str,
) -> Path | None:

    if not SAVE_MARKDOWN:
        return None

    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT
                user_name,
                thread_name,
                created_at
            FROM threads
            WHERE thread_id = %s
            """,
            (thread_id,),
        )

        thread_row = cur.fetchone()

        if thread_row is None:
            return None

        user_name = thread_row[0]
        thread_name = thread_row[1]
        created_at = thread_row[2]

        cur.execute(
            """
            SELECT
                user_prompt,
                ai_response,
                created_at
            FROM thread_messages
            WHERE thread_id = %s
            ORDER BY id;
            """,
            (thread_id,),
        )

        messages = cur.fetchall()

    finally:
        cur.close()

    existing_file = find_existing_thread_file(
        thread_id
    )

    if existing_file is not None:
        file_path = existing_file
    else:
        file_path = build_thread_file_path(
            user_name=user_name,
            thread_name=thread_name,
            thread_id=thread_id,
            created_at=created_at,
        )

    created_text = created_at.strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    content = (
        f"# {user_name} - {thread_name}\n\n"
        f"Thread ID: {thread_id}\n\n"
        f"Created: {created_text}\n\n"
    )

    for (
        user_prompt,
        ai_response,
        message_created_at,
    ) in messages:

        content += (
            "## User\n\n"
            f"{user_prompt}\n\n"
            "## Assistant\n\n"
            f"{ai_response}\n\n"
            "---\n\n"
        )

    file_path.write_text(
        content,
        encoding="utf-8",
    )

    return file_path


# --------------------------------------------------
# SAVE THREAD MESSAGE
# --------------------------------------------------

def save_thread_message(
    user_name: str,
    thread_id: str,
    thread_name: str,
    user_prompt: str,
    ai_response: str,
) -> Path | None:

    user_name = user_name.strip()
    thread_id = thread_id.strip()
    thread_name = thread_name.strip()
    user_prompt = user_prompt.strip()
    ai_response = ai_response.strip()

    if not thread_id:
        raise ValueError(
            "thread_id cannot be empty."
        )

    if not thread_name:
        raise ValueError(
            "thread_name cannot be empty."
        )

    if not user_prompt:
        raise ValueError(
            "user_prompt cannot be empty."
        )

    if not ai_response:
        raise ValueError(
            "ai_response cannot be empty."
        )

    conn = get_db_connection()

    try:
        cur = conn.cursor()

        # ------------------------------------------
        # CREATE THREAD IF NEW
        # ------------------------------------------

        cur.execute(
            """
            INSERT INTO threads (
                thread_id,
                user_name,
                thread_name
            )
            VALUES (%s, %s, %s)
            ON CONFLICT (thread_id)
            DO NOTHING
            """,
            (
                thread_id,
                user_name,
                thread_name,
            ),
        )

        # ------------------------------------------
        # REUSE ORIGINAL THREAD INFORMATION
        # ------------------------------------------

        cur.execute(
            """
            SELECT
                user_name,
                thread_name
            FROM threads
            WHERE thread_id = %s
            """,
            (thread_id,),
        )

        row = cur.fetchone()

        if row:
            user_name = row[0]
            thread_name = row[1]

        # ------------------------------------------
        # DUPLICATE PROTECTION
        # ------------------------------------------

        if message_already_exists(
            conn,
            thread_id,
            user_prompt,
            ai_response,
        ):
            conn.commit()
            cur.close()

            return rebuild_thread_markdown(
                conn,
                thread_id,
            )

        # ------------------------------------------
        # SAVE TO POSTGRESQL
        # ------------------------------------------

        cur.execute(
            """
            INSERT INTO thread_messages (
                thread_id,
                user_prompt,
                ai_response
            )
            VALUES (%s, %s, %s)
            """,
            (
                thread_id,
                user_prompt,
                ai_response,
            ),
        )

        cur.execute(
            """
            UPDATE threads
            SET updated_at =
                CURRENT_TIMESTAMP
            WHERE thread_id = %s
            """,
            (thread_id,),
        )

        conn.commit()
        cur.close()

        # ------------------------------------------
        # BUILD / UPDATE MARKDOWN FROM DATABASE
        # ------------------------------------------

        return rebuild_thread_markdown(
            conn,
            thread_id,
        )

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()