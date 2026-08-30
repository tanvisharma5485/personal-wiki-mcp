from pathlib import Path
import subprocess
import hashlib
import json

RAW_DIR = Path("raw")
WIKI_DIR = Path("wiki")
LOG_DIR = Path("logs")

AGENTS_FILE = Path("AGENTS.md")
STATE_FILE = LOG_DIR / "ingestion_state.json"

CODEX_CMD = r"C:\Users\Tanvi\AppData\Roaming\npm\codex.cmd"

WIKI_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)


# --------------------------------------------------
# HASHING
# --------------------------------------------------

def calculate_hash(file_path):
    sha256 = hashlib.sha256()

    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)

    return sha256.hexdigest()


# --------------------------------------------------
# INGESTION STATE
# --------------------------------------------------

def load_state():
    if not STATE_FILE.exists():
        return {}

    try:
        text = STATE_FILE.read_text(
            encoding="utf-8-sig"
        ).strip()

        if not text:
            return {}

        data = json.loads(text)

        if not isinstance(data, dict):
            return {}

        return data

    except (json.JSONDecodeError, OSError):
        print(
            "Warning: ingestion_state.json could not be read."
        )
        print(
            "No files will be marked as previously processed."
        )
        return {}


def save_state(state):
    temp_file = STATE_FILE.with_suffix(".tmp")

    temp_file.write_text(
        json.dumps(
            state,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    temp_file.replace(STATE_FILE)


# --------------------------------------------------
# SOURCE DISCOVERY
# --------------------------------------------------

def get_top_level_raw_files():
    return sorted(
        RAW_DIR.glob("*.md"),
        key=lambda p: p.name.lower()
    )


def find_changed_sources(raw_files, state):
    changed = []
    unchanged = []

    current_hashes = {}

    for raw_file in raw_files:
        file_hash = calculate_hash(raw_file)

        relative_name = raw_file.as_posix()

        current_hashes[relative_name] = file_hash

        if state.get(relative_name) == file_hash:
            unchanged.append(raw_file)
        else:
            changed.append(raw_file)

    return changed, unchanged, current_hashes


# --------------------------------------------------
# CODEX INGESTION
# --------------------------------------------------

def run_codex(changed_files):
    source_names = "\n".join(
        f"- {file_path.as_posix()}"
        for file_path in changed_files
    )

    prompt = f"""
Read AGENTS.md first and follow it carefully.

You are maintaining the Personal Wiki.

PROCESS ONLY THESE NEW OR CHANGED RAW SOURCES:

{source_names}

IMPORTANT INGESTION BEHAVIOR:

1. Read each listed raw source completely.

2. Treat raw/ as permanent source material.
   NEVER modify, rename, move, or delete raw files.

3. Inspect the existing wiki before deciding where
   information belongs.

4. Do NOT assume:
       one raw file = one wiki file

5. A single raw source may contain information relevant
   to multiple existing wiki concept pages.

6. When information belongs to an existing concept:
   - update that existing wiki page
   - preserve all useful existing knowledge
   - add only important missing information
   - do not replace a richer note with a shorter summary
   - do not delete valid information merely because the
     current raw source does not mention it
   - avoid unnecessary rewriting

7. When the source introduces a genuinely new concept
   that deserves its own knowledge page:
   - create a new Markdown note in wiki/
   - follow the structure required by AGENTS.md

8. Before creating a new page, check for:
   - same concept
   - equivalent title
   - singular/plural variants
   - abbreviations
   - synonyms
   - closely equivalent existing notes

   Prefer updating an existing note instead of creating
   duplicate knowledge pages.

9. Use ONLY information grounded in the listed raw
   sources when adding new factual knowledge.

   Do not add outside factual knowledge.

10. Existing valid wiki knowledge may be preserved even
    when it came from earlier source files.

11. Use meaningful Obsidian [[Internal Links]].

12. Prefer links to existing wiki concepts.

13. Do not intentionally create broken links.

14. Add appropriate source attribution to every wiki
    page that receives information from a source.

15. Rebuild or update wiki/index.md if new pages are
    created or existing navigation requires updating.

16. Update logs/ingestion_log.md with a concise record
    of what was processed and changed.

17. Do NOT modify:
    - agent.py
    - ingest_wiki.py
    - wiki_lint.py
    - AGENTS.md
    - .env
    - requirements.txt
    - src/
    - PostgreSQL
    - MCP configuration
    - Render configuration
    - deployment configuration
    - Git history

18. Do NOT run git commit or git push.

19. Work only on the wiki maintenance required for the
    listed sources.

20. At the end report:
    - raw sources processed
    - wiki pages created
    - wiki pages updated
    - wiki pages left unchanged
    - duplicate pages avoided
    - failures, if any
    - whether raw files were modified
    - final number of Markdown files in wiki/

Do not merely summarize what you would do.
Perform the wiki maintenance.
"""

    print()
    print("Starting Codex ingestion...")
    print()

    result = subprocess.run(
        [CODEX_CMD, "exec", "-"],
        cwd=Path.cwd(),
        input=prompt,
        text=True
    )

    return result.returncode


# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():
    raw_files = get_top_level_raw_files()

    print(
        f"Top-level raw Markdown files: {len(raw_files)}"
    )

    if not raw_files:
        print("No top-level raw Markdown files found.")
        return

    state = load_state()

    changed, unchanged, current_hashes = (
        find_changed_sources(
            raw_files,
            state
        )
    )

    print(f"New or changed sources: {len(changed)}")
    print(f"Unchanged sources: {len(unchanged)}")

    if not changed:
        print()
        print("Nothing to process.")
        print("All raw sources are unchanged.")
        return

    print()
    print("Sources that will be processed:")

    for file_path in changed:
        print(f"  - {file_path.name}")

    print()
    print(
        "Unchanged sources will NOT be sent to Codex."
    )

    return_code = run_codex(changed)

    if return_code != 0:
        print()
        print("Codex ingestion failed.")
        print(
            "ingestion_state.json was NOT updated."
        )
        return

    # --------------------------------------------------
    # IMPORTANT:
    # Only mark successfully processed sources as current.
    # --------------------------------------------------

    for file_path in changed:
        relative_name = file_path.as_posix()

        state[relative_name] = current_hashes[
            relative_name
        ]

    save_state(state)

    print()
    print("Codex ingestion completed successfully.")
    print(
        "Processed source hashes saved to "
        "logs/ingestion_state.json."
    )


if __name__ == "__main__":
    main()