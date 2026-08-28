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


# --------------------------------------------------
# DATABASE CONNECTION
# --------------------------------------------------

def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "personal_wiki"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD"),
    )


# --------------------------------------------------
# TIER ACCESS
# --------------------------------------------------

def get_allowed_tiers() -> list[int]:
    """
    Read allowed tiers from MCP_ALLOWED_TIERS.

    Examples:

    MCP 1:
    MCP_ALLOWED_TIERS=1,2,3

    MCP 2:
    MCP_ALLOWED_TIERS=2,3

    MCP 3:
    MCP_ALLOWED_TIERS=3

    If MCP_ALLOWED_TIERS is not set,
    access defaults to all tiers (1,2,3).
    """

    raw = os.getenv("MCP_ALLOWED_TIERS", "1,2,3")

    allowed = []

    for value in raw.split(","):
        value = value.strip()

        if value:
            allowed.append(int(value))

    return allowed


def tier_filter_sql():
    """
    Build the PostgreSQL tier filter and parameters.
    """

    allowed_tiers = get_allowed_tiers()

    placeholders = ", ".join(["%s"] * len(allowed_tiers))

    return f"tier IN ({placeholders})", allowed_tiers


# --------------------------------------------------
# MCP TOOL: LIST WIKI PAGES
# --------------------------------------------------

@mcp.tool()
def list_wiki_pages() -> list[str]:
    """
    Return wiki page titles accessible to this MCP.
    """

    conn = get_connection()
    cur = conn.cursor()

    tier_sql, tier_params = tier_filter_sql()

    cur.execute(
        f"""
        SELECT title
        FROM wiki_pages
        WHERE {tier_sql}
        ORDER BY title;
        """,
        tier_params,
    )

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return [row[0] for row in rows]


# --------------------------------------------------
# MCP TOOL: GET WIKI PAGE
# --------------------------------------------------

@mcp.tool()
def get_wiki_page(title: str) -> str:
    """
    Return full Markdown content of a page
    only if this MCP has access to its tier.
    """

    conn = get_connection()
    cur = conn.cursor()

    tier_sql, tier_params = tier_filter_sql()

    cur.execute(
        f"""
        SELECT content
        FROM wiki_pages
        WHERE LOWER(title) = LOWER(%s)
          AND {tier_sql};
        """,
        [title] + tier_params,
    )

    row = cur.fetchone()

    cur.close()
    conn.close()

    if row is None:
        return f"No accessible wiki page found for: {title}"

    return row[0]


# --------------------------------------------------
# MCP TOOL: SEARCH WIKI
# --------------------------------------------------

@mcp.tool()
def search_wiki(query: str, limit: int = 10) -> list[dict]:
    """
    Search titles and content only within tiers
    accessible to this MCP.
    """

    conn = get_connection()
    cur = conn.cursor()

    search_term = f"%{query}%"

    tier_sql, tier_params = tier_filter_sql()

    cur.execute(
        f"""
        SELECT title, LEFT(content, 500)
        FROM wiki_pages
        WHERE (
            title ILIKE %s
            OR content ILIKE %s
        )
        AND {tier_sql}
        ORDER BY
            CASE WHEN title ILIKE %s THEN 0 ELSE 1 END,
            title
        LIMIT %s;
        """,
        [
            search_term,
            search_term,
            *tier_params,
            search_term,
            limit,
        ],
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


# --------------------------------------------------
# MCP TOOL: ACCESS INFORMATION
# --------------------------------------------------

@mcp.tool()
def get_mcp_access_info() -> dict:
    """
    Show which database tiers this MCP can access.
    """

    allowed_tiers = get_allowed_tiers()

    return {
        "allowed_tiers": allowed_tiers,
        "description": f"This MCP can access tiers: {allowed_tiers}",
    }


# --------------------------------------------------
# START MCP SERVER
# --------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
