from pathlib import Path
import os
import psycopg2
from dotenv import load_dotenv


# Load environment variables from .env
load_dotenv()

WIKI_DIR = Path("wiki")


def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "personal_wiki"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD"),
    )


def ingest_wiki():
    markdown_files = list(WIKI_DIR.rglob("*.md"))

    print(f"Found {len(markdown_files)} wiki pages.")

    connection = get_connection()
    cursor = connection.cursor()

    for file_path in markdown_files:
        content = file_path.read_text(encoding="utf-8-sig")

        title = file_path.stem
        relative_path = str(file_path.as_posix())

        cursor.execute(
            """
            INSERT INTO wiki_pages (title, file_path, content)
            VALUES (%s, %s, %s)
            ON CONFLICT (title)
            DO UPDATE SET
                file_path = EXCLUDED.file_path,
                content = EXCLUDED.content,
                updated_at = CURRENT_TIMESTAMP;
            """,
            (title, relative_path, content),
        )

        print(f"Ingested: {title}")

    connection.commit()

    cursor.close()
    connection.close()

    print("\nWiki ingestion completed successfully.")


if __name__ == "__main__":
    ingest_wiki()