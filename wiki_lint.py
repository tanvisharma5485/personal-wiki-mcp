from pathlib import Path
from difflib import SequenceMatcher
import re

WIKI_DIR = Path("wiki")
INDEX_FILE = WIKI_DIR / "index.md"

REQUIRED_SECTIONS = [
    "## Key Points",
    "## Related Topics",
    "## Sources",
]


def get_notes():
    return sorted(
        [
            p for p in WIKI_DIR.glob("*.md")
            if p.name.lower() != "index.md"
        ],
        key=lambda p: p.name.lower()
    )


def read_note(path):
    return path.read_text(
        encoding="utf-8-sig",
        errors="ignore"
    )


def check_structure(notes):
    problems = []

    for note in notes:
        text = read_note(note)

        missing = []

        if not text.lstrip().startswith("# "):
            missing.append("Title")

        for section in REQUIRED_SECTIONS:
            if section not in text:
                missing.append(section.replace("## ", ""))

        if missing:
            problems.append((note.name, missing))

    return problems


def check_broken_links(notes):
    existing = {
        p.stem.lower()
        for p in notes
    }

    broken = {}

    for note in notes:
        text = read_note(note)

        links = re.findall(
            r"\[\[([^\]|#]+)",
            text
        )

        missing = sorted({
            link.strip()
            for link in links
            if link.strip().lower() not in existing
        })

        if missing:
            broken[note.name] = missing

    return broken


def check_orphans(notes):
    incoming = {
        p.stem.lower(): 0
        for p in notes
    }

    for note in notes:
        text = read_note(note)

        links = re.findall(
            r"\[\[([^\]|#]+)",
            text
        )

        for link in links:
            target = link.strip().lower()

            if (
                target in incoming
                and target != note.stem.lower()
            ):
                incoming[target] += 1

    return sorted(
        note.name
        for note in notes
        if incoming[note.stem.lower()] == 0
    )


def check_index(notes):
    if not INDEX_FILE.exists():
        return (
            [p.stem for p in notes],
            ["index.md is missing"]
        )

    text = read_note(INDEX_FILE)

    index_links = {
        link.strip()
        for link in re.findall(
            r"\[\[([^\]|#]+)",
            text
        )
    }

    existing = {
        p.stem
        for p in notes
    }

    missing_from_index = sorted(
        existing - index_links
    )

    invalid_links = sorted(
        index_links - existing
    )

    return missing_from_index, invalid_links


def normalize_content(text):
    text = re.sub(
        r"\[\[([^\]|#]+)(?:\|[^\]]+)?\]\]",
        r"\1",
        text
    )

    text = re.sub(
        r"#+\s*",
        "",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip().lower()


def check_content_overlap(notes, threshold=0.70):
    contents = {}

    for note in notes:
        contents[note] = normalize_content(
            read_note(note)
        )

    overlaps = []

    for i in range(len(notes)):
        for j in range(i + 1, len(notes)):

            first = notes[i]
            second = notes[j]

            score = SequenceMatcher(
                None,
                contents[first],
                contents[second]
            ).ratio()

            if score >= threshold:
                overlaps.append(
                    (
                        score,
                        first.name,
                        second.name
                    )
                )

    return sorted(
        overlaps,
        reverse=True
    )


def main():
    notes = get_notes()

    print("=" * 60)
    print("PERSONAL WIKI HEALTH CHECK")
    print("=" * 60)

    print()
    print(f"Knowledge notes: {len(notes)}")
    print(
        f"Markdown files including index: "
        f"{len(notes) + (1 if INDEX_FILE.exists() else 0)}"
    )

    structure = check_structure(notes)
    broken = check_broken_links(notes)
    orphans = check_orphans(notes)

    missing_index, invalid_index = (
        check_index(notes)
    )

    overlaps = check_content_overlap(notes)

    print()
    print("STRUCTURE")
    print("-" * 60)

    if structure:
        for filename, missing in structure:
            print(
                f"{filename}: missing "
                f"{', '.join(missing)}"
            )
    else:
        print("OK - No structure problems.")

    print()
    print("BROKEN LINKS")
    print("-" * 60)

    if broken:
        for filename, links in broken.items():
            print(filename)

            for link in links:
                print(f"  -> {link}")
    else:
        print("OK - No broken internal links.")

    print()
    print("ORPHAN PAGES")
    print("-" * 60)

    if orphans:
        for filename in orphans:
            print(f"  -> {filename}")
    else:
        print("OK - No orphan knowledge pages.")

    print()
    print("INDEX")
    print("-" * 60)

    if not missing_index and not invalid_index:
        print("OK - Index is complete.")
    else:
        for item in missing_index:
            print(
                f"Missing from index: {item}"
            )

        for item in invalid_index:
            print(
                f"Invalid index link: {item}"
            )

    print()
    print("POTENTIAL CONTENT OVERLAP")
    print("-" * 60)

    if overlaps:
        for score, first, second in overlaps:
            print(
                f"{score:.3f} | "
                f"{first} | {second}"
            )
    else:
        print(
            "OK - No note pairs exceeded "
            "the similarity threshold."
        )

    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)

    print(
        f"Structure problems: {len(structure)}"
    )
    print(
        f"Pages with broken links: {len(broken)}"
    )
    print(
        f"Orphan pages: {len(orphans)}"
    )
    print(
        f"Pages missing from index: "
        f"{len(missing_index)}"
    )
    print(
        f"Invalid index links: "
        f"{len(invalid_index)}"
    )
    print(
        f"Potential overlap pairs: "
        f"{len(overlaps)}"
    )

    print()
    print(
        "NOTE: Content overlap is a warning, "
        "not automatic proof of duplication."
    )


if __name__ == "__main__":
    main()