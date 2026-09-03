import asyncio
import json

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


MCPS = {
    "MCP 1": {
        "url": "https://personal-wiki-mcp.onrender.com/mcp",
        "expected_tiers": [1, 2, 3],
        "expected_count": 104,
    },
    "MCP 2": {
        "url": "https://personal-wiki-mcp-tier2.onrender.com/mcp",
        "expected_tiers": [2, 3],
        "expected_count": 88,
    },
    "MCP 3": {
        "url": "https://personal-wiki-mcp-tier3.onrender.com/mcp",
        "expected_tiers": [3],
        "expected_count": 21,
    },
}


def extract_page_titles(result):
    """
    Extract list_wiki_pages result safely from the MCP SDK response.
    """

    # Preferred: structured MCP result
    structured = getattr(result, "structuredContent", None)

    if structured is not None:
        # Some MCP versions wrap the return value in {"result": ...}
        if isinstance(structured, dict):
            if "result" in structured:
                value = structured["result"]

                if isinstance(value, list):
                    return value

            # If another key contains the list, accept it.
            for value in structured.values():
                if isinstance(value, list):
                    return value

        elif isinstance(structured, list):
            return structured

    # Fallback to text content
    if not result.content:
        raise RuntimeError("list_wiki_pages returned no content.")

    page_text = result.content[0].text.strip()

    # Try JSON first
    try:
        value = json.loads(page_text)

        if isinstance(value, list):
            return value

        if isinstance(value, dict):
            if "result" in value and isinstance(value["result"], list):
                return value["result"]

            for item in value.values():
                if isinstance(item, list):
                    return item

    except json.JSONDecodeError:
        pass

    # FastMCP may render a Python list as text.
    # Import locally because this is only a fallback.
    import ast

    try:
        value = ast.literal_eval(page_text)

        if isinstance(value, list):
            return value

    except (ValueError, SyntaxError):
        pass

    raise RuntimeError(
        "Could not determine page list from MCP response.\n"
        f"Text response: {page_text[:500]!r}\n"
        f"Structured response: {structured!r}"
    )


async def test_mcp(name, config):
    url = config["url"]
    expected_tiers = config["expected_tiers"]
    expected_count = config["expected_count"]

    print()
    print("=" * 60)
    print(name)
    print(url)
    print("=" * 60)

    async with streamable_http_client(url) as (
        read_stream,
        write_stream,
        get_session_id,
    ):
        async with ClientSession(
            read_stream,
            write_stream,
        ) as session:

            await session.initialize()

            access = await session.call_tool(
                "get_mcp_access_info",
                arguments={},
            )

            pages = await session.call_tool(
                "list_wiki_pages",
                arguments={},
            )

            earth = await session.call_tool(
                "get_wiki_page",
                arguments={"title": "Earth"},
            )

            print("Access info:")
            print(access.content[0].text)

            page_titles = extract_page_titles(pages)

            print()
            print("Page count:")
            print(len(page_titles))

            print()
            print("Expected page count:")
            print(expected_count)

            if len(page_titles) == expected_count:
                print("COUNT CHECK: PASS")
            else:
                print("COUNT CHECK: FAIL")

            print()
            print("First 10 accessible pages:")

            for title in page_titles[:10]:
                print(f"- {title}")

            print()
            print("Earth access test:")
            print(earth.content[0].text)

            # Additional access validation
            if name == "MCP 1":
                if "Earth" in page_titles:
                    print("EARTH ACCESS CHECK: PASS")
                else:
                    print("EARTH ACCESS CHECK: FAIL")

            else:
                earth_response = earth.content[0].text

                if "No accessible knowledge found" in earth_response:
                    print("EARTH RESTRICTION CHECK: PASS")
                else:
                    print("EARTH RESTRICTION CHECK: FAIL")

            print()
            print(
                f"Expected tiers: {expected_tiers}"
            )


async def main():

    print()
    print("=" * 60)
    print("DEPLOYED MCP ACCESS VERIFICATION")
    print("=" * 60)

    for name, config in MCPS.items():

        try:
            await test_mcp(name, config)

        except Exception as e:

            print()
            print(f"{name} ERROR:")
            print(repr(e))

            # Show nested TaskGroup exceptions
            current = e
            level = 1

            while hasattr(current, "exceptions"):

                exceptions = current.exceptions

                if not exceptions:
                    break

                for i, sub_error in enumerate(exceptions, 1):
                    print(
                        f"  Level {level} sub-error {i}: "
                        f"{repr(sub_error)}"
                    )

                current = exceptions[0]
                level += 1

    print()
    print("=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

