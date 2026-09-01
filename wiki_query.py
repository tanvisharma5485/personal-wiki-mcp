from pathlib import Path
import argparse
import subprocess
import uuid

from thread_saver import (
    save_thread_message,
    get_existing_thread_name,
)


WIKI_DIR = Path("wiki")
AGENTS_FILE = Path("AGENTS.md")

CODEX_CMD = r"C:\Users\Tanvi\AppData\Roaming\npm\codex.cmd"


def main():
    parser = argparse.ArgumentParser(
        description="Query the Personal Wiki and automatically save the conversation."
    )

    parser.add_argument(
        "question",
        nargs="+",
        help="Question to ask the Personal Wiki",
    )

    parser.add_argument(
        "--user-name",
        default="Tanvi",
        help="Name of the user",
    )

    parser.add_argument(
        "--thread-id",
        default=None,
        help="Existing thread ID. If omitted, a new thread ID is generated.",
    )

    parser.add_argument(
        "--thread-name",
        default=None,
        help="Optional thread name.",
    )

    args = parser.parse_args()

    question = " ".join(args.question).strip()

    if not question:
        print("Question cannot be empty.")
        return

    # -----------------------------------------
    # 1. THREAD ID
    # -----------------------------------------

    if args.thread_id:
        thread_id = args.thread_id
    else:
        thread_id = str(uuid.uuid4())

    # -----------------------------------------
    # 2. THREAD NAME
    # -----------------------------------------

    existing_thread_name = None

    if args.thread_id:
        existing_thread_name = get_existing_thread_name(thread_id)

    if existing_thread_name:
        thread_name = existing_thread_name

    elif args.thread_name:
        thread_name = args.thread_name

    else:
        words = question.split()
        thread_name = " ".join(words[:6])

        if len(words) > 6:
            thread_name += "..."

    # -----------------------------------------
    # 3. BUILD WIKI QUERY PROMPT
    # -----------------------------------------

    prompt = f"""
Read AGENTS.md first and follow its rules.

Answer the following question using ONLY knowledge available inside wiki/.

QUESTION:
{question}

QUERY RULES:

1. Start from wiki/index.md.

2. Identify the most relevant wiki notes.

3. Follow useful Obsidian [[Internal Links]] when they help answer the question.

4. Read only the wiki files needed to answer accurately.

5. Do NOT use outside knowledge.

6. Do NOT add facts that are not supported by wiki/.

7. If the answer is not available in the wiki, clearly say that the wiki does not contain enough information.

8. Synthesize information across multiple wiki notes when appropriate.

9. Do not modify:
   - raw/
   - wiki/
   - logs/
   - AGENTS.md
   - agent.py
   - wiki_lint.py
   - ingest_wiki.py
   - src/
   - .env
   - PostgreSQL
   - MCP
   - Render
   - deployment files
   - Git history

10. This is a READ-ONLY query.

11. At the end include:

Sources used:
- wiki/exact-file-name.md
- wiki/another-file.md

Use exact file paths rather than display titles.

Return the answer directly.
"""

    # -----------------------------------------
    # 4. GET EXACT AI RESPONSE
    # -----------------------------------------

    result = subprocess.run(
        [CODEX_CMD, "exec", "-"],
        cwd=Path.cwd(),
        input=prompt,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )

    if result.returncode != 0:
        print("Wiki query failed.")

        if result.stderr:
            print(result.stderr)

        return

    ai_response = result.stdout.strip()

    if not ai_response:
        print("No AI response was returned.")
        return

    # -----------------------------------------
    # 5. AUTOMATIC THREAD SAVE
    # -----------------------------------------

    save_thread_message(
        user_name=args.user_name,
        thread_id=thread_id,
        thread_name=thread_name,
        user_prompt=question,
        ai_response=ai_response,
    )

    # -----------------------------------------
    # 6. SHOW RESPONSE
    # -----------------------------------------

    print(ai_response)

    print()
    print(f"Thread ID: {thread_id}")
    print(f"Thread Name: {thread_name}")


if __name__ == "__main__":
    main()