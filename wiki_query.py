from pathlib import Path
import subprocess
import sys

WIKI_DIR = Path("wiki")
AGENTS_FILE = Path("AGENTS.md")

CODEX_CMD = r"C:\Users\Tanvi\AppData\Roaming\npm\codex.cmd"


def main():
    if len(sys.argv) < 2:
        print('Usage:')
        print('python wiki_query.py "Your question here"')
        return

    question = " ".join(sys.argv[1:]).strip()

    if not question:
        print("Question cannot be empty.")
        return

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

    result = subprocess.run(
        [CODEX_CMD, "exec", "-"],
        cwd=Path.cwd(),
        input=prompt,
        text=True
    )

    if result.returncode != 0:
        print()
        print("Wiki query failed.")


if __name__ == "__main__":
    main()