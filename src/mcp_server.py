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
    List the knowledge topics accessible through this Personal Wiki MCP.

    Use this tool only when it is useful to discover which topics are
    available. For normal user questions, prefer search_wiki instead of
    listing pages first.
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
    Retrieve the full useful knowledge content for one specific wiki topic.

    Use this tool when the user explicitly asks for a complete page/topic,
    or when search_wiki does not provide enough information.

    For ordinary questions such as "What is the Kuiper Belt?" or
    "How did the Kuiper Belt form?", prefer search_wiki.

    The returned content is knowledge for answering the user. Do not treat
    wiki navigation, internal page relationships, source sections, file
    paths, or note structure as part of the answer unless the user
    specifically asks about them.
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

    content = row[0]

    # Remove metadata/navigation sections.
    for section in [
        "## Related Topics",
        "## Sources",
        "## Summary",
    ]:
        if section in content:
            content = content.split(section, 1)[0]

    # Convert Obsidian-style links into normal text.
    content = content.replace("[[", "").replace("]]", "")

    return content.strip()


# --------------------------------------------------
# MCP TOOL: SEARCH WIKI
# --------------------------------------------------

@mcp.tool()
def search_wiki(query: str, limit: int = 10) -> list[dict]:
    """
    Primary question-answering retrieval tool for the Personal Wiki.

    Use this tool for normal natural-language user questions. Pass the
    user's actual question or topic as the query.

    Examples:
    - "What is the Kuiper Belt?"
    - "How did the Kuiper Belt form?"
    - "What causes auroras?"
    - "Difference between the Kuiper Belt and Oort Cloud"

    The tool returns relevant knowledge excerpts from accessible wiki
    content. General topic questions return broad useful information,
    while specific questions prefer the most relevant section.

    Use the retrieved knowledge to answer the user's exact question
    directly and in detail.

    Do not add wiki-management commentary such as page names, internal
    links, related-topic navigation, file paths, source-section metadata,
    or statements like "here is the wiki page" unless the user explicitly
    asks for that information.
    """

    conn = get_connection()
    cur = conn.cursor()

    tier_sql, tier_params = tier_filter_sql()

    stop_words = {
        "the",
        "and",
        "for",
        "with",
        "from",
        "what",
        "when",
        "where",
        "which",
        "who",
        "why",
        "how",
        "about",
        "into",
        "does",
        "did",
        "was",
        "were",
        "are",
        "is",
        "of",
        "to",
        "in",
        "on",
        "a",
        "an",
    }

    words = [
        word.strip(".,?!:;()[]{}").lower()
        for word in query.split()
        if (
            len(word.strip(".,?!:;()[]{}")) >= 3
            and word.strip(".,?!:;()[]{}").lower()
            not in stop_words
        )
    ]

    if not words:
        words = [query.lower()]

    # A page only needs to match one important query word.
    conditions = []
    params = []

    for word in words:
        search_term = f"%{word}%"

        conditions.append(
            "(title ILIKE %s OR content ILIKE %s)"
        )

        params.extend(
            [
                search_term,
                search_term,
            ]
        )

    word_sql = " OR ".join(conditions)

    cur.execute(
        f"""
        SELECT title, content
        FROM wiki_pages
        WHERE ({word_sql})
          AND {tier_sql};
        """,
        [
            *params,
            *tier_params,
        ],
    )

    rows = cur.fetchall()

    cur.close()
    conn.close()

    ranked_results = []

    for title, content in rows:

        clean_content = content

        # Remove metadata/navigation sections.
        for section in [
            "## Related Topics",
            "## Sources",
            "## Summary",
        ]:
            if section in clean_content:
                clean_content = clean_content.split(
                    section,
                    1,
                )[0]

        # Convert Obsidian links to readable text.
        clean_content = clean_content.replace(
            "[[",
            "",
        ).replace(
            "]]",
            "",
        )

        lower_title = title.lower()
        lower_content = clean_content.lower()

        score = 0

        # Title matches are much more important
        # than body matches.
        for word in words:

            if word in lower_title:
                score += 20

            if word in lower_content:
                score += 2

        # Strong bonus when multiple query concepts
        # occur in the title.
        title_matches = sum(
            1
            for word in words
            if word in lower_title
        )

        score += title_matches * 10

        # --------------------------------------------------
        # QUESTION-SPECIFIC EXCERPT SELECTION
        # --------------------------------------------------

        # Words already represented by the page title
        # identify the topic.
        #
        # Remaining words represent what the user
        # specifically wants to know about that topic.
        focus_words = [
            word
            for word in words
            if word not in lower_title
        ]

        # --------------------------------------------------
        # GENERAL TOPIC QUESTION
        # --------------------------------------------------

        # Example:
        #
        # "What is the Kuiper Belt?"
        #
        # After stop-word removal:
        #
        # ["kuiper", "belt"]
        #
        # Both words are already represented by the title,
        # so return the beginning of the page.
        if not focus_words:

            excerpt = clean_content[:2500].strip()

        # --------------------------------------------------
        # SPECIFIC QUESTION
        # --------------------------------------------------

        else:

            lines = clean_content.splitlines()

            best_heading_index = None
            best_heading_score = 0

            # Prefer Markdown headings matching the
            # question-specific concepts.
            for i, line in enumerate(lines):

                stripped = line.strip()

                if not stripped.startswith("#"):
                    continue

                lower_heading = stripped.lower()

                heading_score = sum(
                    1
                    for word in focus_words
                    if word in lower_heading
                )

                if heading_score > best_heading_score:

                    best_heading_score = heading_score
                    best_heading_index = i

            # --------------------------------------------------
            # MATCHING MARKDOWN SECTION FOUND
            # --------------------------------------------------

            if (
                best_heading_index is not None
                and best_heading_score > 0
            ):

                section_lines = []

                for line in lines[best_heading_index:]:

                    # Stop when the next H2 section begins.
                    if (
                        section_lines
                        and line.startswith("## ")
                    ):
                        break

                    section_lines.append(line)

                excerpt = "\n".join(
                    section_lines
                ).strip()

            # --------------------------------------------------
            # NO MATCHING HEADING
            # --------------------------------------------------

            else:

                positions = [
                    lower_content.find(word)
                    for word in focus_words
                    if lower_content.find(word) != -1
                ]

                if positions:

                    match_index = min(positions)

                    start = max(
                        0,
                        match_index - 500,
                    )

                    end = min(
                        len(clean_content),
                        match_index + 2000,
                    )

                    excerpt = clean_content[
                        start:end
                    ].strip()

                else:

                    excerpt = clean_content[
                        :2000
                    ].strip()

        # IMPORTANT:
        # This stays outside the focus_words if/else
        # so both general and specific questions
        # are added to the results.
        ranked_results.append(
            {
                "title": title,
                "excerpt": excerpt,
                "_score": score,
            }
        )

    # --------------------------------------------------
    # RANK RESULTS
    # --------------------------------------------------

    ranked_results.sort(
        key=lambda item: (
            -item["_score"],
            item["title"],
        )
    )

    final_results = ranked_results[:limit]

    # Ranking score is only for internal use.
    for item in final_results:
        item.pop("_score", None)

    return final_results


# --------------------------------------------------
# MCP TOOL: ACCESS INFORMATION
# --------------------------------------------------

@mcp.tool()
def get_mcp_access_info() -> dict:
    """
    Return the database tiers available to this MCP instance.

    This is an administrative/access-information tool and normally should
    not be used for answering ordinary knowledge questions.
    """

    allowed_tiers = get_allowed_tiers()

    return {
        "allowed_tiers": allowed_tiers,
        "description": (
            f"This MCP can access tiers: "
            f"{allowed_tiers}"
        ),
    }


# --------------------------------------------------
# START MCP SERVER
# --------------------------------------------------

if __name__ == "__main__":
    mcp.run(
        transport="streamable-http"
    )
