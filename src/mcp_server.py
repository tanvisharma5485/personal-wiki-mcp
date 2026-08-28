import os
import psycopg2
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

port = int(os.getenv("PORT", "8000"))

mcp = FastMCP(
    "personal-wiki",
    host="0.0.0.0",
    port=port,
)


def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "personal_wiki"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD"),
    )


@mcp.tool()
def list_wiki_pages() -> list[str]:
    """Return all available wiki page titles."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT title FROM wiki_pages ORDER BY title;")
    rows = cur.fetchall()

    cur.close()
    conn.close()

    return [row[0] for row in rows]


@mcp.tool()
def get_wiki_page(title: str) -> str:
    """Return the full Markdown content of a wiki page by title."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT content FROM wiki_pages WHERE LOWER(title) = LOWER(%s);",
        (title,),
    )

    row = cur.fetchone()

    cur.close()
    conn.close()

    if row is None:
        return f"No wiki page found for: {title}"

    return row[0]


@mcp.tool()
def search_wiki(query: str, limit: int = 10) -> list[dict]:
    """Search wiki titles and Markdown content using PostgreSQL text matching."""
    conn = get_connection()
    cur = conn.cursor()

    search_term = f"%{query}%"

    cur.execute(
        """
        SELECT title, LEFT(content, 500)
        FROM wiki_pages
        WHERE title ILIKE %s
           OR content ILIKE %s
        ORDER BY
            CASE WHEN title ILIKE %s THEN 0 ELSE 1 END,
            title
        LIMIT %s;
        """,
        (search_term, search_term, search_term, limit),
    )

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return [
        {
            "title": title,
            "preview": preview,
        }
        for title, preview in rows
    ]


if __name__ == "__main__":
    mcp.run(transport="streamable-http")